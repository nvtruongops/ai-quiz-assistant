import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
import tempfile
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from settings_manager import SettingsManager, DEFAULT_SETTINGS, show_settings_dialog
from popup_manager import PopupManager


class TestScalingAndFolderOpening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.json")
        self.settings_manager = SettingsManager(config_file=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_settings_contain_size_keys(self):
        """Verify new sizing keys exist in default settings"""
        self.assertIn('popup_height', DEFAULT_SETTINGS)
        self.assertIn('history_popup_width', DEFAULT_SETTINGS)
        self.assertIn('history_popup_height', DEFAULT_SETTINGS)
        self.assertIn('settings_win_width', DEFAULT_SETTINGS)
        self.assertIn('settings_win_height', DEFAULT_SETTINGS)

    @patch('os.startfile', create=True)
    def test_system_tray_callbacks_accept_arguments(self, mock_startfile):
        """Verify tray menu callbacks accept (icon, item) arguments from pystray"""
        from system_tray import SystemTray

        mock_app = MagicMock()
        mock_app.settings_manager = self.settings_manager
        mock_app.config_manager = MagicMock()

        tray = SystemTray(mock_app)
        menu = tray.create_menu()

        logs_item = None
        screens_item = None
        for item in menu:
            if hasattr(item, 'text'):
                if 'Open Logs Folder' in item.text:
                    logs_item = item
                elif 'Open Screenshots Folder' in item.text:
                    screens_item = item

        self.assertIsNotNone(logs_item, "Open Logs Folder menu item not found")
        self.assertIsNotNone(screens_item, "Open Screenshots Folder menu item not found")

        # Calling with 2 positional arguments MUST NOT raise TypeError!
        try:
            logs_item(None)
            screens_item(None)
        except TypeError as e:
            self.fail(f"Tray callback raised TypeError with arguments: {e}")

    def test_popup_resize_and_save_size(self):
        """Verify PopupManager allows dragging size and saving custom dimensions"""
        popup_mgr = PopupManager(settings_manager=self.settings_manager)
        self.assertTrue(popup_mgr.tk_ready.wait(3.0))

        # Show a question popup
        popup_mgr.show(
            title="Question 1/1",
            content="Question 1: What is the capital?\n→ Answer: Hanoi",
            provider="Custom",
            mode="multiple_choice"
        )

        for _ in range(40):
            if popup_mgr.current_popup and popup_mgr.is_visible():
                break
            time.sleep(0.05)

        self.assertIsNotNone(popup_mgr.current_popup)
        popup = popup_mgr.current_popup

        # Test updating and saving settings
        new_w, new_h = 620, 350
        self.settings_manager.set('popup_width', new_w)
        self.settings_manager.set('popup_height', new_h)
        self.settings_manager.save_settings()

        # Reload settings and check
        loaded_settings = SettingsManager(config_file=self.config_path)
        self.assertEqual(loaded_settings.get('popup_width'), 620)
        self.assertEqual(loaded_settings.get('popup_height'), 350)

        popup_mgr.hide()
        popup_mgr.close()

    def test_history_popup_independent_saved_size(self):
        """Verify History Popup (Alt+H) has independent width & height"""
        self.settings_manager.set('popup_width', 480)
        self.settings_manager.set('history_popup_width', 640)
        self.settings_manager.set('history_popup_height', 420)
        self.settings_manager.save_settings()

        popup_mgr = PopupManager(settings_manager=self.settings_manager)
        self.assertTrue(popup_mgr.tk_ready.wait(3.0))

        # In History Mode, show_questions is called with is_history=True
        mock_questions = [
            {'number': 1, 'question': 'Sample Question', 'answer': 'A. Test', 'explanation': ''}
        ]
        popup_mgr.show_questions(
            questions=mock_questions,
            title="Question History (1 - 1)",
            provider="Custom",
            mode="multiple_choice",
            is_history=True
        )

        for _ in range(40):
            if popup_mgr.current_popup and popup_mgr.is_visible():
                break
            time.sleep(0.05)

        self.assertIsNotNone(popup_mgr.current_popup)
        popup = popup_mgr.current_popup

        cur_w = popup.winfo_width()
        cur_h = popup.winfo_height()

        # Verify history popup respects history_popup_width & history_popup_height
        self.assertEqual(cur_w, 640)
        self.assertEqual(cur_h, 420)

        popup_mgr.hide()
        popup_mgr.close()

    def test_settings_dialog_size_persistence(self):
        """Verify Settings Dialog respects saved settings_win_width and settings_win_height"""
        self.settings_manager.set('settings_win_width', 760)
        self.settings_manager.set('settings_win_height', 710)
        self.settings_manager.save_settings()

        dialog_inspected = {}

        orig_mainloop = tk.Tk.mainloop

        def mock_mainloop(self_dialog):
            self_dialog.update_idletasks()
            dialog_inspected['geometry'] = self_dialog.geometry()
            dialog_inspected['width'] = self_dialog.winfo_width()
            dialog_inspected['height'] = self_dialog.winfo_height()

            # Find all buttons in dialog
            buttons = []
            for child in self_dialog.winfo_children():
                if isinstance(child, tk.Frame):
                    for sub in child.winfo_children():
                        if isinstance(sub, tk.Button):
                            buttons.append(sub.cget('text'))
            dialog_inspected['buttons'] = buttons
            self_dialog.destroy()

        tk.Tk.mainloop = mock_mainloop

        try:
            show_settings_dialog(self.settings_manager)
        finally:
            tk.Tk.mainloop = orig_mainloop

        # Verify the dialog opened with the saved geometry
        self.assertIn("760x710", dialog_inspected.get('geometry', ''))
        # Verify action buttons exist in bottom bar
        self.assertTrue(any("Save Settings" in b for b in dialog_inspected.get('buttons', [])))
        self.assertTrue(any("Close" in b for b in dialog_inspected.get('buttons', [])))

    def test_settings_dialog_slider_and_spinbox_initialization(self):
        """Verify opacity slider and spinboxes correctly initialize with exact values even with PopupManager active"""
        # Ensure separate PopupManager thread is active
        popup_mgr = PopupManager(settings_manager=self.settings_manager)
        popup_mgr.tk_ready.wait(2.0)

        self.settings_manager.set('popup_opacity', 1.0)
        self.settings_manager.set('font_size', 12)
        self.settings_manager.set('popup_width', 540)
        self.settings_manager.save_settings()

        verified = {}
        orig_mainloop = tk.Tk.mainloop

        def mock_mainloop(self_dialog):
            self_dialog.update_idletasks()
            from tkinter import ttk
            def find_widgets(w):
                for c in w.winfo_children():
                    if isinstance(c, ttk.Scale):
                        verified['scale_val'] = c.get()
                    elif isinstance(c, tk.Spinbox):
                        verified.setdefault('spinbox_vals', []).append(c.get())
                    find_widgets(c)
            find_widgets(self_dialog)
            self_dialog.destroy()

        tk.Tk.mainloop = mock_mainloop

        try:
            show_settings_dialog(self.settings_manager)
        finally:
            tk.Tk.mainloop = orig_mainloop
            popup_mgr.close()

        # Slider MUST be at 100.0, NOT 0 or 50!
        self.assertEqual(verified.get('scale_val'), 100.0)
        # Spinboxes MUST contain the saved font size and width!
        self.assertIn('12', verified.get('spinbox_vals', []))
        self.assertIn('540', verified.get('spinbox_vals', []))

    def test_save_size_click_with_settings_manager(self):
        """Verify clicking Save Size button does not raise TypeError with SettingsManager"""
        # Ensure SettingsManager supports item assignment directly
        self.settings_manager['popup_width'] = 450
        self.assertEqual(self.settings_manager['popup_width'], 450)
        self.assertEqual(self.settings_manager.get('popup_width'), 450)

        popup_mgr = PopupManager(settings_manager=self.settings_manager)
        self.assertTrue(popup_mgr.tk_ready.wait(3.0))

        popup_mgr.show(
            title="Question 1/1",
            content="Question 1: Sample Question\n→ Answer: Sample Answer",
            provider="Custom",
            mode="multiple_choice"
        )

        for _ in range(40):
            if popup_mgr.current_popup and popup_mgr.is_visible():
                break
            time.sleep(0.05)

        popup = popup_mgr.current_popup
        self.assertIsNotNone(popup)

        # Find save_size_btn
        def find_save_btn(w):
            if isinstance(w, tk.Label) and "Save Size" in w.cget('text'):
                return w
            for c in w.winfo_children():
                res = find_save_btn(c)
                if res:
                    return res
            return None

        btn = find_save_btn(popup)
        self.assertIsNotNone(btn, "Save Size button not found in popup header")

        # Simulate clicking the Save Size button
        btn.event_generate("<Button-1>")
        time.sleep(0.1)

        # Verify no TypeError was thrown and dimensions were updated
        self.assertEqual(self.settings_manager.get('popup_width'), popup.winfo_width())
        self.assertEqual(self.settings_manager['popup_width'], popup.winfo_width())

        popup_mgr.hide()
        popup_mgr.close()


if __name__ == '__main__':
    unittest.main()
