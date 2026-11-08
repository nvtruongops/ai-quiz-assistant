"""
Popup Manager Module
Manages a modern, draggable floating HUD popup window to display quiz results and status.
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import re
from typing import Optional, Tuple, List, Union, Any, Callable
from pynput.mouse import Controller as MouseController


def get_popup_theme(bg_hex: str = "#ffffff") -> dict:
    """
    Generate complete cohesive theme colors based on the chosen background color.
    Ensures optimal contrast, readability, and modern aesthetic.
    Supports special 'stealth' / 'ghost' preset for borderless, low-contrast ghost UI.
    """
    bg_clean = (bg_hex or '#ffffff').strip().lower()
    if bg_clean in ('stealth', '#stealth', 'ghost', '#ghost'):
        return {
            'bg': '#ffffff',
            'header_bg': '#ffffff',
            'border': '#ffffff',
            'text': '#71717a',            # subtle muted slate gray
            'question': '#71717a',        # subtle muted gray (no bold)
            'answer': '#52525b',          # subtle gray-charcoal (no bold)
            'badge_bg': '#ffffff',
            'badge_fg': '#a1a1aa',
            'accent': '#94a3b8',
            'close_fg': '#a1a1aa',        # muted gray X (not bright red)
            'copy_fg': '#a1a1aa',         # muted gray Copy
            'exp_box_bg': '#ffffff',
            'exp_box_fg': '#71717a',
            'exp_btn_bg': '#ffffff',
            'exp_btn_fg': '#94a3b8',
            'is_light': True,
            'is_stealth': True
        }

    bg_clean = bg_clean.lstrip('#')
    if len(bg_clean) != 6:
        bg_clean = 'ffffff'
    try:
        r = int(bg_clean[0:2], 16)
        g = int(bg_clean[2:4], 16)
        b = int(bg_clean[4:6], 16)
    except Exception:
        r, g, b = 255, 255, 255
        bg_hex = '#ffffff'

    # Perceived luminance (ITU-R BT.709)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    if luminance > 0.5:
        # Light theme (default white)
        hr, hg, hb = max(0, r - 10), max(0, g - 10), max(0, b - 10)
        br, bg_c, bb = max(0, r - 40), max(0, g - 40), max(0, b - 40)
        bgr, bgg, bgb = max(0, r - 20), max(0, g - 20), max(0, b - 20)
        return {
            'bg': bg_hex,
            'header_bg': f'#{hr:02x}{hg:02x}{hb:02x}',
            'border': f'#{br:02x}{bg_c:02x}{bb:02x}',
            'text': '#0f172a',
            'question': '#0369a1',
            'answer': '#15803d',
            'badge_bg': f'#{bgr:02x}{bgg:02x}{bgb:02x}',
            'badge_fg': '#334155',
            'accent': '#0284c7',
            'close_fg': '#dc2626',
            'copy_fg': '#1e293b',
            'exp_box_bg': f'#{hr:02x}{hg:02x}{hb:02x}',
            'exp_box_fg': '#1e293b',
            'exp_btn_bg': f'#{bgr:02x}{bgg:02x}{bgb:02x}',
            'exp_btn_fg': '#0284c7',
            'is_light': True
        }
    else:
        # Dark theme
        hr, hg, hb = min(255, r + 15), min(255, g + 15), min(255, b + 15)
        br, bg_c, bb = min(255, r + 45), min(255, g + 45), min(255, b + 45)
        bgr, bgg, bgb = min(255, r + 25), min(255, g + 25), min(255, b + 25)
        return {
            'bg': bg_hex,
            'header_bg': f'#{hr:02x}{hg:02x}{hb:02x}',
            'border': f'#{br:02x}{bg_c:02x}{bb:02x}',
            'text': '#cdd6f4',
            'question': '#89dceb',
            'answer': '#a6e3a1',
            'badge_bg': f'#{bgr:02x}{bgg:02x}{bgb:02x}',
            'badge_fg': '#f5c2e7',
            'accent': '#89b4fa',
            'close_fg': '#f38ba8',
            'copy_fg': '#cdd6f4',
            'exp_box_bg': f'#{hr:02x}{hg:02x}{hb:02x}',
            'exp_box_fg': '#f9e2af',
            'exp_btn_bg': f'#{bgr:02x}{bgg:02x}{bgb:02x}',
            'exp_btn_fg': '#f9e2af',
            'is_light': False
        }


class PopupManager:
    """Manages modern floating popup window to display question analysis results"""

    _shared_root = None
    _shared_thread = None
    _shared_ready = threading.Event()
    _shared_lock = threading.Lock()

    def __init__(
        self,
        config_manager=None,
        settings_manager=None,
        settings=None,
        on_prev: Optional[Callable] = None,
        on_next: Optional[Callable] = None,
        on_reload: Optional[Callable] = None
    ):
        self.config = config_manager
        self.settings = settings_manager or settings
        self.settings_manager = settings_manager or (self.settings if hasattr(self.settings, 'save_settings') else None)
        self.on_nav_prev = on_prev
        self.on_nav_next = on_next
        self.on_nav_reload = on_reload
        self.current_popup: Optional[tk.Toplevel] = None
        self.mouse_controller = MouseController()
        self._is_visible = False
        self._current_content = ""
        self._current_title = "AI Quiz Assistant"
        self._provider_badge = "AI"
        self._mode_badge = "Multiple Choice"

        # Queue to pass actions safely to Tkinter event loop
        self.command_queue = queue.Queue()
        self._closed = False

        with PopupManager._shared_lock:
            if PopupManager._shared_thread is None or not PopupManager._shared_thread.is_alive():
                PopupManager._shared_ready.clear()
                PopupManager._shared_thread = threading.Thread(
                    target=PopupManager._run_shared_tkinter, daemon=True, name="PopupTkThread"
                )
                PopupManager._shared_thread.start()
                PopupManager._shared_ready.wait()

        self.root = PopupManager._shared_root
        self.tk_ready = PopupManager._shared_ready
        self.tk_thread = PopupManager._shared_thread

        if self.root:
            try:
                self.root.after(10, self._process_commands)
            except Exception:
                pass

    @classmethod
    def _run_shared_tkinter(cls):
        """Run shared Tkinter mainloop in a single dedicated thread"""
        try:
            cls._shared_root = tk.Tk()
            cls._shared_root.withdraw()
            cls._shared_root.attributes('-alpha', 0)
            cls._shared_root.geometry('1x1+0+0')
        except Exception:
            pass
        finally:
            cls._shared_ready.set()
        if cls._shared_root:
            cls._shared_root.mainloop()

    def set_provider_info(self, provider_name: str, mode: str = "multiple_choice"):
        """Update provider and mode info displayed on the popup header"""
        self._provider_badge = provider_name
        if mode == "essay":
            self._mode_badge = "Essay"
        elif mode == "multiple_choice_explanation":
            self._mode_badge = "MC + Exp"
        else:
            self._mode_badge = "Multiple Choice"

    def set_nav_callbacks(self, on_prev=None, on_next=None, on_reload=None):
        """Set navigation and reload callbacks"""
        self.on_nav_prev = on_prev
        self.on_nav_next = on_next
        self.on_nav_reload = on_reload

    def _process_commands(self):
        """Process incoming commands from queue in Tkinter thread"""
        if self._closed:
            return
        try:
            while not self.command_queue.empty():
                cmd, args = self.command_queue.get_nowait()
                if cmd == "show":
                    content, title, provider, mode = args
                    self._create_popup_internal(content, title, provider, mode, questions=None)
                elif cmd == "show_questions":
                    if len(args) == 6:
                        questions, title, provider, mode, plain_content, is_history = args
                    else:
                        questions, title, provider, mode, plain_content = args
                        is_history = False
                    self._create_popup_internal(plain_content, title, provider, mode, questions=questions, is_history=is_history)
                elif cmd == "hide":
                    self._hide_internal()
        except queue.Empty:
            pass
        finally:
            if self.root and not self._closed:
                try:
                    self.root.after(50, self._process_commands)
                except Exception:
                    pass

    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current mouse cursor position"""
        try:
            pos = self.mouse_controller.position
            return (int(pos[0]), int(pos[1]))
        except Exception:
            return (200, 200)

    def _clamp_to_screen(self, pos: Tuple[int, int], window_size: Tuple[int, int]) -> Tuple[int, int]:
        """Clamp (x, y) coordinates so the window of window_size fits inside screen boundaries"""
        x, y = pos
        win_w, win_h = window_size
        screen_width = 1920
        screen_height = 1080
        try:
            from screeninfo import get_monitors
            monitors = get_monitors()
            if monitors:
                monitor = monitors[0]
                screen_width = monitor.width
                screen_height = monitor.height
        except Exception:
            if self.root:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()

        if x + win_w > screen_width:
            x = max(10, screen_width - win_w - 20)
        if y + win_h > screen_height:
            y = max(10, screen_height - win_h - 20)

        x = max(10, x)
        y = max(10, y)
        return (int(x), int(y))

    def calculate_position(self, cursor_pos: Tuple[int, int], window_size: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate popup coordinates ensuring window stays within screen bounds"""
        x = cursor_pos[0] + 12
        y = cursor_pos[1] + 12
        return self._clamp_to_screen((x, y), window_size)

    def show(self, content: str, title: str = "Quiz Analysis Result", provider: str = None, mode: str = None):
        """Request popup display with plain text content"""
        self._current_content = content
        p_name = provider or self._provider_badge
        m_name = mode or self._mode_badge

        # Clear queue to avoid stale commands
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except Exception:
                break

        self.command_queue.put(("show", (content, title, p_name, m_name)))

    def show_questions(
        self,
        questions: list,
        title: str = "Quiz Analysis Result",
        provider: str = None,
        mode: str = None,
        is_history: bool = False
    ):
        """Request popup display for structured questions with interactive collapsible explanations"""
        p_name = provider or self._provider_badge
        m_name = mode or self._mode_badge

        # Format clean text representation for top copy button
        lines = []
        for item in questions:
            num = getattr(item, 'number', None) or (item.get('number') if isinstance(item, dict) else '?')
            q = getattr(item, 'question', None) or (item.get('question') if isinstance(item, dict) else '')
            ans = getattr(item, 'answer', None) or (item.get('answer') if isinstance(item, dict) else '')
            exp = getattr(item, 'explanation', None) or (item.get('explanation') if isinstance(item, dict) else '')
            is_pending = getattr(item, 'is_pending', False) or (item.get('is_pending', False) if isinstance(item, dict) else False)

            if not ans or not str(ans).strip():
                ans = "[Answer not identified]"

            clean_q = re.sub(r'^(?:Câu|Question|Bài|Item|Q)\s*\d+[\s\:\.\-]+', '', str(q), flags=re.IGNORECASE).strip()
            disp_q = clean_q if clean_q else q

            if is_pending:
                lines.append(f"⏳ Q{num}: {disp_q}")
                lines.append(f"   → {ans}\n")
            else:
                lines.append(f"Question {num}: {disp_q}")
                lines.append(f"→ Answer: {ans}")
                if exp:
                    lines.append(f"Explanation: {exp}\n")
        plain_content = "\n".join(lines).strip()
        self._current_content = plain_content

        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except Exception:
                break

        self.command_queue.put(("show_questions", (questions, title, p_name, m_name, plain_content, is_history)))

    def show_processing(self, request_id: str = "", provider: str = None):
        """Show animated or stylish processing state"""
        p_name = provider or self._provider_badge
        msg = f"🔄 Capturing screen & sending to {p_name}...\n\n⏱️ Please wait a moment"
        if request_id:
            msg += f"\n(Request ID: {request_id[:8]})"
        self.show(msg, title="Processing...", provider=p_name)

    def hide(self):
        """Request hiding and destruction of active popup"""
        self._is_visible = False
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except Exception:
                break
        self.command_queue.put(("hide", ()))

    def _hide_internal(self):
        """Destroy popup in Tkinter thread"""
        if self.current_popup:
            try:
                if self.current_popup.winfo_exists():
                    try:
                        self._last_popup_pos = (self.current_popup.winfo_rootx(), self.current_popup.winfo_rooty())
                    except Exception:
                        pass
                self.current_popup.destroy()
            except Exception:
                pass
            finally:
                self.current_popup = None
                self._is_visible = False
                self._current_content = ""

    def _copy_to_clipboard(self, text: str, copy_btn: tk.Label):
        """Copy text to clipboard with temporary button feedback"""
        if not self.root:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            orig_text = copy_btn.cget('text')
            orig_fg = copy_btn.cget('fg')
            copy_btn.config(text="✓ Copied", fg="#a6e3a1")
            self.root.after(1400, lambda: copy_btn.config(text=orig_text, fg=orig_fg) if copy_btn.winfo_exists() else None)
        except Exception:
            pass

    def _create_popup_internal(
        self,
        content: str,
        title: str,
        provider: str,
        mode: str,
        questions: Optional[list] = None,
        is_history: bool = False
    ):
        """Create and display modern styled floating popup"""
        # Capture current window position and size BEFORE destroying, so reloading/navigating does not jump
        existing_pos = None
        existing_size = None
        if self.current_popup:
            try:
                if self.current_popup.winfo_exists() and self.current_popup.winfo_ismapped():
                    existing_pos = (self.current_popup.winfo_rootx(), self.current_popup.winfo_rooty())
                    existing_size = (self.current_popup.winfo_width(), self.current_popup.winfo_height())
            except Exception:
                existing_pos = None
                existing_size = None

        if not existing_pos and getattr(self, '_last_popup_pos', None) and self._is_visible:
            existing_pos = self._last_popup_pos

        self._hide_internal()

        cursor_pos = self.get_cursor_position()

        # Get settings with robust min-width
        font_size = 10
        popup_opacity = 0.96
        popup_bg_color = "#ffffff"  # Default WHITE background

        if self.settings:
            font_size = int(self.settings.get('font_size', 10) or 10)
            popup_bg_color = self.settings.get('popup_bg_color', '#ffffff')
            opacity_val = self.settings.get('popup_opacity', 0.96)
            try:
                popup_opacity = max(0.5, min(1.0, float(opacity_val)))
            except Exception:
                popup_opacity = 0.96

        # Determine saved dimensions for this mode
        if is_history:
            saved_w = int(self.settings.get('history_popup_width', self.settings.get('popup_width', 560)) or 560) if self.settings else 560
            saved_h = int(self.settings.get('history_popup_height', 0) or 0) if self.settings else 0
        else:
            saved_w = int(self.settings.get('popup_width', 500) or 500) if self.settings else 500
            saved_h = int(self.settings.get('popup_height', 0) or 0) if self.settings else 0

        saved_w = max(400, saved_w)
        popup_width = saved_w

        # Theme colors computed dynamically from popup_bg_color
        theme = get_popup_theme(popup_bg_color)
        is_stealth = theme.get('is_stealth', False)
        BG_COLOR = theme['bg']
        HEADER_BG = theme['header_bg']
        BORDER_COLOR = theme['border']
        TEXT_COLOR = theme['text']
        QUESTION_COLOR = theme['question']
        ANSWER_COLOR = theme['answer']
        BADGE_BG = theme['badge_bg']
        BADGE_FG = theme['badge_fg']
        ACCENT_COLOR = theme['accent']
        CLOSE_FG = theme['close_fg']
        COPY_FG = theme['copy_fg']

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes('-topmost', True)
        popup.attributes('-alpha', popup_opacity)
        popup.config(bg=BORDER_COLOR)

        # Outer border container (borderless in stealth mode)
        outer_frame = tk.Frame(popup, bg=BORDER_COLOR, bd=0 if is_stealth else 1)
        outer_frame.pack(fill=tk.BOTH, expand=True, padx=0 if is_stealth else 1, pady=0 if is_stealth else 1)

        # 1. Top resize edge
        top_edge = tk.Frame(outer_frame, bg=HEADER_BG, height=3 if is_stealth else 5, cursor="size_ns")
        top_edge.pack(side=tk.TOP, fill=tk.X)
        top_edge.pack_propagate(False)

        # 2. Bottom status & resize bar (Pack side=BOTTOM first so it's guaranteed visible!)
        bottom_bar = tk.Frame(outer_frame, bg=HEADER_BG, height=14 if is_stealth else 20)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_bar.pack_propagate(False)

        # Bottom-Left corner grip
        bl_grip = tk.Frame(bottom_bar, bg=HEADER_BG, width=14, cursor="size_ne_sw")
        bl_grip.pack(side=tk.LEFT, fill=tk.Y)
        bl_grip.pack_propagate(False)

        # Bottom-Right corner diagonal gripper
        resize_grip = tk.Label(
            bottom_bar,
            text=" ◢ ",
            font=("Segoe UI", 8 if is_stealth else 9, "normal" if is_stealth else "bold"),
            fg="#ffffff" if is_stealth else ACCENT_COLOR,
            bg=HEADER_BG,
            cursor="size_nw_se",
            padx=4,
            pady=0
        )
        resize_grip.pack(side=tk.RIGHT, fill=tk.Y)
        resize_grip.bind("<Enter>", lambda e: resize_grip.config(fg="#a1a1aa" if is_stealth else "#2563eb", bg="#f4f4f5" if is_stealth else BADGE_BG) if resize_grip.winfo_exists() else None)
        resize_grip.bind("<Leave>", lambda e: resize_grip.config(fg="#ffffff" if is_stealth else ACCENT_COLOR, bg=HEADER_BG) if resize_grip.winfo_exists() else None)

        # Bottom center edge
        bottom_edge = tk.Frame(bottom_bar, bg=HEADER_BG, cursor="size_ns")
        bottom_edge.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 3. Middle container for Left Edge, Main Frame, and Right Edge
        mid_container = tk.Frame(outer_frame, bg=BG_COLOR)
        mid_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left resize edge
        left_edge = tk.Frame(mid_container, bg=HEADER_BG, width=4 if is_stealth else 6, cursor="size_we")
        left_edge.pack(side=tk.LEFT, fill=tk.Y)
        left_edge.pack_propagate(False)

        # Right resize edge
        right_edge = tk.Frame(mid_container, bg=HEADER_BG, width=4 if is_stealth else 8, cursor="size_we")
        right_edge.pack(side=tk.RIGHT, fill=tk.Y)
        right_edge.pack_propagate(False)

        # Main window frame
        main_frame = tk.Frame(mid_container, bg=BG_COLOR)
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- HEADER BAR ---
        header_frame = tk.Frame(main_frame, bg=HEADER_BG, height=28 if is_stealth else 36, padx=6 if is_stealth else 8, pady=2 if is_stealth else 4)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        # Drag handler
        def start_drag(event):
            popup._drag_x = event.x
            popup._drag_y = event.y

        def do_drag(event):
            nx = popup.winfo_x() + (event.x - popup._drag_x)
            ny = popup.winfo_y() + (event.y - popup._drag_y)
            popup.geometry(f"+{nx}+{ny}")
            self._last_popup_pos = (nx, ny)

        header_frame.bind("<Button-1>", start_drag)
        header_frame.bind("<B1-Motion>", do_drag)

        # Helper for modern interactive buttons with hover effect
        def make_header_btn(parent, text, font, fg, bg, active_bg, padx=5, pady=1):
            btn = tk.Label(
                parent,
                text=text,
                font=font,
                bg=bg,
                fg=fg,
                cursor="hand2",
                padx=padx,
                pady=pady,
                bd=0,
                relief=tk.FLAT
            )
            btn.bind("<Enter>", lambda e: btn.config(bg=active_bg) if btn.winfo_exists() else None)
            btn.bind("<Leave>", lambda e: btn.config(bg=bg) if btn.winfo_exists() else None)
            return btn

        # RIGHT ACTIONS CONTAINER (Pack first to guarantee space on right)
        right_frame = tk.Frame(header_frame, bg=HEADER_BG)
        right_frame.pack(side=tk.RIGHT)

        # 1. Close button (✕)
        close_btn = make_header_btn(
            right_frame,
            text=" ✕ ",
            font=("Segoe UI", 8 if is_stealth else 10, "normal" if is_stealth else "bold"),
            fg=CLOSE_FG,
            bg=HEADER_BG,
            active_bg="#f4f4f5" if is_stealth else ("#fee2e2" if theme.get('is_light', True) else "#450a0a"),
            padx=3 if is_stealth else 4,
            pady=0
        )
        close_btn.pack(side=tk.RIGHT, padx=(2, 0))
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # 2. Copy button (📋 Copy)
        copy_btn = make_header_btn(
            right_frame,
            text="📋 Copy",
            font=("Segoe UI", 7 if is_stealth else 8, "normal" if is_stealth else "bold"),
            fg=COPY_FG,
            bg=BADGE_BG,
            active_bg="#f4f4f5" if is_stealth else ("#e2e8f0" if theme.get('is_light', True) else ACCENT_COLOR),
            padx=4 if is_stealth else 6,
            pady=1 if is_stealth else 2
        )
        copy_btn.pack(side=tk.RIGHT, padx=(2, 3))
        copy_btn.bind("<Button-1>", lambda e: self._copy_to_clipboard(content, copy_btn))

        # 3. Reload button (🔄)
        reload_btn = make_header_btn(
            right_frame,
            text="🔄",
            font=("Segoe UI", 7 if is_stealth else 8),
            fg=ACCENT_COLOR,
            bg=BADGE_BG,
            active_bg="#f4f4f5" if is_stealth else ("#e2e8f0" if theme.get('is_light', True) else ACCENT_COLOR),
            padx=4 if is_stealth else 5,
            pady=1 if is_stealth else 2
        )
        reload_btn.pack(side=tk.RIGHT, padx=1)
        if hasattr(self, 'on_nav_reload') and self.on_nav_reload:
            reload_btn.bind("<Button-1>", lambda e: self.on_nav_reload())

        # 4. Next (▼) and Prev (▲) buttons - ONLY in single question mode (not history)!
        # In history mode, ▲/▼ are omitted as history is a continuous scrollable list.
        if not is_history:
            next_btn = make_header_btn(
                right_frame,
                text=" ▼ ",
                font=("Segoe UI", 7 if is_stealth else 8, "normal" if is_stealth else "bold"),
                fg=BADGE_FG,
                bg=BADGE_BG,
                active_bg="#f4f4f5" if is_stealth else ("#e2e8f0" if theme.get('is_light', True) else ACCENT_COLOR),
                padx=3 if is_stealth else 4,
                pady=1 if is_stealth else 2
            )
            next_btn.pack(side=tk.RIGHT, padx=1)

            prev_btn = make_header_btn(
                right_frame,
                text=" ▲ ",
                font=("Segoe UI", 7 if is_stealth else 8, "normal" if is_stealth else "bold"),
                fg=BADGE_FG,
                bg=BADGE_BG,
                active_bg="#f4f4f5" if is_stealth else ("#e2e8f0" if theme.get('is_light', True) else ACCENT_COLOR),
                padx=3 if is_stealth else 4,
                pady=1 if is_stealth else 2
            )
            prev_btn.pack(side=tk.RIGHT, padx=1)

        # 5. Save Size button (appears dynamically when window is resized from saved dimensions)
        save_size_btn = make_header_btn(
            right_frame,
            text="💾 Save Size",
            font=("Segoe UI", 7 if is_stealth else 8, "normal" if is_stealth else "bold"),
            fg="#71717a" if is_stealth else "#ffffff",
            bg="#f4f4f5" if is_stealth else "#0284c7",
            active_bg="#e4e4e7" if is_stealth else "#0369a1",
            padx=4 if is_stealth else 6,
            pady=1 if is_stealth else 2
        )

        # LEFT TITLE & BADGE CONTAINER
        left_frame = tk.Frame(header_frame, bg=HEADER_BG)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        left_frame.bind("<Button-1>", start_drag)
        left_frame.bind("<B1-Motion>", do_drag)

        title_icon = "" if is_stealth else ("📖 " if is_history else "🎯 ")
        clean_title = title.replace("📖", "").replace("🎯", "").strip()
        title_label = tk.Label(
            left_frame,
            text=f"{title_icon}{clean_title}",
            font=("Segoe UI", 8 if is_stealth else 9, "normal" if is_stealth else "bold"),
            bg=HEADER_BG,
            fg=ACCENT_COLOR,
            cursor="fleur"
        )
        title_label.pack(side=tk.LEFT, padx=(0, 6))
        title_label.bind("<Button-1>", start_drag)
        title_label.bind("<B1-Motion>", do_drag)

        # Provider / Mode compact chip (single unified pill to save space)
        p_short = "Custom" if "custom" in (provider or "").lower() else ("Gemini" if "gemini" in (provider or "").lower() else (provider or ""))
        m_short = "Essay" if "essay" in (mode or "").lower() or "tự luận" in (mode or "").lower() else ("MC+Exp" if ("expl" in (mode or "").lower() or "giải thích" in (mode or "").lower()) else ("History" if is_history else "MC"))

        chip_text = f"{p_short} • {m_short}" if (p_short and not is_history) else (p_short or m_short)
        if chip_text:
            chip_badge = tk.Label(
                left_frame,
                text=chip_text,
                font=("Segoe UI", 7),
                bg=BADGE_BG,
                fg=BADGE_FG,
                padx=4 if is_stealth else 5,
                pady=1,
                bd=0,
                relief=tk.FLAT
            )
            chip_badge.pack(side=tk.LEFT, padx=1)
            chip_badge.bind("<Button-1>", start_drag)
            chip_badge.bind("<B1-Motion>", do_drag)

        # --- CONTENT AREA ---
        content_frame = tk.Frame(main_frame, bg=BG_COLOR, padx=8, pady=6)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Clean content text widget without bulky scrollbars
        text_widget = tk.Text(
            content_frame,
            wrap=tk.WORD,
            font=("Segoe UI", font_size),
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            cursor="arrow",
            padx=6,
            pady=6
        )
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Configure style tags with dynamic theme colors (non-bold in stealth mode)
        q_weight = "normal" if is_stealth else "bold"
        ans_weight = "normal" if is_stealth else "bold"
        pending_weight = "normal" if is_stealth else "bold"

        text_widget.tag_configure("question", font=("Segoe UI", font_size, q_weight), foreground=QUESTION_COLOR, spacing1=3 if is_stealth else 4, spacing3=1)
        text_widget.tag_configure("answer_line", font=("Segoe UI", font_size, ans_weight), foreground=ANSWER_COLOR, spacing3=2 if is_stealth else 3)
        text_widget.tag_configure("essay_ans", font=("Segoe UI", font_size, "normal"), foreground=ANSWER_COLOR, spacing1=2, spacing3=3 if is_stealth else 4)
        text_widget.tag_configure("pending_title", font=("Segoe UI", font_size, pending_weight), foreground=QUESTION_COLOR if is_stealth else "#d97706", spacing1=3 if is_stealth else 4, spacing3=1)
        text_widget.tag_configure("pending_ans", font=("Segoe UI", font_size, "italic"), foreground=TEXT_COLOR if is_stealth else "#d97706", spacing3=3 if is_stealth else 4)
        text_widget.tag_configure("error", font=("Segoe UI", font_size, "normal"), foreground=CLOSE_FG)
        text_widget.tag_configure("normal", font=("Segoe UI", font_size, "normal"), foreground=TEXT_COLOR)

        # Mouse wheel support
        def on_mousewheel(event):
            text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        text_widget.bind("<MouseWheel>", on_mousewheel)
        popup.bind("<MouseWheel>", on_mousewheel)

        # Hotkeys on popup
        popup.bind("<Escape>", lambda e: self.hide())
        popup.bind("<Control-c>", lambda e: self._copy_to_clipboard(content, copy_btn))

        # Navigation bindings (▲ / ▼ / 🔄)
        if is_history:
            # In history mode: Up/Down arrow keys scroll text_widget smoothly!
            popup.bind("<Up>", lambda e: text_widget.yview_scroll(-3, "units"))
            popup.bind("<Down>", lambda e: text_widget.yview_scroll(3, "units"))
            popup.bind("<Prior>", lambda e: text_widget.yview_scroll(-8, "units"))
            popup.bind("<Next>", lambda e: text_widget.yview_scroll(8, "units"))
        else:
            # In single question mode: ▲/▼ navigates between questions
            if hasattr(self, 'on_nav_prev') and self.on_nav_prev:
                prev_btn.bind("<Button-1>", lambda e: self.on_nav_prev())
                popup.bind("<Up>", lambda e: self.on_nav_prev())
                popup.bind("<Left>", lambda e: self.on_nav_prev())
            if hasattr(self, 'on_nav_next') and self.on_nav_next:
                next_btn.bind("<Button-1>", lambda e: self.on_nav_next())
                popup.bind("<Down>", lambda e: self.on_nav_next())
                popup.bind("<Right>", lambda e: self.on_nav_next())

        if hasattr(self, 'on_nav_reload') and self.on_nav_reload:
            popup.bind("<F5>", lambda e: self.on_nav_reload())
            popup.bind("<Control-r>", lambda e: self.on_nav_reload())

        # Format and insert content
        if questions:
            self._insert_structured_questions(text_widget, questions, theme, font_size, popup_width)
        else:
            self._insert_styled_content(text_widget, content)

        text_widget.config(state=tk.DISABLED)

        # Calculate height and size
        line_count = len(content.split('\n'))
        if questions:
            line_count = max(line_count, len(questions) * 3)
        text_height = max(3, min(24, line_count + 1))
        text_widget.config(height=text_height)

        popup.update_idletasks()

        line_height = int(font_size * 2.1)
        auto_calc_h = max(110, min(580, (text_height * line_height) + 65))

        if saved_h >= 110:
            calc_h = min(900, max(110, saved_h))
        else:
            calc_h = auto_calc_h

        calc_w = max(400, min(1400, saved_w))
        initial_calc_w = calc_w
        initial_calc_h = calc_h

        if existing_size and existing_size[0] >= 380 and existing_size[1] >= 110:
            calc_w = existing_size[0]
            calc_h = existing_size[1]

        if existing_pos and existing_pos[0] > 0 and existing_pos[1] > 0:
            # Maintain exact same window position when reloading / navigating - NO JUMPING!
            pos = self._clamp_to_screen(existing_pos, (calc_w, calc_h))
        else:
            # Newly opened popup via hotkey: position relative to mouse cursor
            pos = self.calculate_position(cursor_pos, (calc_w, calc_h))

        popup.geometry(f"{int(calc_w)}x{int(calc_h)}+{int(pos[0])}+{int(pos[1])}")
        popup.update()

        # Connect resize handlers & save size logic
        def on_save_size_clicked(e=None):
            cur_w = popup.winfo_width()
            cur_h = popup.winfo_height()
            w_key = 'history_popup_width' if is_history else 'popup_width'
            h_key = 'history_popup_height' if is_history else 'popup_height'

            sm = getattr(self, 'settings_manager', None) or (self.settings if hasattr(self.settings, 'set') else None)
            if sm is not None:
                sm.set(w_key, cur_w)
                sm.set(h_key, cur_h)
                if hasattr(sm, 'save_settings'):
                    try:
                        sm.save_settings()
                    except Exception:
                        pass
            elif isinstance(self.settings, dict):
                self.settings[w_key] = cur_w
                self.settings[h_key] = cur_h

            nonlocal saved_w, saved_h
            saved_w = cur_w
            saved_h = cur_h
            if is_stealth:
                save_size_btn.config(text="✓ Saved!", bg="#f4f4f5", fg="#71717a")
            else:
                save_size_btn.config(text="✓ Saved!", bg="#10b981", fg="#ffffff")
            popup.after(1400, lambda: save_size_btn.pack_forget() if save_size_btn.winfo_exists() and abs(popup.winfo_width() - saved_w) <= 15 and abs(popup.winfo_height() - saved_h) <= 15 else None)
            return "break"

        save_size_btn.bind("<Button-1>", on_save_size_clicked)

        def check_size_diff(w: int, h: int):
            diff_w = abs(w - saved_w) > 15
            diff_h = (saved_h > 0 and abs(h - saved_h) > 15) or (saved_h == 0 and abs(h - initial_calc_h) > 15)
            if diff_w or diff_h:
                if is_stealth:
                    save_size_btn.config(text=f"💾 Save ({w}x{h})", bg="#f4f4f5", fg="#71717a")
                else:
                    save_size_btn.config(text=f"💾 Save Size ({w}x{h})", bg="#0284c7", fg="#ffffff")
                if not save_size_btn.winfo_ismapped():
                    save_size_btn.pack(side=tk.RIGHT, padx=2)
            else:
                if save_size_btn.winfo_ismapped() and save_size_btn.cget('text') != "✓ Saved!":
                    save_size_btn.pack_forget()

        def start_resize(event):
            popup._resizing = True
            popup._resize_start_x = event.x_root
            popup._resize_start_y = event.y_root
            popup._resize_start_w = popup.winfo_width()
            popup._resize_start_h = popup.winfo_height()
            popup._resize_orig_x = popup.winfo_x()
            popup._resize_orig_y = popup.winfo_y()

        def do_resize_corner_se(event):
            if not getattr(popup, '_resizing', False):
                return
            dx = event.x_root - popup._resize_start_x
            dy = event.y_root - popup._resize_start_y
            new_w = max(380, min(1400, popup._resize_start_w + dx))
            new_h = max(110, min(950, popup._resize_start_h + dy))
            popup.geometry(f"{int(new_w)}x{int(new_h)}+{popup._resize_orig_x}+{popup._resize_orig_y}")
            check_size_diff(int(new_w), int(new_h))

        def do_resize_right(event):
            if not getattr(popup, '_resizing', False):
                return
            dx = event.x_root - popup._resize_start_x
            new_w = max(380, min(1400, popup._resize_start_w + dx))
            cur_h = popup.winfo_height()
            popup.geometry(f"{int(new_w)}x{int(cur_h)}+{popup._resize_orig_x}+{popup._resize_orig_y}")
            check_size_diff(int(new_w), int(cur_h))

        def do_resize_bottom(event):
            if not getattr(popup, '_resizing', False):
                return
            dy = event.y_root - popup._resize_start_y
            new_h = max(110, min(950, popup._resize_start_h + dy))
            cur_w = popup.winfo_width()
            popup.geometry(f"{int(cur_w)}x{int(new_h)}+{popup._resize_orig_x}+{popup._resize_orig_y}")
            check_size_diff(int(cur_w), int(new_h))

        def do_resize_left(event):
            if not getattr(popup, '_resizing', False):
                return
            dx = event.x_root - popup._resize_start_x
            new_w = max(380, min(1400, popup._resize_start_w - dx))
            new_x = popup._resize_orig_x + (popup._resize_start_w - new_w)
            cur_h = popup.winfo_height()
            popup.geometry(f"{int(new_w)}x{int(cur_h)}+{int(new_x)}+{popup._resize_orig_y}")
            check_size_diff(int(new_w), int(cur_h))

        def do_resize_top(event):
            if not getattr(popup, '_resizing', False):
                return
            dy = event.y_root - popup._resize_start_y
            new_h = max(110, min(950, popup._resize_start_h - dy))
            new_y = popup._resize_orig_y + (popup._resize_start_h - new_h)
            cur_w = popup.winfo_width()
            popup.geometry(f"{int(cur_w)}x{int(new_h)}+{popup._resize_orig_x}+{int(new_y)}")
            check_size_diff(int(cur_w), int(new_h))

        def do_resize_corner_sw(event):
            if not getattr(popup, '_resizing', False):
                return
            dx = event.x_root - popup._resize_start_x
            dy = event.y_root - popup._resize_start_y
            new_w = max(380, min(1400, popup._resize_start_w - dx))
            new_h = max(110, min(950, popup._resize_start_h + dy))
            new_x = popup._resize_orig_x + (popup._resize_start_w - new_w)
            popup.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{popup._resize_orig_y}")
            check_size_diff(int(new_w), int(new_h))

        def stop_resize(event):
            popup._resizing = False
            self._last_popup_pos = (popup.winfo_x(), popup.winfo_y())
            check_size_diff(popup.winfo_width(), popup.winfo_height())

        # Bindings on all borders and corners
        resize_grip.bind("<Button-1>", start_resize)
        resize_grip.bind("<B1-Motion>", do_resize_corner_se)
        resize_grip.bind("<ButtonRelease-1>", stop_resize)

        bottom_edge.bind("<Button-1>", start_resize)
        bottom_edge.bind("<B1-Motion>", do_resize_bottom)
        bottom_edge.bind("<ButtonRelease-1>", stop_resize)

        bl_grip.bind("<Button-1>", start_resize)
        bl_grip.bind("<B1-Motion>", do_resize_corner_sw)
        bl_grip.bind("<ButtonRelease-1>", stop_resize)

        right_edge.bind("<Button-1>", start_resize)
        right_edge.bind("<B1-Motion>", do_resize_right)
        right_edge.bind("<ButtonRelease-1>", stop_resize)

        left_edge.bind("<Button-1>", start_resize)
        left_edge.bind("<B1-Motion>", do_resize_left)
        left_edge.bind("<ButtonRelease-1>", stop_resize)

        top_edge.bind("<Button-1>", start_resize)
        top_edge.bind("<B1-Motion>", do_resize_top)
        top_edge.bind("<ButtonRelease-1>", stop_resize)

        # Quick scaling via Ctrl+MouseWheel or Ctrl + / Ctrl -
        def on_ctrl_scale(delta_w, delta_h):
            cur_w = popup.winfo_width()
            cur_h = popup.winfo_height()
            nw = max(380, min(1400, cur_w + delta_w))
            nh = max(110, min(950, cur_h + delta_h))
            popup.geometry(f"{int(nw)}x{int(nh)}+{popup.winfo_x()}+{popup.winfo_y()}")
            check_size_diff(int(nw), int(nh))

        def on_mousewheel_scale(event):
            if event.state & 0x0004:
                delta = 30 if event.delta > 0 else -30
                on_ctrl_scale(delta, int(delta * 0.5))
                return "break"

        text_widget.bind("<Control-MouseWheel>", on_mousewheel_scale)
        popup.bind("<Control-MouseWheel>", on_mousewheel_scale)

        popup.bind("<Control-plus>", lambda e: on_ctrl_scale(30, 20))
        popup.bind("<Control-equal>", lambda e: on_ctrl_scale(30, 20))
        popup.bind("<Control-minus>", lambda e: on_ctrl_scale(-30, -20))

        check_size_diff(int(calc_w), int(calc_h))

        self._last_popup_pos = pos
        self.current_popup = popup
        self._is_visible = True

    def _insert_structured_questions(
        self,
        text_widget: tk.Text,
        questions: list,
        theme_or_bg: Any,
        font_size: int,
        popup_width: int
    ):
        """Insert questions into text widget with interactive collapsible explanations and dynamic theme colors"""
        if isinstance(theme_or_bg, dict):
            theme = theme_or_bg
        else:
            theme = get_popup_theme(str(theme_or_bg or "#ffffff"))

        is_stealth = theme.get('is_stealth', False)
        bg_color = theme['bg']
        exp_box_bg = theme['exp_box_bg']
        exp_box_fg = theme['exp_box_fg']
        exp_btn_bg = theme['exp_btn_bg']
        exp_btn_fg = theme['exp_btn_fg']
        accent_color = theme['accent']
        header_bg = theme['header_bg']
        text_color = theme['text']

        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)

        for idx, item in enumerate(questions):
            num = getattr(item, 'number', None) or (item.get('number') if isinstance(item, dict) else str(idx + 1))
            q_text = getattr(item, 'question', None) or (item.get('question') if isinstance(item, dict) else '')
            ans_text = getattr(item, 'answer', None) or (item.get('answer') if isinstance(item, dict) else '')
            exp_text = getattr(item, 'explanation', None) or (item.get('explanation') if isinstance(item, dict) else '')
            is_pending = getattr(item, 'is_pending', False) or (item.get('is_pending', False) if isinstance(item, dict) else False)

            if not ans_text or not str(ans_text).strip():
                ans_text = "[Answer not identified]"

            clean_q = re.sub(r'^(?:Câu|Question|Bài|Item)\s*\d+[\s\:\.\-]+', '', str(q_text), flags=re.IGNORECASE).strip()
            disp_q = clean_q if clean_q else q_text

            # Pending/Queue item in history
            if is_pending:
                p_icon = "" if is_stealth else "⏳ "
                text_widget.insert(tk.END, f"{p_icon}Question {num}: {disp_q}\n", "pending_title")
                text_widget.insert(tk.END, f"   → {ans_text}\n\n", "pending_ans")
                continue

            # 1. Question Title
            text_widget.insert(tk.END, f"Question {num}: {disp_q}\n", "question")

            # 2. Answer
            text_widget.insert(tk.END, f"→ Answer: {ans_text}\n", "answer_line")

            # 3. Interactive Collapsible Explanation (HIDDEN BY DEFAULT)
            if exp_text:
                exp_container = tk.Frame(text_widget, bg=bg_color)

                btn_bar = tk.Frame(exp_container, bg=bg_color)
                btn_bar.pack(anchor=tk.W, pady=(2, 2))

                # Hidden box initially (NOT packed)
                exp_box = tk.Label(
                    exp_container,
                    text=f"💡 Explanation:\n{exp_text}",
                    font=("Segoe UI", max(8, font_size - 1), "normal"),
                    fg=exp_box_fg,
                    bg=exp_box_bg,
                    justify=tk.LEFT,
                    wraplength=max(280, popup_width - 60),
                    padx=10,
                    pady=6,
                    bd=0 if is_stealth else 1,
                    relief=tk.FLAT if is_stealth else tk.SOLID
                )

                def make_toggle(box, t_btn):
                    def _toggle(e=None):
                        if box.winfo_ismapped():
                            box.pack_forget()
                            t_btn.config(text="💡 View Explanation", fg=exp_btn_fg, bg=exp_btn_bg)
                        else:
                            box.pack(fill=tk.X, expand=True, pady=(2, 4))
                            t_btn.config(text="🔼 Hide Explanation", fg=accent_color, bg=header_bg)
                    return _toggle

                def make_copy(text, c_btn):
                    def _copy(e=None):
                        self._copy_to_clipboard(text, c_btn)
                    return _copy

                t_btn = tk.Label(
                    btn_bar,
                    text="💡 View Explanation",
                    font=("Segoe UI", 7 if is_stealth else 8, "normal" if is_stealth else "bold"),
                    bg=exp_btn_bg,
                    fg=exp_btn_fg,
                    cursor="hand2",
                    padx=5 if is_stealth else 7,
                    pady=1 if is_stealth else 2,
                    bd=0 if is_stealth else 1,
                    relief=tk.FLAT if is_stealth else tk.SOLID
                )
                t_btn.pack(side=tk.LEFT, padx=(0, 6))
                t_btn.bind("<Button-1>", make_toggle(exp_box, t_btn))

                c_btn = tk.Label(
                    btn_bar,
                    text="📋 Copy Explanation",
                    font=("Segoe UI", 7 if is_stealth else 8, "normal"),
                    bg=exp_btn_bg,
                    fg=text_color,
                    cursor="hand2",
                    padx=5 if is_stealth else 7,
                    pady=1 if is_stealth else 2,
                    bd=0 if is_stealth else 1,
                    relief=tk.FLAT if is_stealth else tk.SOLID
                )
                c_btn.pack(side=tk.LEFT)
                c_btn.bind("<Button-1>", make_copy(exp_text, c_btn))
                c_btn.pack(side=tk.LEFT)
                c_btn.bind("<Button-1>", make_copy(exp_text, c_btn))

                text_widget.window_create(tk.END, window=exp_container)
                text_widget.insert(tk.END, "\n\n")
            else:
                text_widget.insert(tk.END, "\n")

    def _insert_styled_content(self, text_widget: tk.Text, content: str):
        """Parse text lines and insert with appropriate highlight tags"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)

        lines = content.split('\n')
        for line in lines:
            s_line = line.strip()
            if s_line.startswith('Question') or s_line.startswith('Câu ') or s_line.startswith('Q'):
                text_widget.insert(tk.END, line + '\n', "question")
            elif s_line.startswith('→') or s_line.startswith('Answer:') or s_line.startswith('Đáp án:') or 'Answer' in s_line or 'Đáp án' in s_line:
                text_widget.insert(tk.END, line + '\n', "answer_line")
            elif s_line.startswith('❌') or 'Error' in s_line or 'Lỗi' in s_line:
                text_widget.insert(tk.END, line + '\n', "error")
            elif s_line.startswith('💡') or s_line.startswith('Explanation:'):
                text_widget.insert(tk.END, line + '\n', "answer_line")
            else:
                text_widget.insert(tk.END, line + '\n', "normal")

    def is_visible(self) -> bool:
        """Check if popup is currently displayed"""
        if self.current_popup:
            try:
                if self.current_popup.winfo_exists():
                    return self._is_visible
            except Exception:
                pass
            self.current_popup = None
            self._is_visible = False
        return False

    def close(self):
        """Close and cleanup popup"""
        self._closed = True
        self.hide()
