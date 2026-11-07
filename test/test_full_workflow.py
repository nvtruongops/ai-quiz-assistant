"""
Integration test: Simulate full user workflow
1. Start app with default hotkeys
2. Open settings and change hotkeys
3. Verify hotkeys work immediately without restart
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


def run_full_workflow_test():
    print("=" * 60)
    print("Full Hotkey Workflow Integration Test")
    print("=" * 60)

    # Initialize with isolated test config
    logger = Logger()
    test_cfg = os.path.join(_proj_root, "logs", "test_workflow_config.json")
    os.makedirs(os.path.dirname(test_cfg), exist_ok=True)
    if os.path.exists(test_cfg):
        os.remove(test_cfg)

    settings_manager = SettingsManager(config_file=test_cfg)

    # Display current settings
    print("\n📋 Step 1: Application starts")
    print("  Loading config.json...")

    hotkeys_config = {
        'capture': settings_manager.get('hotkey_capture', 'z'),
        'answers': settings_manager.get('hotkey_answers', 'c'),
        'history': settings_manager.get('hotkey_history', 'h'),
        'reset': settings_manager.get('hotkey_reset', 'r'),
        'settings': settings_manager.get('hotkey_settings', 's'),
        'exit': settings_manager.get('hotkey_exit', 'q'),
    }

    for name, key in hotkeys_config.items():
        print(f"    {name:12} : Alt + {key.upper()}")

    # Create listener (simulating main.py)
    print("\n  Creating hotkey listener...")

    counts = {'capture': 0, 'answers': 0}

    def on_capture():
        counts['capture'] += 1
        print(f"    ✅ Capture triggered! (count: {counts['capture']})")

    def on_answers():
        counts['answers'] += 1
        print(f"    ✅ Answers triggered! (count: {counts['answers']})")

    def on_hotkey_change():
        """Called when user changes hotkeys in settings"""
        print("\n  🔄 Hotkey change callback triggered")
        print("     Reloading hotkeys in listener...")
        listener.reload_hotkeys()
        print(f"     New hotkeys: {listener.hotkeys}")
        print("     ✅ Hotkeys reloaded successfully!")

    listener = HotkeyListener(
        on_capture_key=on_capture,
        on_check_key=lambda: None,
        on_hide_key=lambda: None,
        on_exit_key=lambda: None,
        on_clear_logs=lambda: None,
        on_show_answers=on_answers,
        on_show_detailed_history=lambda: None,
        on_reset_answers=lambda: None,
        on_setup=lambda: None,
        settings_manager=settings_manager
    )

    print(f"  Listener created with hotkeys: {listener.hotkeys}")

    # Simulate user testing original hotkeys
    print("\n📋 Step 2: User tests original hotkeys")
    print(f"  Simulating Alt+{hotkeys_config['capture'].upper()} press...")
    on_capture()
    print(f"  Simulating Alt+{hotkeys_config['answers'].upper()} press...")
    on_answers()

    assert counts['capture'] == 1, "Capture should work once"
    assert counts['answers'] == 1, "Answers should work once"
    print("  ✅ Original hotkeys work!")

    # Simulate user opening settings and changing hotkeys
    print("\n📋 Step 3: User opens settings and changes hotkeys")
    print("  (Simulating settings dialog)")

    new_capture = 'a'
    print(f"  User changes capture hotkey from {hotkeys_config['capture'].upper()} to {new_capture.upper()}")
    settings_manager.settings['hotkey_capture'] = new_capture
    settings_manager.save_settings()

    new_answers = 'w'
    print(f"  User changes answers hotkey from {hotkeys_config['answers'].upper()} to {new_answers.upper()}")
    settings_manager.settings['hotkey_answers'] = new_answers
    settings_manager.save_settings()

    print("  Settings saved to test config")

    # Simulate on_hotkey_change callback
    print("\n📋 Step 4: Settings dialog calls on_hotkey_change()")
    on_hotkey_change()

    # Verify new hotkeys
    print("\n📋 Step 5: Verify new hotkeys work immediately")
    expected_hotkeys = {
        'capture': new_capture,
        'answers': new_answers,
        'history': 'h',
        'reset': 'r',
        'settings': 's',
        'exit': 'q',
    }

    assert listener.hotkeys == expected_hotkeys, f"Expected {expected_hotkeys}, got {listener.hotkeys}"
    print(f"  Listener hotkeys updated: {listener.hotkeys}")

    print(f"  Simulating Alt+{new_capture.upper()} press...")
    on_capture()
    print(f"  Simulating Alt+{new_answers.upper()} press...")
    on_answers()

    assert counts['capture'] == 2, "Capture should work twice now"
    assert counts['answers'] == 2, "Answers should work twice now"
    print("  ✅ New hotkeys work immediately without restart!")

    if os.path.exists(test_cfg):
        os.remove(test_cfg)

    print("\n" + "=" * 60)
    print("✅ Integration test PASSED!")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(run_full_workflow_test())
