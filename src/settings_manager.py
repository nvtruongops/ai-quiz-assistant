"""
Settings Manager Module
Manages application configuration, persistence (config.json & .env), and Settings Dialog GUI.
"""

import os
import sys
import json
import base64
import time
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from typing import Optional, Dict, Any, Callable

_src_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_src_dir)

# Default application settings
DEFAULT_SETTINGS = {
    'font_size': 10,
    'popup_width': 500,
    'popup_height': 0,
    'history_popup_width': 560,
    'history_popup_height': 0,
    'settings_win_width': 720,
    'settings_win_height': 680,
    'popup_opacity': 0.96,
    'popup_bg_color': '#ffffff',                 # Default WHITE background
    'answers_per_line': 10,
    'question_mode': 'multiple_choice',          # 'multiple_choice', 'multiple_choice_explanation', or 'essay'
    'answer_display_mode': 'letter_and_text',    # 'letter_and_text' or 'letter_only'
    'api_provider': 'gemini',                    # 'gemini' or 'custom'
    'gemini_model': '',
    'enable_provider_failover': True,            # Auto-rotate to backup provider on error / rate limit
    # Hotkey combinations (Alt + key)
    'hotkey_capture': 'z',
    'hotkey_autofill': 'x',
    'hotkey_answers': 'c',
    'hotkey_history': 'h',
    'hotkey_reset': 'r',
    'hotkey_settings': 's',
    'hotkey_exit': 'q',
    'enable_mouse_gestures': True,
    'save_screenshots': True,
    'enable_autofill': True,
    'autofill_click_delay_ms': 200,
    'autofill_restore_cursor': True,
    'autofill_smooth_movement': True,
}


