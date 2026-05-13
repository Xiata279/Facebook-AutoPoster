#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Chrome Auto Poster v2
================================
- Kết nối vào Chrome đang chạy (đã đăng nhập Facebook)
- Đọc danh sách trang từ .env (FB_PAGES=slug1,slug2,...)
- Tự điều hướng đến từng trang và đăng bài
- Không cần Page ID API hay Access Token

Cách dùng:
  python chrome_poster.py                      # Đăng lên tất cả trang trong .env
  python chrome_poster.py --pages mypageslug   # Chỉ đăng lên trang chỉ định
  python chrome_poster.py --dry-run            # Thử nghiệm (không bấm Đăng)

@author Xiata
"""

import os, sys, json, time, argparse, socket
from pathlib import Path
from datetime import datetime

# Fix UnicodeEncodeError trên Windows console (cp1252 → utf-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
                                             ElementNotInteractableException)
except ImportError:
    print("❌ Chưa cài selenium! Chạy: pip install selenium webdriver-manager")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

BASE       = Path(__file__).parent
OUTPUT_DIR = BASE / "output"
LOG_DIR    = BASE / "logs"
LOG_FILE   = LOG_DIR / "chrome_poster.log"
DEBUG_PORT = 9222
WAIT_SEC   = 15

# ── Màu console ──
def _c(code, s): return f"\033[{code}m{s}\033[0m"
GREEN  = lambda s: _c("32", s)
YELLOW = lambda s: _c("33", s)
RED    = lambda s: _c("31", s)
CYAN   = lambda s: _c("36", s)
BOLD   = lambda s: _c("1",  s)


def log(msg: str, level="info"):
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    col   = {"info": CYAN, "ok": GREEN, "warn": YELLOW, "error": RED}.get(level, str)
    try:
        print(col(entry))
    except UnicodeEncodeError:
        print(col(entry).encode("ascii", errors="replace").decode("ascii"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


# ════════════════════════════════════════════════════
#  ĐỌC CẤU HÌNH
# ════════════════════════════════════════════════════

def read_env() -> dict:
    env = {}
    f = BASE / ".env"
    if f.exists():
        for line in f.read_text("utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_pages(env: dict, override: list = None) -> list:
    """
    Trả về danh sách page slug/URL để đăng.
    Ưu tiên: --pages argument > FB_PAGES trong .env
    FB_PAGES=slug1,slug2,https://facebook.com/slug3
    """
    if override:
        return [p.strip() for p in override if p.strip()]

    raw = env.get("FB_PAGES", env.get("FB_PAGE_ID", ""))
    if not raw or "THAY" in raw:
        return []

    pages = []
    for p in raw.split(","):
        p = p.strip()
        if not p:
            continue
        # Chuẩn hoá thành slug (bỏ https://www.facebook.com/ nếu có)
        p = p.replace("https://www.facebook.com/", "").replace("https://facebook.com/", "").rstrip("/")
        pages.append(p)
    return pages


def get_post_content() -> str | None:
    """Lấy nội dung bài mới nhất từ output/latest_post.json hoặc .txt"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    jp = OUTPUT_DIR / "latest_post.json"
    if jp.exists():
        try:
            d = json.loads(jp.read_text("utf-8"))
            c = d.get("post_content") or d.get("content", "")
            if c.strip():
                return c.strip()
        except: pass

    # Fallback txt
    txts = sorted(OUTPUT_DIR.glob("summary_post_*.txt"), key=os.path.getmtime, reverse=True)
    if txts:
        return txts[0].read_text("utf-8").strip()
    return None


# ════════════════════════════════════════════════════
#  KẾT NỐI CHROME
# ════════════════════════════════════════════════════

def check_chrome_port() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", DEBUG_PORT), timeout=1)
        s.close(); return True
    except: return False


def connect_chrome() -> webdriver.Chrome:
    if not check_chrome_port():
        log(f"❌ Không thể kết nối Chrome trên cổng {DEBUG_PORT}!", "error")
        log("   → Chạy mo_chrome.bat trước, đăng nhập Facebook, rồi thử lại.", "warn")
        sys.exit(1)

    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    opts.add_argument("--log-level=3")

    try:
        if HAS_WDM:
            service = Service(ChromeDriverManager().install())
            driver  = webdriver.Chrome(service=service, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)

        log(f"✅ Kết nối Chrome thành công (tab: {driver.title[:50]})", "ok")
        return driver
    except Exception as e:
        log(f"❌ Lỗi kết nối Chrome: {e}", "error")
        sys.exit(1)


