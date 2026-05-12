#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Chrome Auto Poster
============================
Đọc bài viết đã được AI tạo ra, kết nối vào Chrome đang chạy
và tự động đăng lên Fanpage Facebook.

Yêu cầu:
    pip install selenium webdriver-manager

Cách dùng:
    1. Chạy mo_chrome.bat để mở Chrome
    2. Đăng nhập Facebook trong Chrome đó
    3. Chạy script này: python chrome_poster.py

@author Xiata
"""

import os
import sys
import json
import time
import glob
import argparse
from datetime import datetime
from pathlib import Path

# ─── Kiểm tra thư viện ───
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("❌ Chưa cài selenium! Chạy: pip install selenium webdriver-manager")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER = True
except ImportError:
    WEBDRIVER_MANAGER = False


# ════════════════════════════════════════════════════════
#  CẤU HÌNH
# ════════════════════════════════════════════════════════

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE   = BASE_DIR / "logs" / "chrome_poster.log"
DEBUG_PORT = 9222   # Phải khớp với mo_chrome.bat
WAIT_SEC   = 20     # Timeout tối đa mỗi thao tác (giây)


# ════════════════════════════════════════════════════════
#  HÀM TIỆN ÍCH
# ════════════════════════════════════════════════════════

def log(msg: str):
    entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(entry)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def get_latest_post_content() -> str | None:
    """Lấy nội dung bài đăng mới nhất từ thư mục output/"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Ưu tiên file JSON (có cấu trúc rõ ràng hơn)
    json_files = sorted(OUTPUT_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    if json_files:
        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)
        return data.get("post_content") or data.get("content")

    # Nếu không có JSON, lấy file .txt mới nhất
    txt_files = sorted(OUTPUT_DIR.glob("summary_post_*.txt"), key=os.path.getmtime, reverse=True)
    if txt_files:
        return txt_files[0].read_text(encoding="utf-8").strip()

    return None


def connect_chrome() -> webdriver.Chrome:
    """Kết nối vào Chrome đang chạy qua Remote Debugging"""
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    opts.add_argument("--log-level=3")  # Giảm log spam

    try:
        if WEBDRIVER_MANAGER:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)

        log(f"✅ Đã kết nối Chrome (tab hiện tại: {driver.title[:50]})")
        return driver

    except Exception as e:
        if "cannot connect" in str(e).lower() or "9222" in str(e):
            log("❌ Không thể kết nối Chrome!")
            log("   → Hãy chạy mo_chrome.bat trước, rồi thử lại.")
        else:
            log(f"❌ Lỗi kết nối: {e}")
        sys.exit(1)


# ════════════════════════════════════════════════════════
#  CLASS FACEBOOK POSTER
# ════════════════════════════════════════════════════════

