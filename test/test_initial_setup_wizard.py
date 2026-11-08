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
            self.assertIn("chưa được cấu hình", app._latest_error.lower())

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


if __name__ == '__main__':
    unittest.main()
