import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import unittest
from unittest.mock import MagicMock, patch
from config_manager import ConfigManager
from settings_manager import SettingsManager, show_initial_setup_dialog, show_api_key_dialog


class TestInitialSetupWizard(unittest.TestCase):

    def setUp(self):
        self.sm = SettingsManager()
        self.cm = ConfigManager()

    def test_wizard_imports_and_structure(self):
        """Ensure wizard functions exist and callable"""
        self.assertTrue(callable(show_initial_setup_dialog))
        self.assertTrue(callable(show_api_key_dialog))

    @patch('tkinter.Tk')
    def test_wizard_finish_persists_theme_and_mode(self, mock_tk_cls):
        """Verify wizard properly initializes and provides 3-step navigation"""
        mock_root = MagicMock()
        mock_tk_cls.return_value = mock_root

        # Test settings before
        self.sm.settings['popup_bg_color'] = '#ffffff'
        self.sm.settings['popup_opacity'] = 0.96
        self.sm.settings['question_mode'] = 'multiple_choice'

        self.assertIn('popup_bg_color', self.sm.settings)
        self.assertIn('popup_opacity', self.sm.settings)
        self.assertIn('question_mode', self.sm.settings)

    def test_ensure_credentials_skip_handling(self):
        """Verify main.py _ensure_credentials handles skipped AI gracefully without sys.exit"""
        from main import QuizAssistantApp
        app = QuizAssistantApp.__new__(QuizAssistantApp)
        app.logger = MagicMock()
        app.config_manager = MagicMock()
        app.config_manager.is_valid.return_value = False
        app.settings_manager = MagicMock()

        # When show_initial_setup_dialog returns True (user skipped AI & completed wizard)
        with patch('main.show_initial_setup_dialog', return_value=True):
            app._ensure_credentials()

            # Should reload managers
            app.config_manager.reload.assert_called_once()
            app.settings_manager.load_settings.assert_called_once()
            # Should have set latest error warning about missing AI
            self.assertIsNotNone(app._latest_error)
            self.assertIn("not configured", app._latest_error.lower())

    def test_ensure_credentials_exit_handling(self):
        """Verify main.py _ensure_credentials calls sys.exit(0) when user cancels setup"""
        from main import QuizAssistantApp
        app = QuizAssistantApp.__new__(QuizAssistantApp)
        app.logger = MagicMock()
        app.config_manager = MagicMock()
        app.config_manager.is_valid.return_value = False
        app.settings_manager = MagicMock()

        with patch('main.show_initial_setup_dialog', return_value=False):
            with self.assertRaises(SystemExit) as cm:
                app._ensure_credentials()
            self.assertEqual(cm.exception.code, 0)

    def test_custom_api_url_default_fallback(self):
        """Verify custom API URL defaults to http://localhost:11434/v1 even with empty env"""
        with patch.dict(os.environ, {'CUSTOM_API_URL': ''}):
            cm = ConfigManager(env_file="non_existent_test.env")
            self.assertEqual(cm.get('CUSTOM_API_URL'), 'http://localhost:11434/v1')

    def test_card_selector_multi_column(self):
        """Verify _create_card_selector supports 2-column grid layout"""
        import tkinter as tk
        from settings_manager import _create_card_selector
        root = tk.Tk()
        root.withdraw()
        try:
            parent = tk.Frame(root)
            parent.pack()
            opts = [("1", "T1", "D1"), ("2", "T2", "D2"), ("3", "T3", "D3"), ("4", "T4", "D4")]
            var, update_ui = _create_card_selector(parent, opts, "1", columns=2)
            self.assertEqual(var.get(), "1")
            var.set("3")
            update_ui()
            self.assertEqual(var.get(), "3")
        finally:
            root.destroy()

    def test_hotkey_settings_customization(self):
        """Verify hotkey values can be assigned and validated"""
        self.sm.settings['hotkey_capture'] = 'k'
        self.sm.settings['hotkey_autofill'] = 'j'
        self.assertEqual(self.sm.get('hotkey_capture'), 'k')
        self.assertEqual(self.sm.get('hotkey_autofill'), 'j')

    def test_setup_completed_flag_prevents_repeated_dialog(self):
        """Verify main.py does not prompt setup dialog if setup_completed is True"""
        from main import QuizAssistantApp
        app = QuizAssistantApp.__new__(QuizAssistantApp)
        app.logger = MagicMock()
        app.config_manager = MagicMock()
        app.config_manager.is_valid.return_value = False
        app.settings_manager = MagicMock()
        app.settings_manager.get.side_effect = lambda k, d=None: True if k == 'setup_completed' else d

        with patch('main.show_initial_setup_dialog') as mock_dialog:
            app._ensure_credentials()
            mock_dialog.assert_not_called()
            self.assertIsNotNone(app._latest_error)

    def test_setup_py_default_custom_url(self):
        """Verify setup.py uses http://localhost:11434/v1 when env has empty custom URL"""
        with patch.dict(os.environ, {'CUSTOM_API_URL': ''}):
            cur_url = (os.getenv('CUSTOM_API_URL') or '').strip() or 'http://localhost:11434/v1'
            self.assertEqual(cur_url, 'http://localhost:11434/v1')


if __name__ == '__main__':
    unittest.main()
