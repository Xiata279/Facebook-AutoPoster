#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Football Auto Poster - Desktop App V1.0.0
Chạy: python app.py
Cài thư viện: pip install customtkinter pillow
"""

VERSION = "V1.1.0"

import os, sys, json, subprocess, threading, time, socket, hashlib
from pathlib import Path
from datetime import datetime, timedelta
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

# ── Cấu hình giao diện ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Bảng màu XIATA — Vibrant Harmony (Light / Dark) ──
# Sáng: nền trắng ngà ấm, accent cam-xanh nổi bật
# Tối: nền đen navy sâu, accent cyan điện sáng
C = {
    # Backgrounds
    "bg":              ("#F7F9FC", "#0D1117"),
    "sidebar":         ("#FFFFFF", "#161B22"),
    "panel":           ("#FFFFFF", "#1C2128"),
    "panel2":          ("#EEF2FF", "#21262D"),
    "card":            ("#FFFFFF", "#1C2128"),
    "card2":           ("#F0F4FF", "#262D3A"),
    "input":           ("#F4F7FF", "#161B22"),
    # Borders
    "border":          ("#D0D9F0", "#30363D"),
    # Text
    "text":            ("#0D1117", "#E6EDF3"),
    "muted":           ("#5A6882", "#8B949E"),
    "subtle":          ("#8896B0", "#6E7A8A"),
    # Accent — Cyan-Blue nổi bật
    "accent":          ("#2563EB", "#58A6FF"),
    "accent_hover":    ("#1D4ED8", "#79BBFF"),
    "accent2":         ("#EFF4FF", "#1F2D45"),
    "deep":            ("#1E40AF", "#93C5FD"),
    # Semantic colors
    "green":           ("#059669", "#3FB950"),
    "red":             ("#DC2626", "#F85149"),
    "yellow":          ("#D97706", "#E3B341"),
    "orange":          ("#EA580C", "#F0883E"),
    "blue":            ("#0284C7", "#79C0FF"),
    "ink":             ("#FFFFFF", "#0D1117"),
    "violet":          ("#7C3AED", "#A5B4FC"),
    "cyan":            ("#0891B2", "#22D3EE"),
    "log_text":        ("#065F46", "#56D364"),
    "progress_track":  ("#E2E8F0", "#21262D"),
    # Status backgrounds
    "status_done_bg":  ("#D1FAE5", "#1A3A2A"),
    "status_warn_bg":  ("#FEF3C7", "#3A2E0F"),
    "status_error_bg": ("#FEE2E2", "#3A1A1A"),
    "status_idle_bg":  ("#EFF4FF", "#1F2D45"),
}

BASE = Path(__file__).parent
PY   = sys.executable
ARTICLE_LINKS_FILE = BASE / "input" / "article_links.txt"
ARTICLE_HISTORY_FILE = BASE / "cache" / "article_history.json"
SCHEDULE_FILE = BASE / "input" / "scheduled_posts.json"
UI_STATE_FILE = BASE / "input" / "ui_state.json"
AUTOPILOT_FILE = BASE / "input" / "autopilot.json"
POST_QUEUE_FILE = BASE / "input" / "post_queue.json"
PAGE_PROFILES_FILE = BASE / "input" / "page_profiles.json"
CONTENT_TEMPLATES = {
    "tin_nong": ("Tin nóng", "Hook mạnh, cập nhật nhanh, ưu tiên thông tin mới nhất."),
    "nhan_dinh": ("Nhận định", "Giọng phân tích, có góc nhìn chuyên môn và bối cảnh."),
    "tranh_luan": ("Tranh luận", "Đặt vấn đề mở để kéo bình luận nhưng không giật tít quá đà."),
    "chuyen_nhuong": ("Chuyển nhượng", "Tập trung tin đồn, khả năng xảy ra, tác động đội hình."),
    "lich_thi_dau": ("Lịch thi đấu", "Rõ giờ, đối thủ, điểm đáng xem, kêu gọi dự đoán."),
    "sau_tran": ("Sau trận", "Tóm điểm nhấn, nhân vật nổi bật, cảm xúc sau trận."),
}
GEMINI_TEXT_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

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
        "FREE_AI_ONLY", "OLLAMA_BASE_URL", "OLLAMA_MODEL",
        "HF_TOKEN", "HF_MODEL",
        "AVOID_RECENT_DUPLICATES", "ARTICLE_HISTORY_DAYS", "MAX_TOTAL_ARTICLES",
        "POST_STYLE", "CONTENT_TEMPLATE", "MAX_POSTS", "MAX_ARTICLES", "FETCH_FULL_CONTENT",
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

def parse_pages(raw: str) -> list:
    pages = []
    for item in (raw or "").replace("\n", ",").split(","):
        p = item.strip()
        if not p or "THAY" in p:
            continue
        p = p.replace("https://www.facebook.com/", "").replace("https://facebook.com/", "").rstrip("/")
        if p and p not in pages:
            pages.append(p)
    return pages

def read_ui_state() -> dict:
    try:
        if UI_STATE_FILE.exists():
            data = json.loads(UI_STATE_FILE.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
    except:
        pass
    return {}

def write_ui_state(updates: dict):
    state = read_ui_state()
    state.update(updates)
    UI_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")

def normalize_image_paths(data: dict) -> list:
    paths = []
    for p in data.get("image_paths") or []:
        if p and p not in paths:
            paths.append(p)
    p = data.get("image_path")
    if p and p not in paths:
        paths.insert(0, p)
    return paths

def read_latest_post() -> dict:
    jp = BASE / "output" / "latest_post.json"
    if not jp.exists():
        return {}
    try:
        data = json.loads(jp.read_text("utf-8"))
        if isinstance(data, dict):
            data["post_content"] = (data.get("post_content") or data.get("content") or "").strip()
            data["image_paths"] = normalize_image_paths(data)
            data["image_path"] = data["image_paths"][0] if data["image_paths"] else data.get("image_path")
            return data
    except:
        pass
    return {}

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

def check_ollama() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 11434), timeout=1)
        s.close(); return True
    except:
        return False

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
        self.title(f"XIATA POST OPS  —  {VERSION}")
        self.geometry("1240x820")
        self.minsize(1060, 700)

        self.current_page = None
        self._scheduled_jobs = self._load_schedule_jobs()
        self._autopilot = self._load_autopilot_config()
        self._post_queue = self._load_post_queue()
        self._preview_img = None
        self._scheduler_busy = False
        self._is_dark = read_ui_state().get("theme", "dark") != "light"
        ctk.set_appearance_mode("dark" if self._is_dark else "light")
        self._build_layout()
        self._show_page("dashboard")

        # Auto refresh mỗi 10s
        self._refresh_loop()

    # ─── Layout chính ───
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=C["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self._logo_img = None

        # ── Brand block ──
        brand = ctk.CTkFrame(self.sidebar, fg_color=C["accent2"], corner_radius=14,
                             border_width=1, border_color=C["border"])
        brand.pack(fill="x", padx=12, pady=(16, 12))
        brand_top = ctk.CTkFrame(brand, fg_color="transparent")
        brand_top.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(brand_top, text="⚡", width=52, height=52,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     fg_color=C["accent"], text_color=C["ink"],
                     corner_radius=13).pack(side="left", padx=(0, 10))
        title_box = ctk.CTkFrame(brand_top, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_box, text="XIATA POST OPS",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"Publishing Suite  ·  {VERSION}",
                     font=ctk.CTkFont(size=10),
                     text_color=C["muted"]).pack(anchor="w", pady=(2, 0))
        # Accent divider
        div = ctk.CTkFrame(brand, height=3, fg_color=C["accent"], corner_radius=6)
        div.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(brand, text="🔵  Content · Chrome · AI",
                     font=ctk.CTkFont(size=10),
                     text_color=C["muted"]).pack(anchor="w", padx=14, pady=(0, 10))

        # ── Nav section label ──
        ctk.CTkLabel(self.sidebar, text="  MENU",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=14, pady=(4, 6))

        self.nav_buttons = {}
        menus = [
            ("dashboard", "🏠", "Tổng quan"),
            ("post",      "✏️", "Tạo bài & Đăng"),
            ("schedule",  "📅", "Lịch xuất bản"),
            ("chat",      "💬", "Trợ lý AI"),
            ("settings",  "⚙️", "Cấu hình"),
            ("logs",      "📋", "Nhật ký"),
        ]
        for key, icon, label in menus:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}  {label}",
                anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                hover_color=C["panel2"],
                text_color=C["muted"],
                height=44,
                corner_radius=10,
                border_width=0,
                border_color=C["border"],
                command=lambda k=key: self._show_page(k)
            )
            try:
                btn.configure(cursor="hand2")
            except:
                pass
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Nút chuyển sáng/tối
        self.sidebar.pack_propagate(False)
        self.btn_theme = self._button(
            self.sidebar, "🌙  Chế độ sáng" if self._is_dark else "☀️  Chế độ tối",
            variant="outline", height=36, font_size=11,
            command=self._toggle_theme
        )
        self.btn_theme.pack(side="bottom", fill="x", padx=12, pady=(0, 6))

        # Trạng thái Chrome ở dưới sidebar
        self.chrome_label = ctk.CTkLabel(
            self.sidebar, text="⚪  Chrome: offline",
            font=ctk.CTkFont(size=11), text_color=C["subtle"]
        )
        self.chrome_label.pack(side="bottom", pady=(4, 2), padx=14)

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Pages container
        self.pages = {}
        for key in ["dashboard", "post", "schedule", "chat", "settings", "logs"]:
            frame = ctk.CTkScrollableFrame(self.content, fg_color=C["bg"],
                                            scrollbar_button_color=C["border"])
            frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            frame.grid_remove()
            self.pages[key] = frame

        self._build_dashboard()
        self._build_post()
        self._build_schedule()
        self._build_chat()
        self._build_settings()
        self._build_logs()
        self._sync_autopilot_jobs()
        self._sched_running = any(j.get("status") == "scheduled" for j in self._scheduled_jobs)
        self._chat_history = []  # lưu lịch sử chat
        self._start_scheduler_thread()

    def _show_page(self, key):
        for k, f in self.pages.items():
            f.grid_remove()
        self.pages[key].grid()
        self.current_page = key

        # Highlight nav button — pill style
        icons = {"dashboard": "🏠", "post": "✏️", "schedule": "📅",
                 "chat": "💬", "settings": "⚙️", "logs": "📋"}
        labels_map = {"dashboard": "Tổng quan", "post": "Tạo bài & Đăng",
                      "schedule": "Lịch xuất bản", "chat": "Trợ lý AI",
                      "settings": "Cấu hình", "logs": "Nhật ký"}
        for k, btn in self.nav_buttons.items():
            active = k == key
            icon = icons.get(k, "")
            lbl  = labels_map.get(k, k)
            btn.configure(
                text=f"  {icon}  {lbl}",
                fg_color=C["accent2"] if active else "transparent",
                text_color=C["accent"] if active else C["muted"],
                font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
                border_width=1 if active else 0,
                border_color=C["accent"] if active else C["border"]
            )

    def _button(self, parent, text, variant="secondary", width=120, height=36,
                command=None, font_size=12, bold=False, **kwargs):
        styles = {
            "primary": {
                "fg_color": C["accent"],
                "hover_color": C["accent_hover"],
                "text_color": C["ink"],
                "border_width": 0,
            },
            "secondary": {
                "fg_color": C["panel2"],
                "hover_color": C["border"],
                "text_color": C["text"],
                "border_width": 1,
            },
            "outline": {
                "fg_color": "transparent",
                "hover_color": C["panel2"],
                "text_color": C["muted"],
                "border_width": 1,
            },
            "soft": {
                "fg_color": C["card2"],
                "hover_color": C["panel2"],
                "text_color": C["accent"],
                "border_width": 1,
            },
            "danger": {
                "fg_color": "transparent",
                "hover_color": C["status_error_bg"],
                "text_color": C["red"],
                "border_width": 1,
            },
        }
        style = styles.get(variant, styles["secondary"]).copy()
        border_width = style.pop("border_width", 0)
        btn = ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=height,
            corner_radius=9,
            border_width=border_width,
            border_color=C["border"],
            font=ctk.CTkFont(size=font_size, weight="bold" if bold else "normal"),
            command=command,
            **style,
            **kwargs,
        )
        try:
            btn.configure(cursor="hand2")
        except:
            pass
        self._attach_button_feedback(btn, variant, style, border_width)
        return btn

    def _attach_button_feedback(self, btn, variant, style, border_width):
        default_normal = {
            "fg_color": style.get("fg_color"),
            "text_color": style.get("text_color"),
            "border_color": C["border"],
            "border_width": border_width,
        }
        pressed = {
            "primary": {
                "fg_color": C["deep"],
                "text_color": C["ink"],
                "border_color": C["deep"],
                "border_width": max(1, border_width),
            },
            "secondary": {
                "fg_color": C["accent2"],
                "text_color": C["deep"],
                "border_color": C["accent"],
                "border_width": max(1, border_width),
            },
            "outline": {
                "fg_color": C["card2"],
                "text_color": C["deep"],
                "border_color": C["accent"],
                "border_width": max(1, border_width),
            },
            "soft": {
                "fg_color": C["panel2"],
                "text_color": C["deep"],
                "border_color": C["accent"],
                "border_width": max(1, border_width),
            },
            "danger": {
                "fg_color": C["status_error_bg"],
                "text_color": C["red"],
                "border_color": C["red"],
                "border_width": max(1, border_width),
            },
        }.get(variant, {})

        def is_ready():
            try:
                return btn.cget("state") != "disabled"
            except:
                return True

        def apply_state(values):
            try:
                btn.configure(**{k: v for k, v in values.items() if v is not None})
            except:
                pass

        def read_button_state(fallback):
            values = {}
            for key in ("fg_color", "text_color", "border_color", "border_width"):
                try:
                    values[key] = btn.cget(key)
                except:
                    values[key] = fallback.get(key)
            return values

        def is_pressed_state():
            current = read_button_state({})
            for key, value in pressed.items():
                if current.get(key) != value:
                    return False
            return True

        def press(_event=None):
            if is_ready():
                btn._xiata_restore_state = read_button_state(default_normal)
                apply_state(pressed)

        def release(_event=None):
            if is_ready():
                restore = getattr(btn, "_xiata_restore_state", default_normal)
                btn.after(85, lambda: apply_state(restore) if is_pressed_state() else None)

        try:
            btn.bind("<ButtonPress-1>", press, add="+")
            btn.bind("<ButtonRelease-1>", release, add="+")
            btn.bind("<Leave>", release, add="+")
        except:
            pass

    # ─── Chuyển sáng / tối ───
    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        if self._is_dark:
            ctk.set_appearance_mode("dark")
            self.btn_theme.configure(text="🌙  Chế độ sáng")
            write_ui_state({"theme": "dark"})
        else:
            ctk.set_appearance_mode("light")
            self.btn_theme.configure(text="☀️  Chế độ tối")
            write_ui_state({"theme": "light"})

    # ─── Card helper ───
    def _card(self, parent, title="", pady=(0,14)):
        f = ctk.CTkFrame(parent, corner_radius=14, fg_color=C["card"],
                         border_width=1, border_color=C["border"])
        f.pack(fill="x", padx=20, pady=pady)
        if title:
            hdr = ctk.CTkFrame(f, fg_color="transparent")
            hdr.pack(fill="x", padx=16, pady=(14, 0))
            # Accent dot
            ctk.CTkFrame(hdr, width=4, height=16, fg_color=C["accent"],
                         corner_radius=3).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(hdr, text=title.upper(),
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=C["muted"]).pack(side="left", anchor="w")
            ctk.CTkFrame(f, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(8, 0))
        return f

    def _page_title(self, parent, kicker, title, subtitle):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=24, pady=(24, 12))
        # Kicker pill
        pill = ctk.CTkFrame(wrap, fg_color=C["accent2"], corner_radius=20)
        pill.pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(pill, text=f"  {kicker.upper()}  ",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["accent"]).pack(padx=4, pady=2)
        ctk.CTkLabel(wrap, text=title,
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(wrap, text=subtitle,
                     font=ctk.CTkFont(size=12),
                     text_color=C["muted"], justify="left",
                     wraplength=780).pack(anchor="w")
        # Bottom rule
        ctk.CTkFrame(wrap, height=1, fg_color=C["border"]).pack(fill="x", pady=(10, 0))
        return wrap

    # ════════════ DASHBOARD ════════════
    def _build_dashboard(self):
        p = self.pages["dashboard"]

        self._page_title(
            p,
            "Operations desk",
            "Bộ điều khiển nội dung",
            "Theo dõi bài sắp đăng, Chrome, fanpage, lịch chạy và Autopilot trong một màn hình vận hành."
        )
        self.dash_time = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=11),
                                       text_color=C["muted"])
        self.dash_time.pack(anchor="w", padx=24, pady=(0,12))

        status_bar = ctk.CTkFrame(p, corner_radius=10, fg_color=C["panel"],
                                  border_width=1, border_color=C["border"])
        status_bar.pack(fill="x", padx=20, pady=(0, 14))
        ctk.CTkFrame(status_bar, height=3, fg_color=C["accent"], corner_radius=10).pack(fill="x", padx=12, pady=(12, 8))
        status_grid = ctk.CTkFrame(status_bar, fg_color="transparent")
        status_grid.pack(fill="x", padx=14, pady=(0, 12))
        status_grid.columnconfigure((0, 1, 2, 3), weight=1)

        self.dash_status = {}
        for i, (key, label) in enumerate([
            ("chrome", "Chrome"),
            ("fanpage", "Fanpage"),
            ("autopilot", "Autopilot"),
            ("next", "Lịch tiếp theo"),
        ]):
            cell = ctk.CTkFrame(status_grid, fg_color=C["card2"], corner_radius=8,
                                border_width=1, border_color=C["border"])
            cell.grid(row=0, column=i, sticky="ew", padx=4)
            ctk.CTkLabel(cell, text=label.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
            value = ctk.CTkLabel(cell, text="Đang kiểm tra", font=ctk.CTkFont(size=13, weight="bold"),
                                 text_color=C["text"])
            value.pack(anchor="w", padx=12, pady=(0, 10))
            self.dash_status[key] = value

        grid = ctk.CTkFrame(p, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=(0, 14))
        grid.columnconfigure(0, weight=2)
        grid.columnconfigure(1, weight=1)

        upcoming = ctk.CTkFrame(grid, corner_radius=10, fg_color=C["card"],
                                border_width=1, border_color=C["border"])
        upcoming.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(upcoming, text="BÀI SẮP ĐĂNG", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["muted"]).pack(anchor="w", padx=16, pady=(16, 6))
        self.latest_post_lbl = ctk.CTkTextbox(upcoming, height=210, font=ctk.CTkFont(size=12),
                                               fg_color=C["input"], text_color=C["text"],
                                               border_width=0, wrap="word")
        self.latest_post_lbl.pack(fill="both", padx=16, pady=(0,16), expand=True)
        self.latest_post_lbl.insert("end", "Chưa có bài sẵn sàng đăng. Bấm Soạn bài để tạo nội dung mới.")
        self.latest_post_lbl.configure(state="disabled")

        side = ctk.CTkFrame(grid, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew")
        today = ctk.CTkFrame(side, corner_radius=10, fg_color=C["card"],
                             border_width=1, border_color=C["border"])
        today.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(today, text="LỊCH HÔM NAY", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["muted"]).pack(anchor="w", padx=16, pady=(16, 6))
        self.dashboard_today_box = ctk.CTkTextbox(today, height=112, font=ctk.CTkFont(size=12),
                                                   fg_color=C["input"], text_color=C["text"], border_width=0)
        self.dashboard_today_box.pack(fill="x", padx=16, pady=(0, 16))
        self.dashboard_today_box.configure(state="disabled")

        auto = ctk.CTkFrame(side, corner_radius=10, fg_color=C["card"],
                            border_width=1, border_color=C["border"])
        auto.pack(fill="x")
        ctk.CTkLabel(auto, text="AUTOPILOT", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["muted"]).pack(anchor="w", padx=16, pady=(16, 6))
        self.dashboard_autopilot_lbl = ctk.CTkLabel(auto, text="Đang kiểm tra",
                                                    font=ctk.CTkFont(size=13, weight="bold"),
                                                    text_color=C["text"], justify="left")
        self.dashboard_autopilot_lbl.pack(anchor="w", padx=16, pady=(0, 4))
        self.dashboard_autopilot_hint = ctk.CTkLabel(auto, text="", font=ctk.CTkFont(size=11),
                                                     text_color=C["muted"], justify="left")
        self.dashboard_autopilot_hint.pack(anchor="w", padx=16, pady=(0, 16))

        report = self._card(p, "Báo cáo vận hành")
        self.ops_report_box = ctk.CTkTextbox(
            report, height=112, font=ctk.CTkFont(size=12, family="Courier New"),
            fg_color=C["input"], text_color=C["text"], border_width=0)
        self.ops_report_box.pack(fill="x", padx=16, pady=(0, 14))
        self.ops_report_box.configure(state="disabled")

    def _refresh_dashboard(self):
        self.dash_time.configure(text=f"Cập nhật: {datetime.now().strftime('%H:%M:%S  %d/%m/%Y')}")

        ok = check_chrome()
        if hasattr(self, "dash_status"):
            self.dash_status["chrome"].configure(
                text="OK" if ok else "Offline",
                text_color=C["green"] if ok else C["red"])
        self.chrome_label.configure(
            text=f"{'🟢' if ok else '🔴'}  Chrome: {'OK' if ok else 'offline'}",
            text_color=C["green"] if ok else C["red"]
        )

        env = read_env()

        pages_val = env.get("FB_PAGES", "")
        pages_count = len(parse_pages(pages_val)) if pages_val else 0
        active_jobs = len([j for j in self._scheduled_jobs if j.get("status") == "scheduled"])
        autopilot_on = self._autopilot.get("enabled", False)
        next_run = self._next_schedule_text(short=True)
        if hasattr(self, "dash_status"):
            self.dash_status["fanpage"].configure(
                text=f"{pages_count} page" if pages_count else "Chưa thiết lập",
                text_color=C["green"] if pages_count else C["red"])
            self.dash_status["autopilot"].configure(
                text="Đang bật" if autopilot_on else "Đang tắt",
                text_color=C["green"] if autopilot_on else C["muted"])
            self.dash_status["next"].configure(
                text=next_run or "Chưa có lịch",
                text_color=C["text"] if next_run else C["muted"])
        if hasattr(self, "dashboard_today_box"):
            self._render_today_timeline(self.dashboard_today_box, compact=True)
        if hasattr(self, "dashboard_autopilot_lbl"):
            times = ", ".join(self._autopilot.get("times", [])) or "chưa đặt giờ"
            limit = self._autopilot.get("max_daily_posts", 3)
            self.dashboard_autopilot_lbl.configure(
                text="Đang vận hành" if autopilot_on else "Đang tắt",
                text_color=C["green"] if autopilot_on else C["muted"])
            self.dashboard_autopilot_hint.configure(
                text=f"Giờ đăng: {times}\nGiới hạn: {limit} bài/ngày · {active_jobs} lịch")

        # Latest post
        d = read_latest_post()
        if d.get("post_content"):
            txt = d.get("post_content", "")[:600] + ("..." if len(d.get("post_content", "")) > 600 else "")
            self.latest_post_lbl.configure(state="normal")
            self.latest_post_lbl.delete("1.0","end")
            self.latest_post_lbl.insert("end", txt)
            self.latest_post_lbl.configure(state="disabled")
        if hasattr(self, "preview_text"):
            self._render_latest_preview()
        if hasattr(self, "queue_box"):
            self._render_post_queue()
        if hasattr(self, "ops_report_box"):
            self._render_ops_report()

    def _render_ops_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        jobs_today = [j for j in self._scheduled_jobs if (j.get("last_run_at", "")[:10] == today or j.get("date") == today)]
        success = len([j for j in jobs_today if j.get("last_result") == "success"])
        failed = len([j for j in jobs_today if j.get("last_result") in ("failed", "chrome_unavailable", "queue_empty") or j.get("status") == "failed"])
        scheduled = len([j for j in self._scheduled_jobs if j.get("status") == "scheduled"])
        queue_ready = len(self._post_queue)
        latest = read_latest_post()
        image_count = len([p for p in normalize_image_paths(latest) if p and Path(p).exists()])
        lines = [
            f"Hôm nay       {len(jobs_today)} lịch liên quan | {success} thành công | {failed} lỗi",
            f"Hàng đợi      {queue_ready} bài sẵn sàng",
            f"Bài hiện tại  {len(latest.get('post_content', ''))} ký tự | {image_count} ảnh hợp lệ",
            f"Lịch mở       {scheduled} lịch đang chờ chạy",
        ]
        self.ops_report_box.configure(state="normal")
        self.ops_report_box.delete("1.0", "end")
        self.ops_report_box.insert("end", "\n".join(lines))
        self.ops_report_box.configure(state="disabled")

    def _next_schedule_text(self, short=False):
        try:
            runs = [(self._next_job_run(job), job) for job in self._scheduled_jobs]
            runs = [(run, job) for run, job in runs if run]
            if not runs:
                return ""
            run, job = min(runs, key=lambda item: item[0])
            if short:
                return run.strftime("%H:%M hôm nay") if run.date() == datetime.now().date() else run.strftime("%d/%m %H:%M")
            source = "Autopilot" if job.get("source") == "autopilot" else "Lịch thủ công"
            action = "tạo bài + đăng" if job.get("action") == "full" else "đăng bài đã tạo"
            return f"{run.strftime('%H:%M  %d/%m/%Y')} · {source} · {action}"
        except:
            return ""

    def _render_today_timeline(self, textbox, compact=False):
        today = datetime.now().date()
        rows = []
        for job in sorted(self._scheduled_jobs, key=lambda j: j.get("time", "")):
            run = self._next_job_run(job)
            if not run or run.date() != today:
                continue
            status = job.get("status", "scheduled")
            pages = len(job.get("pages", []) or parse_pages(read_env().get("FB_PAGES", "")))
            action = "full" if job.get("action") == "full" else "post"
            rows.append(f"{run.strftime('%H:%M')}  {status:<9}  {action:<4}  {pages} page")
        if not rows:
            rows = ["Hôm nay chưa có lịch chạy."]
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("end", "\n".join(rows[:5 if compact else 20]))
        textbox.configure(state="disabled")

    def _render_week_calendar(self):
        if not hasattr(self, "week_calendar_box"):
            return
        start = datetime.now().date()
        rows = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            day_jobs = []
            for job in self._scheduled_jobs:
                run = self._next_job_run(job)
                if run and run.date() == day:
                    action = "full" if job.get("action") == "full" else "post"
                    src = "auto" if job.get("source") == "autopilot" else "manual"
                    day_jobs.append(f"{run.strftime('%H:%M')} {src}/{action}/{job.get('status','?')}")
            label = day.strftime("%d/%m")
            rows.append(f"{label}  " + (" | ".join(day_jobs) if day_jobs else "trống"))
        self.week_calendar_box.configure(state="normal")
        self.week_calendar_box.delete("1.0", "end")
        self.week_calendar_box.insert("end", "\n".join(rows))
        self.week_calendar_box.configure(state="disabled")

    def _load_post_queue(self):
        try:
            if POST_QUEUE_FILE.exists():
                data = json.loads(POST_QUEUE_FILE.read_text("utf-8"))
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict) and (x.get("post_content") or x.get("content"))]
        except:
            pass
        return []

    def _save_post_queue(self):
        POST_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        POST_QUEUE_FILE.write_text(json.dumps(self._post_queue, ensure_ascii=False, indent=2), "utf-8")

    def _queue_entry_from_latest(self):
        data = read_latest_post()
        content = data.get("post_content", "").strip()
        if not content:
            return None
        images = normalize_image_paths(data)
        signature = hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest()[:12]
        return {
            "id": f"post-{signature}",
            "status": "ready",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "timestamp": data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": data.get("source_file", ""),
            "ai_provider": data.get("ai_provider", "unknown"),
            "post_content": content,
            "image_path": images[0] if images else "",
            "image_paths": images,
        }

    def _queue_latest_post(self, silent=False, render=True):
        entry = self._queue_entry_from_latest()
        if not entry:
            if not silent and render and hasattr(self, "queue_status"):
                self.queue_status.configure(text="Chưa có bài mới để thêm vào hàng đợi.", text_color=C["red"])
            return False
        self._post_queue = [x for x in self._post_queue if x.get("id") != entry["id"]]
        self._post_queue.insert(0, entry)
        self._save_post_queue()
        if render:
            self._render_post_queue()
        if not silent and render and hasattr(self, "queue_status"):
            self.queue_status.configure(text="Đã thêm bài mới nhất vào hàng đợi.", text_color=C["green"])
        return True

    def _write_queue_entry_to_latest(self, entry):
        data = {
            "post_content": entry.get("post_content", ""),
            "timestamp": entry.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": entry.get("source_file", ""),
            "ai_provider": entry.get("ai_provider", "queue"),
            "image_path": entry.get("image_path", ""),
            "image_paths": normalize_image_paths(entry),
        }
        out = BASE / "output" / "latest_post.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        return data

    def _promote_queue_entry(self, remove=False):
        if not self._post_queue:
            if hasattr(self, "queue_status"):
                self.queue_status.configure(text="Hàng đợi đang trống.", text_color=C["red"])
            return None
        entry = self._post_queue[0]
        self._write_queue_entry_to_latest(entry)
        if remove:
            self._post_queue.pop(0)
            self._save_post_queue()
        self._render_latest_preview()
        self._render_post_queue()
        if hasattr(self, "queue_status"):
            self.queue_status.configure(text="Đã đưa bài đầu hàng đợi thành bài sẵn sàng đăng.", text_color=C["green"])
        return entry

    def _drop_queue_first(self):
        if self._post_queue:
            self._post_queue.pop(0)
            self._save_post_queue()
        self._render_post_queue()

    def _queue_selected_index(self):
        try:
            value = int(self.queue_index_entry.get().strip())
        except:
            value = 1
        return max(0, min(len(self._post_queue) - 1, value - 1)) if self._post_queue else None

    def _preview_queue_index(self):
        idx = self._queue_selected_index()
        if idx is None:
            if hasattr(self, "queue_status"):
                self.queue_status.configure(text="Hàng đợi đang trống.", text_color=C["red"])
            return
        entry = self._post_queue[idx]
        self._write_queue_entry_to_latest(entry)
        self._render_latest_preview()
        if hasattr(self, "queue_status"):
            self.queue_status.configure(text=f"Đang xem bài số {idx + 1}.", text_color=C["green"])

    def _drop_queue_index(self):
        idx = self._queue_selected_index()
        if idx is None:
            return
        self._post_queue.pop(idx)
        self._save_post_queue()
        self._render_post_queue()
        if hasattr(self, "queue_status"):
            self.queue_status.configure(text=f"Đã bỏ bài số {idx + 1}.", text_color=C["muted"])

    def _move_queue_index(self, delta):
        idx = self._queue_selected_index()
        if idx is None:
            return
        new_idx = max(0, min(len(self._post_queue) - 1, idx + delta))
        if new_idx == idx:
            return
        self._post_queue[idx], self._post_queue[new_idx] = self._post_queue[new_idx], self._post_queue[idx]
        self._save_post_queue()
        self._render_post_queue()
        if hasattr(self, "queue_index_entry"):
            self.queue_index_entry.delete(0, "end")
            self.queue_index_entry.insert(0, str(new_idx + 1))

    def _post_first_queue_entry(self):
        entry = self._promote_queue_entry(remove=False)
        if entry:
            self._run_post_action("chrome", consume_queue_id=entry.get("id"))

    def _clear_post_queue(self):
        self._post_queue = []
        self._save_post_queue()
        self._render_post_queue()
        if hasattr(self, "queue_status"):
            self.queue_status.configure(text="Đã làm trống hàng đợi.", text_color=C["muted"])

    def _render_post_queue(self):
        if not hasattr(self, "queue_box"):
            return
        lines = []
        for idx, item in enumerate(self._post_queue[:12], 1):
            content = (item.get("post_content") or "").replace("\n", " ").strip()
            title = content[:92] + ("..." if len(content) > 92 else "")
            ts = item.get("timestamp") or item.get("created_at", "")
            img_count = len(normalize_image_paths(item))
            lines.append(f"{idx:02}. ready | {ts} | {img_count} ảnh | {title}")
        if not lines:
            lines = ["Hàng đợi đang trống. Tạo bài rồi bấm Thêm bài mới nhất để lưu lại."]
        self.queue_box.configure(state="normal")
        self.queue_box.delete("1.0", "end")
        self.queue_box.insert("end", "\n".join(lines))
        self.queue_box.configure(state="disabled")
        if hasattr(self, "queue_count_lbl"):
            self.queue_count_lbl.configure(text=f"{len(self._post_queue)} bài đang chờ")

    def _render_latest_preview(self):
        if not hasattr(self, "preview_text"):
            return
        data = read_latest_post()
        content = data.get("post_content", "").strip()
        images = normalize_image_paths(data)
        meta = []
        if data.get("timestamp"):
            meta.append(data["timestamp"])
        if data.get("ai_provider"):
            meta.append(f"Nguồn: {data['ai_provider']}")
        meta.append(f"{len(images)} ảnh")
        self.preview_meta.configure(text=" · ".join(meta) if content else "Chưa có bài sẵn sàng đăng")
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("end", content or "Sau khi bấm Xem trước tin hoặc Soạn bài, preview sẽ hiện ở đây.")
        self.preview_text.configure(state="disabled")

        primary = next((p for p in images if p and Path(p).exists()), "")
        if primary and HAS_PIL:
            try:
                img = Image.open(primary).convert("RGB")
                img.thumbnail((230, 150), Image.LANCZOS)
                canvas = Image.new("RGB", (230, 150), "#10242A" if self._is_dark else "#F9FDFE")
                x = (230 - img.width) // 2
                y = (150 - img.height) // 2
                canvas.paste(img, (x, y))
                self._preview_img = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(230, 150))
                self.preview_image_lbl.configure(image=self._preview_img, text="")
                return
            except:
                pass
        self._preview_img = None
        self.preview_image_lbl.configure(image=None, text="Chưa có ảnh")

    def _preflight_checks(self, require_chrome=False, pages=None, require_image=True):
        env = read_env()
        data = read_latest_post()
        content = data.get("post_content", "").strip()
        images = normalize_image_paths(data)
        pages = pages or parse_pages(env.get("FB_PAGES", ""))
        checks = []

        def add(label, ok, detail):
            checks.append({"label": label, "ok": bool(ok), "detail": detail})

        add("Page", bool(pages), f"{len(pages)} page" if pages else "Chưa có page đăng bài")
        if require_chrome:
            chrome_ok = check_chrome()
            add("Chrome", chrome_ok, "Đã kết nối" if chrome_ok else "Chrome chưa mở hoặc chưa bật remote debug")
        add("Caption", len(content) >= 80, f"{len(content)} ký tự" if content else "Chưa có nội dung")
        add("Độ dài", len(content) <= 2200, "Ổn" if len(content) <= 2200 else "Caption quá dài cho thao tác tự động")
        hashtags = [word for word in content.split() if word.startswith("#")]
        add("Hashtag", len(hashtags) <= 10, f"{len(hashtags)} hashtag")
        existing_images = [p for p in images if p and Path(p).exists()]
        add("Ảnh", bool(existing_images) if require_image else True,
            f"{len(existing_images)} ảnh hợp lệ" if existing_images else "Chưa có ảnh hợp lệ")
        sig = hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest()[:12] if content else ""
        dup_count = len([x for x in self._post_queue if x.get("id") == f"post-{sig}"]) if sig else 0
        add("Trùng hàng đợi", dup_count <= 1, "Ổn" if dup_count <= 1 else "Có bài trùng trong hàng đợi")

        ok = all(item["ok"] for item in checks)
        lines = [f"{'OK' if item['ok'] else '!!'}  {item['label']:<15} {item['detail']}" for item in checks]
        return ok, lines, checks

    def _render_preflight(self, require_chrome=False, pages=None):
        ok, lines, _checks = self._preflight_checks(require_chrome=require_chrome, pages=pages)
        if hasattr(self, "preflight_box"):
            self.preflight_box.configure(state="normal")
            self.preflight_box.delete("1.0", "end")
            self.preflight_box.insert("end", "\n".join(lines))
            self.preflight_box.configure(state="disabled")
        if hasattr(self, "preflight_status"):
            self.preflight_status.configure(
                text="Sẵn sàng đăng" if ok else "Cần xử lý trước khi đăng",
                text_color=C["green"] if ok else C["red"])
        return ok, lines

    # ════════════ POST ════════════
    def _build_post(self):
        p = self.pages["post"]
        self._page_title(
            p,
            "Publishing studio",
            "Tạo bài, gắn ảnh, đăng fanpage",
            "Dán link bài viết hằng ngày, soạn caption tự động và kiểm soát Chrome trước khi đăng."
        )

        # ── Chrome Wizard ──
        cc = self._card(p, "Kết nối Chrome & Facebook")

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
                                   fg_color=C["status_idle_bg"], corner_radius=14,
                                   text_color=C["muted"])
            num_lbl.pack(side="left", padx=(10, 6), pady=10)
            txt = ctk.CTkLabel(sf2, text=label, font=ctk.CTkFont(size=12),
                               text_color=C["muted"])
            txt.pack(side="left", pady=10)
            self._step_lbls[k] = (num_lbl, txt)

        # Controls row
        ctrl = ctk.CTkFrame(cc, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 6))

        self.btn_open_chrome = self._button(
            ctrl, "Mở Chrome", variant="primary", width=140, height=36,
            font_size=13, bold=True, command=self._open_chrome)
        self.btn_open_chrome.pack(side="left", padx=(0, 8))

        self.btn_check_fb = self._button(
            ctrl, "Kiểm tra đăng nhập", variant="secondary", width=170, height=36,
            font_size=13, command=self._check_fb_status)
        self.btn_check_fb.pack(side="left", padx=(0, 8))

        self.btn_goto_fb = self._button(
            ctrl, "Mở Facebook", variant="secondary", width=140, height=36,
            font_size=13, command=self._goto_facebook)
        self.btn_goto_fb.pack(side="left")

        # Status label
        self.chrome_status_lbl = ctk.CTkLabel(
            cc, text="Nhấn Mở Chrome để bắt đầu",
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
        path_text = f"Chrome: {chrome_path}" if chrome_path else "Không tìm thấy Chrome. Hãy kiểm tra cài đặt."
        ctk.CTkLabel(cc, text=path_text, font=ctk.CTkFont(size=10),
                     text_color=path_color).pack(anchor="w", padx=16, pady=(0, 12))

        # ── Link bài viết hằng ngày ──
        lc = self._card(p, "Link bài viết hằng ngày")
        ctk.CTkLabel(
            lc,
            text="Dán mỗi link một dòng. Nếu để trống, app sẽ dùng nguồn tin tự động cũ.",
            font=ctk.CTkFont(size=12),
            text_color=C["muted"],
        ).pack(anchor="w", padx=16, pady=(0, 8))
        self.article_links_box = ctk.CTkTextbox(
            lc,
            height=96,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            text_color=C["text"],
            border_width=0,
            wrap="word",
        )
        self.article_links_box.pack(fill="x", padx=16, pady=(0, 8))
        if ARTICLE_LINKS_FILE.exists():
            try:
                self.article_links_box.insert("end", ARTICLE_LINKS_FILE.read_text("utf-8"))
            except:
                pass
        link_actions = ctk.CTkFrame(lc, fg_color="transparent")
        link_actions.pack(fill="x", padx=16, pady=(0, 12))
        self._button(
            link_actions, "Lưu link", variant="secondary",
            width=96, height=30, command=self._save_article_links,
        ).pack(side="left", padx=(0, 8))
        self._button(
            link_actions, "Xóa link", variant="outline",
            width=96, height=30, command=self._clear_article_links,
        ).pack(side="left")
        self.links_status = ctk.CTkLabel(link_actions, text="", font=ctk.CTkFont(size=11), text_color=C["muted"])
        self.links_status.pack(side="left", padx=10)

        compose = self._card(p, "Tùy chọn soạn bài")
        compose_grid = ctk.CTkFrame(compose, fg_color="transparent")
        compose_grid.pack(fill="x", padx=16, pady=(0, 12))
        compose_grid.columnconfigure((0, 1, 2, 3), weight=1)

        style_box = ctk.CTkFrame(compose_grid, fg_color=C["panel"], corner_radius=12,
                                 border_width=1, border_color=C["border"])
        style_box.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(style_box, text="KIỂU BÀI", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 6))
        env_defaults = read_env()
        self.compose_style_var = ctk.StringVar(value=env_defaults.get("POST_STYLE", "tong_hop"))
        ctk.CTkRadioButton(style_box, text="Tổng hợp nhiều tin", variable=self.compose_style_var, value="tong_hop",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=2)
        ctk.CTkRadioButton(style_box, text="Mỗi tin một bài", variable=self.compose_style_var, value="don_le",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=(2, 10))

        count_box = ctk.CTkFrame(compose_grid, fg_color=C["panel"], corner_radius=12,
                                 border_width=1, border_color=C["border"])
        count_box.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(count_box, text="SỐ BÀI CẦN SOẠN", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.compose_count_entry = ctk.CTkEntry(count_box, height=38, font=ctk.CTkFont(size=12),
                                                fg_color=C["input"], border_color=C["border"], text_color=C["text"])
        self.compose_count_entry.insert(0, env_defaults.get("MAX_POSTS", "1"))
        self.compose_count_entry.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(count_box, text="1-6 bài/lần", font=ctk.CTkFont(size=10),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        limit_box = ctk.CTkFrame(compose_grid, fg_color=C["panel"], corner_radius=12,
                                 border_width=1, border_color=C["border"])
        limit_box.grid(row=0, column=2, padx=6, sticky="nsew")
        ctk.CTkLabel(limit_box, text="SỐ TIN ĐẦU VÀO", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.compose_article_limit_entry = ctk.CTkEntry(limit_box, height=38, font=ctk.CTkFont(size=12),
                                                        fg_color=C["input"], border_color=C["border"], text_color=C["text"])
        self.compose_article_limit_entry.insert(0, env_defaults.get("MAX_TOTAL_ARTICLES", "8"))
        self.compose_article_limit_entry.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(limit_box, text="3-24 tin mới", font=ctk.CTkFont(size=10),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        depth_box = ctk.CTkFrame(compose_grid, fg_color=C["panel"], corner_radius=12,
                                 border_width=1, border_color=C["border"])
        depth_box.grid(row=0, column=3, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(depth_box, text="ĐỘ SÂU NỘI DUNG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 6))
        self.compose_full_content_var = ctk.BooleanVar(value=env_defaults.get("FETCH_FULL_CONTENT", "false").lower() == "true")
        ctk.CTkCheckBox(depth_box, text="Đọc nội dung đầy đủ", variable=self.compose_full_content_var,
                        onvalue=True, offvalue=False, text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=(2, 4))
        ctk.CTkLabel(depth_box, text="Chậm hơn nhưng kỹ hơn", font=ctk.CTkFont(size=10),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        # Preview bài đăng Facebook
        template_box = ctk.CTkFrame(compose, fg_color=C["panel"], corner_radius=12,
                                    border_width=1, border_color=C["border"])
        template_box.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(template_box, text="THƯ VIỆN MẪU NỘI DUNG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 4))
        template_row = ctk.CTkFrame(template_box, fg_color="transparent")
        template_row.pack(fill="x", padx=10, pady=(0, 8))
        self.compose_template_var = ctk.StringVar(value=env_defaults.get("CONTENT_TEMPLATE", "tin_nong"))
        for key, (label, _hint) in CONTENT_TEMPLATES.items():
            ctk.CTkRadioButton(
                template_row, text=label, variable=self.compose_template_var, value=key,
                text_color=C["text"], fg_color=C["accent"],
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(0, 12), pady=4)
        self.compose_template_hint = ctk.CTkLabel(
            template_box, text=CONTENT_TEMPLATES.get(self.compose_template_var.get(), CONTENT_TEMPLATES["tin_nong"])[1],
            font=ctk.CTkFont(size=10), text_color=C["subtle"], justify="left")
        self.compose_template_hint.pack(anchor="w", padx=12, pady=(0, 10))
        self.compose_template_var.trace_add("write", lambda *_: self._update_template_hint())

        pc = self._card(p, "Preview Facebook")
        preview_shell = ctk.CTkFrame(pc, fg_color="transparent")
        preview_shell.pack(fill="x", padx=16, pady=(0, 10))
        self.preview_image_lbl = ctk.CTkLabel(
            preview_shell,
            text="Chưa có ảnh",
            width=230,
            height=150,
            fg_color=C["input"],
            text_color=C["muted"],
            corner_radius=8,
        )
        self.preview_image_lbl.pack(side="left", padx=(0, 12), pady=(2, 8))
        preview_body = ctk.CTkFrame(preview_shell, fg_color="transparent")
        preview_body.pack(side="left", fill="both", expand=True)
        preview_head = ctk.CTkFrame(preview_body, fg_color="transparent")
        preview_head.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(preview_head, text="DT", width=34, height=34,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color=C["accent2"], text_color=C["deep"], corner_radius=17).pack(side="left", padx=(0, 8))
        page_meta = ctk.CTkFrame(preview_head, fg_color="transparent")
        page_meta.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            page_meta,
            text="DT68 Chuyên Sân Cỏ",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w")
        self.preview_meta = ctk.CTkLabel(
            page_meta,
            text="Chưa có bài sẵn sàng đăng",
            font=ctk.CTkFont(size=11),
            text_color=C["subtle"],
        )
        self.preview_meta.pack(anchor="w")
        self.preview_text = ctk.CTkTextbox(
            preview_body,
            height=122,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            text_color=C["text"],
            border_width=0,
            wrap="word",
        )
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.configure(state="disabled")
        preview_actions = ctk.CTkFrame(pc, fg_color="transparent")
        preview_actions.pack(fill="x", padx=16, pady=(0, 14))
        self._button(
            preview_actions, "Làm mới preview", variant="secondary",
            width=136, height=32, command=self._render_latest_preview,
        ).pack(side="left", padx=(0, 8))
        self._button(
            preview_actions, "Thêm bài mới nhất", variant="primary",
            width=150, height=32, command=self._queue_latest_post,
        ).pack(side="left", padx=(0, 8))
        self._button(
            preview_actions, "Dùng bài đầu hàng đợi", variant="outline",
            width=170, height=32, command=self._promote_queue_entry,
        ).pack(side="left")

        pf = self._card(p, "Bộ kiểm duyệt trước đăng")
        pf_actions = ctk.CTkFrame(pf, fg_color="transparent")
        pf_actions.pack(fill="x", padx=16, pady=(0, 8))
        self._button(
            pf_actions, "Kiểm tra trước đăng", variant="primary",
            width=160, height=32, command=self._render_preflight,
        ).pack(side="left", padx=(0, 8))
        self.preflight_status = ctk.CTkLabel(
            pf_actions, text="Chưa kiểm tra", font=ctk.CTkFont(size=11), text_color=C["muted"])
        self.preflight_status.pack(side="left", padx=8)
        self.preflight_box = ctk.CTkTextbox(
            pf, height=118, font=ctk.CTkFont(size=11, family="Courier New"),
            fg_color=C["input"], text_color=C["text"], border_width=0)
        self.preflight_box.pack(fill="x", padx=16, pady=(0, 14))
        self.preflight_box.insert("end", "Bấm kiểm tra để rà page, Chrome, caption, ảnh và khả năng trùng lặp.\n")
        self.preflight_box.configure(state="disabled")

        # Hàng đợi bài viết
        qc = self._card(p, "Hàng đợi bài viết")
        q_head = ctk.CTkFrame(qc, fg_color="transparent")
        q_head.pack(fill="x", padx=16, pady=(0, 8))
        self.queue_count_lbl = ctk.CTkLabel(
            q_head,
            text="0 bài đang chờ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text"],
        )
        self.queue_count_lbl.pack(side="left")
        self.queue_status = ctk.CTkLabel(q_head, text="", font=ctk.CTkFont(size=11), text_color=C["muted"])
        self.queue_status.pack(side="left", padx=12)
        self.queue_box = ctk.CTkTextbox(
            qc,
            height=136,
            font=ctk.CTkFont(size=11, family="Courier New"),
            fg_color=C["input"],
            text_color=C["text"],
            border_width=0,
        )
        self.queue_box.pack(fill="x", padx=16, pady=(0, 10))
        self.queue_box.configure(state="disabled")
        queue_actions = ctk.CTkFrame(qc, fg_color="transparent")
        queue_actions.pack(fill="x", padx=16, pady=(0, 14))
        self._button(
            queue_actions, "Đăng bài đầu", variant="primary",
            width=120, height=32, command=self._post_first_queue_entry,
        ).pack(side="left", padx=(0, 8))
        self._button(
            queue_actions, "Bỏ bài đầu", variant="secondary",
            width=112, height=32, command=self._drop_queue_first,
        ).pack(side="left", padx=(0, 8))
        self._button(
            queue_actions, "Xóa hàng đợi", variant="danger",
            width=120, height=32, command=self._clear_post_queue,
        ).pack(side="left")
        queue_tools = ctk.CTkFrame(qc, fg_color="transparent")
        queue_tools.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(queue_tools, text="Bài số", font=ctk.CTkFont(size=11),
                     text_color=C["muted"]).pack(side="left", padx=(0, 6))
        self.queue_index_entry = ctk.CTkEntry(
            queue_tools, width=56, height=30, font=ctk.CTkFont(size=11),
            fg_color=C["input"], border_color=C["border"], text_color=C["text"])
        self.queue_index_entry.insert(0, "1")
        self.queue_index_entry.pack(side="left", padx=(0, 8))
        self._button(queue_tools, "Xem", variant="secondary", width=72, height=30,
                     command=self._preview_queue_index).pack(side="left", padx=(0, 6))
        self._button(queue_tools, "Lên", variant="outline", width=66, height=30,
                     command=lambda: self._move_queue_index(-1)).pack(side="left", padx=(0, 6))
        self._button(queue_tools, "Xuống", variant="outline", width=76, height=30,
                     command=lambda: self._move_queue_index(1)).pack(side="left", padx=(0, 6))
        self._button(queue_tools, "Bỏ bài chọn", variant="danger", width=110, height=30,
                     command=self._drop_queue_index).pack(side="left")
        self._render_latest_preview()
        self._render_post_queue()

        # ══════════════════════════════════════════════════════
        # 🍌 NANO BANANA 2 — AI Image Generator Card
        # ══════════════════════════════════════════════════════
        nb_card = self._card(p, "🍌 Nano Banana 2 — Tạo ảnh AI")

        # Info row
        nb_info = ctk.CTkFrame(nb_card, fg_color=C["panel"], corner_radius=10)
        nb_info.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            nb_info,
            text="Tạo ảnh bằng Gemini API chính thức · Hỗ trợ Flash (nhanh) và Pro (chất lượng cao)",
            font=ctk.CTkFont(size=11),
            text_color=C["subtle"],
        ).pack(anchor="w", padx=12, pady=8)

        # Prompt input
        ctk.CTkLabel(nb_card, text="Prompt mô tả ảnh cần tạo:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).pack(anchor="w", padx=16, pady=(0, 4))
        self.nb_prompt = ctk.CTkTextbox(
            nb_card, height=72, font=ctk.CTkFont(size=12),
            fg_color=C["input"], text_color=C["text"], border_width=0, wrap="word",
        )
        self.nb_prompt.pack(fill="x", padx=16, pady=(0, 8))
        self.nb_prompt.insert("end",
            "Professional football news banner, Vietnamese football, vibrant stadium atmosphere, "
            "dynamic action shot, dramatic lighting, 4K quality")

        # Options row
        nb_opts = ctk.CTkFrame(nb_card, fg_color="transparent")
        nb_opts.pack(fill="x", padx=16, pady=(0, 8))
        nb_opts.columnconfigure((0, 1, 2, 3), weight=1)

        # Model
        model_box = ctk.CTkFrame(nb_opts, fg_color=C["panel"], corner_radius=10,
                                 border_width=1, border_color=C["border"])
        model_box.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(model_box, text="MODEL", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=10, pady=(8, 4))
        self.nb_model_var = ctk.StringVar(value="flash")
        ctk.CTkRadioButton(model_box, text="⚡ Flash (nhanh, rẻ)",
                           variable=self.nb_model_var, value="flash",
                           text_color=C["text"], fg_color=C["accent"],
                           font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=2)
        ctk.CTkRadioButton(model_box, text="💎 Pro (chất lượng cao)",
                           variable=self.nb_model_var, value="pro",
                           text_color=C["text"], fg_color=C["accent"],
                           font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(2, 8))

        # Aspect ratio
        aspect_box = ctk.CTkFrame(nb_opts, fg_color=C["panel"], corner_radius=10,
                                  border_width=1, border_color=C["border"])
        aspect_box.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(aspect_box, text="TỶ LỆ ẢNH", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=10, pady=(8, 4))
        self.nb_aspect_var = ctk.StringVar(value="16:9")
        ctk.CTkOptionMenu(
            aspect_box,
            variable=self.nb_aspect_var,
            values=["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "21:9"],
            fg_color=C["input"], button_color=C["accent"],
            text_color=C["text"], font=ctk.CTkFont(size=11),
            height=32,
        ).pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(aspect_box, text="16:9 = ngang · 9:16 = dọc · 1:1 = vuông",
                     font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=10, pady=(0, 8))

        # Options misc
        misc_box = ctk.CTkFrame(nb_opts, fg_color=C["panel"], corner_radius=10,
                                border_width=1, border_color=C["border"])
        misc_box.grid(row=0, column=2, padx=6, sticky="nsew")
        ctk.CTkLabel(misc_box, text="TÙY CHỌN", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=10, pady=(8, 4))
        self.nb_transparent_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(misc_box, text="🟢 Nền xanh (xóa nền sau)",
                        variable=self.nb_transparent_var,
                        onvalue=True, offvalue=False,
                        text_color=C["text"], fg_color=C["accent"],
                        font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=4)
        self.nb_auto_attach_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(misc_box, text="📎 Tự gắn vào bài đăng",
                        variable=self.nb_auto_attach_var,
                        onvalue=True, offvalue=False,
                        text_color=C["text"], fg_color=C["accent"],
                        font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(2, 8))

        # Cost stats
        cost_box = ctk.CTkFrame(nb_opts, fg_color=C["panel"], corner_radius=10,
                                border_width=1, border_color=C["border"])
        cost_box.grid(row=0, column=3, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(cost_box, text="CHI PHÍ", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=10, pady=(8, 4))
        self.nb_cost_lbl = ctk.CTkLabel(
            cost_box, text="$0.0000\n0 lần tạo",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["accent"], justify="left",
        )
        self.nb_cost_lbl.pack(anchor="w", padx=10, pady=2)
        self._button(cost_box, "Làm mới", variant="outline",
                     width=80, height=24,
                     command=self._nb_refresh_costs).pack(anchor="w", padx=10, pady=(4, 8))

        # Preview + Actions
        nb_bottom = ctk.CTkFrame(nb_card, fg_color="transparent")
        nb_bottom.pack(fill="x", padx=16, pady=(0, 14))

        # Thumbnail preview
        self.nb_preview_lbl = ctk.CTkLabel(
            nb_bottom, text="Chưa có ảnh",
            width=160, height=100,
            fg_color=C["input"], text_color=C["muted"],
            corner_radius=8,
        )
        self.nb_preview_lbl.pack(side="left", padx=(0, 12))

        nb_action_col = ctk.CTkFrame(nb_bottom, fg_color="transparent")
        nb_action_col.pack(side="left", fill="both", expand=True)

        # Status label
        self.nb_status = ctk.CTkLabel(
            nb_action_col,
            text="Nhập prompt và nhấn Tạo ảnh để bắt đầu",
            font=ctk.CTkFont(size=12), text_color=C["muted"], justify="left",
        )
        self.nb_status.pack(anchor="w", pady=(0, 8))

        # Result path
        self.nb_result_path = ctk.CTkLabel(
            nb_action_col, text="", font=ctk.CTkFont(size=10, family="Courier New"),
            text_color=C["subtle"], justify="left",
        )
        self.nb_result_path.pack(anchor="w", pady=(0, 8))

        # Buttons
        nb_btn_row = ctk.CTkFrame(nb_action_col, fg_color="transparent")
        nb_btn_row.pack(anchor="w")
        self.btn_nb_generate = self._button(
            nb_btn_row, "🍌 Tạo ảnh AI", variant="primary",
            width=148, height=36, font_size=13, bold=True,
            command=self._nb_generate,
        )
        self.btn_nb_generate.pack(side="left", padx=(0, 8))
        self._button(
            nb_btn_row, "📁 Mở thư mục", variant="secondary",
            width=120, height=36,
            command=self._nb_open_output_dir,
        ).pack(side="left", padx=(0, 8))
        self._button(
            nb_btn_row, "📎 Gắn ảnh hiện tại", variant="outline",
            width=148, height=36,
            command=self._nb_attach_to_post,
        ).pack(side="left")

        # Refresh cost on open
        self._nb_refresh_costs()

        # ── Workflow ──
        bf = self._card(p, "Quy trình")

        # Full one-click
        full_row = ctk.CTkFrame(bf, fg_color=C["panel"], corner_radius=8)
        full_row.pack(fill="x", padx=16, pady=(0,10))
        ctk.CTkLabel(full_row, text="Chạy toàn bộ (1 click)",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=C["text"]).pack(side="left", padx=12, pady=10)
        self.btn_full = self._button(
            full_row, "Chạy ngay", variant="primary", width=140, height=34,
            font_size=13, bold=True, command=self._run_full_workflow)
        self.btn_full.pack(side="right", padx=12, pady=10)

        ctk.CTkLabel(bf, text="— hoặc từng bước —", font=ctk.CTkFont(size=11),
                     text_color=C["subtle"]).pack(pady=(0,8))

        row = ctk.CTkFrame(bf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0,14))
        self.btn_preview = self._button(
            row, "Xem trước tin", variant="secondary", width=150, height=36,
            command=lambda: self._run_post_action("preview"))
        self.btn_preview.pack(side="left", padx=(0,8))
        self.btn_generate = self._button(
            row, "Soạn bài", variant="primary", width=150, height=36,
            command=lambda: self._run_post_action("generate"))
        self.btn_generate.pack(side="left", padx=(0,8))
        self.btn_batch_generate = self._button(
            row, "Soạn hàng loạt", variant="secondary", width=150, height=36,
            command=self._run_batch_generate)
        self.btn_batch_generate.pack(side="left", padx=(0,8))
        self.btn_chrome = self._button(
            row, "Đăng qua Chrome", variant="primary", width=160, height=36,
            command=lambda: self._run_post_action("chrome"))
        self.btn_chrome.pack(side="left", padx=(0,8))
        self._button(
            row, "Hẹn lịch", variant="outline", width=118, height=36,
            command=lambda: self._show_page("schedule")).pack(side="left")

        self.post_status = ctk.CTkLabel(bf, text="", font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.post_status.pack(anchor="w", padx=16, pady=(0,6))
        progress_wrap = ctk.CTkFrame(bf, fg_color="transparent")
        progress_wrap.pack(fill="x", padx=16, pady=(0, 12))
        self.workflow_progress = ctk.CTkProgressBar(
            progress_wrap, height=12, corner_radius=8,
            progress_color=C["accent"], fg_color=C["progress_track"]
        )
        self.workflow_progress.pack(fill="x", side="left", expand=True, padx=(0, 10))
        self.workflow_progress.set(0)
        self.progress_detail = ctk.CTkLabel(
            progress_wrap, text="0%", width=48,
            font=ctk.CTkFont(size=11, weight="bold"), text_color=C["subtle"]
        )
        self.progress_detail.pack(side="right")
        stage_frame = ctk.CTkFrame(bf, fg_color="transparent")
        stage_frame.pack(fill="x", padx=16, pady=(0, 12))
        stage_frame.columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.workflow_stage_labels = []
        for i, label in enumerate(["Chuẩn bị", "Soạn bài", "Gắn ảnh", "Đăng", "Hoàn tất"]):
            lbl = ctk.CTkLabel(stage_frame, text=label, font=ctk.CTkFont(size=10, weight="bold"),
                               text_color=C["subtle"])
            lbl.grid(row=0, column=i, sticky="w" if i == 0 else "e" if i == 4 else "n")
            self.workflow_stage_labels.append(lbl)

        # Output
        oc = self._card(p, "Output")
        self.post_output = ctk.CTkTextbox(oc, height=340, font=ctk.CTkFont(size=11, family="Courier New"),
                                          fg_color=C["input"], text_color=C["log_text"], border_width=0)
        self.post_output.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self.post_output.insert("end", "Nhấn một nút ở trên để bắt đầu...\n")
        self.post_output.configure(state="disabled")

    def _save_article_links(self):
        ARTICLE_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        raw = self.article_links_box.get("1.0", "end").strip()
        links = []
        for line in raw.replace(",", "\n").splitlines():
            line = line.strip()
            if line.startswith("http://") or line.startswith("https://"):
                links.append(line)
        ARTICLE_LINKS_FILE.write_text("\n".join(dict.fromkeys(links)), "utf-8")
        msg = f"Đã lưu {len(links)} link" if links else "Đã xoá danh sách link"
        self.links_status.configure(text=msg, text_color=C["green"] if links else C["muted"])
        self.after(3000, lambda: self.links_status.configure(text=""))

    def _clear_article_links(self):
        self.article_links_box.delete("1.0", "end")
        self._save_article_links()

    def _open_chrome(self):
        chrome_path = find_chrome_path()
        if not chrome_path:
            self.chrome_status_lbl.configure(
                text="Không tìm thấy Chrome. Kiểm tra cài đặt.",
                text_color=C["red"])
            return

        profile_dir = str(BASE / "chrome_profile")
        self.btn_open_chrome.configure(state="disabled", text="Đang mở...")
        self.chrome_status_lbl.configure(text="Đang khởi động Chrome...", text_color=C["yellow"])
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
                self.btn_open_chrome.configure(state="normal", text="Mở Chrome")
                if ok:
                    self._set_step(1, "done")
                    self.chrome_status_lbl.configure(
                        text="Chrome đã mở. Đăng nhập Facebook rồi nhấn kiểm tra.",
                        text_color=C["green"])
                else:
                    self._set_step(1, "error")
                    self.chrome_status_lbl.configure(
                        text="Chrome đã mở nhưng chưa kết nối được.",
                        text_color=C["red"])
            self.after(0, _upd)
        threading.Thread(target=_do_open, daemon=True).start()

    def _goto_facebook(self):
        """Dẫn Chrome đang chạy đến facebook.com"""
        if not check_chrome():
            self.chrome_status_lbl.configure(
                text="Chrome chưa mở. Nhấn Mở Chrome trước.", text_color=C["yellow"])
            return
        try:
            import urllib.request
            url = "http://127.0.0.1:9222/json/new?https://www.facebook.com"
            req = urllib.request.Request(url, method="PUT")
            urllib.request.urlopen(req, timeout=2)
            self.chrome_status_lbl.configure(
                text="Đã mở tab Facebook trong Chrome.", text_color=C["green"])
        except:
            self.chrome_status_lbl.configure(
                text="Không thể mở tab mới.", text_color=C["yellow"])

    def _check_fb_status(self):
        """Kiểm tra trạng thái đăng nhập Facebook"""
        self.btn_check_fb.configure(state="disabled", text="Đang kiểm tra...")
        def _do():
            info = get_chrome_info()
            env  = read_env()
            pages_raw = env.get("FB_PAGES", "")
            pages = [p.strip() for p in pages_raw.split(",") if p.strip() and "THAY" not in p]

            def _upd():
                self.btn_check_fb.configure(state="normal", text="Kiểm tra đăng nhập")
                if not info["connected"]:
                    self._set_step(1, "error")
                    self._set_step(2, "pending")
                    self.chrome_status_lbl.configure(
                        text="Chrome chưa kết nối. Hãy nhấn Mở Chrome.",
                        text_color=C["red"])
                    return

                self._set_step(1, "done")
                logged_in = check_fb_logged_in(info["fb_url"])

                if logged_in:
                    self._set_step(2, "done")
                    self._set_step(3, "done")
                    pages_info = "\n".join(f"   • facebook.com/{pg}" for pg in pages) or "   (Chưa có trang nào — vào Cài đặt để thêm)"
                    self.chrome_status_lbl.configure(
                        text=f"Đã đăng nhập Facebook. {info['tabs']} tab đang mở.",
                        text_color=C["green"])
                    self.chrome_pages_lbl.configure(
                        text=f"Trang sẽ đăng bài:\n{pages_info}",
                        text_color=C["blue"])
                else:
                    self._set_step(2, "error")
                    self.chrome_status_lbl.configure(
                        text="Chrome mở nhưng chưa đăng nhập Facebook. Nhấn Mở Facebook.",
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
            "pending": (C["yellow"], C["text"], C["status_warn_bg"]),
            "done":    (C["green"], C["text"], C["status_done_bg"]),
            "error":   (C["red"], C["text"], C["status_error_bg"]),
            "idle":    (C["muted"], C["muted"], C["status_idle_bg"]),
        }
        tc, ntc, nbg = colors.get(state, colors["idle"])
        prefix = {"done": "OK", "error": "!", "pending": "..."}.get(state, str(step))
        num_lbl.configure(text=prefix, text_color=ntc, fg_color=nbg)
        txt.configure(text_color=tc)

    def _set_progress(self, value: float, message: str = "", color=None):
        value = max(0, min(1, float(value)))
        if hasattr(self, "workflow_progress"):
            self.workflow_progress.set(value)
            if color:
                self.workflow_progress.configure(progress_color=color)
        if hasattr(self, "progress_detail"):
            self.progress_detail.configure(text=f"{int(value * 100)}%")
        if hasattr(self, "workflow_stage_labels"):
            active_index = min(len(self.workflow_stage_labels) - 1, int(value * len(self.workflow_stage_labels)))
            for i, lbl in enumerate(self.workflow_stage_labels):
                lbl.configure(text_color=C["accent"] if i <= active_index else C["subtle"])
        if message and hasattr(self, "post_status"):
            self.post_status.configure(text=message, text_color=color or C["yellow"])

    def _append_post_output(self, text: str):
        if not text:
            return
        self.post_output.configure(state="normal")
        self.post_output.insert("end", text)
        self.post_output.see("end")
        self.post_output.configure(state="disabled")

    def _run_streaming_cmd(self, cmd, on_line=None, timeout=240):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE),
            env=env,
            bufsize=1,
        )
        output = []
        started = time.time()
        try:
            while True:
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    output.append(line)
                    self.after(0, self._append_post_output, line)
                    if on_line:
                        on_line(line)
                elif proc.poll() is not None:
                    break
                elif time.time() - started > timeout:
                    proc.kill()
                    raise TimeoutError(f"Quá thời gian {timeout}s")
                else:
                    time.sleep(0.05)
            rest = proc.stdout.read() if proc.stdout else ""
            if rest:
                output.append(rest)
                self.after(0, self._append_post_output, rest)
            return "".join(output), proc.returncode == 0
        finally:
            try:
                proc.stdout.close()
            except:
                pass

    def _entry_int(self, widget, default, low, high):
        try:
            value = int(str(widget.get()).strip())
        except:
            value = default
        return max(low, min(high, value))

    def _update_template_hint(self):
        if not hasattr(self, "compose_template_hint"):
            return
        key = self.compose_template_var.get() if hasattr(self, "compose_template_var") else "tin_nong"
        self.compose_template_hint.configure(text=CONTENT_TEMPLATES.get(key, CONTENT_TEMPLATES["tin_nong"])[1])

    def _compose_options(self):
        style = "tong_hop"
        if hasattr(self, "compose_style_var"):
            style = self.compose_style_var.get() or "tong_hop"
        if style not in ("tong_hop", "don_le"):
            style = "tong_hop"
        count = self._entry_int(self.compose_count_entry, 1, 1, 6) if hasattr(self, "compose_count_entry") else 1
        article_limit = self._entry_int(self.compose_article_limit_entry, 8, 3, 24) if hasattr(self, "compose_article_limit_entry") else 8
        full_content = bool(self.compose_full_content_var.get()) if hasattr(self, "compose_full_content_var") else False
        template = self.compose_template_var.get() if hasattr(self, "compose_template_var") else "tin_nong"
        if template not in CONTENT_TEMPLATES:
            template = "tin_nong"
        return {
            "post_style": style,
            "count": count,
            "max_total_articles": article_limit,
            "fetch_full_content": full_content,
            "content_template": template,
        }

    def _preview_post_command(self, options=None):
        cmd = php_command("preview-post")
        if cmd is None:
            return None
        options = options or self._compose_options()
        cmd.extend([
            f"--post-style={options.get('post_style', 'tong_hop')}",
            f"--max-total-articles={int(options.get('max_total_articles', 8))}",
            "--max-posts=1",
            f"--full-content={1 if options.get('fetch_full_content') else 0}",
            f"--content-template={options.get('content_template', 'tin_nong')}",
        ])
        return cmd

    def _workflow_buttons(self):
        names = ["btn_full", "btn_preview", "btn_generate", "btn_batch_generate", "btn_chrome"]
        return [getattr(self, name) for name in names if hasattr(self, name)]

    def _run_batch_generate(self):
        self._save_article_links()
        options = self._compose_options()
        count = options["count"]
        if count <= 1:
            self._run_post_action("generate")
            return
        if options["post_style"] == "tong_hop":
            options["post_style"] = "don_le"
            if hasattr(self, "compose_style_var"):
                self.compose_style_var.set("don_le")

        cmd = self._preview_post_command(options)
        if cmd is None:
            self.post_status.configure(text="ChÆ°a tÃ¬m tháº¥y PHP. CÃ i XAMPP/WAMP hoáº·c thÃªm PHP vÃ o PATH.", text_color=C["red"])
            return

        btns = self._workflow_buttons()
        for b in btns:
            b.configure(state="disabled")
        self._set_progress(0.05, f"Đang soạn {count} bài vào hàng đợi...", C["yellow"])
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"{datetime.now().strftime('%H:%M:%S')} — batch-generate x{count}\n\n")
        self.post_output.configure(state="disabled")

        def _worker():
            success = 0
            failed = 0
            for i in range(count):
                start_p = 0.08 + (i / count) * 0.82
                end_p = 0.08 + ((i + 1) / count) * 0.82
                label = f"Soạn bài {i + 1}/{count}"
                self.after(0, self._set_progress, start_p, label, C["yellow"])
                self.after(0, self._append_post_output, f"\n--- {label} ---\n")
                try:
                    if cmd and len(cmd) > 1 and str(cmd[1]).endswith("chrome_poster.py"):
                        ok_preflight, lines, _checks = self._preflight_checks(require_chrome=True)
                        if not ok_preflight:
                            self.after(0, self._append_post_output, "\n".join(["\nPRE-FLIGHT FAILED", *lines, ""]))
                            final_ok = False
                            break
                    last_tick = {"t": time.time(), "p": start_p}
                    def _line_progress(_line):
                        now = time.time()
                        if now - last_tick["t"] > 1.0 and last_tick["p"] < end_p - 0.02:
                            last_tick["t"] = now
                            last_tick["p"] = min(end_p - 0.02, last_tick["p"] + 0.03)
                            self.after(0, self._set_progress, last_tick["p"], label, C["yellow"])
                    _, ok = self._run_streaming_cmd(self._preview_post_command(options), on_line=_line_progress, timeout=260)
                    if ok and self._queue_latest_post(silent=True, render=False):
                        success += 1
                        self.after(0, self._set_progress, end_p, f"Đã thêm bài {i + 1}/{count} vào hàng đợi", C["accent"])
                    else:
                        failed += 1
                        break
                except Exception as e:
                    failed += 1
                    self.after(0, self._append_post_output, f"\nLỗi: {e}\n")
                    break

            def _done():
                ok = success > 0 and failed == 0
                self._render_latest_preview()
                self._render_post_queue()
                self._refresh_dashboard()
                self._set_progress(1 if ok else 0.98,
                                   f"Đã soạn {success}/{count} bài." if success else "Chưa soạn được bài mới.",
                                   C["green"] if ok else C["red"])
                if hasattr(self, "queue_status"):
                    self.queue_status.configure(
                        text=f"Đã thêm {success} bài vào hàng đợi." if success else "Không có bài mới để thêm.",
                        text_color=C["green"] if success else C["red"])
                for b in btns:
                    b.configure(state="normal")
            self.after(0, _done)
        threading.Thread(target=_worker, daemon=True).start()

    def _run_full_workflow(self):
        """Chạy toàn bộ: PHP scrape + soạn bài → Chrome post"""
        self._save_article_links()
        preview_cmd = self._preview_post_command()
        if preview_cmd is None:
            self.post_status.configure(text="Chưa tìm thấy PHP. Cài XAMPP/WAMP hoặc thêm PHP vào PATH.", text_color=C["red"])
            return

        all_btns = self._workflow_buttons()
        for b in all_btns: b.configure(state="disabled")
        self._set_progress(0.03, "Đang chuẩn bị quy trình...", C["yellow"])
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"BẮT ĐẦU TOÀN BỘ QUY TRÌNH — {datetime.now().strftime('%H:%M:%S')}\n")
        self.post_output.insert("end", "=" * 50 + "\n\n")
        self.post_output.configure(state="disabled")

        def _full_run():
            py_path = PY
            steps = [
                ("Bước 1: Thu thập tin + soạn bài", preview_cmd, 0.10, 0.55),
                ("Bước 2: Đăng lên Facebook qua Chrome", [py_path, str(BASE/"chrome_poster.py")], 0.62, 0.95),
            ]
            final_ok = True
            for label, cmd, start_p, end_p in steps:
                self.after(0, self._set_progress, start_p, label, C["yellow"])
                self.after(0, self._append_post_output, f"\n{'─'*40}\n{label}\n{'─'*40}\n")
                try:
                    last_tick = {"t": time.time(), "p": start_p}
                    def _line_progress(line):
                        now = time.time()
                        if now - last_tick["t"] > 1.2 and last_tick["p"] < end_p - 0.04:
                            last_tick["p"] = min(end_p - 0.04, last_tick["p"] + 0.025)
                            self.after(0, self._set_progress, last_tick["p"], label, C["yellow"])
                    _, ok = self._run_streaming_cmd(cmd, on_line=_line_progress, timeout=240)
                    self.after(0, self._set_progress, end_p, f"Hoàn tất: {label}", C["accent"])
                    if not ok:
                        final_ok = False
                        break
                except Exception as e:
                    self.after(0, self._append_post_output, f"\nLỗi: {e}\n")
                    final_ok = False; break

            def _done():
                self._set_progress(1 if final_ok else 0.98,
                                   "Đã đăng bài thành công." if final_ok else "Có lỗi. Xem output.",
                                   C["green"] if final_ok else C["red"])
                self.post_status.configure(
                    text="Đã đăng bài thành công." if final_ok else "Có lỗi. Xem output.",
                    text_color=C["green"] if final_ok else C["red"]
                )
                for b in all_btns: b.configure(state="normal")
                self._render_latest_preview()
                self._render_post_queue()
                self._refresh_dashboard()
            self.after(0, _done)

        threading.Thread(target=_full_run, daemon=True).start()

    def _run_post_action(self, action, consume_queue_id=None):
        if action in ("preview", "generate"):
            self._save_article_links()
        cmd_map = {
            "preview":  self._preview_post_command(),
            "generate": self._preview_post_command(),
            "chrome":   [PY, str(BASE/"chrome_poster.py")],
        }
        if cmd_map.get(action) is None:
            self.post_status.configure(text="Chưa tìm thấy PHP. Cài XAMPP/WAMP hoặc thêm PHP vào PATH.", text_color=C["red"])
            return

        if action == "chrome":
            ok_preflight, lines = self._render_preflight(require_chrome=True)
            if not ok_preflight:
                self.post_status.configure(text="Chưa thể đăng: cần xử lý mục kiểm duyệt.", text_color=C["red"])
                self._append_post_output("\n".join(["\nPRE-FLIGHT FAILED", *lines, ""]))
                return

        btns = self._workflow_buttons()
        for b in btns: b.configure(state="disabled")
        labels = {"preview": "Đang lấy tin tức...", "generate": "Đang soạn bài...", "chrome": "Đang đăng qua Chrome..."}
        self._set_progress(0.08, f"Đang xử lý: {labels.get(action)}", C["yellow"])
        self.post_output.configure(state="normal")
        self.post_output.delete("1.0", "end")
        self.post_output.insert("end", f"{datetime.now().strftime('%H:%M:%S')} — {action}\n\n")
        self.post_output.configure(state="disabled")

        def _worker():
            ok = False
            try:
                last_tick = {"t": time.time(), "p": 0.08}
                def _line_progress(line):
                    now = time.time()
                    if now - last_tick["t"] > 1.0 and last_tick["p"] < 0.92:
                        last_tick["t"] = now
                        last_tick["p"] = min(0.92, last_tick["p"] + 0.04)
                        self.after(0, self._set_progress, last_tick["p"], f"Đang xử lý: {labels.get(action)}", C["yellow"])
                _, ok = self._run_streaming_cmd(cmd_map[action], on_line=_line_progress, timeout=240)
            except Exception as e:
                self.after(0, self._append_post_output, f"\nLỗi: {e}\n")

            def _u():
                self._set_progress(1 if ok else 0.98,
                                   "Hoàn thành." if ok else "Lỗi.",
                                   C["green"] if ok else C["red"])
                if ok and action in ("preview", "generate"):
                    self._render_latest_preview()
                    self._queue_latest_post(silent=True)
                if ok and consume_queue_id:
                    self._post_queue = [x for x in self._post_queue if x.get("id") != consume_queue_id]
                    self._save_post_queue()
                    self._render_post_queue()
                    if hasattr(self, "queue_status"):
                        self.queue_status.configure(text="Đã đăng và gỡ bài khỏi hàng đợi.", text_color=C["green"])
                elif ok:
                    self._render_latest_preview()
                for b in btns: b.configure(state="normal")
            self.after(0, _u)
        threading.Thread(target=_worker, daemon=True).start()

    # ════════════ SCHEDULE ════════════
    def _build_schedule(self):
        p = self.pages["schedule"]
        self._page_title(
            p,
            "Release calendar",
            "Hẹn lịch đăng bài",
            "Lên lịch một lần hoặc lặp hằng ngày. App sẽ tự tạo bài, gắn ảnh và đăng qua Chrome đúng giờ."
        )

        ap = self._card(p, "Autopilot nuôi trang")
        ctk.CTkLabel(
            ap,
            text="Bật chế độ này để app tự vận hành mỗi ngày: lấy nguồn, soạn bài, mở Chrome khi cần và đăng theo khung giờ.",
            font=ctk.CTkFont(size=12),
            text_color=C["muted"],
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 10))
        self.autopilot_enabled_var = ctk.BooleanVar(value=bool(self._autopilot.get("enabled", False)))
        ctk.CTkCheckBox(
            ap,
            text="Bật Autopilot",
            variable=self.autopilot_enabled_var,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text"],
            fg_color=C["accent"],
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.autopilot_safe_var = ctk.BooleanVar(value=bool(self._autopilot.get("safe_mode", True)))
        ctk.CTkCheckBox(
            ap,
            text="Autopilot an toàn: kiểm tra page, Chrome, caption và ảnh trước khi đăng",
            variable=self.autopilot_safe_var,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(size=11),
            text_color=C["muted"],
            fg_color=C["accent"],
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ap_grid = ctk.CTkFrame(ap, fg_color="transparent")
        ap_grid.pack(fill="x", padx=16, pady=(0, 12))
        ap_grid.columnconfigure(0, weight=3)
        ap_grid.columnconfigure(1, weight=1)
        time_box = ctk.CTkFrame(ap_grid, fg_color=C["panel"], corner_radius=12,
                                border_width=1, border_color=C["border"])
        time_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(time_box, text="KHUNG GIỜ ĐĂNG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.autopilot_times_entry = ctk.CTkEntry(
            time_box,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            border_color=C["border"],
            text_color=C["text"],
        )
        self.autopilot_times_entry.insert(0, ", ".join(self._autopilot.get("times", ["08:00", "13:00", "20:00"])))
        self.autopilot_times_entry.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(time_box, text="VD: 08:00, 13:00, 20:00",
                     font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        limit_box = ctk.CTkFrame(ap_grid, fg_color=C["panel"], corner_radius=12,
                                 border_width=1, border_color=C["border"])
        limit_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(limit_box, text="GIỚI HẠN/NGÀY", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.autopilot_limit_entry = ctk.CTkEntry(
            limit_box,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            border_color=C["border"],
            text_color=C["text"],
        )
        self.autopilot_limit_entry.insert(0, str(self._autopilot.get("max_daily_posts", 3)))
        self.autopilot_limit_entry.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(limit_box, text="Khuyến nghị: 2-4",
                     font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        page_box = ctk.CTkFrame(ap, fg_color=C["panel"], corner_radius=12,
                                border_width=1, border_color=C["border"])
        page_box.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(page_box, text="PAGE SẼ ĐĂNG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.autopilot_pages_entry = ctk.CTkEntry(
            page_box,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            border_color=C["border"],
            text_color=C["text"],
        )
        auto_pages = self._autopilot.get("pages") or parse_pages(read_env().get("FB_PAGES", ""))
        self.autopilot_pages_entry.insert(0, ", ".join(auto_pages))
        self.autopilot_pages_entry.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(page_box, text="Nhập nhiều page bằng dấu phẩy. Để trống sẽ dùng FB_PAGES trong Cấu hình.",
                     font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        ap_btns = ctk.CTkFrame(ap, fg_color="transparent")
        ap_btns.pack(fill="x", padx=16, pady=(0, 10))
        self._button(
            ap_btns, "Lưu Autopilot", variant="primary",
            width=140, height=36, bold=True, command=self._save_autopilot_from_ui,
        ).pack(side="left", padx=(0, 8))
        self._button(
            ap_btns, "Chạy thử ngay", variant="secondary",
            width=130, height=36, command=self._run_full_workflow,
        ).pack(side="left")
        self.autopilot_status = ctk.CTkLabel(ap, text="", font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.autopilot_status.pack(anchor="w", padx=16, pady=(0, 12))
        self._render_autopilot_status()

        sc = self._card(p, "Tạo lịch mới")
        ctk.CTkLabel(sc, text="Page của lịch này", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["muted"]).pack(anchor="w", padx=16, pady=(0, 4))
        self._sched_pages_entry = ctk.CTkEntry(
            sc,
            height=38,
            font=ctk.CTkFont(size=12),
            fg_color=C["input"],
            border_color=C["border"],
            text_color=C["text"],
        )
        self._sched_pages_entry.insert(0, read_env().get("FB_PAGES", ""))
        self._sched_pages_entry.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(sc, text="Có thể nhập nhiều page: page1, page2, https://facebook.com/page3",
                     font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=16, pady=(0, 12))
        form = ctk.CTkFrame(sc, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=(4, 12))
        for col in range(4):
            form.columnconfigure(col, weight=1)

        now = datetime.now() + timedelta(minutes=15)
        self._sched_mode_var = ctk.StringVar(value="once")
        self._sched_action_var = ctk.StringVar(value="full")

        fields = [
            ("Ngày", "date", now.strftime("%Y-%m-%d"), "YYYY-MM-DD"),
            ("Giờ", "time", now.strftime("%H:%M"), "HH:MM"),
        ]
        for col, (label, key, value, hint) in enumerate(fields):
            box = ctk.CTkFrame(form, fg_color=C["panel"], corner_radius=12,
                               border_width=1, border_color=C["border"])
            box.grid(row=0, column=col, padx=5, sticky="ew")
            ctk.CTkLabel(box, text=label.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 2))
            widget = ctk.CTkEntry(box, height=38, font=ctk.CTkFont(size=12),
                                  fg_color=C["input"], border_color=C["border"], text_color=C["text"])
            widget.insert(0, value)
            widget.pack(fill="x", padx=10, pady=(0, 4))
            if key == "date":
                self._sched_date = widget
            else:
                self._sched_time = widget
            ctk.CTkLabel(box, text=hint, font=ctk.CTkFont(size=10),
                         text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(0, 10))

        mode_box = ctk.CTkFrame(form, fg_color=C["panel"], corner_radius=12,
                                border_width=1, border_color=C["border"])
        mode_box.grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkLabel(mode_box, text="KIỂU LỊCH", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkRadioButton(mode_box, text="Một lần", variable=self._sched_mode_var, value="once",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=2)
        ctk.CTkRadioButton(mode_box, text="Hằng ngày", variable=self._sched_mode_var, value="daily",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=(2, 10))

        action_box = ctk.CTkFrame(form, fg_color=C["panel"], corner_radius=12,
                                  border_width=1, border_color=C["border"])
        action_box.grid(row=0, column=3, padx=5, sticky="ew")
        ctk.CTkLabel(action_box, text="HÀNH ĐỘNG", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=C["subtle"]).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkRadioButton(action_box, text="Tạo bài + đăng", variable=self._sched_action_var, value="full",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=2)
        ctk.CTkRadioButton(action_box, text="Chỉ đăng bài đã tạo", variable=self._sched_action_var, value="post_only",
                           text_color=C["text"], fg_color=C["accent"]).pack(anchor="w", padx=12, pady=(2, 10))

        btn_row = ctk.CTkFrame(sc, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0,14))
        self._button(
            btn_row, "Thêm vào lịch", variant="primary", width=150, height=38,
            font_size=13, bold=True, command=self._apply_schedule,
        ).pack(side="left", padx=(0,10))
        self._button(
            btn_row, "Tắt tất cả lịch", variant="danger", width=150, height=38,
            font_size=13, command=self._cancel_schedule,
        ).pack(side="left")

        self.sched_status = ctk.CTkLabel(sc, text="Sẵn sàng nhận lịch mới",
                                          font=ctk.CTkFont(size=12), text_color=C["muted"])
        self.sched_status.pack(anchor="w", padx=16, pady=(0,8))

        nc = self._card(p, "Lần chạy tiếp theo")
        self.next_run_lbl = ctk.CTkLabel(nc, text="Chưa có lịch",
                                          font=ctk.CTkFont(size=14, weight="bold"), text_color=C["muted"])
        self.next_run_lbl.pack(anchor="w", padx=16, pady=(0,14))

        tc = self._card(p, "Timeline hôm nay")
        self.today_timeline_box = ctk.CTkTextbox(tc, height=150, font=ctk.CTkFont(size=12, family="Courier New"),
                                                 fg_color=C["input"], text_color=C["text"], border_width=0)
        self.today_timeline_box.pack(fill="x", padx=16, pady=(0,14))
        self.today_timeline_box.configure(state="disabled")

        wc = self._card(p, "Lịch 7 ngày")
        self.week_calendar_box = ctk.CTkTextbox(wc, height=190, font=ctk.CTkFont(size=12, family="Courier New"),
                                                fg_color=C["input"], text_color=C["text"], border_width=0)
        self.week_calendar_box.pack(fill="x", padx=16, pady=(0,14))
        self.week_calendar_box.configure(state="disabled")

        jc = self._card(p, "Danh sách lịch")
        self.schedule_list_box = ctk.CTkTextbox(jc, height=230, font=ctk.CTkFont(size=12, family="Courier New"),
                                                fg_color=C["input"], text_color=C["text"], border_width=0)
        self.schedule_list_box.pack(fill="x", padx=16, pady=(0,14))
        self.schedule_list_box.configure(state="disabled")
        self._render_schedule_jobs()
        self._update_next_run()

    def _load_schedule_jobs(self):
        try:
            if SCHEDULE_FILE.exists():
                data = json.loads(SCHEDULE_FILE.read_text("utf-8"))
                return data if isinstance(data, list) else []
        except:
            pass
        return []

    def _load_autopilot_config(self):
        default = {
            "enabled": False,
            "times": ["08:00", "13:00", "20:00"],
            "max_daily_posts": 3,
            "safe_mode": True,
            "post_style": "tong_hop",
            "content_template": "tin_nong",
            "max_total_articles": 8,
            "fetch_full_content": False,
        }
        try:
            if AUTOPILOT_FILE.exists():
                data = json.loads(AUTOPILOT_FILE.read_text("utf-8"))
                if isinstance(data, dict):
                    default.update(data)
        except:
            pass
        if not default.get("pages"):
            default["pages"] = parse_pages(read_env().get("FB_PAGES", ""))
        return default

    def _save_autopilot_config(self):
        AUTOPILOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTOPILOT_FILE.write_text(json.dumps(self._autopilot, ensure_ascii=False, indent=2), "utf-8")

    def _parse_autopilot_times(self):
        raw = self.autopilot_times_entry.get().replace(";", ",").replace("\n", ",")
        times = []
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                datetime.strptime(item, "%H:%M")
                if item not in times:
                    times.append(item)
            except:
                pass
        return times

    def _save_autopilot_from_ui(self):
        times = self._parse_autopilot_times()
        if not times:
            self.autopilot_status.configure(text="Cần ít nhất một khung giờ hợp lệ, ví dụ 08:00.", text_color=C["red"])
            return
        try:
            limit = int(self.autopilot_limit_entry.get().strip() or "3")
            limit = max(1, min(8, limit))
        except:
            limit = 3

        compose = self._compose_options()
        self._autopilot = {
            "enabled": bool(self.autopilot_enabled_var.get()),
            "safe_mode": bool(self.autopilot_safe_var.get()) if hasattr(self, "autopilot_safe_var") else True,
            "times": times,
            "max_daily_posts": limit,
            "pages": parse_pages(self.autopilot_pages_entry.get()) or parse_pages(read_env().get("FB_PAGES", "")),
            "post_style": compose.get("post_style", "tong_hop"),
            "content_template": compose.get("content_template", "tin_nong"),
            "max_total_articles": compose.get("max_total_articles", 8),
            "fetch_full_content": compose.get("fetch_full_content", False),
        }
        self._save_autopilot_config()
        self._sync_autopilot_jobs()
        self._render_autopilot_status()
        self._render_schedule_jobs()
        self._update_next_run()
        self._refresh_dashboard()

    def _sync_autopilot_jobs(self):
        today = datetime.now().strftime("%Y-%m-%d")
        times = self._autopilot.get("times", [])
        enabled = bool(self._autopilot.get("enabled", False))

        for job in self._scheduled_jobs:
            if job.get("source") == "autopilot":
                if not enabled or job.get("time") not in times:
                    if job.get("status") in ("scheduled", "running"):
                        job["status"] = "disabled"

        if enabled:
            existing = {
                job.get("time")
                for job in self._scheduled_jobs
                if job.get("source") == "autopilot" and job.get("status") == "scheduled"
            }
            for t in times:
                if t not in existing:
                    self._scheduled_jobs.append({
                        "id": f"auto-{t.replace(':','')}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "date": today,
                        "time": t,
                        "mode": "daily",
                        "action": "full",
                        "status": "scheduled",
                        "source": "autopilot",
                        "pages": self._autopilot.get("pages", []),
                        "post_style": self._autopilot.get("post_style", "tong_hop"),
                        "content_template": self._autopilot.get("content_template", "tin_nong"),
                        "max_total_articles": int(self._autopilot.get("max_total_articles", 8) or 8),
                        "fetch_full_content": bool(self._autopilot.get("fetch_full_content", False)),
                        "safe_mode": bool(self._autopilot.get("safe_mode", True)),
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "last_run_date": "",
                    })
                else:
                    for job in self._scheduled_jobs:
                        if job.get("source") == "autopilot" and job.get("time") == t and job.get("status") == "scheduled":
                            job["pages"] = self._autopilot.get("pages", [])
                            job["post_style"] = self._autopilot.get("post_style", job.get("post_style", "tong_hop"))
                            job["content_template"] = self._autopilot.get("content_template", job.get("content_template", "tin_nong"))
                            job["max_total_articles"] = int(self._autopilot.get("max_total_articles", job.get("max_total_articles", 8)) or 8)
                            job["fetch_full_content"] = bool(self._autopilot.get("fetch_full_content", job.get("fetch_full_content", False)))
                            job["safe_mode"] = bool(self._autopilot.get("safe_mode", job.get("safe_mode", True)))

        self._sched_running = any(j.get("status") == "scheduled" for j in self._scheduled_jobs)
        self._save_schedule_jobs()

    def _render_autopilot_status(self):
        if not hasattr(self, "autopilot_status"):
            return
        if self._autopilot.get("enabled", False):
            times = ", ".join(self._autopilot.get("times", []))
            limit = self._autopilot.get("max_daily_posts", 3)
            page_count = len(self._autopilot.get("pages", []) or parse_pages(read_env().get("FB_PAGES", "")))
            template = CONTENT_TEMPLATES.get(self._autopilot.get("content_template", "tin_nong"), CONTENT_TEMPLATES["tin_nong"])[0]
            safe = "safe" if self._autopilot.get("safe_mode", True) else "fast"
            self.autopilot_status.configure(
                text=f"Autopilot đang bật · giờ đăng: {times} · tối đa {limit} bài/ngày · {page_count} page · {template} · {safe}",
                text_color=C["green"],
            )
        else:
            self.autopilot_status.configure(
                text="Autopilot đang tắt. Lịch thủ công vẫn hoạt động nếu đã tạo.",
                text_color=C["muted"],
            )

    def _save_schedule_jobs(self):
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_FILE.write_text(json.dumps(self._scheduled_jobs, ensure_ascii=False, indent=2), "utf-8")

    def _next_job_run(self, job, now=None):
        now = now or datetime.now()
        if job.get("status") not in ("scheduled", "running"):
            return None
        try:
            t = datetime.strptime(job.get("time", ""), "%H:%M").time()
            if job.get("mode") == "daily":
                start_date = datetime.strptime(job.get("date", now.strftime("%Y-%m-%d")), "%Y-%m-%d").date()
                base_date = max(now.date(), start_date)
                candidate = datetime.combine(base_date, t)
                created_at = None
                try:
                    created_at = datetime.fromisoformat(job.get("created_at", ""))
                except:
                    pass
                if job.get("last_run_date") == now.strftime("%Y-%m-%d"):
                    candidate += timedelta(days=1)
                elif candidate <= now and created_at and created_at > candidate:
                    candidate += timedelta(days=1)
                return candidate
            return datetime.strptime(f"{job.get('date')} {job.get('time')}", "%Y-%m-%d %H:%M")
        except:
            return None

    def _apply_schedule(self):
        self._save_article_links()
        date_val = self._sched_date.get().strip()
        time_val = self._sched_time.get().strip()
        pages = parse_pages(self._sched_pages_entry.get()) or parse_pages(read_env().get("FB_PAGES", ""))
        if not pages:
            self.sched_status.configure(text="Chưa có page để đăng. Nhập page cho lịch hoặc thêm FB_PAGES trong Cấu hình.", text_color=C["red"])
            return
        try:
            datetime.strptime(time_val, "%H:%M")
            if self._sched_mode_var.get() == "once":
                run_at = datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M")
                if run_at <= datetime.now():
                    raise ValueError("past")
            else:
                datetime.strptime(date_val, "%Y-%m-%d")
        except:
            self.sched_status.configure(text="Ngày/giờ chưa hợp lệ hoặc đã qua", text_color=C["red"])
            return

        compose = self._compose_options()
        job = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "date": date_val,
            "time": time_val,
            "mode": self._sched_mode_var.get(),
            "action": self._sched_action_var.get(),
            "pages": pages,
            "post_style": compose["post_style"],
            "content_template": compose["content_template"],
            "max_total_articles": compose["max_total_articles"],
            "fetch_full_content": compose["fetch_full_content"],
            "safe_mode": True,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_run_date": "",
        }
        self._scheduled_jobs.append(job)
        self._save_schedule_jobs()
        self._sched_running = True
        self.sched_status.configure(text="Đã thêm lịch đăng bài", text_color=C["green"])
        self._render_schedule_jobs()
        self._update_next_run()

    def _cancel_schedule(self):
        for job in self._scheduled_jobs:
            if job.get("status") in ("scheduled", "running"):
                job["status"] = "disabled"
        self._save_schedule_jobs()
        self._sched_running = False
        self.sched_status.configure(text="Đã tắt tất cả lịch hẹn", text_color=C["red"])
        self._render_schedule_jobs()
        self._update_next_run()

    def _render_schedule_jobs(self):
        if not hasattr(self, "schedule_list_box"):
            return
        lines = []
        for job in sorted(self._scheduled_jobs, key=lambda j: (j.get("date",""), j.get("time","")), reverse=True):
            mode = "hằng ngày" if job.get("mode") == "daily" else "một lần"
            action = "tạo+đăng" if job.get("action") == "full" else "chỉ đăng"
            source = "auto" if job.get("source") == "autopilot" else "manual"
            style = "từng tin" if job.get("post_style") == "don_le" else "tổng hợp"
            page_count = len(job.get("pages", []) or parse_pages(read_env().get("FB_PAGES", "")))
            lines.append(f"{job.get('status','?'):10} | {source:6} | {job.get('date','----')} {job.get('time','--:--')} | {mode:9} | {action:8} | {style:8} | {page_count} page")
        if not lines:
            lines = ["Chưa có lịch nào. Thêm lịch ở khung phía trên."]
        self.schedule_list_box.configure(state="normal")
        self.schedule_list_box.delete("1.0", "end")
        self.schedule_list_box.insert("end", "\n".join(lines))
        self.schedule_list_box.configure(state="disabled")
        if hasattr(self, "today_timeline_box"):
            self._render_today_timeline(self.today_timeline_box)
        self._render_week_calendar()

    def _update_next_run(self):
        runs = [(self._next_job_run(job), job) for job in self._scheduled_jobs]
        runs = [(run, job) for run, job in runs if run]
        if runs:
            run, job = min(runs, key=lambda item: item[0])
            action = "tạo bài + đăng" if job.get("action") == "full" else "đăng bài đã tạo"
            source = "Autopilot" if job.get("source") == "autopilot" else "Lịch thủ công"
            self.next_run_lbl.configure(text=self._next_schedule_text(), text_color=C["text"])
        else:
            if hasattr(self, "next_run_lbl"):
                self.next_run_lbl.configure(text="Chưa có lịch", text_color=C["muted"])

    def _start_scheduler_thread(self):
        def _loop():
            while True:
                self._run_due_scheduled_jobs()
                time.sleep(15)
        threading.Thread(target=_loop, daemon=True).start()

    def _autopilot_daily_count(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return len([
            j for j in self._scheduled_jobs
            if j.get("source") == "autopilot"
            and j.get("last_run_date") == today
            and j.get("last_result") == "success"
        ])

    def _ensure_chrome_for_autopilot(self):
        if check_chrome():
            return True
        chrome_path = find_chrome_path()
        if not chrome_path:
            return False
        profile_dir = str(BASE / "chrome_profile")
        try:
            subprocess.Popen([
                chrome_path,
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--disable-default-apps",
                "https://www.facebook.com",
            ])
            for _ in range(12):
                if check_chrome():
                    return True
                time.sleep(1)
        except:
            return False
        return check_chrome()

    def _run_due_scheduled_jobs(self):
        if self._scheduler_busy:
            return
        now = datetime.now()
        for job in self._scheduled_jobs:
            run_at = self._next_job_run(job, now)
            if run_at and run_at <= now:
                if job.get("source") == "autopilot":
                    limit = int(self._autopilot.get("max_daily_posts", 3) or 3)
                    if self._autopilot_daily_count() >= limit:
                        job["status"] = "scheduled"
                        job["last_run_date"] = now.strftime("%Y-%m-%d")
                        job["last_result"] = "skipped_daily_limit"
                        self._save_schedule_jobs()
                        self.after(0, lambda: [self._render_schedule_jobs(), self._update_next_run()])
                        continue
                self._scheduler_busy = True
                job["status"] = "running"
                self._save_schedule_jobs()
                self.after(0, lambda: [self._render_schedule_jobs(), self._update_next_run()])
                threading.Thread(target=self._execute_scheduled_job, args=(job,), daemon=True).start()
                return

    def _execute_scheduled_job(self, job):
        action = job.get("action", "full")
        commands = []
        queue_entry_id = None
        if not self._ensure_chrome_for_autopilot():
            job["status"] = "scheduled" if job.get("mode") == "daily" else "failed"
            job["last_result"] = "chrome_unavailable"
            job["last_run_at"] = datetime.now().isoformat(timespec="seconds")
            if job.get("mode") == "daily":
                job["last_run_date"] = datetime.now().strftime("%Y-%m-%d")
            self._scheduler_busy = False
            self._save_schedule_jobs()
            self.after(0, lambda: [
                self.sched_status.configure(text="Không mở được Chrome cho lịch tự động.", text_color=C["red"]),
                self._render_schedule_jobs(),
                self._update_next_run(),
            ])
            return

        if action == "full":
            cmd = self._preview_post_command({
                "post_style": job.get("post_style", "tong_hop"),
                "max_total_articles": int(job.get("max_total_articles", 8) or 8),
                "fetch_full_content": bool(job.get("fetch_full_content", False)),
                "content_template": job.get("content_template", "tin_nong"),
            })
            if cmd:
                commands.append(("Soạn bài", cmd))
            else:
                job["status"] = "failed"
                job["last_result"] = "missing_php"
                self._scheduler_busy = False
                self._save_schedule_jobs()
                self.after(0, lambda: [
                    self.sched_status.configure(text="Lịch lỗi: chưa tìm thấy PHP", text_color=C["red"]),
                    self._render_schedule_jobs(),
                    self._update_next_run()
                ])
                return
        elif self._post_queue:
            queue_entry = self._post_queue[0]
            self._write_queue_entry_to_latest(queue_entry)
            queue_entry_id = queue_entry.get("id")
        else:
            job["status"] = "scheduled" if job.get("mode") == "daily" else "failed"
            job["last_result"] = "queue_empty"
            job["last_run_at"] = datetime.now().isoformat(timespec="seconds")
            if job.get("mode") == "daily":
                job["last_run_date"] = datetime.now().strftime("%Y-%m-%d")
            self._scheduler_busy = False
            self._save_schedule_jobs()
            self.after(0, lambda: [
                self.sched_status.configure(text="Lịch lỗi: hàng đợi chưa có bài để đăng.", text_color=C["red"]),
                self._render_schedule_jobs(),
                self._update_next_run()
            ])
            return
        pages = job.get("pages") or parse_pages(read_env().get("FB_PAGES", ""))
        chrome_cmd = [PY, str(BASE / "chrome_poster.py")]
        if pages:
            chrome_cmd.extend(["--pages", *pages])
        commands.append((f"Đăng qua Chrome ({len(pages)} page)", chrome_cmd))

        ok = True
        output_parts = [f"\n\nLỊCH HẸN CHẠY LÚC {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"]
        for label, cmd in commands:
            output_parts.append(f"\n--- {label} ---\n")
            try:
                if "Chrome" in label and job.get("safe_mode", True):
                    preflight_ok, preflight_lines, _checks = self._preflight_checks(require_chrome=True, pages=pages)
                    if not preflight_ok:
                        output_parts.append("\n".join(["PRE-FLIGHT FAILED", *preflight_lines, ""]))
                        ok = False
                        break
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", cwd=str(BASE), timeout=240, env=env)
                output_parts.append((r.stdout or "") + (r.stderr or ""))
                if r.returncode != 0:
                    ok = False
                    break
            except Exception as e:
                output_parts.append(f"\nLỗi: {e}\n")
                ok = False
                break

        if job.get("mode") == "daily":
            job["status"] = "scheduled"
            job["last_run_date"] = datetime.now().strftime("%Y-%m-%d")
        else:
            job["status"] = "done" if ok else "failed"
        job["last_result"] = "success" if ok else "failed"
        job["last_run_at"] = datetime.now().isoformat(timespec="seconds")
        if ok and queue_entry_id:
            self._post_queue = [x for x in self._post_queue if x.get("id") != queue_entry_id]
            self._save_post_queue()
        self._scheduler_busy = False
        self._save_schedule_jobs()

        def _done():
            if hasattr(self, "post_output"):
                self.post_output.configure(state="normal")
                self.post_output.insert("end", "".join(output_parts))
                self.post_output.see("end")
                self.post_output.configure(state="disabled")
            if hasattr(self, "sched_status"):
                self.sched_status.configure(
                    text="Lịch vừa chạy thành công" if ok else "Lịch chạy lỗi, xem Nhật ký/Output",
                    text_color=C["green"] if ok else C["red"])
            self._render_schedule_jobs()
            self._update_next_run()
            self._render_post_queue()
            self._refresh_dashboard()
        self.after(0, _done)

    # ════════════ CONTENT ASSISTANT ════════════
    def _build_chat(self):
        p = self.pages["chat"]
        self._page_title(
            p,
            "Content assistant",
            "Trợ lý nội dung",
            "Soạn caption, rà lại giọng văn và chuẩn bị nội dung trước khi đăng."
        )

        # Model selector
        sel_row = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=8,
                               border_width=1, border_color=C["border"])
        sel_row.pack(fill="x", padx=20, pady=(0,12))
        ctk.CTkLabel(sel_row, text="Nhà cung cấp", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["muted"]).pack(side="left", padx=(14,10), pady=12)
        self.chat_ai_var = ctk.StringVar(value="auto")
        for val, label in [("auto","Tự động"), ("ollama","Ollama"), ("huggingface","HF"), ("gemini","Gemini"), ("openai","OpenAI"), ("grok","Grok")]:
            ctk.CTkRadioButton(sel_row, text=label, variable=self.chat_ai_var, value=val,
                               font=ctk.CTkFont(size=12), text_color=C["text"],
                               fg_color=C["accent"], hover_color=C["accent_hover"]).pack(side="left", padx=8)

        # Chat history display
        chat_card = ctk.CTkFrame(p, corner_radius=8, fg_color=C["card"],
                                  border_width=1, border_color=C["border"])
        chat_card.pack(fill="x", padx=20, pady=(0,10))
        self.chat_box = ctk.CTkTextbox(chat_card, height=400,
                                        font=ctk.CTkFont(size=12),
                                        fg_color=C["input"], text_color=C["text"],
                                        border_width=0, wrap="word")
        self.chat_box.pack(fill="both", padx=12, pady=12, expand=True)
        self.chat_box.insert("end", "Trợ lý nội dung đã sẵn sàng. Hãy nhập câu hỏi hoặc nhờ viết thử caption.\n\n")
        self.chat_box.configure(state="disabled")

        # Input row
        inp_row = ctk.CTkFrame(p, fg_color="transparent")
        inp_row.pack(fill="x", padx=20, pady=(0,16))
        inp_row.columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(
            inp_row, placeholder_text="Nhập câu hỏi... Enter để gửi",
            font=ctk.CTkFont(size=13), height=42,
            fg_color=C["input"], border_color=C["border"], text_color=C["text"])
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())

        self.btn_send_chat = self._button(
            inp_row, "Gửi", variant="primary", width=90, height=42,
            font_size=13, bold=True, command=self._send_chat)
        self.btn_send_chat.grid(row=0, column=1)

        self._button(
            p, "Xóa lịch sử", variant="outline", width=112, height=32,
            font_size=11, command=self._clear_chat,
        ).pack(anchor="e", padx=20, pady=(0,16))

    def _append_chat(self, role: str, text: str):
        colors = {"Bạn": C["blue"], "Trợ lý": C["green"], "Lỗi": C["red"]}
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
        self._append_chat("Bạn", msg)
        self.btn_send_chat.configure(state="disabled", text="Đang gửi")
        self._chat_history.append({"role": "user", "content": msg})

        def _do():
            env = read_env()
            ai_choice = self.chat_ai_var.get()
            free_only = env.get("FREE_AI_ONLY", "true").strip().lower() != "false"
            ollama_base = env.get("OLLAMA_BASE_URL", "http://localhost:11434")
            ollama_model = env.get("OLLAMA_MODEL", "gemma3")
            hf_token = env.get("HF_TOKEN", "")
            hf_model = env.get("HF_MODEL", "deepseek-ai/DeepSeek-R1:fastest")
            openai_key = env.get("OPENAI_API_KEY", "")
            grok_key   = env.get("GROK_API_KEY", "")
            gemini_key = env.get("GEMINI_API_KEY", "")
            openai_model = env.get("OPENAI_MODEL", "chat-latest")
            grok_model   = env.get("GROK_MODEL", "grok-3-mini-fast")
            gemini_model = env.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

            reply = None; provider = ""; last_error = ""
            if ai_choice in ("auto", "ollama") and ollama_base:
                reply, provider = self._chat_ollama(self._chat_history, ollama_base, ollama_model)
                if reply is None:
                    last_error = provider
            if reply is None and ai_choice in ("auto", "huggingface") and hf_token and "THAY" not in hf_token:
                reply, provider = self._chat_huggingface(self._chat_history, hf_token, hf_model)
                if reply is None:
                    last_error = provider
            if reply is None and ai_choice in ("auto", "gemini") and gemini_key and "THAY" not in gemini_key:
                reply, provider = self._chat_gemini(self._chat_history, gemini_key, gemini_model)
                if reply is None:
                    last_error = provider
            if reply is None and not free_only and ai_choice in ("auto", "openai") and openai_key and "THAY" not in openai_key:
                reply, provider = self._chat_openai(self._chat_history, openai_key, openai_model)
                if reply is None:
                    last_error = provider
            if reply is None and not free_only and ai_choice in ("auto", "grok") and grok_key and "THAY" not in grok_key:
                reply, provider = self._chat_grok(self._chat_history, grok_key, grok_model)
                if reply is None:
                    last_error = provider
            if reply is None:
                if last_error:
                    reply = f"Trợ lý chưa phản hồi được.\nChi tiết: {last_error}"
                else:
                    reply = "Chưa có nguồn soạn nội dung nào được cấu hình.\nVào Cấu hình để điền OLLAMA_BASE_URL hoặc HF_TOKEN, hoặc bật Gemini nếu bạn muốn dùng free-tier."
                provider = "error"

            if provider != "error":
                self._chat_history.append({"role": "assistant", "content": reply})

            def _upd():
                role = "Trợ lý" if provider != "error" else "Lỗi"
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
                "instructions": "Bạn là trợ lý nội dung trong app đăng bài Facebook. Trả lời bằng tiếng Việt tự nhiên, ngắn gọn, hữu ích và ưu tiên gợi ý có thể dùng ngay cho nội dung mạng xã hội.",
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

    def _chat_ollama(self, history, base_url, model):
        try:
            import urllib.request, json as _json
            messages = [
                {"role": "system", "content": "Bạn là trợ lý nội dung thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}
            ] + history
            data = _json.dumps({
                "model": model,
                "messages": messages,
                "stream": False,
            }).encode("utf-8")
            url = base_url.rstrip("/") + "/api/chat"
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                res = _json.loads(r.read())
            text = res.get("message", {}).get("content", "").strip()
            if text:
                return text, "ollama"
            return None, "Ollama không trả về nội dung"
        except Exception as e:
            return None, str(e)

    def _chat_huggingface(self, history, token, model):
        try:
            import urllib.request, json as _json
            messages = [
                {"role": "system", "content": "Bạn là trợ lý nội dung thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}
            ] + history
            data = _json.dumps({
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://router.huggingface.co/v1/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                res = _json.loads(r.read())
            text = res["choices"][0]["message"]["content"].strip()
            if text:
                return text, "huggingface"
            return None, "Hugging Face không trả về nội dung"
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
                {"role": "system", "content": "Bạn là trợ lý nội dung thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}
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
                "systemInstruction": {"parts": [{"text": "Bạn là trợ lý nội dung thông minh, trả lời bằng tiếng Việt ngắn gọn và hữu ích."}]},
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
            }).encode()
            last_error = ""
            for gemini_model in self._gemini_model_candidates(model):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={key}"
                    req = urllib.request.Request(url, data=data,
                                                  headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        res = _json.loads(r.read())
                    return res["candidates"][0]["content"]["parts"][0]["text"].strip(), "gemini"
                except Exception as e:
                    last_error = str(e)
            return None, last_error or "Không có Gemini model khả dụng"
        except Exception as e:
            return None, str(e)

    def _gemini_model_candidates(self, configured):
        models = [configured, *GEMINI_TEXT_MODELS]
        clean = []
        for model in models:
            model = str(model or "").replace("models/", "").strip()
            if model and model not in clean:
                clean.append(model)
        return clean

    # ════════════ SETTINGS ════════════
    def _build_settings(self):
        p = self.pages["settings"]
        self._page_title(
            p,
            "Preferences",
            "Cấu hình hệ thống",
            "Thiết lập fanpage, nguồn soạn nội dung và các dịch vụ dự phòng."
        )

        self.setting_fields = {}
        env = read_env()
        self.free_ai_var = ctk.BooleanVar(
            value=env.get("FREE_AI_ONLY", "true").strip().lower() != "false"
        )
        sections = [
            ("Facebook — Danh sách trang đăng bài", [
                ("FB_PAGES", "Trang Facebook (ngăn cách bằng dấu phẩy)",
                 "VD: myfanpage,another.page hoặc https://facebook.com/page"),
            ]),
            ("Nguồn soạn miễn phí", [
                ("OLLAMA_BASE_URL", "Ollama URL", "http://localhost:11434"),
                ("OLLAMA_MODEL",   "Ollama model", "gemma3"),
                ("HF_TOKEN",       "Hugging Face token", "hf_..."),
                ("HF_MODEL",       "HF model", "deepseek-ai/DeepSeek-R1:fastest"),
            ]),
            ("Chống trùng bản tin", [
                ("AVOID_RECENT_DUPLICATES", "Bật chống trùng", "true"),
                ("ARTICLE_HISTORY_DAYS", "Số ngày né tin cũ", "14"),
                ("MAX_TOTAL_ARTICLES", "Số tin tối đa mỗi bài", "8"),
            ]),
            ("Tùy chọn nội dung mặc định", [
                ("POST_STYLE", "Kiểu bài mặc định", "tong_hop hoặc don_le"),
                ("CONTENT_TEMPLATE", "Mẫu nội dung mặc định", "tin_nong"),
                ("MAX_POSTS", "Số bài tối đa", "1"),
                ("MAX_ARTICLES", "Số tin mỗi nguồn", "5"),
                ("FETCH_FULL_CONTENT", "Đọc nội dung đầy đủ", "false"),
            ]),
            ("Grok", [
                ("GROK_API_KEY",  "API Key", "xai-..."),
                ("GROK_MODEL",    "Model",   "grok-3-mini-fast"),
            ]),
            ("Gemini", [
                ("GEMINI_API_KEY", "API Key", "AIzaSy..."),
                ("GEMINI_MODEL",   "Model",   "gemini-2.5-flash-lite"),
            ]),
        ]

        for sec_title, fields in sections:
            card = self._card(p, sec_title)
            if sec_title.startswith("Nguồn"):
                ctk.CTkCheckBox(
                    card,
                    text="Ưu tiên nguồn miễn phí",
                    variable=self.free_ai_var,
                    onvalue=True,
                    offvalue=False,
                    font=ctk.CTkFont(size=12),
                    text_color=C["text"],
                ).pack(anchor="w", padx=16, pady=(6, 10))
                ctk.CTkLabel(
                    card,
                    text="Bật chế độ này để app ưu tiên Ollama, Hugging Face và Gemini free-tier. Các nguồn trả phí sẽ bị bỏ qua.",
                    font=ctk.CTkFont(size=10),
                    text_color=C["subtle"],
                    justify="left",
                ).pack(anchor="w", padx=16, pady=(0, 8))
            if sec_title.startswith("Chống"):
                ctk.CTkLabel(
                    card,
                    text="App sẽ nhớ link/tiêu đề đã dùng gần đây để hạn chế tạo lại cùng một bản tin.",
                    font=ctk.CTkFont(size=10),
                    text_color=C["subtle"],
                    justify="left",
                ).pack(anchor="w", padx=16, pady=(6, 8))
                dedupe_tools = ctk.CTkFrame(card, fg_color="transparent")
                dedupe_tools.pack(fill="x", padx=16, pady=(0, 8))
                self._button(
                    dedupe_tools, "Xóa lịch sử tin đã dùng", variant="outline",
                    width=170, height=30, command=self._clear_article_history,
                ).pack(side="left")
                self.dedupe_status = ctk.CTkLabel(
                    dedupe_tools, text="", font=ctk.CTkFont(size=11), text_color=C["muted"]
                )
                self.dedupe_status.pack(side="left", padx=10)
            for key, label, placeholder in fields:
                ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12),
                             text_color=C["muted"]).pack(anchor="w", padx=16, pady=(6,2))
                # FB_PAGES: text area lớn hơn để nhập nhiều trang
                if key == "FB_PAGES":
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         font=ctk.CTkFont(size=12), height=38,
                                         fg_color=C["input"], border_color=C["border"],
                                         text_color=C["text"])
                    ctk.CTkLabel(card, text="Mỗi slug cách nhau bằng dấu phẩy. VD: page1,page2,page3",
                                 font=ctk.CTkFont(size=10), text_color=C["subtle"]).pack(anchor="w", padx=16)
                else:
                    show = "*" if "TOKEN" in key or "KEY" in key else None
                    entry = ctk.CTkEntry(card, placeholder_text=placeholder,
                                         show=show,
                                         font=ctk.CTkFont(size=12), height=36,
                                         fg_color=C["input"], border_color=C["border"],
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
        self._button(
            p, "Lưu cấu hình", variant="primary", width=150, height=40,
            font_size=13, bold=True, command=self._save_settings,
        ).pack(anchor="w", padx=20, pady=(8,24))

    def _clear_article_history(self):
        try:
            ARTICLE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            ARTICLE_HISTORY_FILE.write_text("[]", "utf-8")
            if hasattr(self, "dedupe_status"):
                self.dedupe_status.configure(text="Đã xóa bộ nhớ trùng.", text_color=C["green"])
                self.after(3000, lambda: self.dedupe_status.configure(text=""))
        except Exception as e:
            if hasattr(self, "dedupe_status"):
                self.dedupe_status.configure(text=f"Không xóa được: {e}", text_color=C["red"])

    def _save_settings(self):
        env = {}
        for key, entry in self.setting_fields.items():
            val = entry.get().strip()
            env[key] = val
        env["FREE_AI_ONLY"] = "true" if self.free_ai_var.get() else "false"
        write_env(env, managed_keys=set(self.setting_fields.keys()) | {"FREE_AI_ONLY"})
        self.save_status.configure(text="Đã lưu.", text_color=C["green"])
        self._refresh_dashboard()
        self.after(3000, lambda: self.save_status.configure(text=""))

    # ════════════ LOGS ════════════
    def _build_logs(self):
        p = self.pages["logs"]
        self._page_title(
            p,
            "Activity log",
            "Nhật ký vận hành",
            "Theo dõi workflow, Chrome poster và lịch chạy tự động."
        )

        # Tab row
        tf = ctk.CTkFrame(p, fg_color="transparent")
        tf.pack(fill="x", padx=20, pady=(0,12))

        self.log_tabs = {}
        self.current_log = "workflow"
        for key, label in [("workflow","Workflow"), ("chrome","Chrome"), ("cron","Cron")]:
            btn = self._button(
                tf, label, variant="primary" if key == "workflow" else "secondary",
                width=100, height=30, command=lambda k=key: self._switch_log(k)
            )
            btn.pack(side="left", padx=(0,6))
            self.log_tabs[key] = btn

        # Refresh button
        self._button(
            tf, "Làm mới", variant="outline", width=90, height=30,
            command=self._load_logs,
        ).pack(side="left")

        # Log box
        card = self._card(p)
        self.log_box = ctk.CTkTextbox(card, height=440,
                                       font=ctk.CTkFont(size=11, family="Courier New"),
                                       fg_color=C["input"], text_color=C["log_text"],
                                       border_width=0)
        self.log_box.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self._load_logs()

    def _switch_log(self, key):
        self.current_log = key
        for k, btn in self.log_tabs.items():
            if k == key:
                btn.configure(fg_color=C["accent"], hover_color=C["accent_hover"], text_color=C["ink"], border_width=0)
            else:
                btn.configure(fg_color=C["panel2"], hover_color=C["border"], text_color=C["text"], border_width=1)
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
            if hasattr(self, "today_timeline_box"):
                self._render_today_timeline(self.today_timeline_box)
            self._render_week_calendar()
        # Cập nhật trạng thái Chrome trên trang Post
        try:
            ok = check_chrome()
            if ok:
                self._set_step(1, "done")
                self.chrome_status_lbl.configure(
                    text="Chrome đã kết nối. Nhấn kiểm tra đăng nhập.",
                    text_color=C["green"])
            else:
                self.chrome_status_lbl.configure(
                    text="Chrome chưa kết nối. Nhấn Mở Chrome.",
                    text_color=C["muted"])
        except: pass
        self.after(10000, self._refresh_loop)


    # ════════════ NANO BANANA 2 METHODS ════════════

    def _nb_generate(self):
        """Tạo ảnh AI bằng Nano Banana 2 (Gemini) trong thread riêng."""
        import threading
        prompt = self.nb_prompt.get("1.0", "end").strip()
        if not prompt:
            self.nb_status.configure(text="⚠️ Vui lòng nhập prompt!", text_color=C["red"])
            return

        self.btn_nb_generate.configure(state="disabled", text="Đang tạo ảnh...")
        self.nb_status.configure(text="⏳ Đang gọi Gemini API...", text_color=C["muted"])
        self.nb_result_path.configure(text="")

        def _run():
            try:
                from nano_banana import generate_image, _read_env_key
            except ImportError:
                self.after(0, lambda: self._nb_done(
                    {"success": False, "message": "Không tìm thấy nano_banana.py"}))
                return

            result = generate_image(
                prompt,
                api_key=_read_env_key(),
                model=self.nb_model_var.get(),
                aspect=self.nb_aspect_var.get(),
                size="1K",
                transparent=self.nb_transparent_var.get(),
                output_dir=str(BASE / "output"),
                on_log=lambda msg, lvl="info": self.after(
                    0, lambda m=msg: self.nb_status.configure(text=m, text_color=C["muted"])
                ),
            )
            self.after(0, lambda r=result: self._nb_done(r))

        threading.Thread(target=_run, daemon=True).start()

    def _nb_done(self, result: dict):
        """Xử lý kết quả sau khi tạo ảnh xong."""
        self.btn_nb_generate.configure(state="normal", text="🍌 Tạo ảnh AI")
        if result["success"]:
            self.nb_status.configure(
                text=f"✅ Tạo ảnh thành công! Model: {result['model']} · ~${result['cost_usd']:.3f}",
                text_color=C["green"],
            )
            self.nb_result_path.configure(text=result["image_path"])

            # Show thumbnail
            try:
                from PIL import Image, ImageTk
                img = Image.open(result["image_path"])
                img.thumbnail((160, 100))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 100))
                self.nb_preview_lbl.configure(image=ctk_img, text="")
                self.nb_preview_lbl._image = ctk_img
            except Exception:
                self.nb_preview_lbl.configure(text="✅ Ảnh đã tạo")

            # Auto-attach to post if checked
            if self.nb_auto_attach_var.get():
                self._nb_attach_path(result["image_path"])

            self._nb_refresh_costs()
        else:
            self.nb_status.configure(
                text=f"❌ {result['message']}", text_color=C["red"]
            )

    def _nb_attach_path(self, path: str):
        """Ghi image_path vào latest_post.json để chrome_poster.py tự đính kèm."""
        try:
            jp = BASE / "output" / "latest_post.json"
            if jp.exists():
                import json as _json
                d = _json.loads(jp.read_text("utf-8"))
                d["image_path"] = path
                d["image_paths"] = [path]
                jp.write_text(_json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                self.nb_status.configure(
                    text=f"✅ Đã gắn ảnh vào bài · {path.split('/')[-1].split(chr(92))[-1]}",
                    text_color=C["green"],
                )
        except Exception as e:
            self.nb_status.configure(text=f"⚠️ Không gắn được: {e}", text_color=C["red"])

    def _nb_attach_to_post(self):
        """Nút Gắn ảnh hiện tại — gắn ảnh vừa tạo vào latest_post.json."""
        path = self.nb_result_path.cget("text").strip()
        if not path:
            self.nb_status.configure(text="⚠️ Chưa có ảnh để gắn!", text_color=C["red"])
            return
        self._nb_attach_path(path)

    def _nb_open_output_dir(self):
        """Mở thư mục output trong Explorer."""
        import subprocess, os
        out = BASE / "output"
        out.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{out}"')

    def _nb_refresh_costs(self):
        """Cập nhật label chi phí Nano Banana."""
        try:
            from nano_banana import get_total_cost
            info = get_total_cost()
            self.nb_cost_lbl.configure(
                text=f"${info['total_usd']:.4f}\n{info['total_generations']} lần tạo",
                text_color=C["accent"],
            )
        except Exception:
            self.nb_cost_lbl.configure(text="$0.0000\n0 lần tạo")


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
