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
from base_client import AIClientError, NoQuestionsFoundError
from models import QuizResult, QuizQuestion
from settings_manager import DEFAULT_SETTINGS, SettingsManager


class TestProviderFailoverConfig(unittest.TestCase):

    def test_provider_configured_detection(self):
        cm = ConfigManager()
        # Test Gemini check
        cm.config['GEMINI_API_KEY'] = 'AIzaSy_test'
        self.assertTrue(cm.is_provider_configured('gemini'))
        cm.config['GEMINI_API_KEY'] = ''
        self.assertFalse(cm.is_provider_configured('gemini'))

        # Test Custom check
        cm.config['CUSTOM_API_URL'] = 'http://localhost:11434/v1'
        cm.config['CUSTOM_MODEL'] = 'llama3.2-vision'
        self.assertTrue(cm.is_provider_configured('custom'))

        cm.config['CUSTOM_MODEL'] = ''
        self.assertFalse(cm.is_provider_configured('custom'))

    def test_get_alternate_provider(self):
        cm = ConfigManager()
        cm.config['API_PROVIDER'] = 'gemini'
        cm.config['GEMINI_API_KEY'] = 'AIzaSy_test'
        cm.config['CUSTOM_API_URL'] = 'http://localhost:11434/v1'
        cm.config['CUSTOM_MODEL'] = 'llama3.2-vision'

        # Current is gemini -> alternate should be custom
        self.assertEqual(cm.get_alternate_provider('gemini'), 'custom')
        # Current is custom -> alternate should be gemini
        self.assertEqual(cm.get_alternate_provider('custom'), 'gemini')

        # If custom model is missing, alternate for gemini should be None
        cm.config['CUSTOM_MODEL'] = ''
        self.assertIsNone(cm.get_alternate_provider('gemini'))


class TestProviderFailoverExecution(unittest.TestCase):

    def setUp(self):
        from main import QuizAssistantApp
        self.app = QuizAssistantApp.__new__(QuizAssistantApp)
        self.app.logger = MagicMock()
        self.app.tray_manager = MagicMock()
        self.app.config_manager = ConfigManager()
        self.app.config_manager.config = {
            'API_PROVIDER': 'gemini',
            'GEMINI_API_KEY': 'AIzaSy_test',
            'CUSTOM_API_URL': 'http://localhost:11434/v1',
            'CUSTOM_MODEL': 'llama3.2-vision'
        }
        self.app.settings_manager = MagicMock()
        self.app.settings_manager.get.side_effect = lambda k, default=None: {
            'enable_provider_failover': True,
            'question_mode': 'multiple_choice',
            'answer_display_mode': 'letter_and_text'
        }.get(k, default)

    def test_failover_gemini_to_custom_on_quota_error(self):
        primary_client = MagicMock()
        primary_client.analyze_quiz.side_effect = AIClientError("429 ResourceExhausted: Quota exceeded")
        self.app.ai_client = primary_client

        backup_client = MagicMock()
        mock_result = QuizResult(questions=[QuizQuestion(number="1", question="What is 2+2?", answer="A. 4")])
        backup_client.analyze_quiz.return_value = mock_result
        self.app.create_ai_client_for_provider = MagicMock(return_value=backup_client)

        res = self.app._execute_ai_analysis_with_failover(b"img", "req_1")

        self.assertEqual(res, mock_result)
        self.assertTrue(res.is_fallback)
        self.assertIn("Backup", res.provider_name)
        self.app.create_ai_client_for_provider.assert_called_once_with('custom')

    def test_failover_custom_to_gemini_on_error(self):
        self.app.config_manager.config['API_PROVIDER'] = 'custom'
        primary_client = MagicMock()
        primary_client.analyze_quiz.side_effect = AIClientError("Connection refused: 11434")
        self.app.ai_client = primary_client

        backup_client = MagicMock()
        mock_result = QuizResult(questions=[QuizQuestion(number="1", question="What is 2+2?", answer="A. 4")])
        backup_client.analyze_quiz.return_value = mock_result
        self.app.create_ai_client_for_provider = MagicMock(return_value=backup_client)

        res = self.app._execute_ai_analysis_with_failover(b"img", "req_2")

        self.assertEqual(res, mock_result)
        self.assertTrue(res.is_fallback)
        self.assertIn("Backup", res.provider_name)
        self.app.create_ai_client_for_provider.assert_called_once_with('gemini')

    def test_no_failover_when_disabled(self):
        self.app.settings_manager.get.side_effect = lambda k, default=None: {
            'enable_provider_failover': False,
            'question_mode': 'multiple_choice',
            'answer_display_mode': 'letter_and_text'
        }.get(k, default)

        primary_client = MagicMock()
        primary_client.analyze_quiz.side_effect = AIClientError("429 ResourceExhausted")
        self.app.ai_client = primary_client
        self.app.create_ai_client_for_provider = MagicMock()

        with self.assertRaises(AIClientError):
            self.app._execute_ai_analysis_with_failover(b"img", "req_3")

        self.app.create_ai_client_for_provider.assert_not_called()

    def test_no_failover_on_no_questions_found(self):
        primary_client = MagicMock()
        primary_client.analyze_quiz.side_effect = NoQuestionsFoundError("No quiz found")
        self.app.ai_client = primary_client
        self.app.create_ai_client_for_provider = MagicMock()

        with self.assertRaises(NoQuestionsFoundError):
            self.app._execute_ai_analysis_with_failover(b"img", "req_4")

        self.app.create_ai_client_for_provider.assert_not_called()

    def test_both_providers_fail(self):
        primary_client = MagicMock()
        primary_client.analyze_quiz.side_effect = AIClientError("429 Quota Exceeded")
        self.app.ai_client = primary_client

        backup_client = MagicMock()
        backup_client.analyze_quiz.side_effect = AIClientError("500 Internal Server Error")
        self.app.create_ai_client_for_provider = MagicMock(return_value=backup_client)

        with self.assertRaises(AIClientError) as cm:
            self.app._execute_ai_analysis_with_failover(b"img", "req_5")

        err = str(cm.exception).lower()
        self.assertIn("primary", err)
        self.assertIn("backup", err)


class TestProviderFailoverSettings(unittest.TestCase):

    def test_settings_manager_defaults(self):
        self.assertIn('enable_provider_failover', DEFAULT_SETTINGS)
        self.assertTrue(DEFAULT_SETTINGS['enable_provider_failover'])


if __name__ == '__main__':
    unittest.main()
