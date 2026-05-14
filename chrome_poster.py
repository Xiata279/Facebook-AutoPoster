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

import os, sys, json, time, argparse, socket, random
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
WAIT_SEC   = 10

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
        self.composer_dialog = None

    def _visible_dialog(self, keywords=None):
        try:
            dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
            visible = [d for d in dialogs if d.is_displayed()]
            if not visible:
                return None

            if keywords:
                lowered = [k.lower() for k in keywords if k]
                for dialog in reversed(visible):
                    try:
                        text = (dialog.text or "").lower()
                        aria = (dialog.get_attribute("aria-label") or "").lower()
                        if any(k in text or k in aria for k in lowered):
                            return dialog
                    except:
                        continue

            return visible[-1]
        except:
            return None

    def _composer_dialog(self):
        try:
            dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
            visible = [d for d in dialogs if d.is_displayed()]
            matches = []
            for candidate in reversed(visible):
                try:
                    text = (candidate.text or "").lower()
                    aria = (candidate.get_attribute("aria-label") or "").lower()
                    has_keyword = any(k in text or k in aria for k in [
                        "tạo bài viết",
                        "create post",
                        "what's on your mind",
                        "bạn đang nghĩ gì",
                    ])
                    textboxes = candidate.find_elements(
                        By.XPATH,
                        ".//div[@role='textbox' and @contenteditable='true'] | .//*[@contenteditable='true']"
                    )
                    if has_keyword or textboxes:
                        area = self.driver.execute_script("""
                            const r = arguments[0].getBoundingClientRect();
                            return r.width * r.height;
                        """, candidate)
                        matches.append((bool(textboxes), area, candidate))
                except:
                    continue

            if matches:
                matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
                return matches[0][2]
        except:
            pass
        return None

    def _click_visible_button_by_label(self, labels) -> bool:
        try:
            return bool(self.driver.execute_script("""
                const labels = arguments[0].map(s => String(s).toLowerCase());
                const nodes = Array.from(document.querySelectorAll(
                    'div[role="button"], button, a[role="button"]'
                ));

                function visible(el) {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0 &&
                           style.visibility !== 'hidden' &&
                           style.display !== 'none';
                }

                for (const el of nodes) {
                    if (!visible(el)) continue;
                    const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                    const haystack = `${text} ${aria}`;
                    if (labels.some(label => label && haystack.includes(label))) {
                        el.scrollIntoView({block: 'center', inline: 'center'});
                        el.click();
                        return true;
                    }
                }
                return false;
            """, labels))
        except:
            return False

    def _click_dialog_button_by_label(self, labels) -> bool:
        try:
            dialog = self.composer_dialog or self._composer_dialog()
            if not dialog:
                return False
            return bool(self.driver.execute_script("""
                const root = arguments[0];
                const labels = arguments[1].map(s => String(s).toLowerCase());
                const nodes = Array.from(root.querySelectorAll(
                    'div[role="button"], button, a[role="button"]'
                ));

                function visible(el) {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0 &&
                           style.visibility !== 'hidden' &&
                           style.display !== 'none';
                }

                function enabled(el) {
                    const disabled = el.getAttribute('aria-disabled') === 'true' ||
                                     el.disabled === true;
                    const style = window.getComputedStyle(el);
                    return !disabled && style.pointerEvents !== 'none' &&
                           Number(style.opacity || '1') > 0.35;
                }

                for (const el of nodes.reverse()) {
                    if (!visible(el) || !enabled(el)) continue;
                    const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                    const haystack = `${text} ${aria}`;
                    if (labels.some(label => label && haystack.includes(label))) {
                        el.scrollIntoView({block: 'center', inline: 'center'});
                        el.click();
                        return true;
                    }
                }
                return false;
            """, dialog, labels))
        except:
            return False

    # ── 1. Vào trang ──
    def goto_page(self, slug: str):
        url = f"https://www.facebook.com/{slug}"
        log(f"🌐 Điều hướng → {url}")
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 6).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except:
            pass
        time.sleep(1.0)

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
        time.sleep(0.7)

        js_button_groups = [
            ["Bạn đang nghĩ gì", "What's on your mind", "Tạo bài viết", "Create a post", "Create post"],
            ["Ảnh/video", "Photo/video", "Photo or video"],
        ]
        for labels in js_button_groups:
            if self._click_visible_button_by_label(labels):
                time.sleep(random.uniform(0.8, 1.2))
                self.composer_dialog = None
                for _ in range(8):
                    self.composer_dialog = self._composer_dialog()
                    if self.composer_dialog:
                        log("✅ Đã mở ô soạn bài", "ok")
                        return True
                    time.sleep(0.25)

        # Mở rộng selectors cho FB 2024-2025 (cả tiếng Việt & tiếng Anh)
        xpaths = [
            # aria-label bền vững nhất
            "//div[@aria-label='Tạo bài viết']",
            "//div[@aria-label='Create a post']",
            "//div[@aria-label='Create post']",
            # span text chính xác
            "//div[@role='button'][.//span[text()='Tạo bài viết']]",
            "//div[@role='button'][.//span[text()='Create a post']]",
            "//div[@role='button'][.//span[contains(.,\"What's on your mind\")]]",
            "//div[@role='button'][.//span[contains(.,'Bạn đang nghĩ gì')]]",
            # contains linh hoạt hơn
            "//div[@role='button'][.//span[contains(text(),'Tạo bài')]]",
            "//div[@role='button'][.//span[contains(text(),'Create')]]",
            "//div[@role='button'][.//span[contains(.,\"What's\")]]",
            "//div[@role='button'][.//span[contains(text(),'nghĩ gì')]]",
            # fallback chỉ bắt nút tạo bài, tránh ô bình luận
            "//div[@role='button' and contains(.,'Bạn đang nghĩ gì')]",
            "//div[@role='button' and contains(.,'Tạo bài viết')]",
            "//div[@role='button' and contains(.,'Create a post')]",
            "//div[@role='button' and @aria-label='Ảnh/video']",
            "//div[@role='button' and @aria-label='Photo/video']",
        ]

        for xp in xpaths:
            try:
                el = WebDriverWait(self.driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(random.uniform(0.3, 0.7))
                try:
                    el.click()
                except:
                    self.driver.execute_script("arguments[0].click();", el)
                time.sleep(random.uniform(0.8, 1.2))
                self.composer_dialog = None
                for _ in range(6):
                    self.composer_dialog = self._composer_dialog()
                    if self.composer_dialog:
                        break
                    time.sleep(0.25)
                if self.composer_dialog:
                    log("✅ Đã mở ô soạn bài", "ok")
                    return True

                try:
                    is_textbox = (el.get_attribute("role") == "textbox" or
                                  el.get_attribute("contenteditable") == "true")
                    if is_textbox:
                        log("✅ Đã mở ô nhập bài viết", "ok")
                        return True
                except:
                    pass
            except:
                continue

        log("⚠️ Không tìm thấy nút soạn bài tự động", "warn")
        return False

    # ── 3. Nhập nội dung ──
    def type_content(self, content: str) -> bool:
        log(f"⌨️  Đang nhập nội dung ({len(content)} ký tự)...")

        dialog = self.composer_dialog or self._composer_dialog()
        text_xpaths = [
            ".//div[@role='textbox' and @contenteditable='true']",
            ".//div[@contenteditable='true' and @aria-label]",
            ".//div[@contenteditable='true']",
        ]

        textbox = None
        for xp in text_xpaths:
            try:
                scope = dialog if dialog else self.driver
                textbox = WebDriverWait(self.driver, 5).until(
                    lambda d: scope.find_element(By.XPATH, xp)
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textbox)
                textbox.click()
                time.sleep(0.35)
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
            time.sleep(0.7)

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
            time.sleep(0.5)
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
        time.sleep(random.uniform(0.5, 0.8))

        for labels in (["Đăng", "Post", "Share now"], ["Tiếp", "Next", "Continue"]):
            if self._click_dialog_button_by_label(labels):
                label = labels[0]
                log(f"✅ Đã bấm {label}", "ok")
                time.sleep(random.uniform(1.0, 1.5))
                if label in ("Đăng", "Post", "Share now"):
                    return True
                break

        # Danh sách XPath mở rộng cho FB 2024-2025
        submit_xpaths = [
            # Chỉ trong composer dialog
            "//div[@role='dialog']//div[@aria-label='Đăng'][@role='button']",
            "//div[@role='dialog']//div[@aria-label='Post'][@role='button']",
            "//div[@role='dialog']//div[@aria-label='Share now'][@role='button']",
            "//div[@role='dialog']//div[@aria-label='Tiếp'][@role='button']",
            "//div[@role='dialog']//div[@aria-label='Next'][@role='button']",
            "//div[@role='dialog']//button[@aria-label='Đăng']",
            "//div[@role='dialog']//button[@aria-label='Post']",
            "//div[@role='dialog']//button[@aria-label='Tiếp']",
            "//div[@role='dialog']//button[@aria-label='Next']",
            "//div[@role='dialog']//button[text()='Đăng']",
            "//div[@role='dialog']//button[text()='Post']",
            "//div[@role='dialog']//button[text()='Tiếp']",
            "//div[@role='dialog']//button[text()='Next']",
            # aria-label chính xác (tiếng Việt + tiếng Anh)
            "//div[@aria-label='Đăng'][@role='button']",
            "//div[@aria-label='Post'][@role='button']",
            "//div[@aria-label='Share now'][@role='button']",
            "//div[@aria-label='Tiếp'][@role='button']",
            "//div[@aria-label='Next'][@role='button']",
            # button tag
            "//button[@aria-label='Đăng']",
            "//button[@aria-label='Post']",
            "//button[@aria-label='Tiếp']",
            "//button[@aria-label='Next']",
            "//button[text()='Đăng']",
            "//button[text()='Post']",
            "//button[text()='Tiếp']",
            "//button[text()='Next']",
            # span text chính xác bên trong div/button
            "//div[@role='button'][.//span[text()='Đăng']]",
            "//div[@role='button'][.//span[text()='Post']]",
            "//div[@role='button'][.//span[text()='Tiếp']]",
            "//div[@role='button'][.//span[text()='Next']]",
            "//div[@role='button'][./span[text()='Đăng']]",
            # ancestor
            "//span[text()='Đăng']/ancestor::div[@role='button'][1]",
            "//span[text()='Post']/ancestor::div[@role='button'][1]",
            "//span[text()='Tiếp']/ancestor::div[@role='button'][1]",
            "//span[text()='Next']/ancestor::div[@role='button'][1]",
            "//span[text()='Đăng']/ancestor::button[1]",
            # contains linh hoạt
            "//div[@role='button'][contains(@aria-label,'Đăng')]",
            "//div[@role='button'][contains(.//span/text(),'Đăng')]",
        ]

        for xp in submit_xpaths:
            try:
                btn = WebDriverWait(self.driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(random.uniform(0.3, 0.6))
                try:
                    btn.click()
                except:
                    # JS click fallback nếu click thường bị chặn
                    self.driver.execute_script("arguments[0].click();", btn)
                btn_text = ((btn.get_attribute("aria-label") or btn.text or "")).strip()
                if btn_text in ("Tiếp", "Next", "Continue"):
                    log(f"✅ Đã bấm {btn_text}, chờ màn hình xác nhận...", "ok")
                    time.sleep(random.uniform(1.0, 1.5))
                    if self._click_dialog_button_by_label(["Đăng", "Post", "Share now"]):
                        log("✅ Đã bấm Đăng!", "ok")
                        time.sleep(2)
                        return True
                    continue
                log("✅ Đã bấm Đăng!", "ok")
                time.sleep(2)
                # Xác nhận bài đã đăng: kiểm tra dialog đã biến mất
                try:
                    WebDriverWait(self.driver, 6).until(
                        EC.invisibility_of_element_located(
                            (By.XPATH, "//div[@role='dialog']")))
                    log("✅ Xác nhận: Dialog đã đóng — bài đã đăng thành công!", "ok")
                except:
                    log("⚠️ Dialog có thể vẫn mở — kiểm tra thủ công trên trình duyệt", "warn")
                return True
            except:
                continue

        # JS bruteforce: tìm tất cả button khả năng là nút Đăng
        log("🔄 Thử JS bruteforce tìm nút Đăng...", "warn")
        try:
            found = self.driver.execute_script("""
                var texts = ['Đăng', 'Post', 'Share now'];
                var allBtns = document.querySelectorAll(
                    'div[role=\"button\"], button');
                for (var b of allBtns) {
                    var t = (b.innerText || b.textContent || '').trim();
                    if (texts.includes(t) && b.offsetParent !== null) {
                        b.click();
                        return true;
                    }
                }
                return false;
            """)
            if found:
                log("✅ JS bruteforce click thành công!", "ok")
                time.sleep(2)
                return True
        except Exception as e:
            log(f"⚠️ JS bruteforce lỗi: {e}", "warn")

        # Thông báo thủ công
        log("⚠️  Không tìm thấy nút Đăng. Vui lòng bấm thủ công trong 12 giây...", "warn")
        time.sleep(12)
        return True

    # ── 5. Chuyển sang chế độ Fanpage ──
    def switch_to_page_mode(self) -> bool:
        """Click 'Chuyển ngay' để đăng bài với tư cách Fanpage, không phải cá nhân."""
        if self._click_visible_button_by_label(["Chuyển ngay", "Switch now"]):
            time.sleep(random.uniform(0.9, 1.4))
            log("✅ Đã chuyển sang chế độ quản lý Trang (Fanpage)", "ok")
            return True
        log("ℹ Đã ở chế độ trang hoặc không cần chuyển", "info")
        return True

    # ── 6. Upload ảnh vào composer ──
    def upload_image(self, image_path) -> bool:
        """Đính kèm ảnh vào bài viết qua file input hoặc nút ảnh."""
        image_paths = image_path if isinstance(image_path, list) else [image_path]
        image_paths = [p for p in image_paths if p and os.path.exists(p)]
        if not image_paths:
            return False

        upload_value = "\n".join(image_paths)
        log(f">> Dinh kem {len(image_paths)} anh: {', '.join(os.path.basename(p) for p in image_paths)}", "info")
        dialog = self.composer_dialog or self._composer_dialog()

        # Cách 1: Tìm input[type=file] sẵn trong DOM
        try:
            if dialog:
                inputs = dialog.find_elements(By.XPATH, ".//input[@type='file']")
            else:
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            for fi in inputs:
                try:
                    fi.send_keys(upload_value)
                    time.sleep(1.0)
                    log("✅ Upload ảnh thành công (direct file input)", "ok")
                    return True
                except:
                    continue
        except:
            pass

        # Cách 2: Click nút ảnh/video trước, rồi tìm input
        photo_xpaths = [
            "//div[@aria-label='Anh/video']",
            "//div[@aria-label='Photo/video']",
            "//div[@aria-label='Photo or video']",
            "//div[@aria-label='Ảnh/video']",
            "//div[@aria-label='Them anh hoac video']",
            "//div[@aria-label='Thêm ảnh hoặc video']",
            "//div[@aria-label='Add photos or videos']",
            "//div[contains(@aria-label,'photo')]",
            "//div[contains(@aria-label,'anh')]",
        ]
        for xp in photo_xpaths:
            try:
                scope = dialog if dialog else self.driver
                btn = WebDriverWait(self.driver, 3).until(
                    lambda d: scope.find_element(By.XPATH, xp))
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.8)
                # Tìm lại input sau khi click
                if dialog:
                    inputs = dialog.find_elements(By.XPATH, ".//input[@type='file']")
                else:
                    inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                for fi in inputs:
                    try:
                        fi.send_keys(upload_value)
                        time.sleep(1.0)
                        log("✅ Upload ảnh thành công (click photo btn)", "ok")
                        return True
                    except:
                        continue
            except:
                continue

        log("⚠ Không thể upload ảnh tự động — đăng text only", "warn")
        return False

    # ── POST một trang ──
    def post_to_page(self, slug: str, content: str,
                     dry_run: bool = False, image_path=None) -> bool:
        log("=" * 50, "info")
        log(f">> DANG XU LY TRANG: {slug}", "info")
        log("=" * 50, "info")

        if not self.goto_page(slug):
            return False

        # QUAN TRỌNG: Chuyển sang chế độ Fanpage trước khi đăng
        self.switch_to_page_mode()

        if not self.open_composer():
            return False

        if not self.type_content(content):
            return False

        # Upload ảnh sau khi nhập nội dung để Facebook giữ đúng composer hiện tại
        if image_path:
            self.upload_image(image_path)
            time.sleep(random.uniform(0.5, 0.8))

        return self.submit(dry_run)


# ── Tìm ảnh mới nhất trong output/ hoặc images/ ──
def get_images_to_post() -> list:
    """Tìm file ảnh mới nhất để đính kèm (trong vòng 2 giờ gần nhất)."""
    jp = OUTPUT_DIR / "latest_post.json"
    if jp.exists():
        try:
            d = json.loads(jp.read_text("utf-8"))
            image_paths = [p for p in d.get("image_paths", []) if p and os.path.exists(p)]
            if image_paths:
                return image_paths
            image_path = d.get("image_path") or ""
            if image_path and os.path.exists(image_path):
                return [image_path]
        except:
            pass

    dirs = [OUTPUT_DIR, BASE / "images"]
    all_imgs = []
    for d in dirs:
        if d.exists():
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                all_imgs.extend(d.glob(ext))
    if not all_imgs:
        return []
    latest = max(all_imgs, key=lambda f: f.stat().st_mtime)
    age_hours = (time.time() - latest.stat().st_mtime) / 3600
    if age_hours > 2:
        return []
    return [str(latest)]


def get_image_to_post() -> str:
    images = get_images_to_post()
    return images[0] if images else None


def main():
    parser = argparse.ArgumentParser(description="Facebook Chrome Auto Poster v2")
    parser.add_argument("--pages",   nargs="+", help="Slug/URL các trang (ghi đè .env)")
    parser.add_argument("--content", default="",  help="Nội dung bài đăng")
    parser.add_argument("--dry-run", action="store_true", help="Thử nghiệm không bấm Đăng")
    parser.add_argument("--image",   default="",  help="Đường dẫn ảnh đính kèm (tyù chọn)")
    args = parser.parse_args()

    log(BOLD("=" * 50 + " FACEBOOK CHROME AUTO POSTER v2 " + "=" * 50), "info")

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

    # Tìm ảnh tự động
    image_paths = [args.image.strip()] if args.image.strip() else get_images_to_post()
    if image_paths:
        log(f">> Anh dinh kem: {', '.join(image_paths)}", "info")
    else:
        log("ℹ️ Không có ảnh đính kèm (chỉ đăng text)", "info")

    log(f">> Noi dung ({len(content)} ky tu): {content[:100]}...", "info")
    log(f">> Trang dang: {', '.join(pages)}", "info")

    # Kết nối Chrome
    driver = connect_chrome()
    poster = FacebookPoster(driver)

    # Đăng lên từng trang
    results = {}
    for i, slug in enumerate(pages):
        if i > 0:
            log(f"\n>> Cho 6 giay truoc trang tiep theo...", "info")
            time.sleep(6)

        ok = poster.post_to_page(slug, content, args.dry_run, image_paths)
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
