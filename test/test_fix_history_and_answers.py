import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
import unittest
from unittest.mock import MagicMock

from base_client import BaseAIClient, MODE_MULTIPLE_CHOICE, MODE_MC_EXPLANATION, DISPLAY_LETTER_AND_TEXT
from models import QuizQuestion, QuizResult
from main import QuizAssistantApp
from config_manager import ConfigManager
from custom_client import CustomAPIClient
from gemini_client import GeminiAPIClient


class DummyClient(BaseAIClient):
    def analyze_quiz(self, image_bytes, timeout=60):
        pass
    def test_connection(self):
        return True, "OK", 0.1


class TestHistoryAndAnswerFixes(unittest.TestCase):

    def test_corrupt_history_filtering(self):
        """Verify that corrupted punctuation entries in answers.json are sanitized"""
        corrupted_data = [
            {'number': '', 'question': '', 'answer': '['},
            {'number': '', 'question': '', 'answer': '{'},
            {'number': '"number"', 'question': '', 'answer': ':'},
            {'number': '"4"', 'question': '', 'answer': ','},
            {'number': '1', 'question': 'Hà Nội là thủ đô của nước nào?', 'answer': 'A. Việt Nam'},
            {'number': '', 'question': '', 'answer': '}'},
            {'number': '', 'question': '', 'answer': ']'}
        ]

        os.makedirs("logs", exist_ok=True)
        test_file = "logs/test_answers.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(corrupted_data, f)

        # Mock QuizAssistantApp
        app = QuizAssistantApp.__new__(QuizAssistantApp)
        app._answer_file = test_file
        app._answer_txt_file = "logs/test_answers.txt"
        app._answer_history = []
        app.logger = MagicMock()

        app._load_answers_from_file()

        # Should keep only the 1 valid question and renumber it to 1
        self.assertEqual(len(app._answer_history), 1)
        self.assertEqual(app._answer_history[0]['number'], '1')
        self.assertEqual(app._answer_history[0]['answer'], 'A. Việt Nam')

        if os.path.exists(test_file):
            os.remove(test_file)

    def test_missing_answer_fallback_in_base_client(self):
        """Verify that if LLM omits 'answer' field, fallback mechanism avoids blank UI"""
        client = DummyClient()
        raw_json_no_answer = """
        <thinking>
        Some deep thinking here...
        </thinking>
        {
            "questions": [
                {
                    "number": "1",
                    "question": "Đại hội Đảng lần thứ VIII diễn ra khi nào?",
                    "explanation": "Đáp án đúng là B vì Đại hội họp năm 1996."
                }
            ]
        }
        """
        res = client.parse_quiz_response(raw_json_no_answer)
        self.assertEqual(len(res.questions), 1)
        q = res.questions[0]
        self.assertEqual(q.number, "1")
        # Should extract 'B' from explanation regex
        self.assertTrue("B" in q.answer)

        # Case where no explanation either
        raw_json_blank = """
        {
            "questions": [
                {
                    "number": "1",
                    "question": "Câu hỏi không có đáp án"
                }
            ]
        }
        """
        res2 = client.parse_quiz_response(raw_json_blank)
        self.assertEqual(len(res2.questions), 1)
        self.assertNotEqual(res2.questions[0].answer, "")
        self.assertTrue("Chưa xác định" in res2.questions[0].answer or "Answer not identified" in res2.questions[0].answer)

    def test_thinking_tag_cleaning(self):
        """Verify that <thinking>, <thought>, <think> blocks are stripped cleanly"""
        client = DummyClient()
        text_with_think = "<think>Let me reflect on this</think>```json\n{\"questions\": []}\n```"
        cleaned = client.clean_json_response(text_with_think)
        self.assertEqual(cleaned, '{"questions": []}')

    def test_real_screenshot_with_both_providers(self):
        """Verify that both Gemini and Custom Local return valid non-blank answers on actual exam screenshot"""
        img_path = os.path.join(_proj_root, "logs", "screenshots", "screenshot_20261107_190525.png")
        if not os.path.exists(img_path):
            self.skipTest("Screenshot file not found for test")

        with open(img_path, "rb") as f:
            img_bytes = f.read()

        cfg = ConfigManager()

        # 1. Test Gemini
        gemini_key = cfg.get("GEMINI_API_KEY")
        if gemini_key:
            gemini_client = GeminiAPIClient(
                api_key=gemini_key,
                model_name=cfg.get("GEMINI_MODEL"),
                mode=MODE_MULTIPLE_CHOICE,
                answer_display_mode=DISPLAY_LETTER_AND_TEXT
            )
            g_res = gemini_client.analyze_quiz(img_bytes)
            self.assertTrue(len(g_res.questions) >= 1)
            for q in g_res.questions:
                self.assertTrue(len(q.answer.strip()) > 0)
                self.assertFalse(q.answer.strip() == "→ Đáp án:")
                print(f"[Gemini] Q: {q.question[:40]}... -> Ans: {q.answer}")

        # 2. Test Custom API
        custom_url = cfg.get("CUSTOM_API_URL")
        custom_key = cfg.get("CUSTOM_API_KEY")
        custom_model = cfg.get("CUSTOM_MODEL")
        if custom_url and custom_key and custom_model:
            custom_client = CustomAPIClient(
                api_url=custom_url,
                api_key=custom_key,
                model=custom_model,
                mode=MODE_MULTIPLE_CHOICE,
                answer_display_mode=DISPLAY_LETTER_AND_TEXT
            )
            c_res = custom_client.analyze_quiz(img_bytes)
            self.assertTrue(len(c_res.questions) >= 1)
            for q in c_res.questions:
                self.assertTrue(len(q.answer.strip()) > 0)
                self.assertFalse(q.answer.strip() == "→ Đáp án:")
                print(f"[Custom] Q: {q.question[:40]}... -> Ans: {q.answer}")


if __name__ == '__main__':
    unittest.main()
