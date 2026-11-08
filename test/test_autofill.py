"""
Unit tests for Auto-Fill & Click feature (AutoFillManager and Alt+F integration)
"""

import unittest
from unittest.mock import MagicMock, patch
import time

from src.models import QuizResult, QuizQuestion
from src.autofill_manager import AutoFillManager
from src.settings_manager import SettingsManager


class MockMouseController:
    """Mock mouse controller to record movements and clicks without touching physical hardware"""
    def __init__(self, initial_pos=(100, 100)):
        self._position = initial_pos
        self.moves = []
        self.clicks = []

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = (int(pos[0]), int(pos[1]))
        self.moves.append(self._position)

    def press(self, button):
        self.clicks.append(("press", button, self._position))

    def release(self, button):
        self.clicks.append(("release", button, self._position))


class TestAutoFillManager(unittest.TestCase):
    """Test suite for AutoFillManager coordinate computation and clicking logic"""

    def setUp(self):
        self.mock_mouse = MockMouseController(initial_pos=(500, 500))
        self.mock_settings = MagicMock(spec=SettingsManager)
        self.mock_settings.get.side_effect = lambda k, d=None: {
            'enable_autofill': True,
            'autofill_click_delay_ms': 50,
            'autofill_restore_cursor': True,
            'autofill_smooth_movement': False,  # set to False in tests for fast direct jumps
            'hotkey_autofill': 'x'
        }.get(k, d)

        self.manager = AutoFillManager(
            logger=MagicMock(),
            settings_manager=self.mock_settings,
            mouse_controller=self.mock_mouse
        )

    def test_compute_screen_coordinates_normalized_1000(self):
        """Test coordinate conversion from [y, x] (0..1000) on single 1920x1080 display"""
        bbox = (0, 0, 1920, 1080)
        # Point at top-left 10%, 20%
        pt = [100, 200]  # y=100 (10%), x=200 (20%)
        sx, sy = self.manager.compute_screen_coordinates(pt, bbox)
        self.assertEqual(sx, int(0.20 * 1920))  # 384
        self.assertEqual(sy, int(0.10 * 1080))  # 108

        # Center point
        center_pt = [500, 500]
        cx, cy = self.manager.compute_screen_coordinates(center_pt, bbox)
        self.assertEqual(cx, 960)
        self.assertEqual(cy, 540)

    def test_compute_screen_coordinates_multi_monitor_offset(self):
        """Test coordinate conversion with multi-monitor offset (e.g. secondary display at x=1920, y=0)"""
        bbox = (1920, 100, 1920, 1080)
        pt = [500, 500]
        sx, sy = self.manager.compute_screen_coordinates(pt, bbox)
        self.assertEqual(sx, 1920 + 960)
        self.assertEqual(sy, 100 + 540)

    def test_compute_screen_coordinates_clamping(self):
        """Test that negative or >1000 coordinates are clamped safely within screen bounds"""
        bbox = (0, 0, 1000, 1000)
        sx, sy = self.manager.compute_screen_coordinates([-50, 1500], bbox)
        self.assertEqual(sy, 0)
        self.assertEqual(sx, 1000)

    def test_fill_answers_sequential_multi_questions(self):
        """Test sequential clicking across multiple questions and answers"""
        q1 = QuizQuestion(
            number="1",
            question="What is 2+2?",
            answer="B. 4",
            option_letter="B",
            clicks=[{"option": "B", "point": [200, 300]}]  # y=200, x=300
        )
        q2 = QuizQuestion(
            number="2",
            question="What is capital of France?",
            answer="C. Paris",
            option_letter="C",
            clicks=[{"option": "C", "point": [600, 400]}]  # y=600, x=400
        )
        result = QuizResult(questions=[q1, q2])

        bbox = (0, 0, 1000, 1000)
        success_clicks, total_targets = self.manager.fill_answers(result, capture_bbox=bbox)

        self.assertEqual(success_clicks, 2)
        self.assertEqual(total_targets, 2)

        # Verify mouse movements:
        # Initial pos was (500, 500)
        # 1st click at x=300, y=200
        # 2nd click at x=400, y=600
        # Restored cursor back to (500, 500)
        self.assertIn((300, 200), self.mock_mouse.moves)
        self.assertIn((400, 600), self.mock_mouse.moves)
        self.assertEqual(self.mock_mouse.moves[-1], (500, 500))

        # Check clicks: 2 presses and 2 releases
        presses = [c for c in self.mock_mouse.clicks if c[0] == "press"]
        self.assertEqual(len(presses), 2)
        self.assertEqual(presses[0][2], (300, 200))
        self.assertEqual(presses[1][2], (400, 600))

    def test_fill_answers_multi_select(self):
        """Test question with multiple correct options (multi-select / checkboxes)"""
        q1 = QuizQuestion(
            number="1",
            question="Select prime numbers:",
            answer="A, C",
            option_letter="A, C",
            clicks=[
                {"option": "A", "point": [200, 100]},
                {"option": "C", "point": [400, 100]}
            ]
        )
        result = QuizResult(questions=[q1])
        bbox = (0, 0, 1000, 1000)

        success_clicks, total_targets = self.manager.fill_answers(result, capture_bbox=bbox)
        self.assertEqual(success_clicks, 2)
        self.assertEqual(total_targets, 2)

        presses = [c for c in self.mock_mouse.clicks if c[0] == "press"]
        self.assertEqual(len(presses), 2)
        self.assertEqual(presses[0][2], (100, 200))
        self.assertEqual(presses[1][2], (100, 400))

    def test_fill_answers_disabled_setting(self):
        """Test that nothing is clicked if autofill is disabled in settings"""
        self.mock_settings.get.side_effect = lambda k, d=None: {
            'enable_autofill': False
        }.get(k, d)

        q1 = QuizQuestion(
            number="1",
            question="Disabled test",
            answer="A",
            clicks=[{"option": "A", "point": [100, 100]}]
        )
        result = QuizResult(questions=[q1])
        success, total = self.manager.fill_answers(result, capture_bbox=(0, 0, 1000, 1000))

        self.assertEqual(success, 0)
        self.assertEqual(total, 0)
        self.assertEqual(len(self.mock_mouse.clicks), 0)

    def test_fill_answers_empty_clicks(self):
        """Test result with no click targets returns 0 without errors"""
        q1 = QuizQuestion(
            number="1",
            question="No clicks available",
            answer="A",
            clicks=[]
        )
        result = QuizResult(questions=[q1])
        success, total = self.manager.fill_answers(result)
        self.assertEqual(success, 0)
        self.assertEqual(total, 0)
        self.assertEqual(len(self.mock_mouse.clicks), 0)

    def test_fill_answers_abort(self):
        """Test emergency abort stopping execution midway"""
        q1 = QuizQuestion(number="1", question="Q1", answer="A", clicks=[{"option": "A", "point": [100, 100]}])
        q2 = QuizQuestion(number="2", question="Q2", answer="B", clicks=[{"option": "B", "point": [200, 200]}])
        result = QuizResult(questions=[q1, q2])

        def on_progress(idx, total, desc):
            # Abort as soon as target 1 progress is reported
            self.manager.abort()

        success, total = self.manager.fill_answers(
            result,
            capture_bbox=(0, 0, 1000, 1000),
            on_progress=on_progress
        )
        self.assertEqual(success, 0)
        self.assertEqual(total, 2)
        self.assertEqual(len(self.mock_mouse.clicks), 0)