# ════════════════════════════════════════════════════
#  LOGIC ĐĂNG BÀI
# ════════════════════════════════════════════════════

class FacebookPoster:
    def __init__(self, driver: webdriver.Chrome):
        self.driver  = driver
        self.wait    = WebDriverWait(driver, WAIT_SEC)
        self.wait_s  = WebDriverWait(driver, 5)   # Short wait

    # ── 1. Vào trang ──
    def goto_page(self, slug: str):
        url = f"https://www.facebook.com/{slug}"
        log(f"🌐 Điều hướng → {url}")
        self.driver.get(url)
        time.sleep(3)

        # Kiểm tra đã đăng nhập chưa
        if "login" in self.driver.current_url.lower():
            log("❌ Facebook yêu cầu đăng nhập! Hãy đăng nhập trong Chrome rồi thử lại.", "error")
            return False

        # Kiểm tra page có tồn tại không
        if "Page Not Found" in self.driver.title or "Trang không tìm thấy" in self.driver.title:
            log(f"⚠️ Không tìm thấy trang: {slug}", "warn")
            return False

        log(f"✅ Đang ở: {self.driver.title[:60]}", "ok")
        return True

    # ── 2. Mở ô đăng bài ──
    def open_composer(self) -> bool:
        log("🔍 Tìm ô soạn bài...")

        # Các selector nút "Tạo bài viết" / "Create a post"
        xpaths = [
            "//div[@role='button'][.//span[contains(text(),'Tạo bài viết')]]",
            "//div[@role='button'][.//span[contains(text(),'Create a post')]]",
            "//div[@role='button'][.//span[contains(text(),\"What's on your mind\")]]",
            "//div[@role='button'][.//span[contains(text(),'Bạn đang nghĩ gì')]]",
            "//div[contains(@aria-label,'Tạo bài viết')]",
            "//div[contains(@aria-label,'Create a post')]",
            # Fallback: tìm bất kỳ div button có từ "bài"
            "//div[@role='button' and contains(.,'bài viết')]",
            "//div[@role='button' and contains(.,'post')]",
        ]

        for xp in xpaths:
            try:
                el = self.wait_s.until(EC.element_to_be_clickable((By.XPATH, xp)))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.5)
                el.click()
                time.sleep(2)
                log("✅ Đã mở ô soạn bài", "ok")
                return True
            except: continue

        log("⚠️ Không tìm thấy nút soạn bài tự động", "warn")
        return False

    # ── 3. Nhập nội dung ──
    def type_content(self, content: str) -> bool:
        log(f"⌨️  Đang nhập nội dung ({len(content)} ký tự)...")

        text_xpaths = [
            "//div[@role='textbox' and @contenteditable='true']",
            "//div[@contenteditable='true' and @aria-label]",
            "//div[@contenteditable='true']",
        ]

        textbox = None
        for xp in text_xpaths:
            try:
                textbox = self.wait.until(EC.presence_of_element_located((By.XPATH, xp)))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textbox)
                textbox.click()
                time.sleep(0.8)
                break
            except: continue

        if not textbox:
            log("❌ Không tìm thấy ô nhập văn bản", "error")
            return False

        # Paste qua clipboard API (hỗ trợ emoji tốt nhất)
        try:
            self.driver.execute_script("""
                var el = arguments[0];
                el.focus();
                var data = new DataTransfer();
                data.setData('text/plain', arguments[1]);
                el.dispatchEvent(new ClipboardEvent('paste', {
                    clipboardData: data, bubbles: true, cancelable: true
                }));
            """, textbox, content)
            time.sleep(1.2)

            # Kiểm tra đã nhập được chưa
            actual = textbox.get_attribute("innerText") or textbox.text or ""
            if len(actual.strip()) >= 10:
                log("✅ Nội dung đã được nhập (paste method)", "ok")
                return True
        except: pass

        # Fallback: pyperclip hoặc send_keys từng dòng
        try:
            import pyperclip
            pyperclip.copy(content)
            textbox.send_keys(Keys.CONTROL, "a")
            textbox.send_keys(Keys.CONTROL, "v")
            time.sleep(1)
            log("✅ Nội dung đã được nhập (pyperclip method)", "ok")
            return True
        except: pass

        # Last resort: gõ trực tiếp (chậm hơn, emoji có thể bị lỗi)
        log("⌨️  Gõ trực tiếp từng đoạn...", "warn")
        for chunk in [content[i:i+200] for i in range(0, len(content), 200)]:
            textbox.send_keys(chunk)
            time.sleep(0.3)
        log("✅ Đã gõ xong", "ok")
        return True

    # ── 4. Bấm Đăng ──
    def submit(self, dry_run: bool = False) -> bool:
        if dry_run:
            log("🧪 [DRY RUN] Bỏ qua bấm Đăng", "warn")
            return True

        log("📤 Tìm nút Đăng...")
        time.sleep(1)

        submit_xpaths = [
            "//div[@aria-label='Đăng'][@role='button']",
            "//div[@aria-label='Post'][@role='button']",
            "//div[@role='button'][.//span[text()='Đăng']]",
            "//div[@role='button'][.//span[text()='Post']]",
            "//span[text()='Đăng']/ancestor::div[@role='button']",
            "//span[text()='Post']/ancestor::div[@role='button']",
        ]

        for xp in submit_xpaths:
            try:
                btn = self.wait_s.until(EC.element_to_be_clickable((By.XPATH, xp)))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.3)
                btn.click()
                log("✅ Đã bấm Đăng!", "ok")
                time.sleep(4)
                return True
            except: continue

        # Thông báo thủ công
        log("⚠️  Không tìm thấy nút Đăng. Vui lòng bấm thủ công trong 30 giây...", "warn")
        time.sleep(30)
        return True

    # ── POST một trang ──
    def post_to_page(self, slug: str, content: str, dry_run: bool = False) -> bool:
        log(f"\n{'═'*50}", "info")
        log(f"📌 ĐANG XỬ LÝ TRANG: {slug}", "info")
        log(f"{'═'*50}", "info")

        if not self.goto_page(slug):
            return False
        if not self.open_composer():
            return False
        if not self.type_content(content):
            return False
        return self.submit(dry_run)


