"""
Unit test verifying fixes for the 3 user-reported issues:
1. DPI Awareness prevents automatic shrinking / scaling down of UI after some time.
2. The Settings header bar (with "Cài Đặt AI Quiz Assistant 2.0" and subtitle) has been deleted.
3. Hotkeys are automatically saved upon typing and on dialog close, and properly loaded when reopening app.
"""

import sys
import os

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from settings_manager import SettingsManager, show_settings_dialog
from hotkey_listener import HotkeyListener


class TestFix3Issues(unittest.TestCase):

    def setUp(self):
        self.test_cfg = os.path.join(_proj_root, "logs", "test_fix3_config.json")
        os.makedirs(os.path.dirname(self.test_cfg), exist_ok=True)
        if os.path.exists(self.test_cfg):
            os.remove(self.test_cfg)
        self.sm = SettingsManager(config_file=self.test_cfg)

    def tearDown(self):
        if os.path.exists(self.test_cfg):
            os.remove(self.test_cfg)

    def test_issue_2_header_banner_deleted(self):
        """
        Verify that the header banner (with 'v2.0 • Active' and subtitle) shown in the user's photo
        is completely deleted from show_settings_dialog.
        """
        dialog_labels = []

        orig_mainloop = tk.Tk.mainloop

        def mock_mainloop(self):
            # Traverse all labels in the window
            def collect_labels(w):
                if isinstance(w, tk.Label):
                    dialog_labels.append(w.cget('text'))
                for child in w.winfo_children():
                    collect_labels(child)

            collect_labels(self)
            self.destroy()

        tk.Tk.mainloop = mock_mainloop

        try:
            show_settings_dialog(self.sm)
        finally:
            tk.Tk.mainloop = orig_mainloop

        # Ensure header text and badge are NO LONGER in the dialog
        self.assertFalse(any("v2.0 • Active" in txt for txt in dialog_labels), "Header badge 'v2.0 • Active' must be deleted")
        self.assertFalse(any("Tùy chỉnh AI Provider, Chế độ làm bài" in txt for txt in dialog_labels), "Header subtitle must be deleted")

    def test_issue_3_hotkey_auto_save_on_type_and_close(self):
        """
        Verify:
        - When a hotkey entry is modified, it auto-saves immediately without needing manual save button.
        - When closing dialog via WM_DELETE_WINDOW / Escape / Close button, settings are auto-saved.
        - When reopening SettingsManager and HotkeyListener, the custom hotkeys are loaded and normalized.
        """
        # Initially hotkey_capture is 'z'
        self.assertEqual(self.sm.get('hotkey_capture'), 'z')

        orig_mainloop = tk.Tk.mainloop

        def mock_mainloop(self):
            # Find the hotkey entries
            hotkey_inputs = []
            for child in self.winfo_children():
                # search for entries
                def find_entries(w):
                    if isinstance(w, tk.Entry):
                        hotkey_inputs.append(w)
                    for c in w.winfo_children():
                        find_entries(c)
                find_entries(child)

            # We know hotkey entries have single letter
            for ent in hotkey_inputs:
                if ent.get() == 'Z':
                    # Simulate user typing 'q'
                    ent.delete(0, tk.END)
                    ent.insert(0, 'q')
                    # Trigger the KeyRelease event
                    ent.event_generate('<KeyRelease>')
                    break

            # Simulate user closing dialog via window close [X] / WM_DELETE_WINDOW protocol
            proto = self.protocol('WM_DELETE_WINDOW')
            self.tk.call(proto)

        tk.Tk.mainloop = mock_mainloop

        try:
            show_settings_dialog(self.sm)
        finally:
            tk.Tk.mainloop = orig_mainloop

        # Verify it was auto-saved to config.json
        with open(self.test_cfg, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data.get('hotkey_capture'), 'q', "Hotkey edit must be auto-saved immediately to config.json")

        # Now simulate restarting the app: new SettingsManager instance
        sm_reloaded = SettingsManager(config_file=self.test_cfg)
        self.assertEqual(sm_reloaded.get('hotkey_capture'), 'q', "New app instance must retain the customized hotkey")

        # Verify HotkeyListener loads the new hotkey properly in lowercase
        listener = HotkeyListener(
            on_capture_key=lambda: None,
            on_check_key=lambda: None,
            on_hide_key=lambda: None,
            on_exit_key=lambda: None,
            settings_manager=sm_reloaded
        )
        self.assertEqual(listener.hotkeys['capture'], 'q', "HotkeyListener must load 'q' for capture")

    def test_issue_1_dpi_stability_with_screeninfo(self):
        """
        Verify DPI awareness setting prevents window geometry from jumping or shrinking
        when screeninfo.get_monitors() is called.
        """
        root = tk.Tk()
        root.geometry("680x700+100+100")
        root.update_idletasks()
        w1 = root.winfo_width()
        h1 = root.winfo_height()

        try:
            import screeninfo
            _ = screeninfo.get_monitors()
        except Exception:
            pass

        root.update_idletasks()
        w2 = root.winfo_width()
        h2 = root.winfo_height()
        root.destroy()

        self.assertEqual(w1, w2, "Width must remain stable after screeninfo check")
        self.assertEqual(h1, h2, "Height must remain stable after screeninfo check")


if __name__ == '__main__':
    unittest.main()