class TestAppAutoFillIntegration(unittest.TestCase):
    """Test suite for QuizAssistantApp auto-fill hotkey and queue handling"""

    @patch('src.main.SystemTray')
    @patch('src.main.HotkeyListener')
    @patch('src.main.ScreenshotManager')
    @patch('src.main.PopupManager')
    def test_on_autofill_hotkey_enqueues_task(self, mock_popup, mock_screen, mock_hk, mock_tray):
        """Test that Alt+F on_autofill_hotkey captures screen and enqueues task with is_autofill=True"""
        from src.main import QuizAssistantApp
        from PIL import Image

        app = QuizAssistantApp()
        app.settings_manager = MagicMock()
        app.settings_manager.get.side_effect = lambda k, d=None: {
            'enable_autofill': True
        }.get(k, d)

        # Mock screenshot capture
        mock_img = Image.new('RGB', (100, 100), color='white')
        app.screenshot_manager.capture_screen.return_value = mock_img
        app.screenshot_manager.save_to_memory.return_value = b"fake_png_data"
        app.screenshot_manager.compute_image_hash.return_value = "hash_autofill_123"
        app.screenshot_manager.get_last_capture_bbox.return_value = (0, 0, 1920, 1080)

        # Mock queue put to inspect enqueued item directly
        app._capture_queue.put = MagicMock()

        app.on_autofill_hotkey()

        app._capture_queue.put.assert_called_once()
        item = app._capture_queue.put.call_args[0][0]
        self.assertTrue(item.get("is_autofill"))
        self.assertEqual(item.get("img_hash"), "hash_autofill_123")
        self.assertEqual(item.get("capture_bbox"), (0, 0, 1920, 1080))

    @patch('src.main.SystemTray')
    @patch('src.main.HotkeyListener')
    @patch('src.main.ScreenshotManager')
    @patch('src.main.PopupManager')
    def test_process_queue_item_triggers_autofill(self, mock_popup, mock_screen, mock_hk, mock_tray):
        """Test that _process_queue_item executes autofill when item['is_autofill'] is True"""
        from src.main import QuizAssistantApp

        app = QuizAssistantApp()
        app.settings_manager = MagicMock()
        app.settings_manager.get.side_effect = lambda k, d=None: {
            'enable_autofill': True
        }.get(k, d)

        app.autofill_manager = MagicMock()
        app.autofill_manager.is_enabled.return_value = True

        app.ai_client = MagicMock()
        mock_result = QuizResult(questions=[
            QuizQuestion(number="1", question="Test", answer="A", clicks=[{"option": "A", "point": [100, 100]}])
        ])
        app.ai_client.analyze_quiz.return_value = mock_result

        item = {
            "req_id": "test_req_autofill",
            "img_hash": "test_hash_unique",
            "image_bytes": b"bytes",
            "is_autofill": True,
            "capture_bbox": (0, 0, 1920, 1080)
        }

        with patch.object(app, '_execute_autofill') as mock_exec:
            app._process_queue_item(item)
            mock_exec.assert_called_once_with(mock_result, (0, 0, 1920, 1080))


if __name__ == '__main__':
    unittest.main()
