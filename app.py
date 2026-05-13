#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Football Auto Poster - Desktop App V1.0.0
Chạy: python app.py
Cài thư viện: pip install customtkinter pillow
"""

VERSION = "V1.0.3"

import os, sys, json, subprocess, threading, time, socket
from pathlib import Path
from datetime import datetime
try:
    import schedule
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "schedule", "--quiet"], check=True)
    import schedule

try:
    import customtkinter as ctk
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter", "pillow"], check=True)
    import customtkinter as ctk

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "--quiet"], check=True)
    from PIL import Image
    HAS_PIL = True

# ── Cấu hình giao diện 2026 ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette màu 2026: tối, rõ lớp, có điểm nhấn đa sắc
C = {
    "bg":       "#071018",
    "sidebar":  "#0a0f1a",
    "panel":    "#0d1522",
    "panel2":   "#111c2c",
    "card":     "#101b2a",
    "card2":    "#172438",
    "border":   "#26384f",
    "text":     "#edf4ff",
    "muted":    "#96a6ba",
    "subtle":   "#64748b",
    "accent":   "#2dd4bf",
    "accent2":  "#8b5cf6",
    "green":    "#22c55e",
    "red":      "#f43f5e",
    "yellow":   "#f59e0b",
    "orange":   "#fb923c",
    "blue":     "#38bdf8",
}

BASE = Path(__file__).parent
PY   = sys.executable

# Tìm PHP tự động
def find_php() -> str | None:
    candidates = [
        r"C:\xampp\php\php.exe",
        r"C:\wamp64\bin\php\php8.2.0\php.exe",
        r"C:\wamp\bin\php\php8.0.0\php.exe",
        r"C:\php\php.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Thử lệnh php trong PATH
    try:
        r = subprocess.run(["php", "-v"], capture_output=True, timeout=3)
        if r.returncode == 0:
            return "php"
    except: pass
    return None

PHP = find_php()

def php_command(*args):
    if not PHP:
        return None
    return [PHP, str(BASE / "run_football_post.php"), *args]

# Đọc .env
def read_env():
    env = {}
    f = BASE / ".env"
    if f.exists():
        for line in f.read_text("utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def write_env(updates: dict, managed_keys=None):
    env = read_env()
    if managed_keys is None:
        env.update({k: v for k, v in updates.items() if v})
    else:
        for key in managed_keys:
            value = updates.get(key, "").strip()
            if value:
                env[key] = value
            else:
                env.pop(key, None)

    preferred = [
        "FB_PAGES", "FB_ACCESS_TOKEN",
        "OPENAI_API_KEY", "OPENAI_MODEL",
        "GROK_API_KEY", "GROK_MODEL",
        "GEMINI_API_KEY", "GEMINI_MODEL",
    ]
    ordered = [k for k in preferred if k in env] + sorted(k for k in env if k not in preferred)
    content = "\n".join(f"{k}={env[k]}" for k in ordered)
    (BASE / ".env").write_text(content, "utf-8")

def has_key(env: dict, key: str) -> bool:
    value = env.get(key, "")
    return bool(value) and "THAY" not in value

def run_cmd(cmd, callback):
    """Chạy lệnh nền, callback(output, success)"""
    def _run():
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", cwd=str(BASE), timeout=120, env=env)
            callback((r.stdout or "") + (r.stderr or ""), r.returncode == 0)
        except Exception as e:
            callback(str(e), False)
    threading.Thread(target=_run, daemon=True).start()

def find_chrome_path() -> str | None:
    """Tìm đường dẫn Chrome tự động"""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def check_chrome() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 9222), timeout=1)
        s.close(); return True
    except: return False

def get_chrome_info() -> dict:
    """Lấy thông tin Chrome đang chạy qua DevTools API"""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2) as r:
            tabs = json.loads(r.read())
            fb_tabs = [t for t in tabs if "facebook.com" in t.get("url","")]
            return {"connected": True, "tabs": len(tabs),
                    "fb_tabs": len(fb_tabs),
                    "fb_url": fb_tabs[0].get("url","") if fb_tabs else ""}
    except:
        return {"connected": False, "tabs": 0, "fb_tabs": 0, "fb_url": ""}

def check_fb_logged_in(fb_url: str) -> bool:
    """Kiểm tra URL có phải đã đăng nhập không"""
    return "facebook.com" in fb_url and "login" not in fb_url


# ════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"FB AutoPoster Pro  —  {VERSION}")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.current_page = None
        self._build_layout()
        self._show_page("dashboard")

        # Auto refresh mỗi 10s
        self._refresh_loop()

    # ─── Layout chính ───
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=236, corner_radius=0, fg_color=C["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo ảnh Xiata
        logo_path = BASE / "assets" / "logo.png"
        if not logo_path.exists():
            logo_path = BASE / "assets" / "logo.jpg"  # fallback
        self._logo_img = None
        if logo_path.exists() and HAS_PIL:
            try:
                img = Image.open(logo_path).convert("RGBA")
                img = img.resize((84, 84), Image.LANCZOS)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(84, 84))
            except: pass

        if self._logo_img:
            ctk.CTkLabel(self.sidebar, image=self._logo_img, text="").pack(pady=(20, 6))
        else:
            ctk.CTkLabel(self.sidebar, text="⚽", font=ctk.CTkFont(size=36)).pack(pady=(20, 6))

        ctk.CTkLabel(self.sidebar, text="AutoPoster Studio",
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"]).pack(pady=(0, 2))
        ctk.CTkLabel(self.sidebar, text=f"Xiata  ·  {VERSION}",
                     font=ctk.CTkFont(size=11), text_color=C["muted"]).pack(pady=(0, 18))

        ctk.CTkLabel(self.sidebar, text="MENU", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=20, pady=(0,8))

        self.nav_buttons = {}
        menus = [
            ("dashboard",  "⌂  Trang chủ"),
            ("post",       "▶  Đăng bài"),
            ("schedule",   "◷  Lịch hẹn"),
            ("chat",       "✦  ChatGPT"),
            ("settings",   "⚙  Cài đặt"),
            ("logs",       "☰  Nhật ký"),
        ]
        for key, label in menus:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color=C["panel2"],
                text_color=C["muted"], height=42, corner_radius=8,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=10, pady=1)
            self.nav_buttons[key] = btn

        # Nút chuyển sáng/tối
        self.sidebar.pack_propagate(False)
        self._is_dark = True
        self.btn_theme = ctk.CTkButton(
            self.sidebar, text="☀  Chế độ Sáng", height=34,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1, border_color=C["border"],
            hover_color=C["panel2"], text_color=C["muted"],
            command=self._toggle_theme
        )
        self.btn_theme.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

        # Trạng thái Chrome ở dưới sidebar
        self.chrome_label = ctk.CTkLabel(self.sidebar, text="●  Chrome: offline",
                                          font=ctk.CTkFont(size=11), text_color=C["subtle"])
        self.chrome_label.pack(side="bottom", pady=(4, 8), padx=12)

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Pages container
        self.pages = {}
        for key in ["dashboard", "post", "schedule", "chat", "settings", "logs"]:
            frame = ctk.CTkScrollableFrame(self.content, fg_color=C["bg"],
                                            scrollbar_button_color="#1a3a5c")
            frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            frame.grid_remove()
            self.pages[key] = frame

        self._build_dashboard()
        self._build_post()
        self._build_schedule()
        self._build_chat()
        self._build_settings()
        self._build_logs()
        self._sched_running = False
        self._chat_history = []  # lưu lịch sử chat
        self._start_scheduler_thread()

    def _show_page(self, key):
        for k, f in self.pages.items():
            f.grid_remove()
        self.pages[key].grid()
        self.current_page = key

        # Highlight nav button
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color=C["panel2"] if k == key else "transparent",
                          text_color=C["accent"] if k == key else C["muted"])

    # ─── Chuyển sáng / tối ───
    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        if self._is_dark:
            ctk.set_appearance_mode("dark")
            self.btn_theme.configure(text="☀  Chế độ Sáng")
        else:
            ctk.set_appearance_mode("light")
            self.btn_theme.configure(text="☽  Chế độ Tối")

    # ─── Card helper ───
    def _card(self, parent, title="", pady=(0,12)):
        f = ctk.CTkFrame(parent, corner_radius=8, fg_color=C["card"],
                         border_width=1, border_color=C["border"])
        f.pack(fill="x", padx=20, pady=pady)
        if title:
            ctk.CTkLabel(f, text=title.upper(), font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=C["muted"]).pack(anchor="w", padx=18, pady=(16,6))
        return f

    # ════════════ DASHBOARD ════════════
    def _build_dashboard(self):
        p = self.pages["dashboard"]

        ctk.CTkLabel(p, text="Bảng điều khiển", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,2))
        self.dash_time = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=11),
                                       text_color=C["muted"])
        self.dash_time.pack(anchor="w", padx=24, pady=(0,14))

        hero = ctk.CTkFrame(p, corner_radius=8, fg_color=C["panel"],
                            border_width=1, border_color=C["border"])
        hero.pack(fill="x", padx=20, pady=(0, 14))
        ctk.CTkLabel(hero, text="Facebook AutoPoster 2026",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(hero, text="Tạo bài, lên lịch, đăng qua Chrome và trò chuyện với ChatGPT trong cùng một cửa sổ.",
                     font=ctk.CTkFont(size=12), text_color=C["muted"]).pack(anchor="w", padx=18, pady=(0, 16))

        # Status row
        sf = ctk.CTkFrame(p, fg_color="transparent")
        sf.pack(fill="x", padx=20, pady=(0,12))
        sf.columnconfigure((0,1,2,3,4), weight=1)

        self.stat_cards = {}
        stats = [
            ("chrome",   "CHROME",   "Đang kiểm tra...", C["blue"]),
            ("fb_pages", "FANPAGE",  "Chưa thiết lập",   C["green"]),
            ("openai",   "CHATGPT",  "Chưa có",          C["accent"]),
            ("grok",     "GROK",     "Chưa có",          C["accent2"]),
            ("gemini",   "GEMINI",   "Chưa có",          C["orange"]),
        ]
        for i, (k, title, default, accent) in enumerate(stats):
            card = ctk.CTkFrame(sf, corner_radius=8, fg_color=C["card"],
                                border_width=1, border_color=C["border"], height=104)
            card.grid(row=0, column=i, padx=5, sticky="ew")
            card.grid_propagate(False)
            ctk.CTkFrame(card, height=3, fg_color=accent, corner_radius=8).pack(fill="x", padx=12, pady=(12, 8))
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=C["muted"]).pack(anchor="w", padx=14, pady=(0,4))
            lbl = ctk.CTkLabel(card, text=default, font=ctk.CTkFont(size=12, weight="bold"),
                               text_color=C["text"])
            lbl.pack(anchor="w", padx=14)
            self.stat_cards[k] = lbl

        # Latest post
        c2 = self._card(p, "Bài mới nhất")
        self.latest_post_lbl = ctk.CTkTextbox(c2, height=160, font=ctk.CTkFont(size=12),
                                               fg_color=C["panel"], text_color=C["muted"],
                                               border_width=0)
        self.latest_post_lbl.pack(fill="x", padx=16, pady=(0,16))
        self.latest_post_lbl.insert("end", "Chưa có bài mới. Khi bạn tạo bài, nội dung gần nhất sẽ xuất hiện ở đây.")
        self.latest_post_lbl.configure(state="disabled")

    def _refresh_dashboard(self):
        self.dash_time.configure(text=f"Cập nhật: {datetime.now().strftime('%H:%M:%S  %d/%m/%Y')}")

        # Chrome
        ok = check_chrome()
        self.stat_cards["chrome"].configure(
            text="✅ Đã kết nối" if ok else "❌ Chưa kết nối",
            text_color=C["green"] if ok else C["red"]
        )
        self.chrome_label.configure(
            text=f"● Chrome: {'OK' if ok else 'Chưa kết nối'}",
            text_color=C["green"] if ok else C["red"]
        )

        # .env keys
        env = read_env()

        pages_val = env.get("FB_PAGES", "")
        pages_count = len([x for x in pages_val.split(",") if x.strip() and "THAY" not in x]) if pages_val else 0
        self.stat_cards["fb_pages"].configure(
            text=f"✅ {pages_count} trang" if pages_count else "❌ Chưa thiết lập",
            text_color=C["green"] if pages_count else C["red"]
        )
        self.stat_cards["openai"].configure(
            text="✅ Đã thiết lập" if has_key(env, "OPENAI_API_KEY") else "❌ Chưa có",
            text_color=C["green"] if has_key(env, "OPENAI_API_KEY") else C["muted"]
        )
        self.stat_cards["grok"].configure(
            text="✅ Đã thiết lập" if has_key(env, "GROK_API_KEY") else "❌ Chưa có",
            text_color=C["green"] if has_key(env, "GROK_API_KEY") else C["muted"]
        )
        self.stat_cards["gemini"].configure(
            text="✅ Đã thiết lập" if has_key(env, "GEMINI_API_KEY") else "❌ Chưa có",
            text_color=C["green"] if has_key(env, "GEMINI_API_KEY") else C["muted"]
        )

        # Latest post
        jp = BASE / "output" / "latest_post.json"
        if jp.exists():
            try:
                d = json.loads(jp.read_text("utf-8"))
                txt = d.get("post_content","")[:600] + "..."
                self.latest_post_lbl.configure(state="normal")
                self.latest_post_lbl.delete("1.0","end")
                self.latest_post_lbl.insert("end", txt)
                self.latest_post_lbl.configure(state="disabled")
            except: pass

    # ════════════ POST ════════════
    def _build_post(self):
        p = self.pages["post"]
        ctk.CTkLabel(p, text="▶  Tạo & Đăng bài", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,16))

        # ── Chrome Wizard ──
        cc = self._card(p, "🌐 Kết nối Chrome & Facebook")

        # Step indicators
        steps_frame = ctk.CTkFrame(cc, fg_color="transparent")
        steps_frame.pack(fill="x", padx=16, pady=(4, 12))
        steps_frame.columnconfigure((0, 1, 2), weight=1)

        self._step_lbls = {}
        step_defs = [
            ("step1", "1", "Mở Chrome"),
            ("step2", "2", "Đăng nhập FB"),
            ("step3", "3", "Sẵn sàng đăng"),
        ]
        for col, (k, num, label) in enumerate(step_defs):
            sf2 = ctk.CTkFrame(steps_frame, fg_color=C["panel"], corner_radius=8)
            sf2.grid(row=0, column=col, padx=4, sticky="ew", pady=4)
            num_lbl = ctk.CTkLabel(sf2, text=num, width=28, height=28,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color=C["border"], corner_radius=14,
                                   text_color=C["muted"])
            num_lbl.pack(side="left", padx=(10, 6), pady=10)
            txt = ctk.CTkLabel(sf2, text=label, font=ctk.CTkFont(size=12),
                               text_color=C["muted"])
            txt.pack(side="left", pady=10)
            self._step_lbls[k] = (num_lbl, txt)

        # Controls row
        ctrl = ctk.CTkFrame(cc, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 6))

        self.btn_open_chrome = ctk.CTkButton(
            ctrl, text="🟢  Mở Chrome", width=140, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["accent"], hover_color=C["blue"], text_color="#04111d",
            command=self._open_chrome)
        self.btn_open_chrome.pack(side="left", padx=(0, 8))

        self.btn_check_fb = ctk.CTkButton(
            ctrl, text="🔍  Kiểm tra Đăng nhập", width=170, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=C["panel2"], hover_color=C["border"],
            command=self._check_fb_status)
        self.btn_check_fb.pack(side="left", padx=(0, 8))

        self.btn_goto_fb = ctk.CTkButton(
            ctrl, text="📲  Vào Facebook", width=140, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=C["panel2"], hover_color=C["border"],
            command=self._goto_facebook)
        self.btn_goto_fb.pack(side="left")

        # Status label
        self.chrome_status_lbl = ctk.CTkLabel(
            cc, text="● Nhấn Mở Chrome để bắt đầu",
            font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.chrome_status_lbl.pack(anchor="w", padx=16, pady=(0, 4))

        # Pages list
        self.chrome_pages_lbl = ctk.CTkLabel(
            cc, text="", font=ctk.CTkFont(size=11), text_color=C["muted"],
            justify="left")
        self.chrome_pages_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Chrome path info
        chrome_path = find_chrome_path()
        path_color = C["green"] if chrome_path else C["red"]
        path_text = f"📂 Chrome: {chrome_path}" if chrome_path else "❌ Không tìm thấy Chrome! Hãy kiểm tra cài đặt."
        ctk.CTkLabel(cc, text=path_text, font=ctk.CTkFont(size=10),
                     text_color=path_color).pack(anchor="w", padx=16, pady=(0, 12))

        # ── Workflow ──
        bf = self._card(p, "🎛️ Quy trình")

        # Full one-click
        full_row = ctk.CTkFrame(bf, fg_color=C["panel"], corner_radius=8)
        full_row.pack(fill="x", padx=16, pady=(0,10))
        ctk.CTkLabel(full_row, text="⚡ Chạy toàn bộ (1 click)",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=C["text"]).pack(side="left", padx=12, pady=10)
        self.btn_full = ctk.CTkButton(full_row, text="🚀  CHẠY NGAY", width=140, height=34,
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      fg_color=C["green"], hover_color="#16a34a", text_color="#03120a",
                                      command=self._run_full_workflow)
        self.btn_full.pack(side="right", padx=12, pady=10)

        ctk.CTkLabel(bf, text="— hoặc từng bước —", font=ctk.CTkFont(size=11),
                     text_color=C["subtle"]).pack(pady=(0,8))

        row = ctk.CTkFrame(bf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0,14))
        self.btn_preview  = ctk.CTkButton(row, text="👁  Xem trước tin", width=150, height=36,
                                           font=ctk.CTkFont(size=12), fg_color=C["panel2"], hover_color=C["border"],
                                           command=lambda: self._run_post_action("preview"))
        self.btn_preview.pack(side="left", padx=(0,8))
        self.btn_generate = ctk.CTkButton(row, text="✨  Tạo bài (AI)", width=150, height=36,
                                           font=ctk.CTkFont(size=12), fg_color=C["accent"], hover_color=C["blue"], text_color="#04111d",
                                           command=lambda: self._run_post_action("generate"))
        self.btn_generate.pack(side="left", padx=(0,8))
        self.btn_chrome   = ctk.CTkButton(row, text="📤  Đăng qua Chrome", width=160, height=36,
                                           font=ctk.CTkFont(size=12), fg_color=C["accent2"], hover_color="#a78bfa",
                                           command=lambda: self._run_post_action("chrome"))
        self.btn_chrome.pack(side="left")

        self.post_status = ctk.CTkLabel(bf, text="", font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.post_status.pack(anchor="w", padx=16, pady=(0,6))

        # Output
        oc = self._card(p, "📤 Output")
        self.post_output = ctk.CTkTextbox(oc, height=340, font=ctk.CTkFont(size=11, family="Courier New"),
                                          fg_color=C["panel"], text_color=C["green"], border_width=0)
        self.post_output.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self.post_output.insert("end", "Nhấn một nút ở trên để bắt đầu...\n")
        self.post_output.configure(state="disabled")

    def _open_chrome(self):
        chrome_path = find_chrome_path()
        if not chrome_path:
            self.chrome_status_lbl.configure(
                text="❌ Không tìm thấy Chrome! Kiểm tra cài đặt.",
                text_color=C["red"])
            return

        profile_dir = str(BASE / "chrome_profile")
        self.btn_open_chrome.configure(state="disabled", text="⏳ Đang mở...")
        self.chrome_status_lbl.configure(text="⏳ Đang khởi động Chrome...", text_color=C["yellow"])
        self._set_step(1, "pending")

        def _do_open():
            subprocess.Popen([
                chrome_path,
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
                "--no-first-run", "--disable-default-apps",
                "https://www.facebook.com"
            ])
            time.sleep(4)
            ok = check_chrome()
            def _upd():
                self.btn_open_chrome.configure(state="normal", text="🟢  Mở Chrome")
                if ok:
                    self._set_step(1, "done")
                    self.chrome_status_lbl.configure(
                        text="✅ Chrome đã mở — Hãy đăng nhập Facebook rồi nhấn Kiểm tra",
                        text_color=C["green"])
                else:
                    self._set_step(1, "error")
                    self.chrome_status_lbl.configure(
                        text="❌ Chrome mở nhưng chưa kết nối được",
                        text_color=C["red"])
            self.after(0, _upd)
        threading.Thread(target=_do_open, daemon=True).start()

    def _goto_facebook(self):
        """Dẫn Chrome đang chạy đến facebook.com"""
        if not check_chrome():
            self.chrome_status_lbl.configure(
                text="⚠️ Chrome chưa mở — nhấn Mở Chrome trước", text_color=C["yellow"])
            return
        try:
            import urllib.request
            url = "http://127.0.0.1:9222/json/new?https://www.facebook.com"
            req = urllib.request.Request(url, method="PUT")
            urllib.request.urlopen(req, timeout=2)
            self.chrome_status_lbl.configure(
                text="✅ Đã mở tab Facebook trong Chrome", text_color=C["green"])
        except:
            self.chrome_status_lbl.configure(
                text="⚠️ Không thể mở tab mới", text_color=C["yellow"])

    def _check_fb_status(self):
        """Kiểm tra trạng thái đăng nhập Facebook"""
        self.btn_check_fb.configure(state="disabled", text="⏳ Đang kiểm tra...")
        def _do():
            info = get_chrome_info()
            env  = read_env()
            pages_raw = env.get("FB_PAGES", "")
            pages = [p.strip() for p in pages_raw.split(",") if p.strip() and "THAY" not in p]

            def _upd():
                self.btn_check_fb.configure(state="normal", text="🔍  Kiểm tra Đăng nhập")
                if not info["connected"]:
                    self._set_step(1, "error")
                    self._set_step(2, "pending")
                    self.chrome_status_lbl.configure(
                        text="❌ Chrome chưa kết nối — hãy nhấn Mở Chrome",
                        text_color=C["red"])
                    return

                self._set_step(1, "done")
                logged_in = check_fb_logged_in(info["fb_url"])

                if logged_in:
                    self._set_step(2, "done")
                    self._set_step(3, "done")
                    pages_info = "\n".join(f"   • facebook.com/{pg}" for pg in pages) or "   (Chưa có trang nào — vào Cài đặt để thêm)"
                    self.chrome_status_lbl.configure(
                        text=f"✅ Đã đăng nhập Facebook! {info['tabs']} tab đang mở.",
                        text_color=C["green"])
                    self.chrome_pages_lbl.configure(
                        text=f"🎯 Trang sẽ đăng bài:\n{pages_info}",
                        text_color=C["blue"])
                else:
                    self._set_step(2, "error")
                    self.chrome_status_lbl.configure(
                        text="⚠️ Chrome mở nhưng chưa đăng nhập Facebook — nhấn Vào Facebook",
                        text_color=C["yellow"])
                    self.chrome_pages_lbl.configure(text="")
            self.after(0, _upd)
        threading.Thread(target=_do, daemon=True).start()

    def _set_step(self, step: int, state: str):
        """Cập nhật hiển thị step wizard: pending/done/error"""
        key = f"step{step}"
        if key not in self._step_lbls: return
        num_lbl, txt = self._step_lbls[key]
        colors = {
            "pending": (C["yellow"], C["yellow"], "#4a3413"),
            "done":    (C["green"], "#ffffff", "#166534"),
            "error":   (C["red"], "#ffffff", "#7f1d1d"),
            "idle":    (C["muted"], C["muted"], C["border"]),
        }
        tc, ntc, nbg = colors.get(state, colors["idle"])
        prefix = {"done": "✓", "error": "✕", "pending": "●"}.get(state, str(step))
        num_lbl.configure(text=prefix, text_color=ntc, fg_color=nbg)
        txt.configure(text_color=tc)

    def _run_full_workflow(self):
        """Chạy toàn bộ: PHP scrape+AI → Chrome post"""
        preview_cmd = php_command("preview-post")
        if preview_cmd is None:
            self.post_status.configure(text="❌ Chưa tìm thấy PHP. Cài XAMPP/WAMP hoặc thêm PHP vào PATH.", text_color=C["red"])
            return

        all_btns = [self.btn_full, self.btn_preview, self.btn_generate, self.btn_chrome]
        for b in all_btns: b.configure(state="disabled")
        self.post_status.configure(text="⏳ Đang chạy toàn bộ quy trình...", text_color=C["yellow"])
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"🚀 BẮT ĐẦU TOÀN BỘ QUY TRÌNH — {datetime.now().strftime('%H:%M:%S')}\n")
        self.post_output.insert("end", "=" * 50 + "\n\n")
        self.post_output.configure(state="disabled")

        def _full_run():
            py_path = PY
            steps = [
                ("📰 Bước 1: Thu thập tin + AI tạo bài",
                 preview_cmd),
                ("📤 Bước 2: Đăng lên Facebook qua Chrome",
                 [py_path, str(BASE/"chrome_poster.py")]),
            ]
            final_ok = True
            for label, cmd in steps:
                def _add(t):
                    self.after(0, lambda txt=t: [
                        self.post_output.configure(state="normal"),
                        self.post_output.insert("end", txt),
                        self.post_output.see("end"),
                        self.post_output.configure(state="disabled")
                    ])
                _add(f"\n{'─'*40}\n{label}\n{'─'*40}\n")
                try:
                    _env = os.environ.copy()
                    _env["PYTHONIOENCODING"] = "utf-8"
                    _env["PYTHONUTF8"] = "1"
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace",
                                       cwd=str(BASE), timeout=180, env=_env)
                    _add((r.stdout or "") + (r.stderr or ""))
                    if r.returncode != 0:
                        final_ok = False
                        break
                except Exception as e:
                    _add(f"\n❌ Lỗi: {e}\n")
                    final_ok = False; break

            def _done():
                self.post_status.configure(
                    text="✅ Đã đăng bài thành công!" if final_ok else "❌ Có lỗi — xem output",
                    text_color=C["green"] if final_ok else C["red"]
                )
                for b in all_btns: b.configure(state="normal")
                self._refresh_dashboard()
            self.after(0, _done)

        threading.Thread(target=_full_run, daemon=True).start()

    def _run_post_action(self, action):
        cmd_map = {
            "preview":  php_command("preview-post"),
            "generate": php_command("preview-post"),
            "chrome":   [PY, str(BASE/"chrome_poster.py")],
        }
        if cmd_map.get(action) is None:
            self.post_status.configure(text="❌ Chưa tìm thấy PHP. Cài XAMPP/WAMP hoặc thêm PHP vào PATH.", text_color=C["red"])
            return

        btns = [self.btn_full, self.btn_preview, self.btn_generate, self.btn_chrome]
        for b in btns: b.configure(state="disabled")
        labels = {"preview": "Đang lấy tin tức...", "generate": "AI đang tạo bài...", "chrome": "Đang đăng qua Chrome..."}
        self.post_status.configure(text=f"⏳ {labels.get(action)}", text_color=C["yellow"])
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"▶ {datetime.now().strftime('%H:%M:%S')} — {action}\n\n")
        self.post_output.configure(state="disabled")
        def on_done(out, ok):
            def _u():
                self.post_output.configure(state="normal")
                self.post_output.insert("end", out)
                self.post_output.see("end")
                self.post_output.configure(state="disabled")
                self.post_status.configure(text="✅ Hoàn thành!" if ok else "❌ Lỗi",
                                            text_color=C["green"] if ok else C["red"])
                for b in btns: b.configure(state="normal")
            self.after(0, _u)
        run_cmd(cmd_map[action], on_done)

    # ════════════ SCHEDULE ════════════
    def _build_schedule(self):
        p = self.pages["schedule"]
        ctk.CTkLabel(p, text="◷  Lịch hẹn tự động", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,4))
        ctk.CTkLabel(p, text="Thiết lập giờ tự động chạy toàn bộ quy trình mỗi ngày",
                     font=ctk.CTkFont(size=12), text_color=C["muted"]).pack(anchor="w", padx=24, pady=(0,16))

        sc = self._card(p, "🕐 Giờ đăng bài tự động")
        self._sched_entries = []
        default_times = ["07:00", "13:00", "20:00"]
        for t in default_times:
            row = ctk.CTkFrame(sc, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text="🕐", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0,8))
            e = ctk.CTkEntry(row, width=80, height=34, font=ctk.CTkFont(size=13),
                             fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
            e.insert(0, t)
            e.pack(side="left")
            ctk.CTkLabel(row, text="(HH:MM)", font=ctk.CTkFont(size=11),
                         text_color=C["subtle"]).pack(side="left", padx=8)
            self._sched_entries.append(e)

        btn_row = ctk.CTkFrame(sc, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8,14))
        ctk.CTkButton(btn_row, text="✅  Bật lịch hẹn", width=150, height=36,
                      font=ctk.CTkFont(size=13), fg_color=C["green"], hover_color="#16a34a", text_color="#03120a",
                      command=self._apply_schedule).pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="⛔  Tắt lịch hẹn", width=150, height=36,
                      font=ctk.CTkFont(size=13), fg_color=C["red"], hover_color="#fb7185",
                      command=self._cancel_schedule).pack(side="left")

        self.sched_status = ctk.CTkLabel(sc, text="● Chưa bật lịch hẹn",
                                          font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.sched_status.pack(anchor="w", padx=16, pady=(0,8))

        # Next run preview
        nc = self._card(p, "📅 Lần chạy tiếp theo")
        self.next_run_lbl = ctk.CTkLabel(nc, text="Chưa có lịch",
                                          font=ctk.CTkFont(size=13), text_color=C["muted"])
        self.next_run_lbl.pack(anchor="w", padx=16, pady=(0,14))

    def _apply_schedule(self):
        schedule.clear()
        times = [e.get().strip() for e in self._sched_entries if e.get().strip()]
        for t in times:
            schedule.every().day.at(t).do(self._run_full_workflow)
        self._sched_running = True
        self.sched_status.configure(
            text=f"✅ Đang chạy — lịch: {', '.join(times)}", text_color=C["green"])
        self._update_next_run()

    def _cancel_schedule(self):
        schedule.clear()
        self._sched_running = False
        self.sched_status.configure(text="⛔ Đã tắt lịch hẹn", text_color=C["red"])
        self.next_run_lbl.configure(text="Không có lịch")

    def _update_next_run(self):
        nj = schedule.next_run()
        if nj:
            self.next_run_lbl.configure(
                text=f"⏰ {nj.strftime('%H:%M  %d/%m/%Y')}", text_color=C["text"])

    def _start_scheduler_thread(self):
        def _loop():
            while True:
                schedule.run_pending()
                time.sleep(30)
        threading.Thread(target=_loop, daemon=True).start()

    # ════════════ CHAT AI ════════════
    def _build_chat(self):
        p = self.pages["chat"]
        ctk.CTkLabel(p, text="✦  ChatGPT & AI", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,4))
        ctk.CTkLabel(p, text="Soạn nội dung, hỏi ý tưởng bài đăng và kiểm tra caption trước khi đăng.",
                     font=ctk.CTkFont(size=12), text_color=C["muted"]).pack(anchor="w", padx=24, pady=(0,14))

        # Model selector
        sel_row = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=8,
                               border_width=1, border_color=C["border"])
        sel_row.pack(fill="x", padx=20, pady=(0,12))
        ctk.CTkLabel(sel_row, text="Nhà cung cấp", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["muted"]).pack(side="left", padx=(14,10), pady=12)
        self.chat_ai_var = ctk.StringVar(value="auto")
        for val, label in [("auto","Tự động"), ("openai","ChatGPT"), ("grok","Grok"), ("gemini","Gemini")]:
            ctk.CTkRadioButton(sel_row, text=label, variable=self.chat_ai_var, value=val,
                               font=ctk.CTkFont(size=12), text_color=C["text"],
                               fg_color=C["accent"], hover_color=C["blue"]).pack(side="left", padx=8)

        # Chat history display
        chat_card = ctk.CTkFrame(p, corner_radius=8, fg_color=C["card"],
                                  border_width=1, border_color=C["border"])
        chat_card.pack(fill="x", padx=20, pady=(0,10))
        self.chat_box = ctk.CTkTextbox(chat_card, height=400,
                                        font=ctk.CTkFont(size=12),
                                        fg_color=C["panel"], text_color=C["text"],
                                        border_width=0, wrap="word")
        self.chat_box.pack(fill="both", padx=12, pady=12, expand=True)
        self.chat_box.insert("end", "ChatGPT đã sẵn sàng. Hãy nhập câu hỏi hoặc nhờ viết thử caption.\n\n")
        self.chat_box.configure(state="disabled")

        # Input row
        inp_row = ctk.CTkFrame(p, fg_color="transparent")
        inp_row.pack(fill="x", padx=20, pady=(0,16))
        inp_row.columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(
            inp_row, placeholder_text="Nhập câu hỏi... Enter để gửi",
            font=ctk.CTkFont(size=13), height=42,
            fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())

        self.btn_send_chat = ctk.CTkButton(
            inp_row, text="Gửi", width=90, height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["accent"], hover_color=C["blue"], text_color="#04111d",
            command=self._send_chat)
        self.btn_send_chat.grid(row=0, column=1)

        ctk.CTkButton(p, text="Xoá lịch sử", height=32,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", border_width=1, border_color=C["border"],
                      hover_color=C["panel2"], text_color=C["muted"],
                      command=self._clear_chat).pack(anchor="e", padx=20, pady=(0,16))

    def _append_chat(self, role: str, text: str):
        colors = {"👤 Bạn": C["blue"], "🤖 AI": C["green"], "⚠️ Lỗi": C["red"]}
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{role}:\n", role)
        self.chat_box.insert("end", f"{text}\n\n")
        self.chat_box.tag_config(role, foreground=colors.get(role, C["text"]))
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _clear_chat(self):
        self._chat_history = []
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.insert("end", "Lịch sử đã được xoá. Hãy bắt đầu cuộc trò chuyện mới.\n\n")
        self.chat_box.configure(state="disabled")

    def _send_chat(self):
        msg = self.chat_input.get().strip()
        if not msg:
            return
        self.chat_input.delete(0, "end")
        self._append_chat("👤 Bạn", msg)
        self.btn_send_chat.configure(state="disabled", text="⏳...")
        self._chat_history.append({"role": "user", "content": msg})

        def _do():
            env = read_env()
            ai_choice = self.chat_ai_var.get()
            openai_key = env.get("OPENAI_API_KEY", "")
            grok_key   = env.get("GROK_API_KEY", "")
            gemini_key = env.get("GEMINI_API_KEY", "")
            openai_model = env.get("OPENAI_MODEL", "chat-latest")
            grok_model   = env.get("GROK_MODEL", "grok-3-mini-fast")
            gemini_model = env.get("GEMINI_MODEL", "gemini-1.5-flash")

            reply = None; provider = ""; last_error = ""
            if ai_choice in ("auto", "openai") and has_key(env, "OPENAI_API_KEY"):
                reply, provider = self._chat_openai(self._chat_history, openai_key, openai_model)
                if reply is None:
                    last_error = provider
            if reply is None and ai_choice in ("auto", "grok") and grok_key and "THAY" not in grok_key:
                reply, provider = self._chat_grok(self._chat_history, grok_key, grok_model)
                if reply is None:
                    last_error = provider
            if reply is None and ai_choice in ("auto", "gemini") and gemini_key and "THAY" not in gemini_key:
                reply, provider = self._chat_gemini(self._chat_history, gemini_key, gemini_model)
                if reply is None:
                    last_error = provider
            if reply is None:
                if last_error:
                    reply = f"❌ AI chưa phản hồi được.\nChi tiết: {last_error}"
                else:
                    reply = "❌ Chưa cấu hình API Key!\nVào Cài đặt → điền OPENAI_API_KEY, GROK_API_KEY hoặc GEMINI_API_KEY → Lưu cài đặt."
                provider = "error"

            if provider != "error":
                self._chat_history.append({"role": "assistant", "content": reply})

            def _upd():
                role = "🤖 AI" if provider != "error" else "⚠️ Lỗi"
                self._append_chat(role, reply)
                self.btn_send_chat.configure(state="normal", text="Gửi")
            self.after(0, _upd)

        threading.Thread(target=_do, daemon=True).start()

    def _chat_openai(self, history, key, model):
        try:
            import urllib.request, json as _json
            transcript = []
            for m in history[-16:]:
                name = "Người dùng" if m["role"] == "user" else "Trợ lý"
                transcript.append(f"{name}: {m['content']}")

            data = _json.dumps({
                "model": model,
                "instructions": "Bạn là trợ lý ChatGPT trong app đăng bài Facebook. Trả lời bằng tiếng Việt tự nhiên, ngắn gọn, hữu ích và ưu tiên gợi ý có thể dùng ngay cho nội dung mạng xã hội.",
                "input": "\n\n".join(transcript),
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                res = _json.loads(r.read())

            text = self._extract_openai_text(res)
            if text:
                return text, "openai"
            return None, "OpenAI không trả về nội dung"
        except Exception as e:
            return None, str(e)

    def _extract_openai_text(self, res: dict) -> str:
        if isinstance(res.get("output_text"), str):
            return res["output_text"].strip()
        for item in res.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    return content["text"].strip()
        return ""

    def _chat_grok(self, history, key, model):
        try:
            import urllib.request, json as _json
            messages = [
                {"role": "system", "content": "Bạn là trợ lý AI thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}
            ] + history
            data = _json.dumps({
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }).encode()
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                res = _json.loads(r.read())
            return res["choices"][0]["message"]["content"].strip(), "grok"
        except Exception as e:
            return None, str(e)

    def _chat_gemini(self, history, key, model):
        try:
            import urllib.request, json as _json
            contents = []
            for m in history:
                role = "user" if m["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
            data = _json.dumps({
                "contents": contents,
                "systemInstruction": {"parts": [{"text": "Bạn là trợ lý AI thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}]},
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
            }).encode()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(url, data=data,
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = _json.loads(r.read())
            return res["candidates"][0]["content"]["parts"][0]["text"].strip(), "gemini"
        except Exception as e:
            return None, str(e)

    # ════════════ SETTINGS ════════════
    def _build_settings(self):
        p = self.pages["settings"]
        ctk.CTkLabel(p, text="⚙  Cài đặt", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,16))

        self.setting_fields = {}
        sections = [
            ("📘 Facebook — Danh sách trang đăng bài", [
                ("FB_PAGES", "Trang Facebook (ngăn cách bằng dấu phẩy)",
                 "VD: myfanpage,another.page hoặc https://facebook.com/page"),
            ]),
            ("✦ ChatGPT / OpenAI", [
                ("OPENAI_API_KEY", "API Key", "sk-..."),
                ("OPENAI_MODEL",   "Model",   "chat-latest"),
            ]),
            ("🟣 Grok AI (xAI)", [
                ("GROK_API_KEY",  "API Key", "xai-..."),
                ("GROK_MODEL",    "Model",   "grok-3-mini-fast"),
            ]),
            ("🔵 Gemini AI", [
                ("GEMINI_API_KEY", "API Key", "AIzaSy..."),
                ("GEMINI_MODEL",   "Model",   "gemini-1.5-flash"),
            ]),
        ]

        env = read_env()
        for sec_title, fields in sections:
            card = self._card(p, sec_title)
            for key, label, placeholder in fields:
                ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12),
                             text_color=C["muted"]).pack(anchor="w", padx=16, pady=(6,2))
                # FB_PAGES: text area lớn hơn để nhập nhiều trang
                if key == "FB_PAGES":
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         font=ctk.CTkFont(size=12), height=38,
                                         fg_color=C["panel"], border_color=C["border"],
                                         text_color=C["text"])
                    ctk.CTkLabel(card, text="💡 Mỗi slug cách nhau bằng dấu phẩy. VD: page1,page2,page3",
                                 font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=16)
                else:
                    show = "*" if "TOKEN" in key or "KEY" in key else None
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         show=show,
                                         font=ctk.CTkFont(size=12), height=36,
                                         fg_color=C["panel"], border_color=C["border"],
                                         text_color=C["text"])
                entry.pack(fill="x", padx=16, pady=(0,4))
                val = env.get(key, "")
                if val and "THAY" not in val:
                    entry.insert(0, val)
                self.setting_fields[key] = entry
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

        # Save button
        self.save_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=12))
        self.save_status.pack(anchor="w", padx=20)
        ctk.CTkButton(p, text="Lưu cài đặt", height=40, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=C["green"], hover_color="#16a34a", text_color="#03120a",
                      command=self._save_settings).pack(anchor="w", padx=20, pady=(8,24))

    def _save_settings(self):
        env = {}
        for key, entry in self.setting_fields.items():
            val = entry.get().strip()
            env[key] = val
        write_env(env, managed_keys=set(self.setting_fields.keys()))
        self.save_status.configure(text="✅ Đã lưu!", text_color=C["green"])
        self._refresh_dashboard()
        self.after(3000, lambda: self.save_status.configure(text=""))

    # ════════════ LOGS ════════════
    def _build_logs(self):
        p = self.pages["logs"]
        ctk.CTkLabel(p, text="☰  Nhật ký", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,4))

        # Tab row
        tf = ctk.CTkFrame(p, fg_color="transparent")
        tf.pack(fill="x", padx=20, pady=(0,12))

        self.log_tabs = {}
        self.current_log = "workflow"
        for key, label in [("workflow","Workflow"), ("chrome","Chrome"), ("cron","Cron")]:
            btn = ctk.CTkButton(
                tf, text=label, width=100, height=30,
                font=ctk.CTkFont(size=12),
                fg_color=C["accent"] if key=="workflow" else C["panel2"],
                hover_color=C["blue"],
                text_color="#04111d" if key=="workflow" else C["text"],
                command=lambda k=key: self._switch_log(k)
            )
            btn.pack(side="left", padx=(0,6))
            self.log_tabs[key] = btn

        # Refresh button
        ctk.CTkButton(tf, text="🔄 Làm mới", width=90, height=30,
                      font=ctk.CTkFont(size=12),
                      fg_color="transparent", border_width=1, border_color=C["border"],
                      hover_color=C["panel2"], text_color=C["muted"],
                      command=self._load_logs).pack(side="left")

        # Log box
        card = self._card(p)
        self.log_box = ctk.CTkTextbox(card, height=440,
                                       font=ctk.CTkFont(size=11, family="Courier New"),
                                       fg_color=C["panel"], text_color=C["green"],
                                       border_width=0)
        self.log_box.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self._load_logs()

    def _switch_log(self, key):
        self.current_log = key
        for k, btn in self.log_tabs.items():
            btn.configure(
                fg_color=C["accent"] if k==key else C["panel2"],
                text_color="#04111d" if k==key else C["text"],
            )
        self._load_logs()

    def _load_logs(self):
        log_map = {
            "workflow": BASE/"logs"/"workflow.log",
            "chrome":   BASE/"logs"/"chrome_poster.log",
            "cron":     BASE/"logs"/"cron_football.log",
        }
        f = log_map.get(self.current_log)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0","end")
        if f and f.exists():
            lines = f.read_text("utf-8", errors="replace").splitlines()
            self.log_box.insert("end", "\n".join(lines[-100:]))
        else:
            self.log_box.insert("end", "(Chưa có log nào)")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ─── Auto refresh ───
    def _refresh_loop(self):
        self._refresh_dashboard()
        if self.current_page == "logs":
            self._load_logs()
        if self.current_page == "schedule" and self._sched_running:
            self._update_next_run()
        # Cập nhật trạng thái Chrome trên trang Post
        try:
            ok = check_chrome()
            if ok:
                self._set_step(1, "done")
                self.chrome_status_lbl.configure(
                    text="✅ Chrome đã kết nối — nhấn Kiểm tra Đăng nhập",
                    text_color=C["green"])
            else:
                self.chrome_status_lbl.configure(
                    text="⚠️ Chrome chưa kết nối — nhấn Mở Chrome",
                    text_color=C["muted"])
        except: pass
        self.after(10000, self._refresh_loop)


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()

