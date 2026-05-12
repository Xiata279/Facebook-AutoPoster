#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Football Auto Poster - Desktop App
Chạy: python app.py
Cài thư viện: pip install customtkinter pillow
"""

import os, sys, json, subprocess, threading
from pathlib import Path
from datetime import datetime

try:
    import customtkinter as ctk
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter", "pillow"], check=True)
    import customtkinter as ctk

# ── Cấu hình ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE = Path(__file__).parent
PHP  = r"C:\xampp\php\php.exe"
PY   = sys.executable

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
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE), timeout=120)
            callback(r.stdout + r.stderr, r.returncode == 0)
        except Exception as e:
            callback(str(e), False)
    threading.Thread(target=_run, daemon=True).start()

def check_chrome():
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", 9222), timeout=1)
        s.close(); return True
    except: return False


# ════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚽ Football Auto Poster")
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
        self.sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color="#161b22")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo = ctk.CTkLabel(self.sidebar, text="⚽ Auto Poster",
                             font=ctk.CTkFont(size=18, weight="bold"), text_color="#e6edf3")
        logo.pack(pady=(24, 4), padx=16)
        ctk.CTkLabel(self.sidebar, text="by Xiata", font=ctk.CTkFont(size=11),
                     text_color="#8b949e").pack(pady=(0,20))

        ctk.CTkLabel(self.sidebar, text="MENU", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#484f58").pack(anchor="w", padx=20, pady=(0,6))

        self.nav_buttons = {}
        menus = [
            ("dashboard",  "🏠  Dashboard"),
            ("post",       "✨  Tạo & Đăng bài"),
            ("settings",   "⚙️   Cài đặt"),
            ("logs",       "📋  Nhật ký"),
        ]
        for key, label in menus:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", hover_color="#21262d",
                text_color="#c9d1d9", height=40, corner_radius=8,
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Trạng thái Chrome ở dưới sidebar
        self.sidebar.pack_propagate(False)
        self.chrome_label = ctk.CTkLabel(self.sidebar, text="● Chrome: Đang kiểm tra",
                                          font=ctk.CTkFont(size=11), text_color="#8b949e")
        self.chrome_label.pack(side="bottom", pady=16, padx=12)

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1117")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Pages container
        self.pages = {}
        for key in ["dashboard", "post", "settings", "logs"]:
            frame = ctk.CTkScrollableFrame(self.content, fg_color="#0d1117",
                                            scrollbar_button_color="#30363d")
            frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            frame.grid_remove()
            self.pages[key] = frame

        self._build_dashboard()
        self._build_post()
        self._build_settings()
        self._build_logs()

    def _show_page(self, key):
        for k, f in self.pages.items():
            f.grid_remove()
        self.pages[key].grid()
        self.current_page = key

        # Highlight nav button
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color="#21262d" if k == key else "transparent",
                          text_color="#ffffff" if k == key else "#c9d1d9")

    # ─── Card helper ───
    def _card(self, parent, title="", pady=(0,12)):
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color="#161b22",
                         border_width=1, border_color="#30363d")
        f.pack(fill="x", padx=20, pady=pady)
        if title:
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#8b949e").pack(anchor="w", padx=16, pady=(14,4))
        return f

    # ════════════ DASHBOARD ════════════
    def _build_dashboard(self):
        p = self.pages["dashboard"]

        ctk.CTkLabel(p, text="🏠  Dashboard", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#e6edf3").pack(anchor="w", padx=20, pady=(20,4))
        self.dash_time = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=11),
                                       text_color="#8b949e")
        self.dash_time.pack(anchor="w", padx=20, pady=(0,16))

        # Status row
        sf = ctk.CTkFrame(p, fg_color="transparent")
        sf.pack(fill="x", padx=20, pady=(0,12))
        sf.columnconfigure((0,1,2,3), weight=1)

        self.stat_cards = {}
        stats = [
            ("chrome",   "🌐 Chrome",      "Kiểm tra..."),
            ("fb_pages", "📘 Trang FB",    "Chưa có"),
            ("grok",     "🟣 Grok AI",     "Chưa có"),
            ("gemini",   "🔵 Gemini AI",   "Chưa có"),
        ]
        for i, (k, title, default) in enumerate(stats):
            card = ctk.CTkFrame(sf, corner_radius=10, fg_color="#161b22",
                                border_width=1, border_color="#30363d", height=90)
            card.grid(row=0, column=i, padx=6, sticky="ew")
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11),
                         text_color="#8b949e").pack(anchor="w", padx=14, pady=(14,2))
            lbl = ctk.CTkLabel(card, text=default, font=ctk.CTkFont(size=12, weight="bold"),
                               text_color="#e6edf3")
            lbl.pack(anchor="w", padx=14)
            self.stat_cards[k] = lbl

        # Latest post
        c2 = self._card(p, "📄 Bài đăng mới nhất")
        self.latest_post_lbl = ctk.CTkTextbox(c2, height=160, font=ctk.CTkFont(size=12),
                                               fg_color="#0d1117", text_color="#c9d1d9",
                                               border_width=0)
        self.latest_post_lbl.pack(fill="x", padx=16, pady=(0,14))
        self.latest_post_lbl.insert("end", "Chưa có bài đăng nào. Vào 'Tạo & Đăng bài' để bắt đầu.")
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

        # Buttons
        bf = self._card(p, "🎛️ Điều khiển")
        row = ctk.CTkFrame(bf, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0,14))

        self.btn_preview  = ctk.CTkButton(row, text="👁  Xem trước tin", width=160, height=38,
                                           font=ctk.CTkFont(size=13),
                                           fg_color="#21262d", hover_color="#30363d",
                                           command=lambda: self._run_post_action("preview"))
        self.btn_preview.pack(side="left", padx=(0,8))

        self.btn_generate = ctk.CTkButton(row, text="✨  Tạo bài (AI)", width=160, height=38,
                                           font=ctk.CTkFont(size=13),
                                           fg_color="#1f6feb", hover_color="#388bfd",
                                           command=lambda: self._run_post_action("generate"))
        self.btn_generate.pack(side="left", padx=(0,8))

        self.btn_chrome   = ctk.CTkButton(row, text="🚀  Đăng qua Chrome", width=180, height=38,
                                           font=ctk.CTkFont(size=13),
                                           fg_color="#238636", hover_color="#2ea043",
                                           command=lambda: self._run_post_action("chrome"))
        self.btn_chrome.pack(side="left")

        # Progress label
        self.post_status = ctk.CTkLabel(bf, text="", font=ctk.CTkFont(size=12),
                                         text_color="#8b949e")
        self.post_status.pack(anchor="w", padx=16, pady=(0,6))

        # Output
        oc = self._card(p, "📤 Output")
        self.post_output = ctk.CTkTextbox(oc, height=380, font=ctk.CTkFont(size=11, family="Courier New"),
                                          fg_color="#010409", text_color="#7ee787",
                                          border_width=0)
        self.post_output.pack(fill="both", padx=16, pady=(0,14), expand=True)
        self.post_output.insert("end", "Nhấn một nút ở trên để bắt đầu...\n")
        self.post_output.configure(state="disabled")

    def _run_post_action(self, action):
        btns = [self.btn_preview, self.btn_generate, self.btn_chrome]
        for b in btns: b.configure(state="disabled")

        labels = {"preview":"Đang lấy tin tức...", "generate":"AI đang tạo bài...", "chrome":"Đang đăng qua Chrome..."}
        self.post_status.configure(text=f"⏳ {labels.get(action,'...')}", text_color="#d29922")

        self.post_output.configure(state="normal")
        self.post_output.delete("1.0","end")
        self.post_output.insert("end", f"▶ Bắt đầu: {action} lúc {datetime.now().strftime('%H:%M:%S')}\n\n")
        self.post_output.configure(state="disabled")

        if action == "preview":
            cmd = [PHP, str(BASE/"run_football_post.php"), "preview-post"]
        elif action == "generate":
            cmd = [PHP, str(BASE/"run_football_post.php")]
        else:
            py_path = r"C:\Users\Xiata\AppData\Local\Programs\Python\Python312\python.exe"
            cmd = [py_path, str(BASE/"chrome_poster.py")]

        def on_done(out, ok):
            def _update():
                self.post_output.configure(state="normal")
                self.post_output.insert("end", out)
                self.post_output.see("end")
                self.post_output.configure(state="disabled")
                self.post_status.configure(
                    text="✅ Hoàn thành!" if ok else "❌ Có lỗi xảy ra",
                    text_color="#3fb950" if ok else "#da3633"
                )
                for b in btns: b.configure(state="normal")
            self.after(0, _update)

        run_cmd(cmd, on_done)

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
        self.after(10000, self._refresh_loop)


# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
