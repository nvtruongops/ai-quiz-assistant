"""
Hotkey Listener Module
Listen and handle global hotkeys and secondary mouse button
"""

from pynput import keyboard, mouse
from typing import Callable, Optional
import logging
import time


class HotkeyListener:
    """Listen to global hotkeys and secondary mouse button, call corresponding callbacks"""

    # Default hotkeys
    DEFAULT_HOTKEYS = {
        'capture': 'z',
        'answers': 'c',
        'history': 'h',
        'reset': 'r',
        'settings': 's',
        'exit': 'q',
    }

    def __init__(
        self,
        on_capture_key: Callable[[], None],
        on_hide_key: Callable[[], None] = None,
        on_exit_key: Callable[[], None] = None,
        on_clear_logs: Callable[[], None] = None,
        on_show_answers: Callable[[], None] = None,
        on_show_detailed_history: Callable[[], None] = None,
        on_reset_answers: Callable[[], None] = None,
        on_setup: Callable[[], None] = None,
        settings_manager=None,
        on_check_key: Optional[Callable] = None,
        **kwargs
    ):
        self.on_capture_key = on_capture_key
        self.on_hide_key = on_hide_key
        self.on_exit_key = on_exit_key
        self.on_clear_logs = on_clear_logs
        self.on_show_answers = on_show_answers
        self.on_show_detailed_history = on_show_detailed_history
        self.on_reset_answers = on_reset_answers
        self.on_setup = on_setup
        self.settings_manager = settings_manager

        self.hotkeys = self._load_hotkeys()
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        self.logger = logging.getLogger(__name__)

        self.popup_visible = False
        self.middle_button_pressed = False
        self.alt_pressed = False
        self._alt_press_time = 0.0

        self._last_hotkey_time = {}
        self._hotkey_cooldown = 0.4  # seconds

    def _load_hotkeys(self) -> dict:
        """Load hotkeys from settings or use defaults, strictly normalized to lowercase"""
        hotkeys = self.DEFAULT_HOTKEYS.copy()
        if self.settings_manager:
            for k in ('capture', 'answers', 'history', 'reset', 'settings', 'exit'):
                raw = self.settings_manager.get(f'hotkey_{k}', self.DEFAULT_HOTKEYS.get(k, ''))
                hotkeys[k] = str(raw).strip().lower() if raw else self.DEFAULT_HOTKEYS.get(k, '')
        return hotkeys

    def reload_hotkeys(self):
        """Reload hotkeys from settings (call after settings change)"""
        self.hotkeys = self._load_hotkeys()
        self.logger.info(f"Hotkeys reloaded: {self.hotkeys}")

    def start(self):
        """Start listening to hotkeys and mouse buttons"""
        if not self.keyboard_listener or not self.keyboard_listener.is_alive():
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.keyboard_listener.start()
            self.logger.info("Keyboard listener started")

        if not self.mouse_listener or not self.mouse_listener.is_alive():
            self.mouse_listener = mouse.Listener(
                on_click=self.on_mouse_click,
                on_scroll=self.on_mouse_scroll
            )
            self.mouse_listener.start()
            self.logger.info("Mouse listener started")

    def stop(self):
        """Stop listening to hotkeys and mouse buttons"""
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
            self.keyboard_listener = None

        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
            self.mouse_listener = None

    def on_mouse_click(self, x, y, button, pressed):
        """Track middle button state"""
        try:
            if button == mouse.Button.middle:
                self.middle_button_pressed = pressed
        except Exception:
            pass

    def on_mouse_scroll(self, x, y, dx, dy):
        """Handle scroll while middle mouse button is held (if enabled in settings)"""
        try:
            if not self.middle_button_pressed:
                return

            if self.settings_manager and not self.settings_manager.get('enable_mouse_gestures', True):
                return

            if dy > 0:
                self.logger.info("Middle + Scroll UP -> Capture screenshot")
                self.on_capture_key()
            elif dy < 0:
                self.logger.info("Middle + Scroll DOWN -> Show answers")
                if self.on_show_answers:
                    self.on_show_answers()
        except Exception as e:
            self.logger.error(f"Error handling mouse scroll: {e}")

    def on_key_press(self, key):
        """Handle keyboard key down with full Virtual Key and IME/Unikey support"""
        try:
            # 1. Track Alt key down
            if isinstance(key, keyboard.Key):
                if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                    self.alt_pressed = True
                    self._alt_press_time = time.time()

            # 2. Resolve character from either key.char or key.vk (critical for Windows Alt combinations)
            char = None
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
            elif hasattr(key, 'vk') and key.vk:
                if 65 <= key.vk <= 90:  # A-Z
                    char = chr(key.vk).lower()
                elif 48 <= key.vk <= 57:  # 0-9
                    char = chr(key.vk)

            if not char:
                return

            # 3. Check Alt state (software flag + Windows hardware API check)
            is_alt = self.alt_pressed
            if not is_alt:
                try:
                    import ctypes
                    is_alt = bool(ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000)
                except Exception:
                    pass

            # Stale Alt timeout check
            now = time.time()
            if self.alt_pressed and (now - self._alt_press_time > 3.0):
                self.alt_pressed = False
                is_alt = False

            if not is_alt:
                return

            # 4. Route Alt combinations strictly per configuration (NO hardcoded fallback keys)
            cap_key = self.hotkeys.get('capture', 'z')
            ans_key = self.hotkeys.get('answers', 'c')
            his_key = self.hotkeys.get('history', 'h')
            rst_key = self.hotkeys.get('reset', 'r')
            set_key = self.hotkeys.get('settings', 's')
            ext_key = self.hotkeys.get('exit', 'q')

            cooldown = 0.2 if char == cap_key else self._hotkey_cooldown
            last_time = self._last_hotkey_time.get(char, 0.0)
            if now - last_time < cooldown:
                return
            self._last_hotkey_time[char] = now

            if char == cap_key:
                self.logger.info(f"Capture hotkey (Alt+{char.upper()}) pressed")
                self.on_capture_key()
            elif char == ans_key:
                self.logger.info(f"Show answers hotkey (Alt+{char.upper()}) pressed")
                if self.on_show_answers:
                    self.on_show_answers()
            elif char == his_key:
                self.logger.info(f"Show detailed history hotkey (Alt+{char.upper()}) pressed")
                if self.on_show_detailed_history:
                    self.on_show_detailed_history()
            elif char == rst_key:
                self.logger.info(f"Reset answers hotkey (Alt+{char.upper()}) pressed")
                if self.on_reset_answers:
                    self.on_reset_answers()
            elif char == set_key:
                self.logger.info(f"Settings hotkey (Alt+{char.upper()}) pressed")
                if self.on_setup:
                    self.on_setup()
            elif char == ext_key:
                self.logger.info(f"Exit application hotkey (Alt+{char.upper()}) pressed")
                if self.on_exit_key:
                    self.on_exit_key()

        except Exception as e:
            self.logger.error(f"Error handling key press: {e}")

    def on_key_release(self, key):
        """Handle keyboard key release"""
        try:
            if isinstance(key, keyboard.Key):
                if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                    self.alt_pressed = False
        except Exception:
            pass
