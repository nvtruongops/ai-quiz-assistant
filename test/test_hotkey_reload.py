"""
Test hotkey change functionality
1. Display current hotkeys
2. Change hotkeys in config
3. Reload hotkeys
4. Test new hotkeys
"""

import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
from settings_manager import SettingsManager
from hotkey_listener import HotkeyListener
from logger import Logger


def run_hotkey_reload_test():
    print("=" * 60)
    print("Hotkey Change Test")
    print("=" * 60)

    # Initialize with isolated test config
    logger = Logger()
    test_cfg = os.path.join(_proj_root, "logs", "test_hotkey_reload_cfg.json")
    os.makedirs(os.path.dirname(test_cfg), exist_ok=True)
    if os.path.exists(test_cfg):
        os.remove(test_cfg)

    settings_manager = SettingsManager(config_file=test_cfg)

    # Display current hotkeys
    print("\n📋 Step 1: Current hotkey configuration")
    current_hotkeys = {
        'capture': settings_manager.get('hotkey_capture', 'z'),
        'answers': settings_manager.get('hotkey_answers', 'c'),
        'history': settings_manager.get('hotkey_history', 'h'),
        'reset': settings_manager.get('hotkey_reset', 'r'),
        'settings': settings_manager.get('hotkey_settings', 's'),
        'exit': settings_manager.get('hotkey_exit', 'q'),
    }

    for name, key in current_hotkeys.items():
        print(f"  {name:12} : Alt + {key.upper()}")

    # Test callbacks
    test_results = {
        'capture': False,
        'answers': False,
        'history': False,
        'reset': False,
        'settings': False,
        'exit': False,
    }

    def make_callback(name):
        def callback():
            test_results[name] = True
            print(f"  ✅ {name.upper()} hotkey triggered!")
        return callback

    # Create listener with current hotkeys
    print("\n📋 Step 2: Creating listener with current hotkeys")
    listener = HotkeyListener(
        on_capture_key=make_callback('capture'),
        on_check_key=lambda: None,
        on_hide_key=lambda: None,
        on_exit_key=make_callback('exit'),
        on_clear_logs=lambda: None,
        on_show_answers=make_callback('answers'),
        on_show_detailed_history=make_callback('history'),
        on_reset_answers=make_callback('reset'),
        on_setup=make_callback('settings'),
        settings_manager=settings_manager
    )

    # Verify loaded hotkeys
    print("\n📋 Step 3: Verifying loaded hotkeys in listener")
    print(f"  Listener hotkeys: {listener.hotkeys}")
    assert listener.hotkeys == current_hotkeys, f"Hotkeys not loaded correctly! {listener.hotkeys} != {current_hotkeys}"
    print("  ✅ Hotkeys loaded correctly")

    # Change hotkeys in settings
    print("\n📋 Step 4: Changing hotkeys in test config")
    new_hotkeys = {
        'hotkey_capture': 'a',
        'hotkey_answers': 'e',
        'hotkey_history': 'u',
        'hotkey_reset': 'k',
        'hotkey_settings': 'd',
        'hotkey_exit': 'x',
    }

    # Update settings
    for key, value in new_hotkeys.items():
        settings_manager.set(key, value)

    print("  New hotkeys set:")
    for key, value in new_hotkeys.items():
        print(f"    {key:20} : Alt + {value.upper()}")

    # Reload hotkeys in listener
    print("\n📋 Step 5: Reloading hotkeys in listener")
    listener.reload_hotkeys()

    expected_new = {
        'capture': 'a',
        'answers': 'e',
        'history': 'u',
        'reset': 'k',
        'settings': 'd',
        'exit': 'x',
    }

    print(f"  Listener hotkeys after reload: {listener.hotkeys}")
    assert listener.hotkeys == expected_new, f"Hotkeys not reloaded! Expected {expected_new}, got {listener.hotkeys}"
    print("  ✅ Hotkeys reloaded successfully!")

    # Clean up
    if os.path.exists(test_cfg):
        os.remove(test_cfg)

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(run_hotkey_reload_test())
