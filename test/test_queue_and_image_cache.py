"""
Test Queue, Deduplication via Image Hash, and Silent Processing
Verifies:
1. When capturing or when answer is ready, UI popup is NOT automatically shown (silent background).
   UI only opens when user triggers Alt+C or Alt+H.
2. Multiple captures are enqueued in FIFO queue and processed sequentially without conflict.
3. Duplicate images (same image hash) in the same session return cached answer immediately without calling AI again.
4. Reset (Alt+R) clears history and image cache.
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
from PIL import Image, ImageDraw

from screenshot_manager import ScreenshotManager
from models import QuizResult, QuizQuestion
from main import QuizAssistantApp


def create_mock_image(text: str) -> Image.Image:
    """Create a mock test image with specific text"""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), text, fill='black')
    return img


class TestQueueAndImageCache(unittest.TestCase):
    """Test suite for FIFO queue, image deduplication, and silent background processing"""

    def setUp(self):
        # Patch show_initial_setup_dialog to avoid GUI blocking
        self.dialog_patch = patch('main.show_initial_setup_dialog', return_value=True)
        self.dialog_patch.start()

        # Instantiate app with mock components
        with patch('main.HotkeyListener'), patch('main.SystemTray'), patch('main.show_initial_setup_dialog'):
            self.app = QuizAssistantApp()

        # Replace popup_manager with a spy/mock to monitor all calls
        self.popup_spy = MagicMock()
        self.popup_spy.is_visible.return_value = False
        self.app.popup_manager = self.popup_spy

        # Mock AI Client
        self.mock_ai = MagicMock()
        self.app.ai_client = self.mock_ai

        # Clear answer history and cache
        self.app._answer_history.clear()
        self.app._latest_result = None
        self.app._latest_error = None
        self.app._image_cache.clear()

    def tearDown(self):
        self.dialog_patch.stop()
        try:
            self.app._capture_queue.put(None)
        except Exception:
            pass

    def test_image_hash_consistency_and_uniqueness(self):
        """Test ScreenshotManager.compute_image_hash consistency and differentiation"""
        img1 = create_mock_image("Câu 1: Thủ đô của Việt Nam là gì? A. Hà Nội B. Huế")
        img1_copy = create_mock_image("Câu 1: Thủ đô của Việt Nam là gì? A. Hà Nội B. Huế")
        img2 = create_mock_image("Câu 2: Diện tích nước Nga lớn nhất thế giới? A. Đúng B. Sai")

        hash1 = ScreenshotManager.compute_image_hash(img1)
        hash1_copy = ScreenshotManager.compute_image_hash(img1_copy)
        hash2 = ScreenshotManager.compute_image_hash(img2)

        self.assertTrue(len(hash1) > 0, "Hash should be non-empty string")
        self.assertEqual(hash1, hash1_copy, "Identical images must yield identical hash")
        self.assertNotEqual(hash1, hash2, "Different images must yield different hashes")

    def test_silent_capture_and_success_no_auto_popup(self):
        """
        Verify:
        - When capturing (on_capture_hotkey), NO popup is shown.
        - When AI finishes processing, NO popup is shown.
        - Result is stored silently in _latest_result & _answer_history.
        """
        test_img = create_mock_image("Câu 1: Test silent popup")
        img_bytes = b"fake_png_bytes_1"
        self.app.screenshot_manager.capture_screen = MagicMock(return_value=test_img)
        self.app.screenshot_manager.save_to_memory = MagicMock(return_value=img_bytes)

        # Mock AI response
        mock_result = QuizResult(
            questions=[QuizQuestion(number="1", question="Câu 1: Test silent", answer="A. Đúng", explanation="Giải thích 1")]
        )
        self.mock_ai.analyze_quiz.return_value = mock_result

        # Trigger capture
        self.app.on_capture_hotkey()

        # Wait for queue worker to finish processing item
        self.app._capture_queue.join()

        # 1. VERIFY SILENT: popup_manager.show_processing and show_questions were NEVER called automatically!
        self.popup_spy.show_processing.assert_not_called()
        self.popup_spy.show_questions.assert_not_called()
        self.popup_spy.show.assert_not_called()

        # 2. VERIFY RESULT SAVED:
        self.assertIsNotNone(self.app._latest_result)
        self.assertEqual(len(self.app._answer_history), 1)
        self.assertEqual(self.app._answer_history[0]["question"], "Câu 1: Test silent")
        self.assertEqual(self.app._answer_history[0]["answer"], "A. Đúng")

        # 3. VERIFY HOTKEY MANUAL OPEN:
        # User presses Alt+C: NOW popup_manager.show_questions MUST be called!
        self.app.on_show_answers_hotkey()
        self.popup_spy.show_questions.assert_called_once()
        args, kwargs = self.popup_spy.show_questions.call_args
        self.assertEqual(args[0][0].answer, "A. Đúng")

    def test_image_deduplication_cache_skips_ai(self):
        """
        Verify:
        - If an image with the same hash was already processed, the next capture of that image
          hits the cache and returns the cached answer immediately without calling AI again.
        """
        test_img = create_mock_image("Câu 5: Trùng lặp hình ảnh")
        img_bytes = b"fake_png_bytes_dedup"
        self.app.screenshot_manager.capture_screen = MagicMock(return_value=test_img)
        self.app.screenshot_manager.save_to_memory = MagicMock(return_value=img_bytes)

        mock_result = QuizResult(
            questions=[QuizQuestion(number="1", question="Câu 5: Trùng lặp", answer="B. Đáp án chuẩn", explanation="Exp")]
        )
        self.mock_ai.analyze_quiz.return_value = mock_result

        # First capture (Cache miss -> calls AI)
        self.app.on_capture_hotkey()
        self.app._capture_queue.join()

        self.assertEqual(self.mock_ai.analyze_quiz.call_count, 1)
        self.assertEqual(len(self.app._image_cache), 1)

        # Second capture with identical image (Cache hit -> SKIPS AI)
        self.app._last_capture_time = 0.0  # bypass cooldown
        self.app.on_capture_hotkey()
        self.app._capture_queue.join()

        # AI call count MUST still be 1 (NOT 2)!
        self.assertEqual(self.mock_ai.analyze_quiz.call_count, 1, "AI must NOT be called for duplicate image!")

        # Latest result is still available and correct
        self.assertIsNotNone(self.app._latest_result)
        self.assertEqual(self.app._latest_result.questions[0].answer, "B. Đáp án chuẩn")

    def test_queue_sequential_processing_fifo(self):
        """
        Verify multiple rapid captures are queued and processed sequentially without error.
        """
        img1 = create_mock_image("Câu 10: First in queue")
        img2 = create_mock_image("Câu 11: Second in queue")
        img3 = create_mock_image("Câu 12: Third in queue")

        images = [img1, img2, img3]
        captured_counts = 0

        def mock_capture():
            nonlocal captured_counts
            img = images[min(captured_counts, len(images) - 1)]
            captured_counts += 1
            return img

        self.app.screenshot_manager.capture_screen = MagicMock(side_effect=mock_capture)
        self.app.screenshot_manager.save_to_memory = MagicMock(return_value=b"mock_bytes")

        def mock_analyze(b):
            time.sleep(0.05)  # simulate AI latency
            return QuizResult(
                questions=[QuizQuestion(number="1", question=f"Q_{captured_counts}", answer=f"Ans_{captured_counts}")]
            )

        self.mock_ai.analyze_quiz.side_effect = mock_analyze

        # Queue 3 captures rapidly
        for i in range(3):
            self.app._last_capture_time = 0.0
            self.app.on_capture_hotkey()

        # Wait for all 3 to finish
        self.app._capture_queue.join()

        # All 3 were processed in FIFO sequence
        self.assertEqual(self.mock_ai.analyze_quiz.call_count, 3)
        self.assertEqual(len(self.app._answer_history), 3)

        # Check sequential numbering 1, 2, 3
        self.assertEqual(self.app._answer_history[0]["number"], "1")
        self.assertEqual(self.app._answer_history[1]["number"], "2")
        self.assertEqual(self.app._answer_history[2]["number"], "3")

    def test_alt_r_resets_history_and_cache(self):
        """Verify Alt+R clears both answer history and image cache"""
        test_img = create_mock_image("Câu X")
        self.app.screenshot_manager.capture_screen = MagicMock(return_value=test_img)
        self.app.screenshot_manager.save_to_memory = MagicMock(return_value=b"bytes")
        self.mock_ai.analyze_quiz.return_value = QuizResult(
            questions=[QuizQuestion(number="1", question="Câu X", answer="C")]
        )

        self.app.on_capture_hotkey()
        self.app._capture_queue.join()

        self.assertEqual(len(self.app._answer_history), 1)
        self.assertEqual(len(self.app._image_cache), 1)

        # Reset via Alt+R
        self.app.on_reset_answers_hotkey()

        self.assertEqual(len(self.app._answer_history), 0)
        self.assertEqual(len(self.app._image_cache), 0)
        self.assertIsNone(self.app._latest_result)

        # Now capturing the same image again will call AI (cache miss after reset)
        self.app._last_capture_time = 0.0
        self.app.on_capture_hotkey()
        self.app._capture_queue.join()

        self.assertEqual(self.mock_ai.analyze_quiz.call_count, 2)


if __name__ == '__main__':
    unittest.main()
