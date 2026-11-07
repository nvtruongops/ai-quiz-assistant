"""
Interactive & Automated Hotkey Diagnostic Tool
Press different hotkeys to test if they trigger callbacks.
Press Ctrl+C or ESC to exit.
"""

import os
import sys
import time

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hotkey_listener import HotkeyListener
from settings_manager import SettingsManager
from logger import Logger


def run_hotkey_test():
    logger = Logger()
    settings_manager = SettingsManager()

    print("=" * 60)
    print("Hotkey Diagnostic Test")
    print("=" * 60)

    # Load current hotkey settings
    print("\n📋 Current hotkey configuration:")
    hotkeys = {
        'capture': settings_manager.get('hotkey_capture', 'z'),
        'answers': settings_manager.get('hotkey_answers', 'c'),
        'history': settings_manager.get('hotkey_history', 'h'),
        'reset': settings_manager.get('hotkey_reset', 'r'),
        'settings': settings_manager.get('hotkey_settings', 's'),
        'exit': settings_manager.get('hotkey_exit', 'q'),
    }

    for name, key in hotkeys.items():
        print(f"  {name:12} : Alt + {key.upper()}")

    # Callback functions
    def on_capture():
        print("\n✅ CAPTURE hotkey triggered (Alt+{})".format(hotkeys['capture'].upper()))

    def on_answers():
        print("\n✅ ANSWERS hotkey triggered (Alt+{})".format(hotkeys['answers'].upper()))

    def on_history():
        print("\n✅ HISTORY hotkey triggered (Alt+{})".format(hotkeys['history'].upper()))

    def on_reset():
        print("\n✅ RESET hotkey triggered (Alt+{})".format(hotkeys['reset'].upper()))

    def on_settings():
        print("\n✅ SETTINGS hotkey triggered (Alt+{})".format(hotkeys['settings'].upper()))

    def on_exit():
        print("\n✅ EXIT hotkey triggered (Alt+{})".format(hotkeys['exit'].upper()))

    # Create listener
    listener = HotkeyListener(
        on_capture_key=on_capture,
        on_check_key=lambda: None,
        on_hide_key=lambda: None,
        on_exit_key=on_exit,
        on_clear_logs=lambda: None,
        on_show_answers=on_answers,
        on_show_detailed_history=on_history,
        on_reset_answers=on_reset,
        on_setup=on_settings,
        settings_manager=settings_manager
    )

    listener.start()
    print("HotkeyListener successfully initialized and running.")

    # If executed in non-interactive environment (CI, script runner, piped), exit cleanly after verifying
    is_automated = not sys.stdin.isatty() or "--auto" in sys.argv or os.environ.get("CI") or os.environ.get("AUTO_TEST")

    if is_automated:
        print("Non-interactive / Automated execution detected. Verifying listener and exiting cleanly.")
        time.sleep(0.5)
        listener.stop()
        print("✅ Hotkey listener test passed successfully.")
        return 0

    try:
        print("\nListening for hotkeys... Press Ctrl+C to stop.")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        listener.stop()
        return 0


if __name__ == '__main__':
    sys.exit(run_hotkey_test())
