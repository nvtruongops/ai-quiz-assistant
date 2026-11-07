"""
Unit tests verifying:
1. History card (Alt+H) does NOT display Up/Down (▲ / ▼) buttons.
2. Popup position does NOT jump when clicking Reload (🔄) or Next/Prev (▲ / ▼).
3. Multiple captures process 100% silently in background without auto-opening UI;
   UI only opens via hotkey, and updates in-place without jumping when Reload is clicked.
"""

import sys
import os

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from popup_manager import PopupManager
from main import QuizAssistantApp
from models import QuizResult, QuizQuestion
from base_client import MODE_MULTIPLE_CHOICE


class TestFixJumpAndSilentQueue(unittest.TestCase):

    def setUp(self):
        self.pm = PopupManager()

    def tearDown(self):
        self.pm.close()

    def wait_until_visible(self, timeout=3.5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.pm.is_visible():
                return True
            time.sleep(0.05)
        return self.pm.is_visible()

    def test_history_card_omits_up_down_buttons(self):
        """
        Verify that in history mode (is_history=True):
        - Up/Down (▲ / ▼) buttons are NOT packed into the header.
        - Reload (🔄), Copy (📋 Chép), and Close (✕) buttons ARE present.
        """
        questions = [
            {"number": "1", "question": "Q1", "answer": "A", "explanation": ""},
            {"number": "2", "question": "Q2", "answer": "B", "explanation": ""}
        ]

        self.pm.show_questions(
            questions=questions,
            title="Lịch Sử (1 - 2)",
            provider="Custom",
            is_history=True
        )
        self.assertTrue(self.wait_until_visible())
        popup = self.pm.current_popup
        self.assertIsNotNone(popup)

        # Collect all label button texts in popup
        labels = []
        def collect_texts(widget):
            if isinstance(widget, tk.Label):
                labels.append(widget.cget('text'))
            for child in widget.winfo_children():
                collect_texts(child)
        collect_texts(popup)

        # ▲ and ▼ must NOT be present
        self.assertFalse(any("▲" in t for t in labels), "History card must NOT contain ▲ button")
        self.assertFalse(any("▼" in t for t in labels), "History card must NOT contain ▼ button")

        # 🔄, 📋 Copy, ✕ must be present
        self.assertTrue(any("🔄" in t for t in labels), "History card must contain 🔄 button")
        self.assertTrue(any("Copy" in t or "Chép" in t for t in labels), "History card must contain Copy button")
        self.assertTrue(any("✕" in t for t in labels), "History card must contain Close button")

    def test_single_question_card_has_up_down_buttons(self):
        """
        Verify that in single question mode (is_history=False):
        - Up/Down (▲ / ▼) buttons ARE present in the header.
        """
        questions = [
            {"number": "1", "question": "Q1", "answer": "A", "explanation": ""}
        ]

        self.pm.show_questions(
            questions=questions,
            title="Câu 1/1",
            provider="Custom",
            is_history=False
        )
        self.assertTrue(self.wait_until_visible())
        popup = self.pm.current_popup

        labels = []
        def collect_texts(widget):
            if isinstance(widget, tk.Label):
                labels.append(widget.cget('text'))
            for child in widget.winfo_children():
                collect_texts(child)
        collect_texts(popup)

        self.assertTrue(any("▲" in t for t in labels), "Single question card MUST contain ▲ button")
        self.assertTrue(any("▼" in t for t in labels), "Single question card MUST contain ▼ button")

    def test_popup_position_stability_on_reload_and_nav(self):
        """
        Verify that when clicking reload (🔄) or navigating:
        - The popup window position (x, y) stays rock solid and does NOT jump to mouse cursor!
        """
        questions1 = [
            {"number": "1", "question": "Question 1", "answer": "A. Option 1"}
        ]
        self.pm.show_questions(questions=questions1, title="Câu 1/2", is_history=False)
        self.assertTrue(self.wait_until_visible())
        orig_x = self.pm.current_popup.winfo_rootx()
        orig_y = self.pm.current_popup.winfo_rooty()
        self.assertGreater(orig_x, 0)
        self.assertGreater(orig_y, 0)

        # Simulate mouse moved far away to (100, 100)
        self.pm.mouse_controller.position = (100, 100)

        # Update popup with Question 2 (simulate navigation)
        questions2 = [
            {"number": "2", "question": "Question 2", "answer": "B. Option 2"}
        ]
        self.pm.show_questions(questions=questions2, title="Câu 2/2", is_history=False)
        self.assertTrue(self.wait_until_visible())

        new_x = self.pm.current_popup.winfo_rootx()
        new_y = self.pm.current_popup.winfo_rooty()

        # Window MUST remain at orig_x, orig_y, NOT jumped to (100, 100) + 12!
        self.assertEqual(orig_x, new_x, f"Popup X jumped! Expected {orig_x}, got {new_x}")
        self.assertEqual(orig_y, new_y, f"Popup Y jumped! Expected {orig_y}, got {new_y}")

    @patch('main.SystemTray')
    def test_multi_captures_silent_background_processing(self, mock_tray):
        """
        Verify:
        Multiple screenshots captured -> processed in background ->
        NO UI popup is ever shown automatically!
        UI only shows when user hits Alt+C or Alt+H.
        """
        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        # Mock AI to return a result
        mock_result = QuizResult(
            questions=[QuizQuestion(number="1", question="Silent Q", answer="A. Đúng")],
            timestamp=time.time(),
            mode=MODE_MULTIPLE_CHOICE
        )

        # Worker handles API success
        app._handle_api_success(mock_result, "req_1", "hash_1")

        # Verify NO popup was opened!
        self.assertFalse(app.popup_manager.is_visible(), "Popup must NOT be visible after background success")

        # Now user presses Alt+C: NOW popup opens!
        app.on_show_answers_hotkey()
        t0 = time.time()
        while time.time() - t0 < 2.0:
            if app.popup_manager.is_visible():
                break
            time.sleep(0.05)
        self.assertTrue(app.popup_manager.is_visible(), "Popup must be visible after Alt+C")

        app.stop()


if __name__ == '__main__':
    unittest.main()
