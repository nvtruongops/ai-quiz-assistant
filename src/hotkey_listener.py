"""
Hotkey Listener Module
Listen and handle global hotkeys and secondary mouse button
"""

from pynput import keyboard, mouse
from typing import Callable, Optional
import logging


class HotkeyListener:
    """Listen to global hotkeys and secondary mouse button, call corresponding callbacks"""
    
    # Default hotkeys
    DEFAULT_HOTKEYS = {
        'capture': 'z',
        'results': 'x',
        'answers': 'c',
        'reset': 'r',
        'settings': 's',
    }
    
    def __init__(self, 
                 on_capture_key: Callable[[], None],
                 on_check_key: Callable[[], None],
                 on_hide_key: Callable[[], None],
                 on_exit_key: Callable[[], None],
                 on_clear_logs: Callable[[], None] = None,
                 on_show_answers: Callable[[], None] = None,
                 on_reset_answers: Callable[[], None] = None,
                 on_setup: Callable[[], None] = None,
                 settings_manager = None):
        """
        Initialize HotkeyListener
        
        Args:
            on_capture_key: Callback when MIDDLE + scroll UP or Alt+Z - capture screen
            on_check_key: Callback when MIDDLE + scroll DOWN or Alt+X - toggle result popup
            on_hide_key: Callback when MIDDLE + scroll DOWN twice or Alt+X - hide popup
            on_exit_key: Callback when F12 pressed - exit program
            on_clear_logs: Callback when Delete pressed - clear logs and answers
            on_show_answers: Callback when Alt+C pressed - toggle answers popup
            on_reset_answers: Callback when Alt+R pressed - reset answer history
            on_setup: Callback when Alt+S pressed - show setup dialog
            settings_manager: SettingsManager instance for custom hotkeys
        """
        self.on_capture_key = on_capture_key
        self.on_check_key = on_check_key
        self.on_hide_key = on_hide_key
        self.on_exit_key = on_exit_key
        self.on_clear_logs = on_clear_logs
        self.on_show_answers = on_show_answers
        self.on_reset_answers = on_reset_answers
        self.on_setup = on_setup
        self.settings_manager = settings_manager
        
        # Load custom hotkeys from settings
        self.hotkeys = self._load_hotkeys()
        
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        self.logger = logging.getLogger(__name__)
        
        # Toggle state for check/hide button
        self.popup_visible = False
        
        # Middle button state
        self.middle_button_pressed = False
        
        # Alt key state
        self.alt_pressed = False
        
        # Debounce to avoid multiple triggers
        self._last_hotkey_time = {}
        self._hotkey_cooldown = 0.5  # 500ms cooldown
    
    def _load_hotkeys(self) -> dict:
        """Load hotkeys from settings or use defaults"""
        hotkeys = self.DEFAULT_HOTKEYS.copy()
        if self.settings_manager:
            hotkeys['capture'] = self.settings_manager.get('hotkey_capture', 'z')
            hotkeys['results'] = self.settings_manager.get('hotkey_results', 'x')
            hotkeys['answers'] = self.settings_manager.get('hotkey_answers', 'c')
            hotkeys['reset'] = self.settings_manager.get('hotkey_reset', 'r')
            hotkeys['settings'] = self.settings_manager.get('hotkey_settings', 's')
        return hotkeys
    
    def reload_hotkeys(self):
        """Reload hotkeys from settings (call after settings change)"""
        self.hotkeys = self._load_hotkeys()
        self.logger.info(f"Hotkeys reloaded: {self.hotkeys}")
    
    def start(self):
        """
        Start listening to hotkeys and mouse buttons
        Listeners run in separate threads
        """
        # Start keyboard listener
        if self.keyboard_listener and self.keyboard_listener.is_alive():
            self.logger.warning("Keyboard listener is already running")
        else:
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.keyboard_listener.start()
            self.logger.info("Keyboard listener started")
        
        # Start mouse listener
        if self.mouse_listener and self.mouse_listener.is_alive():
            self.logger.warning("Mouse listener is already running")
        else:
            self.mouse_listener = mouse.Listener(
                on_click=self.on_mouse_click,
                on_scroll=self.on_mouse_scroll
            )
            self.mouse_listener.start()
            self.logger.info("Mouse listener started")
    
    def stop(self):
        """
        Stop listening to hotkeys and mouse buttons
        """
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            self.logger.info("Keyboard listener stopped")
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
            self.logger.info("Mouse listener stopped")
    
    def on_mouse_click(self, x, y, button, pressed):
        """
        Handle mouse click event - track middle button state
        
        Args:
            x, y: Mouse coordinates
            button: Mouse button pressed
            pressed: True if pressed, False if released
        """
        try:
            if button == mouse.Button.middle:
                self.middle_button_pressed = pressed
                if pressed:
                    self.logger.debug("Middle button pressed - ready for scroll")
                else:
                    self.logger.debug("Middle button released")
        except Exception as e:
            self.logger.error(f"Error handling mouse click: {e}", exc_info=True)
    
    def on_mouse_scroll(self, x, y, dx, dy):
        """
        Handle mouse scroll event (only when middle button is held)
        - MIDDLE + Scroll UP (dy > 0): Capture screen (Alt+Z)
        - MIDDLE + Scroll DOWN (dy < 0): Show answers (Alt+C)
        
        Args:
            x, y: Mouse coordinates
            dx: Horizontal scroll (not used)
            dy: Vertical scroll (>0 = up, <0 = down)
        """
        try:
            # Only process when middle button is held
            if not self.middle_button_pressed:
                return
            
            if dy > 0:
                # MIDDLE + Scroll UP - Capture screen
                self.logger.info("MIDDLE + Scroll UP - Capture screenshot")
                self.on_capture_key()
                
            elif dy < 0:
                # MIDDLE + Scroll DOWN - Show answers
                self.logger.info("MIDDLE + Scroll DOWN - Show answers")
                if self.on_show_answers:
                    self.on_show_answers()
        
        except Exception as e:
            self.logger.error(f"Error handling mouse scroll: {e}", exc_info=True)
    
    def on_key_press(self, key):
        """
        Handle key press event
        Delete: Clear logs
        F12: Exit program
        
        Args:
            key: Key object from pynput
        """
        try:
            # Track Alt key
            if isinstance(key, keyboard.Key):
                if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                    self.alt_pressed = True
                elif key == keyboard.Key.delete:
                    self.logger.info("Clear logs hotkey (Delete) pressed")
                    if self.on_clear_logs:
                        self.on_clear_logs()

            
            # Handle Alt + custom hotkeys with debounce
            elif hasattr(key, 'char') and key.char:
                # Handle ` (backtick) key for exit
                if key.char == '`':
                    self.logger.info("Exit hotkey (`) pressed")
                    self.on_exit_key()
                    return
                
                if self.alt_pressed:
                    import time
                    current_time = time.time()
                    key_char = key.char.lower()
                    
                    # Check debounce
                    last_time = self._last_hotkey_time.get(key_char, 0)
                    if current_time - last_time < self._hotkey_cooldown:
                        self.logger.debug(f"Hotkey {key_char} ignored (debounce)")
                        return
                    
                    # Update last time
                    self._last_hotkey_time[key_char] = current_time
                    
                    # Check against custom hotkeys
                    if key_char == self.hotkeys['capture']:
                        self.logger.info(f"Capture hotkey (Alt+{key_char.upper()}) pressed")
                        self.on_capture_key()
                    elif key_char == self.hotkeys['results']:
                        self.logger.info(f"Toggle result popup hotkey (Alt+{key_char.upper()}) pressed")
                        self.on_check_key()
                    elif key_char == self.hotkeys['answers']:
                        self.logger.info(f"Toggle answers popup hotkey (Alt+{key_char.upper()}) pressed")
                        if self.on_show_answers:
                            self.on_show_answers()
                    elif key_char == self.hotkeys['reset']:
                        self.logger.info(f"Reset answers hotkey (Alt+{key_char.upper()}) pressed")
                        if self.on_reset_answers:
                            self.on_reset_answers()
                    elif key_char == self.hotkeys['settings']:
                        self.logger.info(f"Setup hotkey (Alt+{key_char.upper()}) pressed")
                        if self.on_setup:
                            self.on_setup()
        
        except Exception as e:
            self.logger.error(f"Error handling key press: {e}", exc_info=True)
    
    def on_key_release(self, key):
        """Handle key release event"""
        try:
            if isinstance(key, keyboard.Key):
                if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                    self.alt_pressed = False
        except Exception as e:
            self.logger.error(f"Error handling key release: {e}", exc_info=True)