class SettingsManager:
    """Manages application settings persistence and access"""

    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        if not config_file:
            config_file = os.path.join(PROJECT_ROOT, "config.json")
        elif not os.path.isabs(config_file):
            config_file = os.path.join(PROJECT_ROOT, config_file)

        if not env_file:
            env_file = os.path.join(PROJECT_ROOT, ".env")
        elif not os.path.isabs(env_file):
            env_file = os.path.join(PROJECT_ROOT, env_file)

        self.config_file = config_file
        self.env_file = env_file
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self) -> None:
        """Load settings from config.json and .env file"""
        # Load from config.json first
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    for k, v in cfg.items():
                        self.settings[k] = v
                    # Clean up legacy api key if previously stored in config.json
                    self.settings.pop('gemini_api_key', None)
            except Exception:
                pass

        # Load environment values
        try:
            from dotenv import load_dotenv
            if os.path.exists(self.env_file):
                load_dotenv(self.env_file, override=True)
        except ImportError:
            if os.path.exists(self.env_file):
                try:
                    with open(self.env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                k, v = line.split('=', 1)
                                os.environ[k.strip()] = v.strip().strip('"').strip("'")
                except Exception:
                    pass

        env_provider = os.getenv('API_PROVIDER')
        if env_provider in ['gemini', 'custom']:
            self.settings['api_provider'] = env_provider

        env_gemini_model = os.getenv('GEMINI_MODEL')
        if env_gemini_model:
            self.settings['gemini_model'] = env_gemini_model

    def save_settings(self) -> None:
        """Save settings to config.json and synchronize .env"""
        try:
            cfg = {}
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except Exception:
                    cfg = {}

            cfg.update(self.settings)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)

            self._update_env_file()

        except Exception as e:
            print(f"Error saving settings: {e}")

    def _update_env_file(self) -> None:
        """Synchronize settings with .env file"""
        env_lines = []
        if os.path.exists(self.env_file):
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()
            except Exception:
                env_lines = []

        def set_or_add_env(lines, key, val):
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={val}\n"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={val}\n")
            return lines

        provider = self.settings.get('api_provider', 'gemini')
        env_lines = set_or_add_env(env_lines, 'API_PROVIDER', provider)

        gemini_model = self.settings.get('gemini_model', '')
        env_lines = set_or_add_env(env_lines, 'GEMINI_MODEL', gemini_model)

        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value and persist"""
        self.settings[key] = value
        self.save_settings()

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like item access: settings[key]"""
        return self.settings[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like item assignment: settings[key] = value"""
        self.settings[key] = value
        self.save_settings()

    def __contains__(self, key: str) -> bool:
        """Allow 'key in settings' checks"""
        return key in self.settings

    def __iter__(self):
        """Allow iterating over keys"""
        return iter(self.settings)


def _create_card_selector(parent, options, current_val, on_change=None, columns: int = 1):
    """
    Creates an interactive, beautiful Card/Tile radio selector with zero ambiguity.
    options = [(val, title, description), ...]
    columns: 1 for single column (pack), >=2 for grid layout.
    Returns (var: tk.StringVar, update_func)
    """
    var = tk.StringVar(master=parent, value=current_val)
    cards = {}

    selected_badge = "✔" if columns > 1 else "✔ Selected"

    def update_ui():
        sel = var.get()
        for v, (c_frame, ind_lbl, t_lbl, d_lbl, badge_lbl) in cards.items():
            if v == sel:
                c_frame.config(bg="#eff6ff", highlightbackground="#0066cc", highlightcolor="#0066cc", highlightthickness=2)
                ind_lbl.config(text="🔘", fg="#0066cc", bg="#eff6ff")
                t_lbl.config(fg="#004085", bg="#eff6ff", font=("Segoe UI", 9, "bold"))
                d_lbl.config(fg="#374151", bg="#eff6ff")
                badge_lbl.config(text=selected_badge, fg="#0066cc", bg="#dbeafe")
            else:
                c_frame.config(bg="#ffffff", highlightbackground="#d1d5db", highlightcolor="#d1d5db", highlightthickness=1)
                ind_lbl.config(text="⚪", fg="#9ca3af", bg="#ffffff")
                t_lbl.config(fg="#1f2937", bg="#ffffff", font=("Segoe UI", 9))
                d_lbl.config(fg="#6b7280", bg="#ffffff")
                badge_lbl.config(text="", bg="#ffffff")

    if columns > 1:
        for c in range(columns):
            parent.grid_columnconfigure(c, weight=1)

    for i, (val, title, desc) in enumerate(options):
        pad_y = 5 if columns > 1 else 8
        card = tk.Frame(parent, bg="#ffffff", relief=tk.FLAT, bd=0, padx=8, pady=pad_y, cursor="hand2")
        if columns > 1:
            r_idx, c_idx = divmod(i, columns)
            card.grid(row=r_idx, column=c_idx, sticky="nsew", padx=4, pady=3)
        else:
            card.pack(fill=tk.X, pady=4)

        top_row = tk.Frame(card, bg="#ffffff")
        top_row.pack(fill=tk.X)

        ind_lbl = tk.Label(top_row, text="⚪", font=("Segoe UI", 10), bg="#ffffff", cursor="hand2")
        ind_lbl.pack(side=tk.LEFT, padx=(0, 4))

        t_lbl = tk.Label(top_row, text=title, font=("Segoe UI", 8 if columns > 1 else 9), bg="#ffffff", cursor="hand2")
        t_lbl.pack(side=tk.LEFT)

        badge_lbl = tk.Label(top_row, text="", font=("Segoe UI", 8, "bold"), padx=4, pady=0, cursor="hand2")
        badge_lbl.pack(side=tk.RIGHT)

        wrap_w = 260 if columns > 1 else 540
        d_lbl = tk.Label(card, text=desc, font=("Segoe UI", 7 if columns > 1 else 8), bg="#ffffff", justify=tk.LEFT, wraplength=wrap_w, cursor="hand2")
        d_lbl.pack(anchor=tk.W, padx=(20, 0), pady=(1, 0))

        def make_click_handler(choice_val):
            def _handler(e=None):
                var.set(choice_val)
                update_ui()
                if on_change:
                    on_change(choice_val)
            return _handler

        click_fn = make_click_handler(val)
        for w in (card, top_row, ind_lbl, t_lbl, badge_lbl, d_lbl):
            w.bind("<Button-1>", click_fn)

        cards[val] = (card, ind_lbl, t_lbl, d_lbl, badge_lbl)

    update_ui()
    return var, update_ui


def pick_color_at_cursor(parent, callback: Callable[[str], None]) -> None:
    """
    Eyedropper tool: creates a transparent fullscreen overlay to pick pixel color under cursor.
    Click confirms color; Escape or right-click cancels.
    """
    import ctypes

    def get_pixel_color(x, y):
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            rgb_int = ctypes.windll.gdi32.GetPixel(hdc, int(x), int(y))
            ctypes.windll.user32.ReleaseDC(0, hdc)
            r = rgb_int & 0xFF
            g = (rgb_int >> 8) & 0xFF
            b = (rgb_int >> 16) & 0xFF
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#ffffff"

    overlay = tk.Toplevel(parent)
    overlay.attributes('-fullscreen', True)
    overlay.attributes('-alpha', 0.05)
    overlay.attributes('-topmost', True)
    overlay.config(cursor="crosshair")

    # Floating indicator loupe
    loupe = tk.Toplevel(overlay)
    loupe.overrideredirect(True)
    loupe.attributes('-topmost', True)
    loupe_frame = tk.Frame(loupe, bg="#1e293b", bd=2, relief=tk.SOLID, padx=6, pady=4)
    loupe_frame.pack()

    chip = tk.Frame(loupe_frame, width=22, height=22, bd=1, relief=tk.SOLID)
    chip.pack(side=tk.LEFT, padx=(0, 6))

    hex_lbl = tk.Label(loupe_frame, text="#FFFFFF", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1e293b")
    hex_lbl.pack(side=tk.LEFT, padx=(0, 6))

    hint_lbl = tk.Label(loupe_frame, text="Click: Select | Esc: Cancel", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b")
    hint_lbl.pack(side=tk.LEFT)

    def on_motion(e):
        x, y = e.x_root, e.y_root
        c = get_pixel_color(x, y)
        chip.config(bg=c)
        hex_lbl.config(text=c.upper())
        lx = min(overlay.winfo_screenwidth() - 220, x + 16)
        ly = min(overlay.winfo_screenheight() - 60, y + 16)
        loupe.geometry(f"+{lx}+{ly}")

    def on_click(e):
        x, y = e.x_root, e.y_root
        c = get_pixel_color(x, y)
        close_picker()
        callback(c)

    def close_picker(e=None):
        try:
            loupe.destroy()
        except Exception:
            pass
        try:
            overlay.destroy()
        except Exception:
            pass

    overlay.bind("<Motion>", on_motion)
    overlay.bind("<Button-1>", on_click)
    overlay.bind("<Button-3>", close_picker)
    overlay.bind("<Escape>", close_picker)
    loupe.bind("<Button-1>", on_click)
    loupe.bind("<Escape>", close_picker)


def create_scrollable_tab(notebook, title: str):
    """
    Creates a tab with 100% width, hidden scrollbar (clean UI), and smooth mousewheel scrolling.
    Returns: (outer_tab, inner_content_frame, canvas)
    """
    outer_tab = ttk.Frame(notebook)
    canvas = tk.Canvas(outer_tab, borderwidth=0, highlightthickness=0, bg="#f8fafc")
    inner_content = tk.Frame(canvas, bg="#f8fafc", padx=14, pady=12)

    canvas_window = canvas.create_window((0, 0), window=inner_content, anchor="nw")
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _configure_content(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _configure_canvas(event):
        canvas.itemconfig(canvas_window, width=event.width)

    inner_content.bind("<Configure>", _configure_content)
    canvas.bind("<Configure>", _configure_canvas)

    notebook.add(outer_tab, text=title)
    return outer_tab, inner_content, canvas


def show_initial_setup_dialog(
    config_manager: Optional[Any] = None,
    settings_manager: Optional[SettingsManager] = None,
    parent: Optional[tk.Tk] = None
) -> bool:
    """
    Initial Setup Wizard (3-Step Stepper):
    - Step 1: 🤖 AI Provider (Google Gemini / Custom Local / Skip AI)
    - Step 2: 🎨 UI Theme for Popup HUD (Stealth, White, Dark, Cream, Blue, Gray) + Live Preview Card + Opacity
    - Step 3: 🎯 Quiz Mode & Hotkeys Cheatsheet Reference (Finish & Start)
    """
    if settings_manager is None:
        settings_manager = SettingsManager()

    env_path = os.path.join(PROJECT_ROOT, ".env")

    # Read current env values if available
    cur_provider = os.getenv('API_PROVIDER', 'gemini')
    cur_gemini_key = os.getenv('GEMINI_API_KEY', '')
    cur_gemini_model = os.getenv('GEMINI_MODEL', '')
    cur_custom_url = (os.getenv('CUSTOM_API_URL') or '').strip()
    cur_custom_key = os.getenv('CUSTOM_API_KEY', '')
    cur_custom_model = os.getenv('CUSTOM_MODEL', '')

    if config_manager:
        cur_provider = config_manager.get('API_PROVIDER', cur_provider)
        cur_gemini_key = config_manager.get('GEMINI_API_KEY', cur_gemini_key)
        cur_gemini_model = config_manager.get('GEMINI_MODEL', cur_gemini_model)
        cfg_custom_url = config_manager.get('CUSTOM_API_URL')
        if cfg_custom_url and str(cfg_custom_url).strip():
            cur_custom_url = str(cfg_custom_url).strip()
        cur_custom_key = config_manager.get('CUSTOM_API_KEY', cur_custom_key)
        cur_custom_model = config_manager.get('CUSTOM_MODEL', cur_custom_model)

    if not cur_custom_url:
        cur_custom_url = 'http://localhost:11434/v1'

    root = tk.Tk()
    root.title("AI Quiz Assistant 2.0 - Initial Setup Wizard")
    ww, wh = 660, 720
    root.geometry(f"{ww}x{wh}")
    root.minsize(620, 680)
    root.resizable(True, True)

    # Set modern app window icon
    ico_path = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if not os.path.exists(ico_path):
        ico_path = os.path.join(PROJECT_ROOT, "icon.ico")
    png_path = os.path.join(PROJECT_ROOT, "assets", "icon.png")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass
    if os.path.exists(png_path):
        try:
            _setup_icon_img = tk.PhotoImage(file=png_path)
            root.iconphoto(True, _setup_icon_img)
            root._setup_icon_img = _setup_icon_img
        except Exception:
            pass

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(0, (sw - ww) // 2)
    y = max(20, (sh - wh) // 2)
    root.geometry(f"+{x}+{y}")

    root.lift()
    root.attributes('-topmost', True)
    root.after(150, lambda: root.attributes('-topmost', False))
    root.focus_force()

    result = {'success': False, 'skipped_ai': False}
    current_step = [1]

    # Redesigned cohesive header
    header = tk.Frame(root, bg="#1e293b", padx=16, pady=12)
    header.pack(fill=tk.X)

    title_box = tk.Frame(header, bg="#1e293b")
    title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Label(
        title_box,
        text="⚙️ AI Quiz Assistant 2.0 — Initial Setup",
        font=("Segoe UI", 12, "bold"),
        fg="#89b4fa",
        bg="#1e293b"
    ).pack(anchor=tk.W)

    sub_title_lbl = tk.Label(
        title_box,
        text="Step 1/3: 🤖 Configure AI Provider (or Skip to explore first)",
        font=("Segoe UI", 9),
        fg="#94a3b8",
        bg="#1e293b"
    )
    sub_title_lbl.pack(anchor=tk.W, pady=(2, 0))

    # Stepper Progress Bar
    stepper_frame = tk.Frame(root, bg="#0f172a", padx=14, pady=8)
    stepper_frame.pack(fill=tk.X)

    step_pills = []
    step_labels = [
        "1. 🤖 AI Provider",
        "2. 🎨 HUD Theme",
        "3. 🎯 Mode & Hotkeys"
    ]
    for idx, s_text in enumerate(step_labels):
        pill = tk.Label(
            stepper_frame,
            text=s_text,
            font=("Segoe UI", 8, "bold" if idx == 0 else "normal"),
            bg="#0284c7" if idx == 0 else "#1e293b",
            fg="#ffffff" if idx == 0 else "#94a3b8",
            padx=10,
            pady=4,
            relief=tk.FLAT
        )
        pill.pack(side=tk.LEFT, padx=(0, 8))
        step_pills.append(pill)

    content_container = tk.Frame(root, padx=16, pady=10)
    content_container.pack(fill=tk.BOTH, expand=True)

    # 3 Frames for the 3 steps
    step1_frame = tk.Frame(content_container)
    step2_frame = tk.Frame(content_container)
    step3_frame = tk.Frame(content_container)

    # ========================================================
    # STEP 1: AI Provider (Gemini / Custom / Skip)
    # ========================================================
    tk.Label(
        step1_frame,
        text="1. Select AI Vision Provider:",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor=tk.W, pady=(0, 6))

    prov_options = [
        ("gemini", "Google Gemini AI Studio (Cloud)", "Free, ultra-fast vision analysis (~1.4s), high quality multimodal reasoning from Google."),
        ("custom", "Custom Local / Proxy (OpenAI-compatible)", "Compatible with Ollama, vLLM, LM Studio, Claude Proxy, or OpenAI-format endpoints.")
    ]
    provider_var, _ = _create_card_selector(step1_frame, prov_options, cur_provider if cur_provider in ['gemini', 'custom'] else 'gemini')

    config_container = tk.LabelFrame(step1_frame, text=" 2. API Connection Details & Model ", font=("Segoe UI", 9, "bold"), padx=12, pady=8)
    config_container.pack(fill=tk.X, pady=(6, 8))

    # --- Gemini Frame ---
    gemini_frame = tk.Frame(config_container)

    tk.Label(gemini_frame, text="Gemini API Key:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    g_key_box = tk.Frame(gemini_frame)
    g_key_box.pack(fill=tk.X, pady=(2, 6))

    def toggle_g_key():
        if gemini_key_entry.cget('show') == '*':
            gemini_key_entry.config(show='')
            toggle_g_btn.config(text="🙈 Hide")
        else:
            gemini_key_entry.config(show='*')
            toggle_g_btn.config(text="👁 Show")

    toggle_g_btn = tk.Button(g_key_box, text="👁 Show", command=toggle_g_key, padx=10, font=("Segoe UI", 8))
    toggle_g_btn.pack(side=tk.RIGHT, padx=(6, 0))

    gemini_key_entry = tk.Entry(g_key_box, show="*", font=("Segoe UI", 10))
    gemini_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_gemini_key:
        gemini_key_entry.insert(0, cur_gemini_key)

    tk.Label(gemini_frame, text="Gemini Model:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    g_model_box = tk.Frame(gemini_frame)
    g_model_box.pack(fill=tk.X, pady=(2, 4))

    gemini_model_combo = ttk.Combobox(
        g_model_box,
        values=[cur_gemini_model] if cur_gemini_model else [],
        state="normal",
        font=("Segoe UI", 9)
    )
    gemini_model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_gemini_model:
        gemini_model_combo.set(cur_gemini_model)

    def fetch_gemini_models():
        k = gemini_key_entry.get().strip()
        if not k:
            messagebox.showwarning("Warning", "Please enter Gemini API Key first!", parent=root)
            return

        def _worker():
            g_status_lbl.config(text="⏳ Fetching available models from Google...", fg="#e67e22")
            try:
                try:
                    from gemini_client import GeminiAPIClient
                except ImportError:
                    from src.gemini_client import GeminiAPIClient
                ok, models, msg = GeminiAPIClient.list_models(k)
                if ok and models:
                    def _apply():
                        gemini_model_combo['values'] = models
                        if not gemini_model_combo.get() or gemini_model_combo.get() not in models:
                            gemini_model_combo.set(models[0])
                        g_status_lbl.config(text=f"✅ Found {len(models)} available models", fg="#27ae60")
                    root.after(0, _apply)
                else:
                    g_status_lbl.config(text=f"❌ {msg[:45]}", fg="#e74c3c")
            except Exception as ex:
                g_status_lbl.config(text=f"❌ {str(ex)[:45]}", fg="#e74c3c")

        threading.Thread(target=_worker, daemon=True).start()

    fetch_g_btn = tk.Button(g_model_box, text="🔄 Fetch Models", command=fetch_gemini_models, font=("Segoe UI", 8), padx=6)
    fetch_g_btn.pack(side=tk.LEFT, padx=(6, 0))

    link_g = tk.Label(gemini_frame, text="👉 Click here to get a free API Key at Google AI Studio", font=("Segoe UI", 8, "underline"), fg="#0066cc", cursor="hand2")
    link_g.pack(anchor=tk.W, pady=(2, 6))
    link_g.bind("<Button-1>", lambda e: os.startfile("https://aistudio.google.com/app/apikey"))

    g_test_row = tk.Frame(gemini_frame)
    g_test_row.pack(fill=tk.X, pady=(2, 0))
    g_status_lbl = tk.Label(g_test_row, text="Not tested", font=("Segoe UI", 8, "italic"), fg="#7f8c8d")

    def test_gemini_action():
        k = gemini_key_entry.get().strip()
        m = gemini_model_combo.get().strip()
        if not k:
            messagebox.showwarning("Warning", "Please enter Gemini API Key before testing!", parent=root)
            return

        def _worker():
            g_status_lbl.config(text="⏳ Testing Gemini connection...", fg="#e67e22")
            t0 = time.time()
            try:
                try:
                    from gemini_client import GeminiAPIClient
                except ImportError:
                    from src.gemini_client import GeminiAPIClient
                ok, models, _ = GeminiAPIClient.list_models(k)
                curr_m = m
                if ok and models:
                    def _update_models():
                        gemini_model_combo['values'] = models
                        if not gemini_model_combo.get() or gemini_model_combo.get() not in models:
                            gemini_model_combo.set(models[0])
                    root.after(0, _update_models)
                    if not curr_m:
                        curr_m = models[0]
                if not curr_m:
                    curr_m = "gemini-2.5-flash"
                from google import genai
                client = genai.Client(api_key=k)
                client.models.generate_content(model=curr_m, contents="ping")
                lat = round(time.time() - t0, 2)
                g_status_lbl.config(text=f"✅ Connected successfully ({lat}s)!", fg="#27ae60")
            except Exception as e:
                err_str = str(e)
                if "API_KEY_INVALID" in err_str:
                    g_status_lbl.config(text="❌ Error: Invalid API Key!", fg="#e74c3c")
                else:
                    g_status_lbl.config(text=f"❌ Error: {err_str[:40]}...", fg="#e74c3c")

        threading.Thread(target=_worker, daemon=True).start()

    tk.Button(g_test_row, text="⚡ Test Connection", command=test_gemini_action, font=("Segoe UI", 8), bg="#27ae60", fg="white", padx=8).pack(side=tk.LEFT)
    g_status_lbl.pack(side=tk.LEFT, padx=10)

    # --- Custom Frame ---
    custom_frame = tk.Frame(config_container)

    tk.Label(custom_frame, text="API Endpoint URL (Standard /v1):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    custom_url_entry = tk.Entry(custom_frame, font=("Segoe UI", 10))
    custom_url_entry.pack(fill=tk.X, pady=(2, 6))
    custom_url_entry.insert(0, cur_custom_url or 'http://localhost:11434/v1')

    tk.Label(custom_frame, text="API Key (Optional for local / Bearer key for proxy):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    c_key_box = tk.Frame(custom_frame)
    c_key_box.pack(fill=tk.X, pady=(2, 6))

    def toggle_c_key():
        if custom_key_entry.cget('show') == '*':
            custom_key_entry.config(show='')
            toggle_c_btn.config(text="🙈 Hide")
        else:
            custom_key_entry.config(show='*')
            toggle_c_btn.config(text="👁 Show")

    toggle_c_btn = tk.Button(c_key_box, text="👁 Show", command=toggle_c_key, padx=10, font=("Segoe UI", 8))
    toggle_c_btn.pack(side=tk.RIGHT, padx=(6, 0))

    custom_key_entry = tk.Entry(c_key_box, show="*", font=("Segoe UI", 10))
    custom_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_custom_key:
        custom_key_entry.insert(0, cur_custom_key)

    tk.Label(custom_frame, text="Model Name (Vision-capable):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    c_model_box = tk.Frame(custom_frame)
    c_model_box.pack(fill=tk.X, pady=(2, 6))

    custom_model_combo = ttk.Combobox(
        c_model_box,
        values=[cur_custom_model] if cur_custom_model else [],
        state="normal",
        font=("Segoe UI", 9)
    )
    custom_model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_custom_model:
        custom_model_combo.set(cur_custom_model)

    def fetch_custom_models():
        url = custom_url_entry.get().strip()
        k = custom_key_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter API URL first!", parent=root)
            return

        def _worker():
            c_status_lbl.config(text="⏳ Fetching models from server...", fg="#e67e22")
            try:
                try:
                    from custom_client import CustomAPIClient
                except ImportError:
                    from src.custom_client import CustomAPIClient
                ok, models, msg = CustomAPIClient.list_models(url, k)
                if ok and models:
                    def _apply():
                        custom_model_combo['values'] = models
                        if not custom_model_combo.get() or custom_model_combo.get() not in models:
                            custom_model_combo.set(models[0])
                        c_status_lbl.config(text=f"✅ Found {len(models)} models", fg="#27ae60")
                    root.after(0, _apply)
                else:
                    c_status_lbl.config(text=f"❌ {msg[:45]}", fg="#e74c3c")
            except Exception as ex:
                c_status_lbl.config(text=f"❌ {str(ex)[:45]}", fg="#e74c3c")

        threading.Thread(target=_worker, daemon=True).start()

    fetch_c_btn = tk.Button(c_model_box, text="🔄 Fetch Models", command=fetch_custom_models, font=("Segoe UI", 8), padx=6)
    fetch_c_btn.pack(side=tk.LEFT, padx=(6, 0))

    c_test_row = tk.Frame(custom_frame)
    c_test_row.pack(fill=tk.X, pady=(2, 0))
    c_status_lbl = tk.Label(c_test_row, text="Not tested", font=("Segoe UI", 8, "italic"), fg="#7f8c8d")

    def test_custom_action():
        url = custom_url_entry.get().strip()
        k = custom_key_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter API URL!", parent=root)
            return

        def _worker():
            c_status_lbl.config(text="⏳ Testing connection...", fg="#e67e22")
            t0 = time.time()
            try:
                try:
                    from custom_client import CustomAPIClient
                except ImportError:
                    from src.custom_client import CustomAPIClient
                ok, models, _ = CustomAPIClient.list_models(url, k)
                lat = round(time.time() - t0, 2)
                if ok and models:
                    def _update_c_models():
                        custom_model_combo['values'] = models
                        if not custom_model_combo.get() or custom_model_combo.get() not in models:
                            custom_model_combo.set(models[0])
                    root.after(0, _update_c_models)
                    c_status_lbl.config(text=f"✅ Connected ({len(models)} models, {lat}s)!", fg="#27ae60")
                else:
                    c_status_lbl.config(text=f"⚠️ Server reached ({lat}s), but no models listed", fg="#e67e22")
            except Exception as e:
                c_status_lbl.config(text=f"❌ Error: {str(e)[:40]}...", fg="#e74c3c")

        threading.Thread(target=_worker, daemon=True).start()

    tk.Button(c_test_row, text="⚡ Test Connection", command=test_custom_action, font=("Segoe UI", 8), bg="#8e44ad", fg="white", padx=8).pack(side=tk.LEFT)
    c_status_lbl.pack(side=tk.LEFT, padx=10)

    def on_provider_toggle(*args):
        p = provider_var.get()
        if p == 'gemini':
            custom_frame.pack_forget()
            gemini_frame.pack(fill=tk.X, expand=True)
        else:
            gemini_frame.pack_forget()
            custom_frame.pack(fill=tk.X, expand=True)
            if not custom_url_entry.get().strip():
                custom_url_entry.delete(0, tk.END)
                custom_url_entry.insert(0, "http://localhost:11434/v1")

    provider_var.trace_add("write", on_provider_toggle)
    on_provider_toggle()

    tip1_card = tk.Frame(step1_frame, bg="#f1f5f9", padx=10, pady=8, bd=1, relief=tk.SOLID)
    tip1_card.pack(fill=tk.X, pady=(6, 0))
    tk.Label(
        tip1_card,
        text="💡 Tip: You can click '⏭️ Skip AI' below if you want to explore the interface first.\n"
             "The assistant will run normally in your System Tray, and you can configure your API key anytime via Alt+S.",
        font=("Segoe UI", 8),
        fg="#475569",
        bg="#f1f5f9",
        justify=tk.LEFT
    ).pack(anchor=tk.W)

    # ========================================================
    # STEP 2: UI Theme for Popup HUD
    # ========================================================
    tk.Label(
        step2_frame,
        text="Select Floating HUD Card Style (Exam Result Overlay):",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor=tk.W, pady=(0, 2))
    tk.Label(
        step2_frame,
        text="Click any theme to preview background color, borders, and text contrast:",
        font=("Segoe UI", 8),
        fg="#64748b"
    ).pack(anchor=tk.W, pady=(0, 4))

    cur_theme = settings_manager.get('popup_bg_color', '#ffffff')
    if str(cur_theme).startswith('stealth'):
        cur_theme_init = 'stealth'
    elif str(cur_theme).lower() in ['#ffffff', '#1e1e2e', '#fef9c3', '#e0f2fe', '#f8fafc']:
        cur_theme_init = str(cur_theme).lower()
    else:
        cur_theme_init = '#ffffff'

    theme_options = [
        ("stealth", "👻 Stealth (Tàng hình)", "Ghost card matching screen, borderless, muted non-bold text."),
        ("#ffffff", "⚪ Pure White (Trắng sáng)", "Clean pure white, subtle border, high-contrast dark text."),
        ("#1e1e2e", "🌙 Dark Mode (Tối dịu mắt)", "Catppuccin Mocha dark theme with crisp white text."),
        ("#fef9c3", "🍦 Warm Cream (Vàng kem)", "Warm cream tone, reduces eye strain during long tests."),
        ("#e0f2fe", "🔵 Soft Blue (Xanh dịu)", "Pastel blue background, modern and elegant aesthetic."),
        ("#f8fafc", "🌫️ Modern Gray (Xám nhạt)", "Neutral light gray minimalist theme, professional look.")
    ]

    selected_theme_var = tk.StringVar(value=cur_theme_init)

    themes_wrapper = tk.Frame(step2_frame)
    themes_wrapper.pack(fill=tk.X, pady=(0, 4))

    # Helper functions for color blending and live opacity simulation
    def _hex_to_rgb(hex_s):
        s = hex_s.lstrip('#')
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        return (255, 255, 255)

    def _rgb_to_hex(rgb):
        return f"#{max(0, min(255, int(round(rgb[0])))):02x}{max(0, min(255, int(round(rgb[1])))):02x}{max(0, min(255, int(round(rgb[2])))):02x}"

    def blend_color(fg_hex, bg_hex, alpha):
        try:
            fg = _hex_to_rgb(fg_hex)
            bg = _hex_to_rgb(bg_hex)
            blended = (
                fg[0] * alpha + bg[0] * (1.0 - alpha),
                fg[1] * alpha + bg[1] * (1.0 - alpha),
                fg[2] * alpha + bg[2] * (1.0 - alpha)
            )
            return _rgb_to_hex(blended)
        except Exception:
            return fg_hex

    preview_box = tk.LabelFrame(
        step2_frame,
        text=" 👁️ Live HUD Card Preview (Desktop Background Simulation) ",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=6,
        bg="#0f172a",
        fg="#94a3b8"
    )
    preview_box.pack(fill=tk.X, pady=(2, 4))

    preview_outer = tk.Frame(preview_box, bd=1, relief=tk.SOLID)
    preview_outer.pack(fill=tk.X, padx=4, pady=4)

    preview_header = tk.Frame(preview_outer, padx=8, pady=3)
    preview_header.pack(fill=tk.X)

    preview_title = tk.Label(preview_header, text="Question 1/1", font=("Segoe UI", 8, "bold"))
    preview_title.pack(side=tk.LEFT)

    preview_badge = tk.Label(preview_header, text="AI Vision", font=("Segoe UI", 7), padx=4, pady=1)
    preview_badge.pack(side=tk.LEFT, padx=(6, 0))

    preview_close = tk.Label(preview_header, text="✕", font=("Segoe UI", 8, "bold"))
    preview_close.pack(side=tk.RIGHT)

    preview_body = tk.Frame(preview_outer, padx=10, pady=6)
    preview_body.pack(fill=tk.X)

    preview_q = tk.Label(
        preview_body,
        text="Question 1: Which country do the Paracel (Hoàng Sa) and Spratly (Trường Sa) Islands belong to?",
        font=("Segoe UI", 8, "bold"),
        anchor=tk.W,
        wraplength=580,
        justify=tk.LEFT
    )
    preview_q.pack(anchor=tk.W)

    preview_a = tk.Label(
        preview_body,
        text="✓ Answer: A. Vietnam (Việt Nam)",
        font=("Segoe UI", 9, "bold"),
        anchor=tk.W
    )
    preview_a.pack(anchor=tk.W, pady=(2, 2))

    preview_exp_btn = tk.Label(
        preview_body,
        text="💡 Explanation: The Paracel and Spratly Islands have historically and legally belonged under the continuous sovereign territory of Vietnam (Việt Nam).",
        font=("Segoe UI", 7),
        anchor=tk.W,
        wraplength=580,
        justify=tk.LEFT,
        padx=6,
        pady=2
    )
    preview_exp_btn.pack(anchor=tk.W)

    # State for real floating HUD window on desktop
    real_hud_state = {'win': None, 'widgets': {}}

    def close_real_hud():
        if real_hud_state['win']:
            try:
                if real_hud_state['win'].winfo_exists():
                    real_hud_state['win'].destroy()
            except Exception:
                pass
            real_hud_state['win'] = None

    def update_real_hud_content(th, is_st, alpha):
        win = real_hud_state.get('win')
        if not win or not win.winfo_exists():
            return
        try:
            win.attributes('-alpha', alpha)
            widgets = real_hud_state.get('widgets', {})
            if not widgets:
                return
            widgets['outer'].config(
                bg=th.get('border', '#cbd5e1'),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )
            widgets['header'].config(bg=th.get('header_bg', '#f1f5f9'))
            widgets['title'].config(
                bg=th.get('header_bg', '#f1f5f9'),
                fg=th.get('accent', '#0284c7'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            widgets['badge'].config(
                bg=th.get('badge_bg', '#e2e8f0'),
                fg=th.get('badge_fg', '#334155'),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )
            widgets['close'].config(
                bg=th.get('header_bg', '#f1f5f9'),
                fg=th.get('close_fg', '#dc2626')
            )
            widgets['body'].config(bg=th.get('bg', '#ffffff'))
            widgets['q'].config(
                bg=th.get('bg', '#ffffff'),
                fg=th.get('question', '#0369a1'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            widgets['a'].config(
                bg=th.get('bg', '#ffffff'),
                fg=th.get('answer', '#15803d'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            widgets['exp'].config(
                bg=th.get('exp_btn_bg', '#e2e8f0'),
                fg=th.get('exp_btn_fg', '#0284c7'),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )
        except Exception:
            pass

    def apply_theme_preview(theme_code=None):
        if theme_code is None:
            theme_code = selected_theme_var.get()
        try:
            try:
                from popup_manager import get_popup_theme
            except ImportError:
                from src.popup_manager import get_popup_theme
            th = get_popup_theme(theme_code)
            is_st = th.get('is_stealth', False)
            alpha = float(opacity_var.get()) / 100.0

            # Compute blended colors simulating transparency over the desktop container #0f172a
            raw_bg = th.get('bg', '#ffffff')
            raw_hdr = th.get('header_bg', '#f1f5f9')
            bg_blended = blend_color(raw_bg, "#0f172a", alpha)
            hdr_blended = blend_color(raw_hdr, "#0f172a", alpha)

            preview_outer.config(
                bg=blend_color(th.get('border', '#cbd5e1'), "#0f172a", alpha),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )
            preview_header.config(bg=hdr_blended)
            preview_title.config(
                bg=hdr_blended,
                fg=th.get('accent', '#0284c7'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            preview_badge.config(
                bg=blend_color(th.get('badge_bg', '#e2e8f0'), "#0f172a", alpha),
                fg=th.get('badge_fg', '#334155'),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )
            preview_close.config(
                bg=hdr_blended,
                fg=th.get('close_fg', '#dc2626'),
                font=("Segoe UI", 8 if is_st else 9, "normal" if is_st else "bold")
            )
            preview_body.config(bg=bg_blended)
            preview_q.config(
                bg=bg_blended,
                fg=th.get('question', '#0369a1'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            preview_a.config(
                bg=bg_blended,
                fg=th.get('answer', '#15803d'),
                font=("Segoe UI", 8, "normal" if is_st else "bold")
            )
            preview_exp_btn.config(
                bg=blend_color(th.get('exp_btn_bg', '#e2e8f0'), "#0f172a", alpha),
                fg=th.get('exp_btn_fg', '#0284c7'),
                bd=0 if is_st else 1,
                relief=tk.FLAT if is_st else tk.SOLID
            )

            if real_hud_state['win'] and real_hud_state['win'].winfo_exists():
                update_real_hud_content(th, is_st, alpha)
        except Exception:
            pass

    def on_theme_change(new_th):
        selected_theme_var.set(new_th)
        apply_theme_preview(new_th)

    _, _ = _create_card_selector(themes_wrapper, theme_options, cur_theme_init, on_change=on_theme_change, columns=2)

    # Opacity row
    op_box = tk.Frame(step2_frame)
    op_box.pack(fill=tk.X, pady=(2, 2))

    cur_opacity_pct = int(round(float(settings_manager.get('popup_opacity', 0.96)) * 100))
    opacity_var = tk.IntVar(value=cur_opacity_pct)

    tk.Label(op_box, text="HUD Window Opacity:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
    op_val_lbl = tk.Label(op_box, text=f"{cur_opacity_pct}%", font=("Segoe UI", 9, "bold"), fg="#0284c7", width=5)
    op_val_lbl.pack(side=tk.RIGHT)

    def toggle_real_hud():
        if real_hud_state['win'] and real_hud_state['win'].winfo_exists():
            close_real_hud()
            real_hud_btn.config(text="🪟 Test Real HUD on Desktop", bg="#0284c7")
        else:
            show_real_hud()
            real_hud_btn.config(text="✕ Close Real HUD", bg="#dc2626")

    def show_real_hud():
        close_real_hud()
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        alpha = float(opacity_var.get()) / 100.0
        win.attributes('-alpha', alpha)

        sw = root.winfo_screenwidth()
        win_w, win_h = 420, 150
        pos_x = max(20, sw - win_w - 40)
        pos_y = 60
        win.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        r_outer = tk.Frame(win, bd=1, relief=tk.SOLID)
        r_outer.pack(fill=tk.BOTH, expand=True)

        r_header = tk.Frame(r_outer, padx=8, pady=3)
        r_header.pack(fill=tk.X)

        r_title = tk.Label(r_header, text="Question 1/1 [Real HUD Preview]", font=("Segoe UI", 8, "bold"))
        r_title.pack(side=tk.LEFT)

        r_badge = tk.Label(r_header, text="Live HUD", font=("Segoe UI", 7), padx=4, pady=1)
        r_badge.pack(side=tk.LEFT, padx=(6, 0))

        r_close = tk.Label(r_header, text="✕", font=("Segoe UI", 8, "bold"), cursor="hand2")
        r_close.pack(side=tk.RIGHT)
        r_close.bind("<Button-1>", lambda e: toggle_real_hud())

        r_body = tk.Frame(r_outer, padx=10, pady=6)
        r_body.pack(fill=tk.BOTH, expand=True)

        r_q = tk.Label(
            r_body,
            text="Question 1: Which country do the Paracel (Hoàng Sa) and Spratly (Trường Sa) Islands belong to?",
            font=("Segoe UI", 8, "bold"),
            anchor=tk.W,
            wraplength=390,
            justify=tk.LEFT
        )
        r_q.pack(anchor=tk.W)

        r_a = tk.Label(
            r_body,
            text="✓ Answer: A. Vietnam (Việt Nam)",
            font=("Segoe UI", 8, "bold"),
            anchor=tk.W
        )
        r_a.pack(anchor=tk.W, pady=(2, 2))

        r_exp = tk.Label(
            r_body,
            text="💡 Explanation: The Paracel and Spratly Islands have historically and legally belonged under the continuous sovereign territory of Vietnam (Việt Nam).",
            font=("Segoe UI", 7),
            anchor=tk.W,
            wraplength=390,
            justify=tk.LEFT,
            padx=4,
            pady=1
        )
        r_exp.pack(anchor=tk.W)

        real_hud_state['win'] = win
        real_hud_state['widgets'] = {
            'outer': r_outer,
            'header': r_header,
            'title': r_title,
            'badge': r_badge,
            'close': r_close,
            'body': r_body,
            'q': r_q,
            'a': r_a,
            'exp': r_exp
        }

        try:
            try:
                from popup_manager import get_popup_theme
            except ImportError:
                from src.popup_manager import get_popup_theme
            th = get_popup_theme(selected_theme_var.get())
            is_st = th.get('is_stealth', False)
            update_real_hud_content(th, is_st, alpha)
        except Exception:
            pass

    real_hud_btn = tk.Button(
        op_box,
        text="🪟 Test Real HUD on Desktop",
        command=toggle_real_hud,
        font=("Segoe UI", 8, "bold"),
        bg="#0284c7",
        fg="#ffffff",
        padx=8,
        pady=2,
        cursor="hand2"
    )
    real_hud_btn.pack(side=tk.RIGHT, padx=(6, 8))

    def on_op_slide(val):
        pct = int(float(val))
        op_val_lbl.config(text=f"{pct}%")
        apply_theme_preview()

    op_scale = ttk.Scale(op_box, from_=60, to=100, variable=opacity_var, command=on_op_slide)
    op_scale.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(8, 4))

    apply_theme_preview(cur_theme_init)

    # ========================================================
    # STEP 3: Quiz Mode & Hotkeys Customization
    # ========================================================
    tk.Label(
        step3_frame,
        text="1. Select Default Quiz Solving Mode:",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor=tk.W, pady=(0, 4))

    mode_options = [
        ("multiple_choice", "⚡ Quick Multiple Choice (Answers Only) - Recommended", "Extracts questions and chosen answers (A, B, C, D...) directly without lengthy explanations."),
        ("multiple_choice_explanation", "📝 Multiple Choice + Explanation", "Extracts questions, answers, and collapsible step-by-step explanations."),
        ("essay", "✍️ Essay / Step-by-Step Solutions", "Extracts open-ended, mathematical, or essay questions with full written solutions.")
    ]
    cur_mode = settings_manager.get('question_mode', 'multiple_choice')
    mode_var, _ = _create_card_selector(step3_frame, mode_options, cur_mode)

    hk_box = tk.LabelFrame(step3_frame, text=" 2. Customize Keyboard Shortcuts (Click any box to change key) ", font=("Segoe UI", 9, "bold"), padx=12, pady=6)
    hk_box.pack(fill=tk.X, pady=(6, 4))

    step3_hotkey_entries = {}
    hotkey_defs = [
        ('hotkey_capture',  '📸 Silent Screen Capture & Solve:', 'z', 'Captures screen silently; solves quiz in background'),
        ('hotkey_autofill', '⚡ Auto-Fill & Click Choices:',     'x', 'AI coordinates detection & automated mouse clicks'),
        ('hotkey_answers',  '👁 Show Latest Question Result:',   'c', 'Toggles floating HUD card with latest question answer'),
        ('hotkey_history',  '📜 View Full Question History:',    'h', 'Browses captured questions in order (1..N) & queue'),
        ('hotkey_reset',    '🔄 Reset Quiz Session:',            'r', 'Clears session history & cached answers for new test'),
        ('hotkey_settings', '⚙️ Open Settings Dialog:',          's', 'Opens settings to adjust themes, AI keys & options')
    ]

    def make_step3_hk_formatter(ent):
        def on_key_typed(event):
            val = ent.get().strip()
            if not val:
                return
            char = val[-1].lower()
            if char.isalnum():
                ent.delete(0, tk.END)
                ent.insert(0, char.upper())
        return on_key_typed

    for hk_key, label_text, default_val, desc in hotkey_defs:
        row = tk.Frame(hk_box)
        row.pack(fill=tk.X, pady=2)

        lbl = tk.Label(row, text=label_text, font=("Segoe UI", 8, "bold"), width=30, anchor=tk.W)
        lbl.pack(side=tk.LEFT)

        tk.Label(row, text="Alt +", font=("Consolas", 9, "bold"), fg="#475569").pack(side=tk.LEFT, padx=(2, 2))

        curr_val = settings_manager.get(hk_key, default_val)
        entry = tk.Entry(row, width=3, font=("Consolas", 10, "bold"), justify=tk.CENTER, bd=1, relief=tk.SOLID)
        entry.insert(0, str(curr_val).upper())
        entry.pack(side=tk.LEFT, padx=(0, 8))
        entry.bind("<KeyRelease>", make_step3_hk_formatter(entry))
        step3_hotkey_entries[hk_key] = entry

        tk.Label(row, text=desc, font=("Segoe UI", 8), fg="#64748b", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)

    note3 = tk.Label(
        step3_frame,
        text="💡 Upon clicking Finish, the assistant runs silently in your System Tray (bottom-right taskbar).\n"
             "You can reopen Settings anytime by pressing Alt+S or right-clicking the tray icon.",
        font=("Segoe UI", 8, "italic"),
        fg="#64748b",
        justify=tk.LEFT
    )
    note3.pack(anchor=tk.W, pady=(4, 0))

    # ========================================================
    # STEPPER NAVIGATION LOGIC
    # ========================================================
    btn_box = tk.Frame(root, padx=16, pady=10)
    btn_box.pack(fill=tk.X, side=tk.BOTTOM)

    def on_exit():
        close_real_hud()
        root.destroy()

    def update_stepper_ui(step_num):
        subtitles = {
            1: "Step 1/3: 🤖 Configure AI Provider (or Skip to explore first)",
            2: "Step 2/3: 🎨 Choose HUD Appearance (UI Theme & Transparency)",
            3: "Step 3/3: 🎯 Default Quiz Mode & Custom Hotkeys"
        }
        sub_title_lbl.config(text=subtitles.get(step_num, ""))

        for i, pill in enumerate(step_pills):
            s_idx = i + 1
            if s_idx == step_num:
                pill.config(bg="#0284c7", fg="#ffffff", font=("Segoe UI", 8, "bold"), text=step_labels[i])
            elif s_idx < step_num:
                pill.config(bg="#16a34a", fg="#ffffff", font=("Segoe UI", 8), text=f"✓ {step_labels[i]}")
            else:
                pill.config(bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 8), text=step_labels[i])

    def skip_step1():
        result['skipped_ai'] = True
        show_step(2)

    def submit_step1():
        sel_p = provider_var.get()
        if sel_p == 'gemini':
            g_key = gemini_key_entry.get().strip()
            g_model = gemini_model_combo.get().strip()
            if not g_key:
                ans = messagebox.askyesno(
                    "Gemini API Key Missing",
                    "No Gemini API Key entered.\n\n"
                    "Would you like to skip AI configuration for now and explore the app (you can configure it later via Alt+S)?",
                    parent=root
                )
                if ans:
                    skip_step1()
                return
            if len(g_key) < 15:
                messagebox.showerror("Error", "Gemini API Key is too short! Please verify.", parent=root)
                return
            if not g_model:
                gemini_model_combo.set("gemini-2.5-flash")
            result['skipped_ai'] = False
            show_step(2)
        else:
            c_url = custom_url_entry.get().strip()
            c_model = custom_model_combo.get().strip()
            if not c_url or not c_model:
                ans = messagebox.askyesno(
                    "Custom Configuration Incomplete",
                    "API URL or Model Name is missing.\n\n"
                    "Would you like to skip AI configuration for now and continue?",
                    parent=root
                )
                if ans:
                    skip_step1()
                return
            result['skipped_ai'] = False
            show_step(2)

    def on_save_finish():
        # 1. Save AI Credentials if not skipped
        if not result['skipped_ai']:
            sel_p = provider_var.get()
            env_lines = []
            if os.path.exists(env_path):
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        env_lines = f.readlines()
                except Exception:
                    env_lines = []

            def set_line(lines, k, v):
                found = False
                for i, line in enumerate(lines):
                    if line.strip().startswith(f"{k}="):
                        lines[i] = f"{k}={v}\n"
                        found = True
                        break
                if not found:
                    lines.append(f"{k}={v}\n")
                return lines

            env_lines = set_line(env_lines, 'API_PROVIDER', sel_p)
            if sel_p == 'gemini':
                env_lines = set_line(env_lines, 'GEMINI_API_KEY', gemini_key_entry.get().strip())
                env_lines = set_line(env_lines, 'GEMINI_MODEL', gemini_model_combo.get().strip())
            else:
                env_lines = set_line(env_lines, 'CUSTOM_API_URL', custom_url_entry.get().strip())
                env_lines = set_line(env_lines, 'CUSTOM_API_KEY', custom_key_entry.get().strip())
                env_lines = set_line(env_lines, 'CUSTOM_MODEL', custom_model_combo.get().strip())

            try:
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(env_lines)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to write .env: {e}", parent=root)
                return

            os.environ['API_PROVIDER'] = sel_p
            if sel_p == 'gemini':
                os.environ['GEMINI_API_KEY'] = gemini_key_entry.get().strip()
                os.environ['GEMINI_MODEL'] = gemini_model_combo.get().strip()
            else:
                os.environ['CUSTOM_API_URL'] = custom_url_entry.get().strip()
                os.environ['CUSTOM_API_KEY'] = custom_key_entry.get().strip()
                os.environ['CUSTOM_MODEL'] = custom_model_combo.get().strip()

            settings_manager.settings['api_provider'] = sel_p
            if sel_p == 'gemini':
                settings_manager.settings['gemini_model'] = gemini_model_combo.get().strip()

        # Validate unique hotkeys (Step 3)
        used_keys = {}
        for hk_key, ent in step3_hotkey_entries.items():
            val = ent.get().strip().lower()
            if not val or not val.isalnum():
                messagebox.showerror("Invalid Hotkey", "Please enter a valid single letter or number for each shortcut.", parent=root)
                return
            char = val[0]
            if char in used_keys:
                messagebox.showerror("Duplicate Hotkey", f"The hotkey 'Alt + {char.upper()}' is assigned to multiple actions! Please assign distinct keys.", parent=root)
                return
            used_keys[char] = hk_key

        # Save Hotkeys (Step 3)
        for hk_key, ent in step3_hotkey_entries.items():
            val = ent.get().strip().lower()
            if val and val.isalnum():
                settings_manager.settings[hk_key] = val[0]

        # 2. Save Theme & Opacity (Step 2)
        settings_manager.settings['popup_bg_color'] = selected_theme_var.get()
        settings_manager.settings['popup_opacity'] = round(opacity_var.get() / 100.0, 2)

        # 3. Save Quiz Mode (Step 3)
        settings_manager.settings['question_mode'] = mode_var.get()

        settings_manager.save_settings()

        if config_manager:
            config_manager.reload()

        close_real_hud()
        result['success'] = True
        root.destroy()

    def show_step(step_num):
        close_real_hud()
        current_step[0] = step_num
        update_stepper_ui(step_num)

        step1_frame.pack_forget()
        step2_frame.pack_forget()
        step3_frame.pack_forget()

        if step_num == 1:
            step1_frame.pack(fill=tk.BOTH, expand=True)
        elif step_num == 2:
            step2_frame.pack(fill=tk.BOTH, expand=True)
        elif step_num == 3:
            step3_frame.pack(fill=tk.BOTH, expand=True)

        for w in btn_box.winfo_children():
            w.destroy()

        if step_num == 1:
            tk.Button(btn_box, text="✕ Exit", command=on_exit, font=("Segoe UI", 9), padx=12, pady=4).pack(side=tk.LEFT)
            tk.Button(btn_box, text="Next ➡️", command=submit_step1, font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", padx=16, pady=4).pack(side=tk.RIGHT)
            tk.Button(btn_box, text="⏭️ Skip AI", command=skip_step1, font=("Segoe UI", 9), bg="#475569", fg="white", padx=12, pady=4).pack(side=tk.RIGHT, padx=6)

        elif step_num == 2:
            tk.Button(btn_box, text="⬅️ Back", command=lambda: show_step(1), font=("Segoe UI", 9), padx=12, pady=4).pack(side=tk.LEFT)
            tk.Button(btn_box, text="Next ➡️", command=lambda: show_step(3), font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", padx=16, pady=4).pack(side=tk.RIGHT)

        elif step_num == 3:
            tk.Button(btn_box, text="⬅️ Back", command=lambda: show_step(2), font=("Segoe UI", 9), padx=12, pady=4).pack(side=tk.LEFT)
            tk.Button(btn_box, text="🚀 Finish & Start", command=on_save_finish, font=("Segoe UI", 10, "bold"), bg="#16a34a", fg="white", padx=18, pady=4).pack(side=tk.RIGHT)

    show_step(1)

    root.bind("<Escape>", lambda e: on_exit())
    root.protocol("WM_DELETE_WINDOW", on_exit)

    root.mainloop()
    return result['success']


def show_api_key_dialog(parent: Optional[tk.Tk] = None) -> Optional[str]:
    """Compatibility wrapper that launches show_initial_setup_dialog"""
    try:
        from config_manager import ConfigManager
    except ImportError:
        from src.config_manager import ConfigManager
    cm = ConfigManager()
    sm = SettingsManager()
    ok = show_initial_setup_dialog(config_manager=cm, settings_manager=sm, parent=parent)
    if ok:
        return os.getenv('GEMINI_API_KEY') or os.getenv('CUSTOM_API_KEY') or 'configured'
    return None


_active_settings_dialog: Optional[tk.Tk] = None


def show_settings_dialog(
    settings_manager: SettingsManager,
    on_api_change: Optional[Callable] = None,
    on_settings_change: Optional[Callable] = None,
    on_mode_change: Optional[Callable[[str], None]] = None,
    on_hotkey_change: Optional[Callable] = None,
    on_close: Optional[Callable] = None,
    on_clear_data: Optional[Callable] = None
) -> None:
    """Modern full-featured Settings Dialog with live testing, scrollable tabs, eyedropper, and pinned footer"""
    global _active_settings_dialog
    if _active_settings_dialog is not None:
        try:
            if _active_settings_dialog.winfo_exists():
                _active_settings_dialog.lift()
                _active_settings_dialog.focus_force()
                return
        except Exception:
            _active_settings_dialog = None

    try:
        settings_manager.load_settings()
    except Exception:
        pass

    env_path = os.path.join(PROJECT_ROOT, '.env')
    try:
        from dotenv import load_dotenv
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
    except ImportError:
        pass

    if sys.platform == 'win32':
        try:
            import ctypes
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass
        except Exception:
            pass

    dialog = tk.Tk()
    _active_settings_dialog = dialog
    dialog.title("Settings - AI Quiz Assistant 2.0")

    # Set modern app window icon
    ico_path = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if not os.path.exists(ico_path):
        ico_path = os.path.join(PROJECT_ROOT, "icon.ico")
    png_path = os.path.join(PROJECT_ROOT, "assets", "icon.png")
    if os.path.exists(ico_path):
        try:
            dialog.iconbitmap(ico_path)
        except Exception:
            pass
    if os.path.exists(png_path):
        try:
            _app_icon_img = tk.PhotoImage(file=png_path)
            dialog.iconphoto(True, _app_icon_img)
            dialog._app_icon_img = _app_icon_img
        except Exception:
            pass

    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    win_w = max(660, int(settings_manager.get('settings_win_width', 720) or 720))
    win_h = max(520, int(settings_manager.get('settings_win_height', 680) or 680))
    x = max(0, (sw - win_w) // 2)
    y = max(0, (sh - win_h) // 2)
    dialog.geometry(f"{win_w}x{win_h}+{x}+{y}")
    dialog.minsize(660, 520)
    dialog.resizable(True, True)

    dialog.lift()
    dialog.attributes('-topmost', True)
    dialog.after(100, lambda: dialog.attributes('-topmost', False))
    dialog.focus_force()

    style = ttk.Style(dialog)
    try:
        style.theme_use('clam')
        style.configure("TNotebook", background="#f1f5f9")
        style.configure("TNotebook.Tab", padding=[8, 5], font=("Segoe UI", 9, "bold"))
    except Exception:
        pass

    # ========================================================
    # 1. PIN BOTTOM ACTION BAR FIRST (Guaranteed ALWAYS visible!)
    # ========================================================
    bottom_bar = tk.Frame(dialog, pady=10, padx=14, bg="#f8fafc", bd=1, relief=tk.SOLID)
    bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

    save_status_lbl = tk.Label(bottom_bar, text="", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#f8fafc")
    save_status_lbl.pack(side=tk.LEFT)

    saved_win_w = win_w
    saved_win_h = win_h

    save_win_size_btn = tk.Button(
        bottom_bar,
        text="💾 Save Window Size",
        font=("Segoe UI", 8, "bold"),
        bg="#0284c7",
        fg="white",
        padx=10,
        pady=3,
        cursor="hand2"
    )

    def on_save_win_size_clicked():
        nonlocal saved_win_w, saved_win_h
        cur_w = dialog.winfo_width()
        cur_h = dialog.winfo_height()
        saved_win_w = cur_w
        saved_win_h = cur_h
        settings_manager.settings['settings_win_width'] = cur_w
        settings_manager.settings['settings_win_height'] = cur_h
        if 'on_save_all' in globals_or_locals:
            globals_or_locals['on_save_all'](close_after=False)
        else:
            settings_manager.save_settings()
        save_win_size_btn.config(text="✓ Size & Settings Saved!", bg="#10b981")
        dialog.after(1600, lambda: save_win_size_btn.pack_forget() if save_win_size_btn.winfo_exists() and abs(dialog.winfo_width() - saved_win_w) <= 20 and abs(dialog.winfo_height() - saved_win_h) <= 20 else None)

    save_win_size_btn.config(command=on_save_win_size_clicked)

    _last_w = [win_w]
    _last_h = [win_h]

    def on_dialog_configure(event):
        if event.widget != dialog:
            return
        cur_w = dialog.winfo_width()
        cur_h = dialog.winfo_height()
        if cur_w < 200 or cur_h < 200:
            return
        if cur_w == _last_w[0] and cur_h == _last_h[0]:
            return
        _last_w[0] = cur_w
        _last_h[0] = cur_h
        diff = abs(cur_w - saved_win_w) > 20 or abs(cur_h - saved_win_h) > 20
        if diff:
            save_win_size_btn.config(text=f"💾 Save Window Size ({cur_w}x{cur_h})", bg="#0284c7")
            if not save_win_size_btn.winfo_ismapped():
                save_win_size_btn.pack(side=tk.LEFT, padx=10)
        else:
            if save_win_size_btn.winfo_ismapped() and save_win_size_btn.cget('text') != "✓ Window Size Saved!":
                save_win_size_btn.pack_forget()

    dialog.bind("<Configure>", on_dialog_configure)

    # Buttons will be linked to on_save_all
    def trigger_save_close():
        if 'on_save_all' in globals_or_locals:
            globals_or_locals['on_save_all'](close_after=True)

    def trigger_cancel_close():
        global _active_settings_dialog
        _active_settings_dialog = None
        try:
            dialog.destroy()
        finally:
            if on_close:
                try:
                    on_close()
                except Exception:
                    pass

    globals_or_locals = {}

    tk.Button(
        bottom_bar,
        text="✕ Close",
        command=trigger_cancel_close,
        font=("Segoe UI", 9),
        bg="#e2e8f0",
        fg="#1e293b",
        padx=14,
        pady=4,
        cursor="hand2"
    ).pack(side=tk.RIGHT, padx=5)

    tk.Button(
        bottom_bar,
        text="💾 Save Settings",
        command=trigger_save_close,
        font=("Segoe UI", 9, "bold"),
        bg="#0066cc",
        fg="white",
        padx=16,
        pady=4,
        cursor="hand2"
    ).pack(side=tk.RIGHT, padx=5)

    # ========================================================
    # 2. NOTEBOOK IN REMAINING SPACE
    # ========================================================
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))

    tab_canvases = {}

    # ========================================================
    # TAB 1: AI PROVIDER (Scrollable, hidden scrollbar)
    # ========================================================
    tab_provider_outer, tab_provider, canvas_provider = create_scrollable_tab(notebook, " 🤖 AI Provider ")
    tab_canvases[str(tab_provider_outer)] = canvas_provider

    tk.Label(tab_provider, text="Select AI Provider:", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(anchor=tk.W, pady=(0, 6))

    current_provider = settings_manager.get('api_provider', os.getenv('API_PROVIDER', 'gemini'))
    prov_options = [
        ("gemini", "Google Gemini AI Studio (Cloud)", "Free, ultra-fast vision analysis (~1.4s), high quality from Google."),
        ("custom", "Custom Local / Proxy (OpenAI-compatible)", "Compatible with Ollama, vLLM, LM Studio, Claude Proxy, or OpenAI API.")
    ]
    provider_var, _ = _create_card_selector(tab_provider, prov_options, current_provider)

    # Gemini Config Box
    gemini_box = ttk.LabelFrame(tab_provider, text=" Google Gemini Configuration ", padding=10)
    gemini_box.pack(fill=tk.X, pady=6)

    tk.Label(gemini_box, text="Gemini API Key:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    gem_key_frame = tk.Frame(gemini_box)
    gem_key_frame.pack(fill=tk.X, pady=(2, 6))

    def toggle_gem_show():
        if gem_key_entry.cget('show') == '*':
            gem_key_entry.config(show='')
            gem_toggle_btn.config(text="🙈 Hide")
        else:
            gem_key_entry.config(show='*')
            gem_toggle_btn.config(text="👁 Show")

    gem_toggle_btn = tk.Button(gem_key_frame, text="👁 Show", command=toggle_gem_show, font=("Segoe UI", 8), padx=10)
    gem_toggle_btn.pack(side=tk.RIGHT, padx=(6, 0))

    cur_gem_key = os.getenv('GEMINI_API_KEY', '')
    gem_key_entry = tk.Entry(gem_key_frame, font=("Segoe UI", 9), show="*")
    gem_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    gem_key_entry.insert(0, cur_gem_key)

    tk.Label(gemini_box, text="Gemini Model:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    g_model_row = tk.Frame(gemini_box)
    g_model_row.pack(fill=tk.X, pady=(2, 8))

    cur_gem_model = settings_manager.get('gemini_model', os.getenv('GEMINI_MODEL', ''))
    gem_model_cb = ttk.Combobox(
        g_model_row,
        values=[cur_gem_model] if cur_gem_model else [],
        font=("Segoe UI", 9),
        state="normal"
    )
    gem_model_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_gem_model:
        gem_model_cb.set(cur_gem_model)

    def do_fetch_gemini_models():
        k = gem_key_entry.get().strip()
        if not k:
            gem_status_lbl.config(text="❌ Please enter Gemini API Key first", fg="red")
            return
        gem_status_lbl.config(text="⏳ Fetching models...", fg="#0066cc")

        def _w():
            try:
                try:
                    from gemini_client import GeminiAPIClient
                except ImportError:
                    from src.gemini_client import GeminiAPIClient
                ok, models, msg = GeminiAPIClient.list_models(k)
                if ok and models:
                    def _apply():
                        gem_model_cb['values'] = models
                        if not gem_model_cb.get() or gem_model_cb.get() not in models:
                            gem_model_cb.set(models[0])
                        gem_status_lbl.config(text=f"✅ Loaded {len(models)} models", fg="green")
                    dialog.after(0, _apply)
                else:
                    gem_status_lbl.config(text=f"❌ {msg[:45]}", fg="red")
            except Exception as e:
                gem_status_lbl.config(text=f"❌ {str(e)[:45]}", fg="red")

        threading.Thread(target=_w, daemon=True).start()

    tk.Button(g_model_row, text="🔄 Fetch Models", command=do_fetch_gemini_models, font=("Segoe UI", 8), padx=6).pack(side=tk.LEFT, padx=(6, 0))

    gem_test_row = tk.Frame(gemini_box)
    gem_test_row.pack(fill=tk.X)
    gem_status_lbl = tk.Label(gem_test_row, text="", font=("Segoe UI", 9))

    def do_test_gemini():
        key = gem_key_entry.get().strip()
        model = gem_model_cb.get().strip()
        if not key:
            gem_status_lbl.config(text="❌ Please enter Gemini API Key", fg="red")
            return
        gem_status_lbl.config(text="⏳ Testing Gemini connection...", fg="#0066cc")

        def _w():
            try:
                try:
                    from gemini_client import GeminiAPIClient
                except ImportError:
                    from src.gemini_client import GeminiAPIClient

                # Auto-fetch if model list is currently empty
                m = model
                ok_list, models, _ = GeminiAPIClient.list_models(key)
                if ok_list and models:
                    def _up():
                        gem_model_cb['values'] = models
                        if not gem_model_cb.get() or gem_model_cb.get() not in models:
                            gem_model_cb.set(models[0])
                    dialog.after(0, _up)
                    if not m:
                        m = models[0]

                if not m:
                    m = "gemini-2.5-flash"

                client = GeminiAPIClient(api_key=key, model_name=m)
                ok, msg, lat = client.test_connection()
                if ok:
                    gem_status_lbl.config(text=f"✅ {msg} ({lat:.2f}s)", fg="green")
                else:
                    gem_status_lbl.config(text=f"❌ {msg}", fg="red")
            except Exception as e:
                gem_status_lbl.config(text=f"❌ Error: {e}", fg="red")

        threading.Thread(target=_w, daemon=True).start()

    tk.Button(gem_test_row, text="⚡ Test Gemini Connection", command=do_test_gemini, font=("Segoe UI", 8), bg="#27ae60", fg="white", padx=8).pack(side=tk.LEFT)
    gem_status_lbl.pack(side=tk.LEFT, padx=10)

    # Custom Config Box
    custom_box = ttk.LabelFrame(tab_provider, text=" Custom Local / Proxy Configuration ", padding=10)
    custom_box.pack(fill=tk.X, pady=6)

    tk.Label(custom_box, text="Endpoint URL (OpenAI-compatible):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    custom_url_entry = tk.Entry(custom_box, font=("Segoe UI", 9))
    custom_url_entry.pack(fill=tk.X, pady=(2, 6))
    cur_settings_custom_url = (os.getenv('CUSTOM_API_URL') or '').strip()
    if not cur_settings_custom_url:
        cur_settings_custom_url = 'http://localhost:11434/v1'
    custom_url_entry.insert(0, cur_settings_custom_url)

    tk.Label(custom_box, text="API Key (Optional for local / Bearer key for proxy):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    custom_key_frame = tk.Frame(custom_box)
    custom_key_frame.pack(fill=tk.X, pady=(2, 6))

    def toggle_cust_show():
        if custom_key_entry.cget('show') == '*':
            custom_key_entry.config(show='')
            cust_toggle_btn.config(text="🙈 Hide")
        else:
            custom_key_entry.config(show='*')
            cust_toggle_btn.config(text="👁 Show")

    cust_toggle_btn = tk.Button(custom_key_frame, text="👁 Show", command=toggle_cust_show, font=("Segoe UI", 8), padx=10)
    cust_toggle_btn.pack(side=tk.RIGHT, padx=(6, 0))

    custom_key_entry = tk.Entry(custom_key_frame, font=("Segoe UI", 9), show="*")
    custom_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    custom_key_entry.insert(0, os.getenv('CUSTOM_API_KEY', ''))

    tk.Label(custom_box, text="Model Name:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
    c_model_row = tk.Frame(custom_box)
    c_model_row.pack(fill=tk.X, pady=(2, 8))

    cur_cust_model = os.getenv('CUSTOM_MODEL', '')
    custom_model_cb = ttk.Combobox(
        c_model_row,
        values=[cur_cust_model] if cur_cust_model else [],
        font=("Segoe UI", 9),
        state="normal"
    )
    custom_model_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if cur_cust_model:
        custom_model_cb.set(cur_cust_model)

    def do_fetch_custom_models():
        url = custom_url_entry.get().strip()
        key = custom_key_entry.get().strip()
        if not url:
            cust_status_lbl.config(text="❌ Please enter URL first", fg="red")
            return
        cust_status_lbl.config(text="⏳ Fetching models...", fg="#0066cc")

        def _w():
            try:
                try:
                    from custom_client import CustomAPIClient
                except ImportError:
                    from src.custom_client import CustomAPIClient
                ok, models, msg = CustomAPIClient.list_models(url, key)
                if ok and models:
                    def _apply():
                        custom_model_cb['values'] = models
                        if not custom_model_cb.get() or custom_model_cb.get() not in models:
                            custom_model_cb.set(models[0])
                        cust_status_lbl.config(text=f"✅ Loaded {len(models)} models", fg="green")
                    dialog.after(0, _apply)
                else:
                    cust_status_lbl.config(text=f"❌ {msg[:45]}", fg="red")
            except Exception as e:
                cust_status_lbl.config(text=f"❌ {str(e)[:45]}", fg="red")

        threading.Thread(target=_w, daemon=True).start()

    tk.Button(c_model_row, text="🔄 Fetch Models", command=do_fetch_custom_models, font=("Segoe UI", 8), padx=6).pack(side=tk.LEFT, padx=(6, 0))

    cust_test_row = tk.Frame(custom_box)
    cust_test_row.pack(fill=tk.X)
    cust_status_lbl = tk.Label(cust_test_row, text="", font=("Segoe UI", 9))

    def do_test_custom():
        url = custom_url_entry.get().strip()
        key = custom_key_entry.get().strip()
        model = custom_model_cb.get().strip()
        if not url:
            cust_status_lbl.config(text="❌ Please enter URL", fg="red")
            return
        cust_status_lbl.config(text="⏳ Testing Custom API connection...", fg="#0066cc")

        def _w():
            try:
                try:
                    from custom_client import CustomAPIClient
                except ImportError:
                    from src.custom_client import CustomAPIClient

                # Auto-fetch if model combobox is empty
                m = model
                ok_list, models, _ = CustomAPIClient.list_models(url, key)
                if ok_list and models:
                    def _up():
                        custom_model_cb['values'] = models
                        if not custom_model_cb.get() or custom_model_cb.get() not in models:
                            custom_model_cb.set(models[0])
                    dialog.after(0, _up)
                    if not m:
                        m = models[0]

                if not m:
                    cust_status_lbl.config(text="❌ Please enter or select a model name", fg="red")
                    return

                cclient = CustomAPIClient(api_url=url, api_key=key, model=m)
                ok, msg, lat = cclient.test_connection()
                if ok:
                    cust_status_lbl.config(text=f"✅ {msg} ({lat:.2f}s)", fg="green")
                else:
                    cust_status_lbl.config(text=f"❌ {msg}", fg="red")
            except Exception as e:
                cust_status_lbl.config(text=f"❌ Error: {e}", fg="red")

        threading.Thread(target=_w, daemon=True).start()

    tk.Button(cust_test_row, text="⚡ Test Custom Connection", command=do_test_custom, font=("Segoe UI", 8), bg="#8e44ad", fg="white", padx=8).pack(side=tk.LEFT)
    cust_status_lbl.pack(side=tk.LEFT, padx=10)

    # Failover / Auto-rotation Frame
    failover_box = ttk.LabelFrame(tab_provider, text=" 🔄 Automatic Provider Failover & Rotation ", padding=10)
    failover_box.pack(fill=tk.X, pady=(10, 6))

    failover_var = tk.BooleanVar(value=settings_manager.get('enable_provider_failover', True))
    failover_chk = ttk.Checkbutton(
        failover_box,
        text="Enable Automatic Provider Failover (Auto-rotate to backup provider on error / rate limit)",
        variable=failover_var
    )
    failover_chk.pack(anchor=tk.W)

    failover_desc = tk.Label(
        failover_box,
        text="When enabled, if the primary AI provider encounters an error, rate limit (HTTP 429), or timeout,\n"
             "requests will automatically rotate to your configured alternate provider seamlessly.",
        font=("Segoe UI", 8),
        fg="#64748b",
        justify=tk.LEFT
    )
    failover_desc.pack(anchor=tk.W, pady=(2, 6))

    failover_status_lbl = tk.Label(
        failover_box,
        text="",
        font=("Segoe UI", 8, "italic")
    )
    failover_status_lbl.pack(anchor=tk.W)

    def update_failover_status(*_):
        p = provider_var.get()
        alt = 'custom' if p == 'gemini' else 'gemini'
        if alt == 'gemini':
            alt_ready = bool(gem_key_entry.get().strip() or os.getenv('GEMINI_API_KEY'))
            alt_name = "Google Gemini"
        else:
            alt_ready = bool(
                (custom_url_entry.get().strip() or os.getenv('CUSTOM_API_URL')) and
                (custom_model_cb.get().strip() or os.getenv('CUSTOM_MODEL'))
            )
            alt_name = "Custom Local / Proxy"

        if alt_ready:
            failover_status_lbl.config(
                text=f"✅ Backup provider ready: {alt_name}",
                fg="#16a34a"
            )
        else:
            failover_status_lbl.config(
                text=f"⚠️ Backup provider ({alt_name}) not fully configured yet. Configure credentials above for automatic failover.",
                fg="#d97706"
            )

    provider_var.trace_add("write", update_failover_status)
    gem_key_entry.bind("<KeyRelease>", update_failover_status)
    custom_url_entry.bind("<KeyRelease>", update_failover_status)
    custom_model_cb.bind("<<ComboboxSelected>>", update_failover_status)
    custom_model_cb.bind("<KeyRelease>", update_failover_status)
    update_failover_status()

    # ========================================================
    # TAB 2: MODE & PROMPT (Scrollable, hidden scrollbar)
    # ========================================================
    tab_mode_outer, tab_mode, canvas_mode = create_scrollable_tab(notebook, " 🎯 Quiz Modes ")
    tab_canvases[str(tab_mode_outer)] = canvas_mode

    tk.Label(tab_mode, text="1. Quiz Question Type & Processing:", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(anchor=tk.W, pady=(0, 4))

    mode_options = [
        (
            "multiple_choice",
            "Quick Multiple Choice (Answers Only)",
            "Extracts all multiple-choice questions, showing questions and chosen answers without explanations."
        ),
        (
            "multiple_choice_explanation",
            "Multiple Choice + Detailed Explanations",
            "Extracts questions, answers, and detailed explanations (collapsible on demand with one-click copy)."
        ),
        (
            "essay",
            "Essay / Detailed Solutions",
            "Extracts open-ended and essay questions with step-by-step detailed solutions."
        )
    ]
    cur_mode = settings_manager.get('question_mode', 'multiple_choice')
    mode_var, _ = _create_card_selector(tab_mode, mode_options, cur_mode)

    tk.Label(tab_mode, text="2. Answer Display Format:", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(anchor=tk.W, pady=(12, 4))

    ans_options = [
        (
            "letter_and_text",
            "Letter + Full Answer Text",
            "e.g.: B. Paris  or  B. 42  (Recommended for easy verification)."
        ),
        (
            "letter_only",
            "Option Letter Only",
            "e.g.: B  or  A  (Ultra-compact for rapid multiple-choice exams)."
        )
    ]
    cur_ans_disp = settings_manager.get('answer_display_mode', 'letter_and_text')
    ans_disp_var, _ = _create_card_selector(tab_mode, ans_options, cur_ans_disp)

    # ========================================================
    # TAB 3: UI & POPUP (With Eyedropper, Palette & Live Card Preview)
    # ========================================================
    tab_ui_outer, tab_ui, canvas_ui = create_scrollable_tab(notebook, " 🎨 HUD Appearance ")
    tab_canvases[str(tab_ui_outer)] = canvas_ui

    tk.Label(tab_ui, text="Customize HUD Popup & Theme Colors:", font=("Segoe UI", 10, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor=tk.W, pady=(0, 6))

    # Color Picker LabelFrame
    color_box = ttk.LabelFrame(tab_ui, text=" 🎨 Card Background Color (Default: White) ", padding=12)
    color_box.pack(fill=tk.X, pady=(0, 10))

    cur_bg_color = settings_manager.get('popup_bg_color', '#ffffff')
    is_initial_stealth = str(cur_bg_color).strip().lower().startswith(('stealth', '#stealth', 'ghost', '#ghost'))
    initial_stealth_hex = '#ffffff'
    if is_initial_stealth and ':' in str(cur_bg_color):
        p = str(cur_bg_color).split(':', 1)[1].strip()
        if p.startswith('#') and len(p) in (4, 7):
            initial_stealth_hex = p
        elif not p.startswith('#') and len(p) in (3, 6):
            initial_stealth_hex = f"#{p}"

    bg_color_var = tk.StringVar(master=dialog, value=cur_bg_color)

    tk.Label(
        color_box,
        text="Default background is White (#FFFFFF). You can sample colors from your screen using the eyedropper, or pick from the palette. Foreground text and border colors automatically adjust for optimal contrast.",
        font=("Segoe UI", 8),
        fg="#64748b",
        wraplength=580,
        justify=tk.LEFT
    ).pack(anchor=tk.W, pady=(0, 8))

    ctrl_row = tk.Frame(color_box, bg="#ffffff", bd=1, relief=tk.SOLID, padx=8, pady=8)
    ctrl_row.pack(fill=tk.X, pady=(0, 8))

    initial_chip_bg = initial_stealth_hex if is_initial_stealth else '#ffffff'
    if not is_initial_stealth and str(cur_bg_color).startswith('#') and len(str(cur_bg_color)) in (4, 7):
        initial_chip_bg = cur_bg_color

    color_chip = tk.Frame(ctrl_row, width=32, height=32, bg=initial_chip_bg, bd=1, relief=tk.SOLID, cursor="hand2")
    color_chip.pack(side=tk.LEFT, padx=(0, 8))
    color_chip.pack_propagate(False)

    chip_icon = tk.Label(color_chip, text="🎯", font=("Segoe UI", 11), bg=initial_chip_bg, fg="#0284c7", cursor="hand2")
    if is_initial_stealth:
        chip_icon.pack(expand=True)

    code_box = tk.Frame(ctrl_row, bg="#ffffff")
    code_box.pack(side=tk.LEFT, padx=(0, 12))

    init_code_text = f"Color Code: 👻 STEALTH ({initial_stealth_hex.upper()})" if is_initial_stealth else f"Color Code: {str(cur_bg_color).upper()}"
    color_val_lbl = tk.Label(code_box, text=init_code_text, font=("Consolas", 10, "bold"), bg="#ffffff", fg="#0f172a")
    color_val_lbl.pack(anchor=tk.W)

    status_badge = tk.Label(code_box, text="", font=("Segoe UI", 8, "bold"), padx=6, pady=1)
    status_badge.pack(anchor=tk.W, pady=(2, 0))

    def update_color_ui(new_color: str):
        new_color = (new_color or "#ffffff").strip()
        is_stealth = new_color.lower().startswith(('stealth', '#stealth', 'ghost', '#ghost'))
        stealth_hex = '#ffffff'
        if is_stealth:
            if ':' in new_color:
                part = new_color.split(':', 1)[1].strip()
                if part.startswith('#') and len(part) in (4, 7):
                    stealth_hex = part
                elif not part.startswith('#') and len(part) in (3, 6):
                    stealth_hex = f"#{part}"
            bg_color_var.set(f"stealth:{stealth_hex}")
        else:
            if not new_color.startswith('#'):
                new_color = f"#{new_color}"
            bg_color_var.set(new_color)

        try:
            try:
                from popup_manager import get_popup_theme
            except ImportError:
                from src.popup_manager import get_popup_theme
            theme = get_popup_theme(bg_color_var.get())
        except Exception:
            theme = {'is_light': True, 'text': '#0f172a', 'bg': stealth_hex if is_stealth else new_color, 'header_bg': stealth_hex if is_stealth else '#f1f5f9', 'border': stealth_hex if is_stealth else '#cbd5e1', 'question': '#71717a' if is_stealth else '#0369a1', 'answer': '#52525b' if is_stealth else '#15803d', 'badge_bg': '#e2e8f0', 'badge_fg': '#334155', 'close_fg': '#a1a1aa' if is_stealth else '#dc2626', 'copy_fg': '#a1a1aa' if is_stealth else '#1e293b', 'is_stealth': is_stealth}

        if is_stealth:
            color_chip.config(bg=stealth_hex, cursor="hand2")
            chip_icon.config(text="🎯", bg=stealth_hex, fg="#0284c7")
            chip_icon.pack(expand=True)
            color_val_lbl.config(text=f"Color Code: 👻 STEALTH ({stealth_hex.upper()})")
            status_badge.config(
                text=f"👻 Stealth Active: Borderless, Muted Non-bold Text ({stealth_hex.upper()})",
                bg="#f4f4f5",
                fg="#52525b"
            )
            try:
                # Auto-adjust font size to 8 for stealth
                font_sb.delete(0, tk.END)
                font_sb.insert(0, "8")
                font_var.set(8)
            except Exception:
                pass
        else:
            chip_icon.pack_forget()
            safe_chip_bg = new_color if (new_color.startswith('#') and len(new_color) in (4, 7)) else '#ffffff'
            try:
                color_chip.config(bg=safe_chip_bg, cursor="")
            except Exception:
                color_chip.config(bg='#ffffff', cursor="")
            color_val_lbl.config(text=f"Color Code: {new_color.upper()}")
            if theme.get('is_light', True):
                status_badge.config(text="⚪ Light Theme (Dark Text)", bg="#dbeafe", fg="#1e40af")
            else:
                status_badge.config(text="🌑 Dark Theme (Light Text)", bg="#334155", fg="#f8fafc")

        # Update Live Mini Preview Card
        is_st = theme.get('is_stealth', False)
        card_preview_outer.config(
            bg=theme.get('border', '#cbd5e1'),
            bd=0 if is_st else 1,
            relief=tk.FLAT if is_st else tk.SOLID
        )
        card_preview_header.config(bg=theme.get('header_bg', '#f1f5f9'))
        card_preview_title.config(
            bg=theme.get('header_bg', '#f1f5f9'),
            fg=theme.get('accent', '#0284c7'),
            font=("Segoe UI", 8, "normal" if is_st else "bold")
        )
        card_preview_badge1.config(
            bg=theme.get('badge_bg', '#e2e8f0'),
            fg=theme.get('badge_fg', '#334155'),
            bd=0 if is_st else 1,
            relief=tk.FLAT if is_st else tk.SOLID
        )
        card_preview_badge2.config(
            bg=theme.get('badge_bg', '#e2e8f0'),
            fg=theme.get('badge_fg', '#334155'),
            bd=0 if is_st else 1,
            relief=tk.FLAT if is_st else tk.SOLID
        )
        card_preview_copy.config(
            bg=theme.get('badge_bg', '#e2e8f0'),
            fg=theme.get('copy_fg', '#1e293b'),
            bd=0 if is_st else 1,
            relief=tk.FLAT if is_st else tk.SOLID,
            font=("Segoe UI", 7, "normal" if is_st else "bold")
        )
        card_preview_close.config(
            bg=theme.get('header_bg', '#f1f5f9'),
            fg=theme.get('close_fg', '#dc2626'),
            font=("Segoe UI", 8 if is_st else 9, "normal" if is_st else "bold")
        )

        card_preview_body.config(bg=theme.get('bg', '#ffffff'))
        card_preview_q.config(
            bg=theme.get('bg', '#ffffff'),
            fg=theme.get('question', '#0369a1'),
            font=("Segoe UI", 8, "normal" if is_st else "bold")
        )
        card_preview_a.config(
            bg=theme.get('bg', '#ffffff'),
            fg=theme.get('answer', '#15803d'),
            font=("Segoe UI", 8, "normal" if is_st else "bold")
        )
        card_preview_exp_btn.config(
            bg=theme.get('exp_btn_bg', '#e2e8f0'),
            fg=theme.get('exp_btn_fg', '#0284c7'),
            bd=0 if is_st else 1,
            relief=tk.FLAT if is_st else tk.SOLID,
            font=("Segoe UI", 7, "normal" if is_st else "bold")
        )

    def do_eyedropper():
        def on_color_picked(c_hex):
            cur = bg_color_var.get().strip().lower()
            if cur.startswith(('stealth', '#stealth', 'ghost', '#ghost')):
                update_color_ui(f"stealth:{c_hex}")
            else:
                update_color_ui(c_hex)
        pick_color_at_cursor(dialog, on_color_picked)

    def do_palette():
        cur = bg_color_var.get().strip().lower()
        is_cur_st = cur.startswith(('stealth', '#stealth', 'ghost', '#ghost'))
        init_c = "#ffffff"
        if ':' in cur:
            part = cur.split(':', 1)[1].strip()
            if part.startswith('#') and len(part) in (4, 7):
                init_c = part
        elif not is_cur_st and cur.startswith('#') and len(cur) in (4, 7):
            init_c = cur

        chosen = colorchooser.askcolor(color=init_c, parent=dialog, title="Select HUD Background Color")[1]
        if chosen:
            if is_cur_st:
                update_color_ui(f"stealth:{chosen}")
            else:
                update_color_ui(chosen)

    color_chip.bind("<Button-1>", lambda e: do_eyedropper())
    chip_icon.bind("<Button-1>", lambda e: do_eyedropper())

    tk.Button(
        ctrl_row,
        text="🎯 Pick Color at Cursor",
        command=do_eyedropper,
        font=("Segoe UI", 9, "bold"),
        bg="#0284c7",
        fg="white",
        padx=10,
        pady=3,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=4)

    tk.Button(
        ctrl_row,
        text="🎨 Choose from Palette",
        command=do_palette,
        font=("Segoe UI", 9),
        bg="#f1f5f9",
        fg="#1e293b",
        padx=10,
        pady=3,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=4)

    # Preset quick chips
    preset_row = tk.Frame(color_box, bg="#ffffff")
    preset_row.pack(fill=tk.X, pady=(0, 8))

    tk.Label(preset_row, text="Quick Presets:", font=("Segoe UI", 8, "bold"), fg="#475569", bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

    presets = [
        ("⚪ White", "#ffffff"),
        ("👻 Stealth", "stealth"),
        ("🌫️ Gray", "#f8fafc"),
        ("📜 Cream", "#fef9c3"),
        ("🌊 Blue", "#e0f2fe"),
        ("🌑 Dark", "#1e1e2e")
    ]

    def apply_preset(p_hex):
        if p_hex == 'stealth':
            cur = bg_color_var.get().strip().lower()
            if ':' in cur:
                part = cur.split(':', 1)[1].strip()
                update_color_ui(f"stealth:{part}")
            elif cur.startswith('#') and len(cur) in (4, 7) and cur != '#ffffff':
                update_color_ui(f"stealth:{cur}")
            else:
                update_color_ui("stealth:#ffffff")
        else:
            update_color_ui(p_hex)

    for p_name, p_hex in presets:
        tk.Button(
            preset_row,
            text=p_name,
            command=lambda h=p_hex: apply_preset(h),
            font=("Segoe UI", 8),
            bg="#f8fafc",
            fg="#1e293b",
            padx=6,
            pady=2,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=3)

    # Live Mini Preview Card Container
    tk.Label(color_box, text="Live HUD Card Preview:", font=("Segoe UI", 8, "bold"), fg="#475569", bg="#ffffff").pack(anchor=tk.W, pady=(4, 2))

    card_preview_outer = tk.Frame(color_box, bd=1, relief=tk.SOLID, padx=1, pady=1)
    card_preview_outer.pack(fill=tk.X, pady=(0, 4))

    card_preview_header = tk.Frame(card_preview_outer, padx=6, pady=3)
    card_preview_header.pack(fill=tk.X)

    card_preview_title = tk.Label(card_preview_header, text="🎯 Latest Question (1 question)", font=("Segoe UI", 8, "bold"))
    card_preview_title.pack(side=tk.LEFT, padx=(0, 4))

    card_preview_badge1 = tk.Label(card_preview_header, text=" Gemini ", font=("Segoe UI", 7), bd=1, relief=tk.SOLID)
    card_preview_badge1.pack(side=tk.LEFT, padx=2)

    card_preview_badge2 = tk.Label(card_preview_header, text=" Multiple Choice ", font=("Segoe UI", 7), bd=1, relief=tk.SOLID)
    card_preview_badge2.pack(side=tk.LEFT, padx=2)

    card_preview_close = tk.Label(card_preview_header, text=" ✕ ", font=("Segoe UI", 9, "bold"))
    card_preview_close.pack(side=tk.RIGHT)

    card_preview_copy = tk.Label(card_preview_header, text="📋 Copy", font=("Segoe UI", 7, "bold"), bd=1, relief=tk.SOLID, padx=4)
    card_preview_copy.pack(side=tk.RIGHT, padx=4)

    card_preview_body = tk.Frame(card_preview_outer, padx=8, pady=6)
    card_preview_body.pack(fill=tk.X)

    card_preview_q = tk.Label(card_preview_body, text="Question 1: What country do Hoang Sa and Truong Sa belong to?", font=("Segoe UI", 8, "bold"), anchor="w")
    card_preview_q.pack(fill=tk.X)

    card_preview_a = tk.Label(card_preview_body, text="→ Answer: A. Vietnam", font=("Segoe UI", 8, "bold"), anchor="w")
    card_preview_a.pack(fill=tk.X, pady=(2, 4))

    card_preview_exp_btn = tk.Label(card_preview_body, text=" 💡 View Explanation ", font=("Segoe UI", 7, "bold"), bd=1, relief=tk.SOLID, padx=4, pady=1)
    card_preview_exp_btn.pack(anchor=tk.W)

    update_color_ui(cur_bg_color)

    # General HUD Settings
    hud_box = ttk.LabelFrame(tab_ui, text=" HUD Dimensions & Transparency ", padding=10)
    hud_box.pack(fill=tk.X, pady=(0, 8))

    grid = tk.Frame(hud_box)
    grid.pack(fill=tk.X, pady=5)

    tk.Label(grid, text="HUD Font Size:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky=tk.W, pady=6)
    cur_font_val = settings_manager.get('font_size', 10)
    font_var = tk.IntVar(master=dialog, value=cur_font_val)
    font_sb = tk.Spinbox(
        grid,
        from_=8,
        to=22,
        textvariable=font_var,
        width=10,
        font=("Segoe UI", 9, "bold"),
        justify=tk.CENTER,
        bg="#ffffff",
        fg="#1e293b",
        bd=1,
        relief=tk.SOLID
    )
    font_sb.delete(0, tk.END)
    font_sb.insert(0, str(cur_font_val))
    font_sb.grid(row=0, column=1, sticky=tk.W, padx=10)

    tk.Label(grid, text="HUD Card Width (px):", font=("Segoe UI", 9)).grid(row=1, column=0, sticky=tk.W, pady=6)
    cur_width_val = settings_manager.get('popup_width', 500)
    width_var = tk.IntVar(master=dialog, value=cur_width_val)
    width_sb = tk.Spinbox(
        grid,
        from_=320,
        to=1000,
        increment=20,
        textvariable=width_var,
        width=10,
        font=("Segoe UI", 9, "bold"),
        justify=tk.CENTER,
        bg="#ffffff",
        fg="#1e293b",
        bd=1,
        relief=tk.SOLID
    )
    width_sb.delete(0, tk.END)
    width_sb.insert(0, str(cur_width_val))
    width_sb.grid(row=1, column=1, sticky=tk.W, padx=10)

    tk.Label(grid, text="HUD Card Opacity (%):", font=("Segoe UI", 9)).grid(row=2, column=0, sticky=tk.W, pady=6)
    cur_op = int(settings_manager.get('popup_opacity', 0.96) * 100)
    cur_op = max(50, min(100, cur_op))
    opacity_var = tk.IntVar(master=dialog, value=cur_op)
    op_scale = ttk.Scale(grid, from_=50, to=100, variable=opacity_var, orient=tk.HORIZONTAL, length=150)
    op_scale.set(cur_op)
    op_scale.grid(row=2, column=1, sticky=tk.W, padx=10)
    op_lbl = tk.Label(grid, text=f"{cur_op}%", font=("Segoe UI", 9))
    op_lbl.grid(row=2, column=2, sticky=tk.W)

    def on_opacity_change(v):
        try:
            val = int(float(v))
            op_lbl.config(text=f"{val}%")
            opacity_var.set(val)
        except Exception:
            pass

    op_scale.configure(command=on_opacity_change)

    tk.Label(grid, text="Save Screenshots to Disk:", font=("Segoe UI", 9)).grid(row=3, column=0, sticky=tk.W, pady=6)
    save_ss_var = tk.BooleanVar(master=dialog, value=settings_manager.get('save_screenshots', True))
    ttk.Checkbutton(grid, text="Enabled (logs/screenshots/)", variable=save_ss_var).grid(row=3, column=1, sticky=tk.W, padx=10)

    # ========================================================
    # TAB 4: HOTKEYS (Scrollable, with clean 2-column Grid)
    # ========================================================
    tab_hotkeys_outer, tab_hotkeys, canvas_hotkeys = create_scrollable_tab(notebook, " ⌨️ Hotkeys ")
    tab_canvases[str(tab_hotkeys_outer)] = canvas_hotkeys

    tk.Label(tab_hotkeys, text="Customize Global Keyboard Shortcuts (Alt + Key):", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(anchor=tk.W, pady=(0, 10))

    hk_grid = tk.Frame(tab_hotkeys, bg="#f8fafc")
    hk_grid.pack(fill=tk.X, pady=5)

    hotkey_entries = {}
    hotkey_defs = [
        ('hotkey_capture',  'Capture & Analyze Screen:', 'z'),
        ('hotkey_autofill', 'Auto-Fill & Click Answer Choices:', 'x'),
        ('hotkey_answers',  'Show Latest Question Result:', 'c'),
        ('hotkey_history',  'View Question History (1..x):', 'h'),
        ('hotkey_reset',    'Reset Quiz Session History:', 'r'),
        ('hotkey_settings', 'Open Settings Dialog:', 's'),
        ('hotkey_exit',     'Exit Application:', 'q'),
    ]

    def make_hotkey_formatter(ent):
        def on_key_typed(event):
            val = ent.get().strip()
            if not val:
                return
            char = val[-1].lower()
            if char.isalnum():
                ent.delete(0, tk.END)
                ent.insert(0, char.upper())
        return on_key_typed

    for idx, (hk_key, label_text, default_val) in enumerate(hotkey_defs):
        tk.Label(hk_grid, text=label_text, font=("Segoe UI", 9), bg="#f8fafc").grid(row=idx, column=0, sticky=tk.W, pady=4)
        tk.Label(hk_grid, text="Alt + ", font=("Consolas", 10, "bold"), bg="#f8fafc").grid(row=idx, column=1, sticky=tk.E, padx=(10, 0))
        entry = tk.Entry(hk_grid, width=4, font=("Consolas", 10, "bold"), justify=tk.CENTER)
        curr_val = settings_manager.get(hk_key, default_val)
        entry.insert(0, str(curr_val).upper())
        entry.grid(row=idx, column=2, sticky=tk.W, padx=(2, 0))
        entry.bind("<KeyRelease>", make_hotkey_formatter(entry))
        hotkey_entries[hk_key] = entry

    # Auto-Fill Configuration Box
    autofill_box = ttk.LabelFrame(tab_hotkeys, text=" ⚡ Automated Answer Click & Fill (Alt + X) ", padding=10)
    autofill_box.pack(fill=tk.X, pady=(12, 6))

    enable_autofill_var = tk.BooleanVar(master=dialog, value=settings_manager.get('enable_autofill', True))
    ttk.Checkbutton(
        autofill_box,
        text="Enable Automated Answer Clicking (Captures screen, solves quiz, and clicks choices)",
        variable=enable_autofill_var
    ).pack(anchor=tk.W, pady=(2, 6))

    af_opts_row = tk.Frame(autofill_box, bg="#f8fafc")
    af_opts_row.pack(fill=tk.X, pady=(4, 2))

    tk.Label(af_opts_row, text="Click Delay (ms):", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 4))
    cur_af_delay = settings_manager.get('autofill_click_delay_ms', 200)
    af_delay_sb = tk.Spinbox(af_opts_row, from_=50, to=1500, increment=50, width=5, font=("Segoe UI", 9))
    af_delay_sb.delete(0, tk.END)
    af_delay_sb.insert(0, str(cur_af_delay))
    af_delay_sb.pack(side=tk.LEFT, padx=(0, 16))

    restore_cursor_var = tk.BooleanVar(master=dialog, value=settings_manager.get('autofill_restore_cursor', True))
    ttk.Checkbutton(
        af_opts_row,
        text="Restore cursor position after clicking",
        variable=restore_cursor_var
    ).pack(side=tk.LEFT, padx=(0, 12))

    smooth_move_var = tk.BooleanVar(master=dialog, value=settings_manager.get('autofill_smooth_movement', True))
    ttk.Checkbutton(
        af_opts_row,
        text="Smooth natural mouse movement",
        variable=smooth_move_var
    ).pack(side=tk.LEFT)

    mouse_box = ttk.LabelFrame(tab_hotkeys, text=" Additional Navigation & Gestures ", padding=10)
    mouse_box.pack(fill=tk.X, pady=(8, 16))

    enable_mouse_var = tk.BooleanVar(master=dialog, value=settings_manager.get('enable_mouse_gestures', True))
    ttk.Checkbutton(
        mouse_box,
        text="Enable Middle Mouse Wheel Shortcuts (Scroll Up: Capture, Scroll Down: Latest Result)",
        variable=enable_mouse_var
    ).pack(anchor=tk.W, pady=(2, 6))

    help_hints = [
        ("Popup Navigation:", "Esc to close, Ctrl+C to copy, Up/Down arrow keys to switch questions"),
        ("History Mode:", "Up/Down arrow keys or PageUp/PageDown to scroll through question log"),
        ("Configurable Hotkeys:", "All shortcuts use Alt + [Key] (configurable in table above)")
    ]
    for h_title, h_desc in help_hints:
        hint_row = tk.Frame(mouse_box, bg="#f8fafc")
        hint_row.pack(fill=tk.X, pady=2)
        tk.Label(hint_row, text=h_title, font=("Segoe UI", 9, "bold"), fg="#1e293b", width=18, anchor="w").pack(side=tk.LEFT)
        tk.Label(hint_row, text=h_desc, font=("Segoe UI", 9), fg="#475569", anchor="w").pack(side=tk.LEFT)

    # ========================================================
    # TAB 5: DATA & LOGS (Scrollable, hidden scrollbar)
    # ========================================================
    tab_data_outer, tab_data, canvas_data = create_scrollable_tab(notebook, " 📁 Data & Logs ")
    tab_canvases[str(tab_data_outer)] = canvas_data

    tk.Label(tab_data, text="File Management & Session Storage:", font=("Segoe UI", 10, "bold"), bg="#f8fafc").pack(anchor=tk.W, pady=(0, 10))

    def open_folder(path):
        try:
            try:
                from system_tray import launch_file_explorer
            except ImportError:
                from src.system_tray import launch_file_explorer
            launch_file_explorer(path)
        except Exception:
            if not os.path.isabs(path):
                target_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
            else:
                target_path = os.path.normpath(path)
            os.makedirs(target_path, exist_ok=True)
            subprocess.Popen(['explorer.exe', target_path])

    btn_row1 = tk.Frame(tab_data, bg="#f8fafc")
    btn_row1.pack(fill=tk.X, pady=6)
    tk.Button(btn_row1, text="📁 Open Logs Folder", command=lambda: open_folder("logs"), width=22, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
    tk.Button(btn_row1, text="📸 Open Screenshots Folder", command=lambda: open_folder("logs/screenshots"), width=24, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

    # Clean data section
    clean_box = ttk.LabelFrame(tab_data, text=" Data & Memory Cleanup ", padding=10)
    clean_box.pack(fill=tk.X, pady=(16, 8))

    tk.Label(
        clean_box,
        text="Clear all log files, question history, and screenshot captures:",
        font=("Segoe UI", 9),
        fg="#475569"
    ).pack(anchor=tk.W, pady=(0, 8))

    clean_status_lbl = tk.Label(clean_box, text="", font=("Segoe UI", 9, "bold"), fg="#10b981")
    clean_status_lbl.pack(anchor=tk.W, pady=(4, 0))

    def do_clear_all_logs_and_screenshots():
        if not messagebox.askyesno(
            "Confirm Data Wipe",
            "Are you sure you want to permanently clear all logs, answers, and screenshots?\n\nThis will clear current session memory and delete all saved files.",
            parent=dialog
        ):
            return

        del_logs = 0
        del_screens = 0

        # Synchronously call the app's in-memory + file clearing handler if provided
        if on_clear_data:
            try:
                del_logs, del_screens = on_clear_data()
            except Exception as e:
                pass
        else:
            import glob
            # Delete logs & answers
            for f in glob.glob(os.path.join(PROJECT_ROOT, "logs", "*.log*")):
                try:
                    os.remove(f)
                    del_logs += 1
                except Exception:
                    pass

            for fname in ["answers.json", "answers.txt"]:
                f = os.path.join(PROJECT_ROOT, "logs", fname)
                if os.path.exists(f):
                    try:
                        os.remove(f)
                        del_logs += 1
                    except Exception:
                        pass

            # Delete all screenshot images
            for f in glob.glob(os.path.join(PROJECT_ROOT, "logs", "screenshots", "*.png")):
                try:
                    os.remove(f)
                    del_screens += 1
                except Exception:
                    pass

        clean_status_lbl.config(
            text=f"✅ Cleared: {del_logs} log files and {del_screens} screenshots!",
            fg="#10b981"
        )

    tk.Button(
        clean_box,
        text="🗑️ Clear Logs & Screenshots",
        command=do_clear_all_logs_and_screenshots,
        font=("Segoe UI", 9, "bold"),
        bg="#ef4444",
        fg="white",
        padx=12,
        pady=5,
        cursor="hand2"
    ).pack(anchor=tk.W)

    # About / Branding Section
    about_box = ttk.LabelFrame(tab_data, text=" ℹ️ Application Information ", padding=10)
    about_box.pack(fill=tk.X, pady=(16, 8))

    brand_row = tk.Frame(about_box, bg="#f8fafc")
    brand_row.pack(fill=tk.X)

    icon_48_path = os.path.join(PROJECT_ROOT, "assets", "icon_48.png")
    if os.path.exists(icon_48_path):
        try:
            about_icon_img = tk.PhotoImage(file=icon_48_path)
            icon_lbl = tk.Label(brand_row, image=about_icon_img, bg="#f8fafc")
            icon_lbl.image = about_icon_img
            icon_lbl.pack(side=tk.LEFT, padx=(4, 12))
        except Exception:
            pass

    info_col = tk.Frame(brand_row, bg="#f8fafc")
    info_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tk.Label(info_col, text="AI Quiz Assistant 2.0", font=("Segoe UI", 11, "bold"), fg="#0284c7", bg="#f8fafc").pack(anchor=tk.W)
    tk.Label(info_col, text="Smart AI Quiz Assistant • Silent Background Processing", font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc").pack(anchor=tk.W, pady=(1, 3))
    tk.Label(info_col, text="Supports Google Gemini & Custom OpenAI-compatible API", font=("Segoe UI", 8), fg="#475569", bg="#f8fafc").pack(anchor=tk.W)

    # Global MouseWheel Scroll for active tab
    def on_dialog_mousewheel(event):
        try:
            cur_tab = notebook.select()
            if cur_tab and str(cur_tab) in tab_canvases:
                tab_canvases[str(cur_tab)].yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    dialog.bind_all("<MouseWheel>", on_dialog_mousewheel)

    # Save logic
    def on_save_all(close_after: bool = False):
        try:
            selected_provider = provider_var.get()
            gemini_key = gem_key_entry.get().strip()
            gemini_model = gem_model_cb.get().strip()

            custom_url = custom_url_entry.get().strip()
            custom_key = custom_key_entry.get().strip()
            custom_model = custom_model_cb.get().strip()

            env_path = os.path.join(PROJECT_ROOT, '.env')
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

            def update_line(lines, k, v):
                done = False
                for i, line in enumerate(lines):
                    if line.strip().startswith(f"{k}="):
                        lines[i] = f"{k}={v}\n"
                        done = True
                        break
                if not done:
                    lines.append(f"{k}={v}\n")
                return lines

            env_lines = update_line(env_lines, 'API_PROVIDER', selected_provider)
            env_lines = update_line(env_lines, 'GEMINI_API_KEY', gemini_key)
            env_lines = update_line(env_lines, 'GEMINI_MODEL', gemini_model)
            env_lines = update_line(env_lines, 'CUSTOM_API_URL', custom_url)
            env_lines = update_line(env_lines, 'CUSTOM_API_KEY', custom_key)
            env_lines = update_line(env_lines, 'CUSTOM_MODEL', custom_model)

            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(env_lines)

            os.environ['API_PROVIDER'] = selected_provider
            os.environ['GEMINI_API_KEY'] = gemini_key
            os.environ['GEMINI_MODEL'] = gemini_model
            os.environ['CUSTOM_API_URL'] = custom_url
            os.environ['CUSTOM_API_KEY'] = custom_key
            os.environ['CUSTOM_MODEL'] = custom_model

            settings_manager.settings['api_provider'] = selected_provider
            settings_manager.settings['gemini_model'] = gemini_model
            try:
                settings_manager.settings['font_size'] = int(font_sb.get().strip())
            except Exception:
                settings_manager.settings['font_size'] = font_var.get()

            try:
                settings_manager.settings['popup_width'] = int(width_sb.get().strip())
            except Exception:
                settings_manager.settings['popup_width'] = width_var.get()

            settings_manager.settings['popup_opacity'] = round(opacity_var.get() / 100.0, 2)
            settings_manager.settings['popup_bg_color'] = bg_color_var.get()
            settings_manager.settings['save_screenshots'] = save_ss_var.get()
            settings_manager.settings['enable_mouse_gestures'] = enable_mouse_var.get()
            settings_manager.settings['enable_autofill'] = enable_autofill_var.get()
            settings_manager.settings['enable_provider_failover'] = failover_var.get()
            try:
                settings_manager.settings['autofill_click_delay_ms'] = int(af_delay_sb.get().strip())
            except Exception:
                pass
            settings_manager.settings['autofill_restore_cursor'] = restore_cursor_var.get()
            settings_manager.settings['autofill_smooth_movement'] = smooth_move_var.get()

            if save_win_size_btn.winfo_exists() and save_win_size_btn.winfo_ismapped():
                save_win_size_btn.pack_forget()

            new_mode = mode_var.get()
            new_ans_disp = ans_disp_var.get()
            settings_manager.settings['question_mode'] = new_mode
            settings_manager.settings['answer_display_mode'] = new_ans_disp

            hotkeys_changed = False
            for hk_key, entry in hotkey_entries.items():
                new_v = entry.get().strip().lower()
                if new_v and len(new_v) == 1:
                    if settings_manager.get(hk_key) != new_v:
                        hotkeys_changed = True
                        settings_manager.settings[hk_key] = new_v

            cur_dlg_w = dialog.winfo_width()
            cur_dlg_h = dialog.winfo_height()
            if cur_dlg_w >= 500 and cur_dlg_h >= 400:
                settings_manager.settings['settings_win_width'] = cur_dlg_w
                settings_manager.settings['settings_win_height'] = cur_dlg_h

            settings_manager.save_settings()

            if on_api_change:
                try:
                    on_api_change()
                except Exception:
                    pass

            if on_settings_change:
                try:
                    on_settings_change()
                except Exception:
                    pass

            if on_mode_change:
                try:
                    on_mode_change(new_mode)
                except Exception:
                    pass

            if hotkeys_changed and on_hotkey_change:
                try:
                    on_hotkey_change()
                except Exception:
                    pass

            if close_after:
                global _active_settings_dialog
                _active_settings_dialog = None
                try:
                    dialog.destroy()
                finally:
                    if on_close:
                        try:
                            on_close()
                        except Exception:
                            pass
            else:
                save_status_lbl.config(text="✅ Settings saved successfully!", fg="#10b981")
                dialog.after(3000, lambda: save_status_lbl.config(text="") if save_status_lbl.winfo_exists() else None)

        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}", parent=dialog)

    globals_or_locals['on_save_all'] = on_save_all

    def on_window_close_clicked():
        trigger_save_close()

    dialog.protocol("WM_DELETE_WINDOW", on_window_close_clicked)
    dialog.bind("<Escape>", lambda e: on_window_close_clicked())
    dialog.mainloop()
