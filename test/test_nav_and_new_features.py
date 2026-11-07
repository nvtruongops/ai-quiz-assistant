"""
Comprehensive Test Suite for Navigation, Live Auto-Update, Hotkeys, and MCQ Formats
"""

import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
import json
import unittest
from unittest.mock import MagicMock, patch

from models import QuizResult, QuizQuestion
from base_client import (
    BaseAIClient,
    MODE_MULTIPLE_CHOICE,
    MODE_MC_EXPLANATION,
    MODE_ESSAY,
    DISPLAY_LETTER_AND_TEXT,
    DISPLAY_LETTER_ONLY
)
from main import QuizAssistantApp
from hotkey_listener import HotkeyListener
from settings_manager import SettingsManager, _active_settings_dialog


class TestDummyAIClient(BaseAIClient):
    def analyze_quiz(self, image_bytes: bytes, timeout: int = 45):
        return QuizResult(questions=[], timestamp=time.time())

    def test_connection(self):
        return (True, "OK", 0.05)


class TestNewFeaturesAndFixes(unittest.TestCase):

    def setUp(self):
        self.client = TestDummyAIClient(
            mode=MODE_MULTIPLE_CHOICE,
            answer_display_mode=DISPLAY_LETTER_AND_TEXT
        )

    def test_mc_answer_parsing_multi_and_true_false(self):
        """Test parsing of single choice, multi-select (2-3 options), and True/False"""
        # Single choice
        l, t, f = self.client.parse_mc_answer("B. Carbon Dioxide")
        self.assertEqual(l, "B")
        self.assertEqual(t, "Carbon Dioxide")
        self.assertEqual(f, "B. Carbon Dioxide")

        # Multi-select: comma separated
        l, t, f = self.client.parse_mc_answer("A, C")
        self.assertEqual(l, "A, C")
        self.assertEqual(f, "A, C")

        # Multi-select: 3 options
        l, t, f = self.client.parse_mc_answer("A, B, D")
        self.assertEqual(l, "A, B, D")

        # Multi-select: Vietnamese 'và'
        l, t, f = self.client.parse_mc_answer("A và B")
        self.assertEqual(l, "A, B")

        # Multi-select: Ampersand
        l, t, f = self.client.parse_mc_answer("A & C")
        self.assertEqual(l, "A, C")

        # True / False
        l, t, f = self.client.parse_mc_answer("Đúng")
        self.assertEqual(l, "Đúng")
        l, t, f = self.client.parse_mc_answer("Sai")
        self.assertEqual(l, "Sai")
        l, t, f = self.client.parse_mc_answer("True")
        self.assertEqual(l, "True")
        l, t, f = self.client.parse_mc_answer("False")
        self.assertEqual(l, "False")

        # A. Đúng
        l, t, f = self.client.parse_mc_answer("A. Đúng")
        self.assertEqual(l, "A")
        self.assertEqual(t, "Đúng")
        self.assertEqual(f, "A. Đúng")

    def test_display_mode_letter_only_vs_full(self):
        """Test answer_display_mode effects"""
        client_letter = TestDummyAIClient(
            mode=MODE_MULTIPLE_CHOICE,
            answer_display_mode=DISPLAY_LETTER_ONLY
        )
        client_full = TestDummyAIClient(
            mode=MODE_MULTIPLE_CHOICE,
            answer_display_mode=DISPLAY_LETTER_AND_TEXT
        )

        json_payload = json.dumps({
            "questions": [
                {"number": "1", "question": "What gas?", "answer": "B. Carbon Dioxide"},
                {"number": "2", "question": "Select two cities", "answer": "A, C"},
                {"number": "3", "question": "Is earth round?", "answer": "Đúng"}
            ]
        })

        res_letter = client_letter.parse_quiz_response(json_payload)
        res_full = client_full.parse_quiz_response(json_payload)

        self.assertEqual(res_letter.questions[0].answer, "B")
        self.assertEqual(res_full.questions[0].answer, "B. Carbon Dioxide")

        self.assertEqual(res_letter.questions[1].answer, "A, C")
        self.assertEqual(res_full.questions[1].answer, "A, C")

        self.assertEqual(res_letter.questions[2].answer, "Đúng")
        self.assertEqual(res_full.questions[2].answer, "Đúng")

    def test_alt_x_completely_removed(self):
        """Verify Alt+X is removed from hotkeys listener defaults"""
        self.assertNotIn('results', HotkeyListener.DEFAULT_HOTKEYS)
        self.assertNotIn('x', HotkeyListener.DEFAULT_HOTKEYS.values())

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_navigation_and_unviewed_first_logic(self, mock_pm_cls, mock_tray_cls):
        """
        Verify Requirement 2 & 3:
        When UI was hidden at question x and user captured multiple questions,
        opening Alt+C shows the FIRST unviewed question (x+1), NOT the last question!
        """
        mock_pm = MagicMock()
        mock_pm.is_visible.return_value = False
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        # Seed answer history with questions 1, 2, 3, 4, 5
        app._answer_history = [
            {"number": "1", "question": "Q1", "answer": "A. Ans 1"},
            {"number": "2", "question": "Q2", "answer": "B. Ans 2"},
            {"number": "3", "question": "Q3", "answer": "C. Ans 3"},
            {"number": "4", "question": "Q4", "answer": "D. Ans 4"},
            {"number": "5", "question": "Q5", "answer": "A. Ans 5"}
        ]

        # Scenario: User had previously viewed up to Question 2 (index 1)
        app._last_viewed_history_index = 1
        app._current_view_index = 1

        # Now user triggers Alt+C
        app.on_show_answers_hotkey()

        # It MUST open question index 2 (Question 3 - the first unviewed question!)
        self.assertEqual(app._current_view_index, 2)
        mock_pm.show_questions.assert_called()
        call_args = mock_pm.show_questions.call_args[0]
        # First arg is questions list
        displayed_q = call_args[0][0]
        self.assertEqual(displayed_q["number"], "3")

        # Test Prev navigation (▲)
        app.on_nav_prev()
        self.assertEqual(app._current_view_index, 1)

        # Test Next navigation (▼)
        app.on_nav_next()
        self.assertEqual(app._current_view_index, 2)
        app.on_nav_next()
        self.assertEqual(app._current_view_index, 3)
        self.assertEqual(app._last_viewed_history_index, 3)

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_alt_r_silent_reset(self, mock_pm_cls, mock_tray_cls):
        """Verify Requirement 4: Alt+R resets cleanly WITHOUT showing any popup"""
        mock_pm = MagicMock()
        mock_pm.is_visible.return_value = False
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        app._answer_history = [{"number": "1", "question": "Q1", "answer": "A"}]
        app._image_cache["fake_hash"] = MagicMock()

        # Trigger Alt+R
        app.on_reset_answers_hotkey()

        self.assertEqual(len(app._answer_history), 0)
        self.assertEqual(len(app._image_cache), 0)
        self.assertEqual(app._current_view_index, -1)
        self.assertEqual(app._last_viewed_history_index, -1)
        # popup_manager.show MUST NOT have been called!
        mock_pm.show.assert_not_called()

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_live_runtime_auto_update(self, mock_pm_cls, mock_tray_cls):
        """
        Verify:
        Background processing completes silently (does NOT auto-popup).
        User clicks Reload (on_nav_reload) to update the visible popup with the new answer!
        """
        mock_pm = MagicMock()
        mock_pm.is_visible.return_value = True  # Popup is currently open!
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        # User is waiting for question index 0
        app._current_view_index = 0
        app._last_viewed_history_index = -1

        new_result = QuizResult(
            questions=[QuizQuestion(number="1", question="New Q", answer="B. New Ans")],
            timestamp=time.time(),
            mode=MODE_MULTIPLE_CHOICE
        )

        # Background worker completes silently - MUST NOT auto-call show_questions!
        app._handle_api_success(new_result, "req_123", "hash_abc")
        mock_pm.show_questions.assert_not_called()

        # User clicks 🔄 reload button: NOW show_questions must be called with the new question!
        app.on_nav_reload()
        mock_pm.show_questions.assert_called_once()
        displayed_q = mock_pm.show_questions.call_args[0][0][0]
        self.assertEqual(displayed_q["question"], "New Q")
        self.assertEqual(displayed_q["answer"], "B. New Ans")

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_singleton_settings_dialog(self, mock_pm_cls, mock_tray_cls):
        """Verify Requirement 7: Prevent duplicate Settings dialogs"""
        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        app._settings_open = True
        with patch('main.show_settings_dialog') as mock_ssd:
            app.on_setup_hotkey()
            mock_ssd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