class FacebookChromePoster:

    def __init__(self, driver: webdriver.Chrome, page_id_or_name: str):
        self.driver = driver
        self.wait   = WebDriverWait(driver, WAIT_SEC)
        self.page   = page_id_or_name  # Page ID số hoặc tên page (slug)

    def navigate_to_page(self):
        """Điều hướng đến trang fanpage"""
        url = f"https://www.facebook.com/{self.page}"
        log(f"🌐 Điều hướng đến: {url}")
        self.driver.get(url)
        time.sleep(3)

        # Kiểm tra có vào được trang không
        if "facebook.com" not in self.driver.current_url:
            raise Exception("Không thể truy cập Facebook. Kiểm tra kết nối mạng.")

        # Kiểm tra đã đăng nhập chưa
        if "login" in self.driver.current_url:
            raise Exception("Chưa đăng nhập Facebook! Vào Chrome và đăng nhập trước.")

        log(f"✅ Đang ở trang: {self.driver.title[:60]}")

    def find_post_box(self):
        """Tìm và click vào ô soạn bài đăng"""
        log("🔍 Đang tìm ô đăng bài...")

        # Các selector thường gặp của nút "Tạo bài viết"
        selectors = [
            # Tiếng Việt
            "//div[@role='button' and contains(., 'Tạo bài viết')]",
            "//div[@role='button' and contains(., 'Bạn đang nghĩ gì')]",
            "//span[contains(., 'Tạo bài viết')]",
            "//div[contains(@aria-label, 'Tạo bài viết')]",
            # Tiếng Anh
            "//div[@role='button' and contains(., 'Create a post')]",
            "//div[@role='button' and contains(., \"What's on your mind\")]",
            "//div[contains(@aria-label, 'Create a post')]",
            # Generic
            "//div[@data-pagelet='ProfileComposer']//div[@role='button']",
            "//div[contains(@class, 'composer')]//div[@role='button']",
        ]

        for selector in selectors:
            try:
                elem = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                elem.click()
                log(f"✅ Đã mở ô đăng bài")
                time.sleep(2)
                return True
            except TimeoutException:
                continue

        raise Exception("Không tìm thấy nút 'Tạo bài viết'. Trang có thể đã thay đổi giao diện.")

    def type_content(self, content: str):
        """Gõ nội dung vào ô soạn thảo"""
        log(f"⌨️ Đang nhập nội dung ({len(content)} ký tự)...")

        # Tìm textarea/contenteditable đang focus
        selectors = [
            "//div[@role='textbox' and @contenteditable='true']",
            "//div[@aria-label and @contenteditable='true']",
            "//div[@data-contents='true']",
        ]

        text_area = None
        for selector in selectors:
            try:
                text_area = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                text_area.click()
                break
            except TimeoutException:
                continue

        if not text_area:
            raise Exception("Không tìm thấy ô nhập nội dung bài viết.")

        time.sleep(1)

        # Dùng JavaScript để paste nội dung (nhanh và hỗ trợ emoji tốt hơn)
        safe_content = content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        self.driver.execute_script("""
            var el = arguments[0];
            el.focus();
            var text = arguments[1];

            // Tạo DataTransfer để paste
            var dt = new DataTransfer();
            dt.setData('text/plain', text);
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true}));
        """, text_area, content)

        time.sleep(1)

        # Kiểm tra nếu paste không hoạt động, gõ từng chữ
        current_text = text_area.text or text_area.get_attribute("innerText") or ""
        if len(current_text.strip()) < 10:
            log("⌨️ Paste không hoạt động, đang gõ trực tiếp...")
            text_area.send_keys(content)

        log("✅ Đã nhập nội dung xong")
        time.sleep(2)

    def submit_post(self, dry_run: bool = False):
        """Bấm nút Đăng"""
        if dry_run:
            log("🧪 [DRY RUN] Bỏ qua bước bấm Đăng")
            return True

        log("📤 Đang bấm nút Đăng...")

        submit_selectors = [
            # Tiếng Việt
            "//div[@aria-label='Đăng'][@role='button']",
            "//span[text()='Đăng']/parent::div[@role='button']",
            "//div[@role='button' and .//span[text()='Đăng']]",
            # Tiếng Anh
            "//div[@aria-label='Post'][@role='button']",
            "//span[text()='Post']/parent::div[@role='button']",
        ]

        for selector in submit_selectors:
            try:
                btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                btn.click()
                log("✅ Đã bấm Đăng!")
                time.sleep(4)
                return True
            except TimeoutException:
                continue

        log("⚠️ Không tìm thấy nút Đăng tự động. Vui lòng bấm Đăng thủ công trong vòng 30 giây...")
        time.sleep(30)
        return True

    def post(self, content: str, dry_run: bool = False) -> bool:
        """Thực hiện toàn bộ quy trình đăng bài"""
        try:
            self.navigate_to_page()
            self.find_post_box()
            self.type_content(content)
            self.submit_post(dry_run)
            log("🎉 Đăng bài hoàn thành!")
            return True
        except Exception as e:
            log(f"❌ Lỗi khi đăng bài: {e}")
            return False


# ════════════════════════════════════════════════════════
#  CHẠY CHÍNH
# ════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Facebook Chrome Auto Poster")
    parser.add_argument("--page",    default="",    help="Page ID hoặc tên page (VD: 123456789 hoặc 'mypage')")
    parser.add_argument("--content", default="",    help="Nội dung bài đăng (nếu không muốn đọc từ output/)")
    parser.add_argument("--dry-run", action="store_true", help="Thử nghiệm (không bấm Đăng thật)")
    args = parser.parse_args()

    # Đọc cấu hình từ .env
    env_path = BASE_DIR / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    page = args.page or env.get("FB_PAGE_ID", "")
    if not page:
        log("❌ Chưa có Page ID! Thêm FB_PAGE_ID vào file .env hoặc dùng --page=ID")
        sys.exit(1)

    # Lấy nội dung bài đăng
    content = args.content
    if not content:
        content = get_latest_post_content()

    if not content:
        log("❌ Không có nội dung để đăng! Chạy PHP trước: php run_football_post.php preview-post")
        sys.exit(1)

    log("════════════════════════════════════════")
    log("BẮT ĐẦU ĐĂNG BÀI QUA CHROME")
    log("════════════════════════════════════════")
    log(f"📄 Nội dung ({len(content)} ký tự):\n{content[:200]}...")

    # Kết nối Chrome
    driver = connect_chrome()

    # Đăng bài
    poster = FacebookChromePoster(driver, page)
    success = poster.post(content, dry_run=args.dry_run)

    if success:
        log("✅ Hoàn thành!")
    else:
        log("❌ Thất bại!")
        sys.exit(1)


if __name__ == "__main__":
    main()
