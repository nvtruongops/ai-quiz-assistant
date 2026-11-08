"""
System Tray Module
Manages system tray icon, notification popups, and quick action context menu.
"""

import os
import subprocess
import pystray
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from typing import Optional

_src_dir = os.path.dirname(os.path.abspath(__file__))
try:
    from path_utils import get_app_dir, get_resource_path
    PROJECT_ROOT = get_app_dir()
except ImportError:
    try:
        from src.path_utils import get_app_dir, get_resource_path
        PROJECT_ROOT = get_app_dir()
    except ImportError:
        PROJECT_ROOT = os.path.dirname(_src_dir)
        def get_resource_path(p=""): return os.path.join(PROJECT_ROOT, p)

try:
    from constants import GITHUB_REPO_URL, DOCUMENTATION_URL, GITHUB_ISSUES_URL
except ImportError:
    try:
        from src.constants import GITHUB_REPO_URL, DOCUMENTATION_URL, GITHUB_ISSUES_URL
    except ImportError:
        GITHUB_REPO_URL = "https://github.com/nvtruongops/ai-quiz-assistant"
        DOCUMENTATION_URL = "https://github.com/nvtruongops/ai-quiz-assistant#readme"
        GITHUB_ISSUES_URL = "https://github.com/nvtruongops/ai-quiz-assistant/issues"


def launch_file_explorer(path: str) -> bool:
    """Open folder in Windows File Explorer using multiple robust fallback methods"""
    try:
        if not os.path.isabs(path):
            target_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
        else:
            target_path = os.path.normpath(path)
        os.makedirs(target_path, exist_ok=True)

        # Method 1: Direct explorer.exe subprocess (opens active window in foreground)
        try:
            subprocess.Popen(['explorer.exe', target_path])
            return True
        except Exception:
            pass

        # Method 2: ShellExecuteW with explorer.exe and SW_SHOWNORMAL (1)
        try:
            import ctypes
            res = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", target_path, None, 1)
            if res > 32:
                return True
        except Exception:
            pass

        # Method 3: os.startfile
        try:
            os.startfile(target_path)
            return True
        except Exception:
            pass

        # Method 4: cmd start
        try:
            subprocess.Popen(f'start "" "{target_path}"', shell=True)
            return True
        except Exception:
            pass

        return False
    except Exception:
        return False


