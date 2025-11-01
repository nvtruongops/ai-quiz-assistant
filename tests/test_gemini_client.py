"""
Unit tests for Gemini API Client
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from src.gemini_client import GeminiAPIClient
from src.models import QuizResult, QuizQuestion
from src.logger import Logger


class TestGeminiAPIClient(unittest.TestCase):
    """Test cases for GeminiAPIClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key_12345"
        self.logger = Mock(spec=Logger)
    
    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model:
                client = GeminiAPIClient(self.api_key, self.logger)
                self.assertEqual(client.api_key, self.api_key)
                self.assertIsNotNone(client.model)
    
    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key raises ValueError"""
        with self.assertRaises(ValueError) as context:
            GeminiAPIClient("", self.logger)
        self.assertIn("không được để trống", str(context.exception))
    
    def test_build_prompt(self):
        """Test prompt building"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                prompt = client.build_prompt()
                
                # Verify prompt contains key elements
                self.assertIn("trắc nghiệm", prompt)
                self.assertIn("JSON", prompt)
                self.assertIn("questions", prompt)
                self.assertIn("number", prompt)
                self.assertIn("question", prompt)
                self.assertIn("answer", prompt)
    
    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                
                response_text = json.dumps({
                    "questions": [
                        {
                            "number": "1",
                            "question": "What is 2+2?",
                            "answer": "A"
                        },
                        {
                            "number": "2",
                            "question": "What is the capital of France?",
                            "answer": "B"
                        }
                    ]
                })
                
                result = client.parse_response(response_text)
                
                self.assertIsInstance(result, QuizResult)
                self.assertEqual(len(result.questions), 2)
                self.assertEqual(result.questions[0].number, "1")
                self.assertEqual(result.questions[0].answer, "A")
    
    def test_parse_response_with_markdown_code_block(self):
        """Test parsing response with markdown code block"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                
                response_text = """```json
{
  "questions": [
    {
      "number": "1",
      "question": "Test question",
      "answer": "C"
    }
  ]
}
```"""
                
                result = client.parse_response(response_text)
                
                self.assertIsInstance(result, QuizResult)
                self.assertEqual(len(result.questions), 1)
                self.assertEqual(result.questions[0].answer, "C")
    
    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON raises ValueError"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                
                with self.assertRaises(ValueError) as context:
                    client.parse_response("This is not JSON")
                self.assertIn("không phải JSON hợp lệ", str(context.exception))
    
    def test_parse_response_missing_questions_field(self):
        """Test parsing response without questions field raises ValueError"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                
                response_text = json.dumps({"data": []})
                
                with self.assertRaises(ValueError) as context:
                    client.parse_response(response_text)
                self.assertIn("thiếu trường 'questions'", str(context.exception))
    
    def test_parse_response_empty_questions(self):
        """Test parsing response with no valid questions raises ValueError"""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                client = GeminiAPIClient(self.api_key, self.logger)
                
                response_text = json.dumps({
                    "questions": [
                        {"number": "1"}  # Missing question and answer
                    ]
                })
                
                with self.assertRaises(ValueError) as context:
                    client.parse_response(response_text)
                self.assertIn("Không tìm thấy câu hỏi hợp lệ", str(context.exception))


if __name__ == '__main__':
    unittest.main()
