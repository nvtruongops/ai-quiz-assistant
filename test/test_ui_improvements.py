import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import unittest
import json
import tkinter as tk
from unittest.mock import MagicMock

from settings_manager import (
    SettingsManager,
    DEFAULT_SETTINGS,
    create_scrollable_tab,
    pick_color_at_cursor
)
from popup_manager import get_popup_theme, PopupManager
from models import QuizQuestion


class TestUIImprovements(unittest.TestCase):

    def test_default_settings_color_is_white(self):
        """Verify that default UI background color is white #ffffff"""
        self.assertIn('popup_bg_color', DEFAULT_SETTINGS)
        self.assertEqual(DEFAULT_SETTINGS['popup_bg_color'], '#ffffff')

    def test_popup_theme_contrast_calculation(self):
        """Verify dynamic contrast palette calculation for both light and dark backgrounds"""
        # 1. White background
        theme_white = get_popup_theme('#ffffff')
        self.assertTrue(theme_white['is_light'])
        self.assertEqual(theme_white['bg'], '#ffffff')
        self.assertEqual(theme_white['text'], '#0f172a')   # Dark charcoal text
        self.assertEqual(theme_white['answer'], '#15803d') # Crisp forest green

        # 2. Dark background
        theme_dark = get_popup_theme('#1e1e2e')
        self.assertFalse(theme_dark['is_light'])
        self.assertEqual(theme_dark['bg'], '#1e1e2e')
        self.assertEqual(theme_dark['text'], '#cdd6f4')    # Light soft text
        self.assertEqual(theme_dark['answer'], '#a6e3a1')  # Soft green

        # 3. Custom color (e.g. pastel cream #fef9c3)
        theme_cream = get_popup_theme('#fef9c3')
        self.assertTrue(theme_cream['is_light'])
        self.assertEqual(theme_cream['text'], '#0f172a')

    def test_settings_manager_saves_and_loads_color(self):
        """Verify SettingsManager persists and restores popup_bg_color"""
        test_cfg = "logs/test_config.json"
        os.makedirs("logs", exist_ok=True)
        sm = SettingsManager(config_file=test_cfg)
        sm.settings['popup_bg_color'] = '#e0f2fe'
        sm.save_settings()

        sm2 = SettingsManager(config_file=test_cfg)
        self.assertEqual(sm2.get('popup_bg_color'), '#e0f2fe')

        if os.path.exists(test_cfg):
            os.remove(test_cfg)

    def test_scrollable_tab_structure(self):
        """Verify create_scrollable_tab builds canvas with 100% width and no scrollbar widget"""
        root = tk.Tk()
        root.withdraw()
        from tkinter import ttk
        nb = ttk.Notebook(root)
        outer, inner, canvas = create_scrollable_tab(nb, "Test Tab")
        self.assertIsInstance(canvas, tk.Canvas)
        self.assertIsInstance(inner, tk.Frame)

        # Check children of outer frame: MUST NOT have a ttk.Scrollbar / tk.Scrollbar
        child_types = [type(c).__name__ for c in outer.winfo_children()]
        self.assertNotIn("Scrollbar", child_types)
        root.destroy()

    def test_popup_rendering_with_white_theme(self):
        """Verify PopupManager renders structured questions with default white theme"""
        root = tk.Tk()
        root.withdraw()

        pm = PopupManager(settings={'popup_bg_color': '#ffffff', 'font_size': 10, 'popup_width': 480})
        pm.root = root

        # Test internal popup creation with question
        q = QuizQuestion(
            number="1",
            question="Thủ đô của Việt Nam là gì?",
            answer="A. Hà Nội",
            explanation="Hà Nội là thủ đô của nước CHXHCN Việt Nam."
        )

        pm._create_popup_internal(
            content="Câu 1: Thủ đô của Việt Nam là gì?\n→ Đáp án: A. Hà Nội",
            title="Kiểm tra giao diện",
            provider="Gemini",
            mode="Trắc nghiệm",
            questions=[q]
        )

        self.assertIsNotNone(pm.current_popup)
        # Background of main frame should be white
        self.assertEqual(pm.current_popup.winfo_exists(), 1)
        pm.hide()
        root.destroy()

    def test_popup_theme_stealth(self):
        """Verify stealth / ghost theme returns borderless white palette with muted non-bold text"""
        for stealth_key in ['stealth', '#stealth', 'ghost', '#ghost', 'STEALTH']:
            theme = get_popup_theme(stealth_key)
            self.assertTrue(theme.get('is_stealth'), f"Failed for key {stealth_key}")
            self.assertTrue(theme.get('is_light'))
            self.assertEqual(theme['bg'], '#ffffff')
            self.assertEqual(theme['header_bg'], '#ffffff')
            self.assertEqual(theme['border'], '#ffffff')
            self.assertEqual(theme['text'], '#71717a')
            self.assertEqual(theme['question'], '#71717a')
            self.assertEqual(theme['answer'], '#52525b')
            self.assertEqual(theme['close_fg'], '#a1a1aa')

    def test_popup_rendering_with_stealth_theme(self):
        """Verify PopupManager properly builds borderless stealth HUD with font size 8"""
        root = tk.Tk()
        root.withdraw()

        pm = PopupManager(settings={'popup_bg_color': 'stealth', 'font_size': 8, 'popup_width': 380})
        pm.root = root

        q = QuizQuestion(
            number="1",
            question="Thủ đô của Việt Nam là gì?",
            answer="A. Hà Nội",
            explanation="Hà Nội là thủ đô."
        )

        pm._create_popup_internal(
            content="Câu 1: Thủ đô của Việt Nam là gì?\n→ Đáp án: A. Hà Nội",
            title="Stealth HUD",
            provider="Gemini",
            mode="Trắc nghiệm",
            questions=[q]
        )

        self.assertIsNotNone(pm.current_popup)
        self.assertEqual(pm.current_popup.cget('bg'), '#ffffff')
        self.assertEqual(pm.current_popup.winfo_exists(), 1)
        pm.hide()
        root.destroy()

    def test_settings_dialog_initialization_with_stealth(self):
        """Verify show_settings_dialog initializes cleanly with popup_bg_color='stealth' without TclError"""
        from settings_manager import show_settings_dialog
        sm = SettingsManager()
        sm.settings['popup_bg_color'] = 'stealth'

        def mock_mainloop(dlg_self):
            dlg_self.update_idletasks()
            dlg_self.destroy()

        with unittest.mock.patch.object(tk.Tk, 'mainloop', mock_mainloop):
            # Must not raise _tkinter.TclError: unknown color name "stealth"
            show_settings_dialog(sm)


if __name__ == '__main__':
    unittest.main()