class SystemTray:
    """Manages system tray icon and context menu"""

    def __init__(self, app):
        """
        Initialize SystemTray
        Args:
            app: QuizAssistantApp instance
        """
        self.app = app
        self.icon: Optional[pystray.Icon] = None
        self._running = False

    def create_icon(self) -> Image.Image:
        """
        Load assets/icon.png or icon.ico if present, otherwise generate modern PIL icon
        """
        png_path = get_resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(png_path):
            try:
                img = Image.open(png_path).convert('RGBA')
                return img.resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

        ico_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if not os.path.exists(ico_path):
            ico_path = get_resource_path("icon.ico")
        if os.path.exists(ico_path):
            try:
                img = Image.open(ico_path)
                return img
            except Exception:
                pass

        # Fallback generated icon (Obsidian squircle with cyan accent)
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((2, 2, 61, 61), radius=14, fill=(15, 23, 42, 255), outline=(2, 132, 199, 255), width=2)

        try:
            font = ImageFont.truetype("segoeui.ttf", 32)
        except Exception:
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except Exception:
                font = ImageFont.load_default()

        text = "Q"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = 24, 24

        x = (width - tw) // 2
        y = (height - th) // 2 - 2
        draw.text((x, y), text, fill=(6, 182, 212, 255), font=font)
        return image

    def create_menu(self) -> pystray.Menu:
        """Create context menu with quick actions"""
        provider_name = "Gemini"
        mode_name = "Multiple Choice"

        if hasattr(self.app, 'config_manager'):
            provider = self.app.config_manager.get('API_PROVIDER', 'gemini')
            provider_name = "Google Gemini" if provider == 'gemini' else "Custom Local"

        hk_c = "Z"
        hk_f = "F"
        hk_ans = "C"
        hk_h = "H"
        hk_s = "S"

        if hasattr(self.app, 'settings_manager'):
            mode = self.app.settings_manager.get('question_mode', 'multiple_choice')
            if mode == 'essay':
                mode_name = "Essay / Open-ended"
            elif mode == 'multiple_choice_explanation':
                mode_name = "MC + Explanation"
            else:
                mode_name = "Multiple Choice"

            hk_c = self.app.settings_manager.get('hotkey_capture', 'z').upper()
            hk_f = self.app.settings_manager.get('hotkey_autofill', 'x').upper()
            hk_ans = self.app.settings_manager.get('hotkey_answers', 'c').upper()
            hk_h = self.app.settings_manager.get('hotkey_history', 'h').upper()
            hk_s = self.app.settings_manager.get('hotkey_settings', 's').upper()

        def trigger(callback):
            def wrapper(icon=None, item=None):
                try:
                    callback()
                except Exception as e:
                    if hasattr(self.app, 'logger'):
                        self.app.logger.error(f"Tray action error: {e}")
            return wrapper

        def open_folder(path):
            def wrapper(icon=None, item=None):
                if hasattr(self.app, 'logger'):
                    self.app.logger.info(f"Opening folder via system tray: {path}")
                launch_file_explorer(path)
            return wrapper

        def open_link(url):
            def wrapper(icon=None, item=None):
                try:
                    import webbrowser
                    webbrowser.open_new_tab(url)
                except Exception as e:
                    if hasattr(self.app, 'logger'):
                        self.app.logger.error(f"Failed to open url {url}: {e}")
            return wrapper

        def toggle_provider(icon=None, item=None):
            if not hasattr(self.app, 'settings_manager') or not hasattr(self.app, 'config_manager'):
                return
            cur = self.app.config_manager.get('API_PROVIDER', 'gemini')
            nxt = 'custom' if cur == 'gemini' else 'gemini'
            self.app.settings_manager.set('api_provider', nxt)
            self.app.config_manager.config['API_PROVIDER'] = nxt
            os.environ['API_PROVIDER'] = nxt
            self.app._initialize_ai_client()
            p_display = "Google Gemini" if nxt == 'gemini' else "Custom Local"
            self.show_notification("AI Quiz Assistant", f"Switched provider to: {p_display}")
            if self.icon:
                self.icon.menu = self.create_menu()

        menu_items = [
            pystray.MenuItem("🟢 Status: Active", lambda: None, enabled=False),
            pystray.MenuItem(f"🤖 Provider: {provider_name} (Click to switch)", toggle_provider),
            pystray.MenuItem(f"📝 Mode: {mode_name}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"📸 Capture Screen (Alt+{hk_c})", trigger(self.app.on_capture_hotkey)),
            pystray.MenuItem(f"⚡ Auto-Fill Answers (Alt+{hk_f})", trigger(getattr(self.app, 'on_autofill_hotkey', lambda: None))),
            pystray.MenuItem(f"🎯 Show Latest Result (Alt+{hk_ans})", trigger(self.app.on_show_answers_hotkey)),
            pystray.MenuItem(f"📖 Detailed History (Alt+{hk_h})", trigger(self.app.on_show_detailed_history_hotkey)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"⚙️ Settings (Alt+{hk_s})", trigger(self.app.on_setup_hotkey)),
            pystray.MenuItem("📁 Open Logs Folder", open_folder("logs")),
            pystray.MenuItem("📸 Open Screenshots Folder", open_folder("logs/screenshots")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🌐 GitHub Repository", open_link(GITHUB_REPO_URL)),
            pystray.MenuItem("📖 Documentation", open_link(DOCUMENTATION_URL)),
            pystray.MenuItem("💬 Report Issue", open_link(GITHUB_ISSUES_URL)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit Application", self.on_quit)
        ]

        return pystray.Menu(*menu_items)

    def on_quit(self, icon=None, item=None):
        """Handle Quit menu click"""
        if self.icon:
            self.icon.stop()
        if self.app:
            self.app.stop()

    def show_notification(self, title: str, message: str):
        """Show Windows tray notification"""
        if self.icon and self.icon.visible:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def run(self):
        """Run system tray event loop in background thread"""
        if self._running:
            return
        self._running = True

        icon_image = self.create_icon()
        menu = self.create_menu()

        self.icon = pystray.Icon(
            "QuizAssistant",
            icon_image,
            "AI Quiz Assistant",
            menu
        )
        self.icon.run()

    def start(self):
        """Start system tray thread"""
        if not self._running:
            thread = Thread(target=self.run, daemon=True, name="SystemTrayThread")
            thread.start()

    def stop(self):
        """Stop system tray"""
        if self.icon:
            self.icon.stop()
        self._running = False
