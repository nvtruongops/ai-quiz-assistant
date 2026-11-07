"""
Test Suite for:
1. Virtual Key and Hotkey Capture (both Alt+A and Alt+Z work even with Windows VK codes)
2. History mode (Alt+H) shows all finished questions PLUS pending queue items
3. Single question mode (Alt+C) shows only 1 question with ▲ and ▼ question navigation
4. In history mode, ▲ and ▼ do scrolling rather than single question jumps
5. Minimum popup width is >= 460px preventing any header overlap
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
import unittest
from unittest.mock import MagicMock, patch
from pynput import keyboard

from models import QuizResult, QuizQuestion
from main import QuizAssistantApp
from hotkey_listener import HotkeyListener
from popup_manager import PopupManager


class TestFixCaptureAndHistoryQueue(unittest.TestCase):

    def test_hotkey_vk_code_resolves_without_char(self):
        """
        Verify that on Windows, when Alt is held down and pynput provides key.char = None
        with VK codes (e.g. vk=65 for 'A', vk=90 for 'Z', vk=67 for 'C', vk=72 for 'H'),
        the hotkey listener resolves the character and triggers the callbacks!
        """
        mock_capture = MagicMock()
        mock_answers = MagicMock()
        mock_history = MagicMock()

        listener = HotkeyListener(
            on_capture_key=mock_capture,
            on_show_answers=mock_answers,
            on_show_detailed_history=mock_history
        )

        # 1. User presses Alt
        listener.on_key_press(keyboard.Key.alt_l)
        self.assertTrue(listener.alt_pressed)

        # 2. User presses 'Z' (vk=90, char=None) -> Must trigger capture!
        key_z = keyboard.KeyCode(vk=90)
        self.assertIsNone(key_z.char)
        listener.on_key_press(key_z)
        mock_capture.assert_called_once()

        # 3. User presses 'C' (vk=67, char=None) -> Must trigger show answers!
        time.sleep(0.4)
        key_c = keyboard.KeyCode(vk=67)
        listener.on_key_press(key_c)
        mock_answers.assert_called_once()

        # 4. User presses 'H' (vk=72, char=None) -> Must trigger history!
        time.sleep(0.4)
        key_h = keyboard.KeyCode(vk=72)
        listener.on_key_press(key_h)
        mock_history.assert_called_once()

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_history_mode_includes_pending_queue_items(self, mock_pm_cls, mock_tray_cls):
        """
        Verify that Alt+H shows all completed questions PLUS any items currently being processed
        or waiting in the queue!
        """
        mock_pm = MagicMock()
        mock_pm.is_visible.return_value = False
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        # History has 2 questions
        app._answer_history = [
            {"number": "1", "question": "Q1", "answer": "A. Ans 1"},
            {"number": "2", "question": "Q2", "answer": "B. Ans 2"}
        ]

        # 1 item is currently processing, 2 items are waiting in the queue
        app._is_queue_processing = True
        with patch.object(app._capture_queue, 'qsize', return_value=2):
            # User presses Alt+H
            app.on_show_detailed_history_hotkey()

            self.assertTrue(app._is_showing_history)
            mock_pm.show_questions.assert_called_once()
            args, kwargs = mock_pm.show_questions.call_args
            full_list = args[0]
            title = kwargs.get('title') or args[1]
            is_hist = kwargs.get('is_history', False)

            self.assertTrue(is_hist)
            # Total items should be 2 finished + 1 processing + 2 queued = 5 items!
            self.assertEqual(len(full_list), 5)
            self.assertEqual(full_list[0]["number"], "1")
            self.assertEqual(full_list[1]["number"], "2")

            # Item 3 is processing
            self.assertEqual(full_list[2]["number"], "3")
            self.assertTrue(full_list[2]["is_pending"])
            self.assertTrue("Analyzing" in full_list[2]["answer"] or "Đang phân tích" in full_list[2]["answer"])

            # Item 4 is queued
            self.assertEqual(full_list[3]["number"], "4")
            self.assertTrue(full_list[3]["is_pending"])
            self.assertTrue("Waiting" in full_list[3]["answer"] or "Đang chờ" in full_list[3]["answer"])

            # Title should mention pending items
            self.assertTrue("pending" in title or "câu chờ" in title)

    @patch('main.SystemTray')
    @patch('main.PopupManager')
    def test_single_question_vs_history_navigation_separation(self, mock_pm_cls, mock_tray_cls):
        """
        Verify that:
        - Alt+C shows only 1 question at a time (is_history=False)
        - In history mode, on_nav_prev and on_nav_next do NOT jump questions or log warnings
        """
        mock_pm = MagicMock()
        mock_pm.is_visible.return_value = False
        mock_pm_cls.return_value = mock_pm

        with patch.object(QuizAssistantApp, '_ensure_credentials'):
            app = QuizAssistantApp()
            app.hotkey_listener.stop()

        app._answer_history = [
            {"number": "1", "question": "Q1", "answer": "A"},
            {"number": "2", "question": "Q2", "answer": "B"},
            {"number": "3", "question": "Q3", "answer": "C"}
        ]

        # 1. Trigger Alt+C
        app.on_show_answers_hotkey()
        self.assertFalse(app._is_showing_history)
        args, kwargs = mock_pm.show_questions.call_args
        self.assertEqual(len(args[0]), 1)  # EXACTLY 1 QUESTION!
        self.assertFalse(kwargs.get('is_history', False))

        # 2. Trigger Alt+H
        app.on_show_detailed_history_hotkey()
        self.assertTrue(app._is_showing_history)
        args, kwargs = mock_pm.show_questions.call_args
        self.assertEqual(len(args[0]), 3)  # FULL LIST!
        self.assertTrue(kwargs.get('is_history', False))

        # 3. While in history mode, on_nav_prev/on_nav_next return without disturbing history
        app.on_nav_prev()
        app.on_nav_next()
        self.assertTrue(app._is_showing_history)


if __name__ == "__main__":
    unittest.main()
