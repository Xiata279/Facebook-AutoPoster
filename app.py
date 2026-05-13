#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Football Auto Poster - Desktop App V1.0.0
Chạy: python app.py
Cài thư viện: pip install customtkinter pillow
"""

VERSION = "V1.0.2"

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

# Palette màu 2026 Deep Space
C = {
    "bg":       "#050b18",   # Nền chính (deep space)
    "sidebar":  "#070e1f",   # Sidebar
    "card":     "#0a1628",   # Card
    "card2":    "#0d1e35",   # Card hover
    "border":   "#1a3a5c",   # Viền card
    "text":     "#e2e8f0",   # Chữ chính
    "muted":    "#4a6080",   # Chữ mờ
    "accent":   "#0ea5e9",   # Xanh cyan néon
    "accent2":  "#6366f1",   # Tím indigo
    "green":    "#10b981",   # Xanh lá thành công
    "red":      "#ef4444",   # Đỏ lỗi
    "yellow":   "#f59e0b",   # Vàng cảnh báo
}

BASE = Path(__file__).parent
PY   = sys.executable

# Tìm PHP tự động
def find_php() -> str:
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
    return r"C:\xampp\php\php.exe"  # fallback

PHP = find_php()

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

def write_env(env: dict):
    content = "\n".join(f"{k}={v}" for k, v in env.items())
    (BASE / ".env").write_text(content, "utf-8")

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
        self.geometry("1050x680")
        self.minsize(900, 600)

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
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=C["sidebar"])
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
                img = img.resize((90, 90), Image.LANCZOS)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(90, 90))
            except: pass

        if self._logo_img:
            ctk.CTkLabel(self.sidebar, image=self._logo_img, text="").pack(pady=(18, 4))
        else:
            ctk.CTkLabel(self.sidebar, text="⚽", font=ctk.CTkFont(size=36)).pack(pady=(18, 4))

        ctk.CTkLabel(self.sidebar, text="AutoPoster Pro",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color=C["text"]).pack(pady=(0, 2))
        ctk.CTkLabel(self.sidebar, text=f"Xiata  ·  {VERSION}",
                     font=ctk.CTkFont(size=10), text_color=C["muted"]).pack(pady=(0, 16))

        ctk.CTkLabel(self.sidebar, text="NAVIGATION", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#1e3a5f").pack(anchor="w", padx=20, pady=(0,6))

        self.nav_buttons = {}
        menus = [
            ("dashboard",  " ▣  Trang chủ"),
            ("post",       " ▶  Đăng bài"),
            ("schedule",   " ◐  Lịch hẹn"),
            ("chat",       " ◆  Chat AI"),
            ("settings",   " ▪  Cài đặt"),
            ("logs",       " ▫  Nhật ký"),
        ]
        for key, label in menus:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=12),
                fg_color="transparent", hover_color="#0d2044",
                text_color=C["muted"], height=38, corner_radius=6,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=10, pady=1)
            self.nav_buttons[key] = btn

        # Nút chuyển sáng/tối
        self.sidebar.pack_propagate(False)
        self._is_dark = True
        self.btn_theme = ctk.CTkButton(
            self.sidebar, text="☀  Chế độ Sáng", height=32,
            font=ctk.CTkFont(size=10),
            fg_color="transparent", border_width=1, border_color="#1a3a5c",
            hover_color="#0d2044", text_color=C["muted"],
            command=self._toggle_theme
        )
        self.btn_theme.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

        # Trạng thái Chrome ở dưới sidebar
        self.chrome_label = ctk.CTkLabel(self.sidebar, text="●  Chrome: offline",
                                          font=ctk.CTkFont(size=10), text_color="#1e3a5f")
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
            btn.configure(fg_color="#0d2044" if k == key else "transparent",
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
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color=C["card"],
                         border_width=1, border_color=C["border"])
        f.pack(fill="x", padx=20, pady=pady)
        if title:
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=C["muted"]).pack(anchor="w", padx=16, pady=(14,4))
        return f

    # ════════════ DASHBOARD ════════════
    def _build_dashboard(self):
        p = self.pages["dashboard"]

        ctk.CTkLabel(p, text="Overview", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=24, pady=(24,2))
        self.dash_time = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=11),
                                       text_color=C["muted"])
        self.dash_time.pack(anchor="w", padx=24, pady=(0,16))

        # Status row
        sf = ctk.CTkFrame(p, fg_color="transparent")
        sf.pack(fill="x", padx=20, pady=(0,12))
        sf.columnconfigure((0,1,2,3), weight=1)

        self.stat_cards = {}
        stats = [
            ("chrome",   "CHROME",    "Checking..."),
            ("fb_pages", "FB PAGES",  "Not set"),
            ("grok",     "GROK AI",   "Not set"),
            ("gemini",   "GEMINI AI", "Not set"),
        ]
        for i, (k, title, default) in enumerate(stats):
            card = ctk.CTkFrame(sf, corner_radius=10, fg_color=C["card"],
                                border_width=1, border_color=C["border"], height=90)
            card.grid(row=0, column=i, padx=5, sticky="ew")
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=C["muted"]).pack(anchor="w", padx=14, pady=(14,2))
            lbl = ctk.CTkLabel(card, text=default, font=ctk.CTkFont(size=12, weight="bold"),
                               text_color=C["text"])
            lbl.pack(anchor="w", padx=14)
            self.stat_cards[k] = lbl

        # Latest post
        c2 = self._card(p, "LATEST POST")
        self.latest_post_lbl = ctk.CTkTextbox(c2, height=160, font=ctk.CTkFont(size=12),
                                               fg_color=C["bg"], text_color="#94a3b8",
                                               border_width=0)
        self.latest_post_lbl.pack(fill="x", padx=16, pady=(0,14))
        self.latest_post_lbl.insert("end", "No posts yet. Go to Post tab to get started.")
        self.latest_post_lbl.configure(state="disabled")

    def _refresh_dashboard(self):
        self.dash_time.configure(text=f"Cập nhật: {datetime.now().strftime('%H:%M:%S  %d/%m/%Y')}")

        # Chrome
        ok = check_chrome()
        self.stat_cards["chrome"].configure(
            text="✅ Đã kết nối" if ok else "❌ Chưa kết nối",
            text_color="#3fb950" if ok else "#da3633"
        )
        self.chrome_label.configure(
            text=f"● Chrome: {'OK' if ok else 'Chưa kết nối'}",
            text_color="#3fb950" if ok else "#da3633"
        )

        # .env keys
        env = read_env()
        def key_ok(v): return bool(v) and "THAY" not in v

        pages_val = env.get("FB_PAGES", "")
        pages_count = len([x for x in pages_val.split(",") if x.strip() and "THAY" not in x]) if pages_val else 0
        self.stat_cards["fb_pages"].configure(
            text=f"✅ {pages_count} trang" if pages_count else "❌ Chưa thiết lập",
            text_color="#3fb950" if pages_count else "#da3633"
        )
        self.stat_cards["grok"].configure(
            text="✅ Đã thiết lập" if key_ok(env.get("GROK_API_KEY","")) else "❌ Chưa có",
            text_color="#3fb950" if key_ok(env.get("GROK_API_KEY","")) else "#8b949e"
        )
        self.stat_cards["gemini"].configure(
            text="✅ Đã thiết lập" if key_ok(env.get("GEMINI_API_KEY","")) else "❌ Chưa có",
            text_color="#3fb950" if key_ok(env.get("GEMINI_API_KEY","")) else "#8b949e"
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
        ctk.CTkLabel(p, text="✨  Tạo & Đăng bài", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,16))

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
            sf2 = ctk.CTkFrame(steps_frame, fg_color="#0d1117", corner_radius=8)
            sf2.grid(row=0, column=col, padx=4, sticky="ew", pady=4)
            num_lbl = ctk.CTkLabel(sf2, text=num, width=28, height=28,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color="#30363d", corner_radius=14,
                                   text_color="#8b949e")
            num_lbl.pack(side="left", padx=(10, 6), pady=10)
            txt = ctk.CTkLabel(sf2, text=label, font=ctk.CTkFont(size=12),
                               text_color="#8b949e")
            txt.pack(side="left", pady=10)
            self._step_lbls[k] = (num_lbl, txt)

        # Controls row
        ctrl = ctk.CTkFrame(cc, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 6))

        self.btn_open_chrome = ctk.CTkButton(
            ctrl, text="🟢  Mở Chrome", width=140, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            command=self._open_chrome)
        self.btn_open_chrome.pack(side="left", padx=(0, 8))

        self.btn_check_fb = ctk.CTkButton(
            ctrl, text="🔍  Kiểm tra Đăng nhập", width=170, height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d", hover_color="#30363d",
            command=self._check_fb_status)
        self.btn_check_fb.pack(side="left", padx=(0, 8))

        self.btn_goto_fb = ctk.CTkButton(
            ctrl, text="📲  Vào Facebook", width=140, height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d", hover_color="#30363d",
            command=self._goto_facebook)
        self.btn_goto_fb.pack(side="left")

        # Status label
        self.chrome_status_lbl = ctk.CTkLabel(
            cc, text="● Nhấn Mở Chrome để bắt đầu",
            font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.chrome_status_lbl.pack(anchor="w", padx=16, pady=(0, 4))

        # Pages list
        self.chrome_pages_lbl = ctk.CTkLabel(
            cc, text="", font=ctk.CTkFont(size=11), text_color="#8b949e",
            justify="left")
        self.chrome_pages_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Chrome path info
        chrome_path = find_chrome_path()
        path_color = "#3fb950" if chrome_path else "#da3633"
        path_text = f"📂 Chrome: {chrome_path}" if chrome_path else "❌ Không tìm thấy Chrome! Hãy kiểm tra cài đặt."
        ctk.CTkLabel(cc, text=path_text, font=ctk.CTkFont(size=10),
                     text_color=path_color).pack(anchor="w", padx=16, pady=(0, 12))

        # ── Workflow ──
        bf = self._card(p, "🎛️ Quy trình")

        # Full one-click
        full_row = ctk.CTkFrame(bf, fg_color="#0d1117", corner_radius=8)
        full_row.pack(fill="x", padx=16, pady=(0,10))
        ctk.CTkLabel(full_row, text="⚡ Chạy toàn bộ (1 click)",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#e6edf3").pack(side="left", padx=12, pady=10)
        self.btn_full = ctk.CTkButton(full_row, text="🚀  CHẠY NGAY", width=140, height=34,
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      fg_color="#238636", hover_color="#2ea043",
                                      command=self._run_full_workflow)
        self.btn_full.pack(side="right", padx=12, pady=10)

        ctk.CTkLabel(bf, text="— hoặc từng bước —", font=ctk.CTkFont(size=11),
                     text_color="#484f58").pack(pady=(0,8))

        row = ctk.CTkFrame(bf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0,14))
        self.btn_preview  = ctk.CTkButton(row, text="👁  Xem trước tin", width=150, height=36,
                                           font=ctk.CTkFont(size=12), fg_color="#21262d", hover_color="#30363d",
                                           command=lambda: self._run_post_action("preview"))
        self.btn_preview.pack(side="left", padx=(0,8))
        self.btn_generate = ctk.CTkButton(row, text="✨  Tạo bài (AI)", width=150, height=36,
                                           font=ctk.CTkFont(size=12), fg_color="#1f6feb", hover_color="#388bfd",
                                           command=lambda: self._run_post_action("generate"))
        self.btn_generate.pack(side="left", padx=(0,8))
        self.btn_chrome   = ctk.CTkButton(row, text="📤  Đăng qua Chrome", width=160, height=36,
                                           font=ctk.CTkFont(size=12), fg_color="#6e40c9", hover_color="#8957e5",
                                           command=lambda: self._run_post_action("chrome"))
        self.btn_chrome.pack(side="left")

        self.post_status = ctk.CTkLabel(bf, text="", font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.post_status.pack(anchor="w", padx=16, pady=(0,6))

        # Output
        oc = self._card(p, "📤 Output")
        self.post_output = ctk.CTkTextbox(oc, height=340, font=ctk.CTkFont(size=11, family="Courier New"),
                                          fg_color="#010409", text_color="#7ee787", border_width=0)
        self.post_output.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self.post_output.insert("end", "Nhấn một nút ở trên để bắt đầu...\n")
        self.post_output.configure(state="disabled")

    def _open_chrome(self):
        chrome_path = find_chrome_path()
        if not chrome_path:
            self.chrome_status_lbl.configure(
                text="❌ Không tìm thấy Chrome! Kiểm tra cài đặt.",
                text_color="#da3633")
            return

        profile_dir = str(BASE / "chrome_profile")
        self.btn_open_chrome.configure(state="disabled", text="⏳ Đang mở...")
        self.chrome_status_lbl.configure(text="⏳ Đang khởi động Chrome...", text_color="#d29922")
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
                        text_color="#3fb950")
                else:
                    self._set_step(1, "error")
                    self.chrome_status_lbl.configure(
                        text="❌ Chrome mở nhưng chưa kết nối được",
                        text_color="#da3633")
            self.after(0, _upd)
        threading.Thread(target=_do_open, daemon=True).start()

    def _goto_facebook(self):
        """Dẫn Chrome đang chạy đến facebook.com"""
        if not check_chrome():
            self.chrome_status_lbl.configure(
                text="⚠️ Chrome chưa mở — nhấn Mở Chrome trước", text_color="#d29922")
            return
        try:
            import urllib.request
            url = "http://127.0.0.1:9222/json/new?https://www.facebook.com"
            urllib.request.urlopen(url, timeout=2)
            self.chrome_status_lbl.configure(
                text="✅ Đã mở tab Facebook trong Chrome", text_color="#3fb950")
        except:
            self.chrome_status_lbl.configure(
                text="⚠️ Không thể mở tab mới", text_color="#d29922")

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
                        text_color="#da3633")
                    return

                self._set_step(1, "done")
                logged_in = check_fb_logged_in(info["fb_url"])

                if logged_in:
                    self._set_step(2, "done")
                    self._set_step(3, "done")
                    pages_info = "\n".join(f"   • facebook.com/{pg}" for pg in pages) or "   (Chưa có trang nào — vào Cài đặt để thêm)"
                    self.chrome_status_lbl.configure(
                        text=f"✅ Đã đăng nhập Facebook! {info['tabs']} tab đang mở.",
                        text_color="#3fb950")
                    self.chrome_pages_lbl.configure(
                        text=f"🎯 Trang sẽ đăng bài:\n{pages_info}",
                        text_color="#58a6ff")
                else:
                    self._set_step(2, "error")
                    self.chrome_status_lbl.configure(
                        text="⚠️ Chrome mở nhưng chưa đăng nhập Facebook — nhấn Vào Facebook",
                        text_color="#d29922")
                    self.chrome_pages_lbl.configure(text="")
            self.after(0, _upd)
        threading.Thread(target=_do, daemon=True).start()

    def _set_step(self, step: int, state: str):
        """Cập nhật hiển thị step wizard: pending/done/error"""
        key = f"step{step}"
        if key not in self._step_lbls: return
        num_lbl, txt = self._step_lbls[key]
        colors = {
            "pending": ("#d29922", "#d29922", "#484f58"),
            "done":    ("#3fb950", "#ffffff", "#238636"),
            "error":   ("#da3633", "#ffffff", "#67060c"),
            "idle":    ("#8b949e", "#8b949e", "#30363d"),
        }
        tc, ntc, nbg = colors.get(state, colors["idle"])
        prefix = {"done": "✓", "error": "✕", "pending": "●"}.get(state, str(step))
        num_lbl.configure(text=prefix, text_color=ntc, fg_color=nbg)
        txt.configure(text_color=tc)

    def _run_full_workflow(self):
        """Chạy toàn bộ: PHP scrape+AI → Chrome post"""
        all_btns = [self.btn_full, self.btn_preview, self.btn_generate, self.btn_chrome]
        for b in all_btns: b.configure(state="disabled")
        self.post_status.configure(text="⏳ Đang chạy toàn bộ quy trình...", text_color="#d29922")
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"🚀 BẮT ĐẦU TOÀN BỘ QUY TRÌNH — {datetime.now().strftime('%H:%M:%S')}\n")
        self.post_output.insert("end", "=" * 50 + "\n\n")
        self.post_output.configure(state="disabled")

        def _full_run():
            py_path = PY
            steps = [
                ("📰 Bước 1: Thu thập tin + AI tạo bài",
                 [PHP, str(BASE/"run_football_post.php"), "preview-post"]),
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
                    text_color="#3fb950" if final_ok else "#da3633"
                )
                for b in all_btns: b.configure(state="normal")
                self._refresh_dashboard()
            self.after(0, _done)

        threading.Thread(target=_full_run, daemon=True).start()

    def _run_post_action(self, action):
        btns = [self.btn_full, self.btn_preview, self.btn_generate, self.btn_chrome]
        for b in btns: b.configure(state="disabled")
        labels = {"preview": "Đang lấy tin tức...", "generate": "AI đang tạo bài...", "chrome": "Đang đăng qua Chrome..."}
        self.post_status.configure(text=f"⏳ {labels.get(action)}", text_color="#d29922")
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"▶ {datetime.now().strftime('%H:%M:%S')} — {action}\n\n")
        self.post_output.configure(state="disabled")
        cmd_map = {
            "preview":  [PHP, str(BASE/"run_football_post.php"), "preview-post"],
            "generate": [PHP, str(BASE/"run_football_post.php"), "preview-post"],
            "chrome":   [PY, str(BASE/"chrome_poster.py")],
        }
        def on_done(out, ok):
            def _u():
                self.post_output.configure(state="normal")
                self.post_output.insert("end", out)
                self.post_output.see("end")
                self.post_output.configure(state="disabled")
                self.post_status.configure(text="✅ Hoàn thành!" if ok else "❌ Lỗi",
                                            text_color="#3fb950" if ok else "#da3633")
                for b in btns: b.configure(state="normal")
            self.after(0, _u)
        run_cmd(cmd_map[action], on_done)

    # ════════════ SCHEDULE ════════════
    def _build_schedule(self):
        p = self.pages["schedule"]
        ctk.CTkLabel(p, text="⏰  Lịch hẹn tự động", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,4))
        ctk.CTkLabel(p, text="Thiết lập giờ tự động chạy toàn bộ quy trình mỗi ngày",
                     font=ctk.CTkFont(size=12), text_color="#8b949e").pack(anchor="w", padx=20, pady=(0,16))

        sc = self._card(p, "🕐 Giờ đăng bài tự động")
        self._sched_entries = []
        default_times = ["07:00", "13:00", "20:00"]
        for t in default_times:
            row = ctk.CTkFrame(sc, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(row, text="🕐", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0,8))
            e = ctk.CTkEntry(row, width=80, height=34, font=ctk.CTkFont(size=13),
                             fg_color="#0d1117", border_color="#30363d")
            e.insert(0, t)
            e.pack(side="left")
            ctk.CTkLabel(row, text="(HH:MM)", font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(side="left", padx=8)
            self._sched_entries.append(e)

        btn_row = ctk.CTkFrame(sc, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8,14))
        ctk.CTkButton(btn_row, text="✅  Bật lịch hẹn", width=150, height=36,
                      font=ctk.CTkFont(size=13), fg_color="#238636", hover_color="#2ea043",
                      command=self._apply_schedule).pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="⛔  Tắt lịch hẹn", width=150, height=36,
                      font=ctk.CTkFont(size=13), fg_color="#da3633", hover_color="#f85149",
                      command=self._cancel_schedule).pack(side="left")

        self.sched_status = ctk.CTkLabel(sc, text="● Chưa bật lịch hẹn",
                                          font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.sched_status.pack(anchor="w", padx=16, pady=(0,8))

        # Next run preview
        nc = self._card(p, "📅 Lần chạy tiếp theo")
        self.next_run_lbl = ctk.CTkLabel(nc, text="Chưa có lịch",
                                          font=ctk.CTkFont(size=13), text_color="#8b949e")
        self.next_run_lbl.pack(anchor="w", padx=16, pady=(0,14))

    def _apply_schedule(self):
        schedule.clear()
        times = [e.get().strip() for e in self._sched_entries if e.get().strip()]
        for t in times:
            schedule.every().day.at(t).do(self._run_full_workflow)
        self._sched_running = True
        self.sched_status.configure(
            text=f"✅ Đang chạy — lịch: {', '.join(times)}", text_color="#3fb950")
        self._update_next_run()

    def _cancel_schedule(self):
        schedule.clear()
        self._sched_running = False
        self.sched_status.configure(text="⛔ Đã tắt lịch hẹn", text_color="#da3633")
        self.next_run_lbl.configure(text="Không có lịch")

    def _update_next_run(self):
        nj = schedule.next_run()
        if nj:
            self.next_run_lbl.configure(
                text=f"⏰ {nj.strftime('%H:%M  %d/%m/%Y')}", text_color="#e6edf3")

    def _start_scheduler_thread(self):
        def _loop():
            while True:
                schedule.run_pending()
                time.sleep(30)
        threading.Thread(target=_loop, daemon=True).start()

    # ════════════ CHAT AI ════════════
    def _build_chat(self):
        p = self.pages["chat"]
        ctk.CTkLabel(p, text="💬  Chat AI", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,4))
        ctk.CTkLabel(p, text="Trò chuyện với Grok hoặc Gemini AI (dùng key trong Cài đặt)",
                     font=ctk.CTkFont(size=12), text_color="#8b949e").pack(anchor="w", padx=20, pady=(0,12))

        # Model selector
        sel_row = ctk.CTkFrame(p, fg_color="transparent")
        sel_row.pack(fill="x", padx=20, pady=(0,10))
        ctk.CTkLabel(sel_row, text="🤖 AI:", font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0,8))
        self.chat_ai_var = ctk.StringVar(value="auto")
        for val, label in [("auto","🔁 Tự động"), ("grok","🟣 Grok"), ("gemini","🔵 Gemini")]:
            ctk.CTkRadioButton(sel_row, text=label, variable=self.chat_ai_var, value=val,
                               font=ctk.CTkFont(size=12), text_color="#c9d1d9").pack(side="left", padx=8)

        # Chat history display
        chat_card = ctk.CTkFrame(p, corner_radius=10, fg_color="#161b22",
                                  border_width=1, border_color="#30363d")
        chat_card.pack(fill="x", padx=20, pady=(0,10))
        self.chat_box = ctk.CTkTextbox(chat_card, height=400,
                                        font=ctk.CTkFont(size=12),
                                        fg_color="#0d1117", text_color="#e6edf3",
                                        border_width=0, wrap="word")
        self.chat_box.pack(fill="both", padx=12, pady=12, expand=True)
        self.chat_box.insert("end", "🤖 Xin chào! Tôi là trợ lý AI. Hãy đặt câu hỏi cho tôi!\n\n")
        self.chat_box.configure(state="disabled")

        # Input row
        inp_row = ctk.CTkFrame(p, fg_color="transparent")
        inp_row.pack(fill="x", padx=20, pady=(0,16))
        inp_row.columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(
            inp_row, placeholder_text="Nhập câu hỏi... (Enter để gửi)",
            font=ctk.CTkFont(size=13), height=42,
            fg_color="#161b22", border_color="#30363d")
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())

        self.btn_send_chat = ctk.CTkButton(
            inp_row, text="📨 Gửi", width=90, height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            command=self._send_chat)
        self.btn_send_chat.grid(row=0, column=1)

        ctk.CTkButton(p, text="🗑 Xoá lịch sử", height=32,
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", border_width=1, border_color="#30363d",
                      hover_color="#21262d", text_color="#8b949e",
                      command=self._clear_chat).pack(anchor="e", padx=20, pady=(0,16))

    def _append_chat(self, role: str, text: str):
        colors = {"👤 Bạn": "#58a6ff", "🤖 AI": "#3fb950", "⚠️ Lỗi": "#da3633"}
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{role}:\n", role)
        self.chat_box.insert("end", f"{text}\n\n")
        self.chat_box.tag_config(role, foreground=colors.get(role, "#e6edf3"))
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def _clear_chat(self):
        self._chat_history = []
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.insert("end", "🤖 Lịch sử đã được xoá. Hãy bắt đầu cuộc trò chuyện mới!\n\n")
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
            grok_key   = env.get("GROK_API_KEY", "")
            gemini_key = env.get("GEMINI_API_KEY", "")
            grok_model   = env.get("GROK_MODEL", "grok-3-mini-fast")
            gemini_model = env.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

            reply = None; provider = ""
            if ai_choice in ("auto", "grok") and grok_key and "THAY" not in grok_key:
                reply, provider = self._chat_grok(self._chat_history, grok_key, grok_model)
            if reply is None and ai_choice in ("auto", "gemini") and gemini_key and "THAY" not in gemini_key:
                reply, provider = self._chat_gemini(self._chat_history, gemini_key, gemini_model)
            if reply is None:
                reply = "❌ Chưa cấu hình API Key!\nVào ⚙️ Cài đặt → điền GROK_API_KEY hoặc GEMINI_API_KEY → Lưu cài đặt."
                provider = "error"

            if provider != "error":
                self._chat_history.append({"role": "assistant", "content": reply})

            def _upd():
                role = "🤖 AI" if provider != "error" else "⚠️ Lỗi"
                self._append_chat(role, reply)
                self.btn_send_chat.configure(state="normal", text="📨 Gửi")
            self.after(0, _upd)

        threading.Thread(target=_do, daemon=True).start()

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
        ctk.CTkLabel(p, text="⚙️  Cài đặt", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,16))

        self.setting_fields = {}
        sections = [
            ("📘 Facebook — Danh sách trang đăng bài", [
                ("FB_PAGES", "Trang Facebook (ngăn cách bằng dấu phẩy)",
                 "VD: myfanpage,another.page hoặc https://facebook.com/page"),
            ]),
            ("🟣 Grok AI (xAI)", [
                ("GROK_API_KEY",  "API Key", "xai-..."),
                ("GROK_MODEL",    "Model",   "grok-3-mini-fast"),
            ]),
            ("🔵 Gemini AI", [
                ("GEMINI_API_KEY", "API Key", "AIzaSy..."),
                ("GEMINI_MODEL",   "Model",   "gemini-2.5-flash-lite"),
            ]),
        ]

        env = read_env()
        for sec_title, fields in sections:
            card = self._card(p, sec_title)
            for key, label, placeholder in fields:
                ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12),
                             text_color="#8b949e").pack(anchor="w", padx=16, pady=(6,2))
                # FB_PAGES: text area lớn hơn để nhập nhiều trang
                if key == "FB_PAGES":
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         font=ctk.CTkFont(size=12), height=38,
                                         fg_color="#0d1117", border_color="#30363d")
                    ctk.CTkLabel(card, text="💡 Mỗi slug cách nhau bằng dấu phẩy. VD: page1,page2,page3",
                                 font=ctk.CTkFont(size=10), text_color="#484f58").pack(anchor="w", padx=16)
                else:
                    show = "*" if "TOKEN" in key or "KEY" in key else None
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         show=show,
                                         font=ctk.CTkFont(size=12), height=36,
                                         fg_color="#0d1117", border_color="#30363d")
                entry.pack(fill="x", padx=16, pady=(0,4))
                val = env.get(key, "")
                if val and "THAY" not in val:
                    entry.insert(0, val)
                self.setting_fields[key] = entry
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

        # Save button
        self.save_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=12))
        self.save_status.pack(anchor="w", padx=20)
        ctk.CTkButton(p, text="💾  Lưu cài đặt", height=40, font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color="#238636", hover_color="#2ea043",
                      command=self._save_settings).pack(anchor="w", padx=20, pady=(8,24))

    def _save_settings(self):
        env = {}
        for key, entry in self.setting_fields.items():
            val = entry.get().strip()
            if val:
                env[key] = val
        write_env(env)
        self.save_status.configure(text="✅ Đã lưu!", text_color="#3fb950")
        self.after(3000, lambda: self.save_status.configure(text=""))

    # ════════════ LOGS ════════════
    def _build_logs(self):
        p = self.pages["logs"]
        ctk.CTkLabel(p, text="📋  Nhật ký", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,4))

        # Tab row
        tf = ctk.CTkFrame(p, fg_color="transparent")
        tf.pack(fill="x", padx=20, pady=(0,12))

        self.log_tabs = {}
        self.current_log = "workflow"
        for key, label in [("workflow","Workflow"), ("chrome","Chrome"), ("cron","Cron")]:
            btn = ctk.CTkButton(
                tf, text=label, width=100, height=30,
                font=ctk.CTkFont(size=12),
                fg_color="#1f6feb" if key=="workflow" else "#21262d",
                hover_color="#388bfd",
                command=lambda k=key: self._switch_log(k)
            )
            btn.pack(side="left", padx=(0,6))
            self.log_tabs[key] = btn

        # Refresh button
        ctk.CTkButton(tf, text="🔄 Làm mới", width=90, height=30,
                      font=ctk.CTkFont(size=12),
                      fg_color="transparent", border_width=1, border_color="#30363d",
                      hover_color="#21262d",
                      command=self._load_logs).pack(side="left")

        # Log box
        card = self._card(p)
        self.log_box = ctk.CTkTextbox(card, height=440,
                                       font=ctk.CTkFont(size=11, family="Courier New"),
                                       fg_color="#010409", text_color="#7ee787",
                                       border_width=0)
        self.log_box.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self._load_logs()

    def _switch_log(self, key):
        self.current_log = key
        for k, btn in self.log_tabs.items():
            btn.configure(fg_color="#1f6feb" if k==key else "#21262d")
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
                    text_color="#3fb950")
            else:
                self.chrome_status_lbl.configure(
                    text="⚠️ Chrome chưa kết nối — nhấn Mở Chrome",
                    text_color="#8b949e")
        except: pass
        self.after(10000, self._refresh_loop)


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()