# ════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Facebook Chrome Auto Poster v2")
    parser.add_argument("--pages",   nargs="+", help="Slug/URL các trang (ghi đè .env)")
    parser.add_argument("--content", default="",  help="Nội dung bài đăng")
    parser.add_argument("--dry-run", action="store_true", help="Thử nghiệm không bấm Đăng")
    args = parser.parse_args()

    log(BOLD("════════════ FACEBOOK CHROME AUTO POSTER v2 ════════════"), "info")

    env   = read_env()
    pages = get_pages(env, args.pages)

    if not pages:
        log("❌ Chưa có trang nào để đăng!", "error")
        log("   → Thêm FB_PAGES=trang1,trang2 vào file .env", "warn")
        log("   → Hoặc dùng: python chrome_poster.py --pages tentrang", "warn")
        sys.exit(1)

    content = args.content.strip() or get_post_content()
    if not content:
        log("❌ Không có nội dung bài đăng!", "error")
        log("   → Chạy PHP trước: php run_football_post.php", "warn")
        sys.exit(1)

    log(f"📄 Nội dung ({len(content)} ký tự): {content[:100]}...", "info")
    log(f"🎯 Trang đăng: {', '.join(pages)}", "info")

    # Kết nối Chrome
    driver = connect_chrome()
    poster = FacebookPoster(driver)

    # Đăng lên từng trang
    results = {}
    for i, slug in enumerate(pages):
        if i > 0:
            log(f"\n⏳ Chờ 15 giây trước trang tiếp theo...", "info")
            time.sleep(15)

        ok = poster.post_to_page(slug, content, args.dry_run)
        results[slug] = ok

    # Tổng kết
    log(f"\n{'═'*50}", "info")
    log("📊 KẾT QUẢ:", "info")
    for slug, ok in results.items():
        status = GREEN("✅ Thành công") if ok else RED("❌ Thất bại")
        log(f"   {slug}: {status}", "info")

    success_count = sum(1 for v in results.values() if v)
    log(f"\n🎉 Đăng thành công {success_count}/{len(pages)} trang!", "ok" if success_count else "error")

    if success_count < len(pages):
        sys.exit(1)


if __name__ == "__main__":
    main()
