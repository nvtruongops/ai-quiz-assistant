"""
Gemini API Client Module
Communicate with Google Gemini API to analyze quiz questions
"""

import json
import time
from typing import Optional
import google.generativeai as genai
from models import QuizResult, QuizQuestion
from logger import Logger


class NoQuestionsFoundError(Exception):
    """Exception raised when no questions are found in the response"""
    pass


class GeminiAPIClient:
    """Client to communicate with Gemini API"""
    
    def __init__(self, api_key: str, logger: Optional[Logger] = None):
        """
        Initialize Gemini API Client
        
        Args:
            api_key: Google Gemini API key
            logger: Logger instance (optional)
        
        Raises:
            ValueError: If API key is empty or invalid
        """
        if not api_key or api_key.strip() == '':
            raise ValueError("API key không được để trống")
        
        self.api_key = api_key
        self.model = None
        self.logger = logger
        self.initialize()
    
    def initialize(self) -> None:
        """
        Initialize Gemini model with API key
        Use gemini-1.5-flash for fast processing
        
        Raises:
            Exception: If unable to initialize model
        """
        try:
            genai.configure(api_key=self.api_key)
            # Sử dụng gemini-2.5-flash cho xử lý hình ảnh nhanh và hiệu quả
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            
            if self.logger:
                self.logger.info("Gemini API client initialized successfully")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Gemini API: {str(e)}", exc_info=True)
            raise
    
    def build_prompt(self) -> str:
        """
        Create prompt template for Gemini API
        Require identification and return JSON format
        
        Returns:
            Prompt string to send to Gemini API
        """
        prompt = """You are an assistant that answers multiple-choice questions. Analyze this image and:

IMPORTANT: ONLY identify REAL multiple-choice questions:
- Clear format: "Question 1:", "Question 2:", "Q1:", etc.
- Have answer choices: A, B, C, D or True/False
- Are knowledge-testing questions, exams, quizzes

DO NOT identify:
- Code, programming commands
- Text editor, terminal, console
- Task lists, notes
- Regular text that is not quiz questions

If NO real quiz questions found, return:
{
  "questions": []
}

If questions found, return JSON:
{
  "questions": [
    {
      "number": "1",
      "question": "Question content",
      "answer": "A"
    }
  ]
}

Return only JSON, no other text."""
        
        return prompt
    
    def analyze_quiz(self, image_bytes: bytes, timeout: int = 30) -> QuizResult:
        """
        Send image to Gemini API and get question analysis
        
        Args:
            image_bytes: Image in bytes (PNG format)
            timeout: Timeout for API call (default: 30 seconds)
        
        Returns:
            QuizResult object containing question list and answers
        
        Raises:
            ValueError: If API key invalid (authentication failed)
            TimeoutError: If API not responding within timeout
            Exception: Other API errors
        """
        if not self.model:
            raise Exception("Gemini model not initialized")
        
        try:
            if self.logger:
                self.logger.info("Sending request to Gemini API")
            
            start_time = time.time()
            
            # Create prompt
            prompt = self.build_prompt()
            
            # Prepare image data
            image_parts = [
                {
                    "mime_type": "image/png",
                    "data": image_bytes
                }
            ]
            
            # Send request to Gemini API with timeout
            # Note: google.generativeai does not support timeout directly
            # We check elapsed time after receiving response
            response = self.model.generate_content([prompt, image_parts[0]])
            
            elapsed_time = time.time() - start_time
            
            # Check timeout
            if elapsed_time > timeout:
                if self.logger:
                    self.logger.error(f"API call timeout after {elapsed_time:.2f} seconds")
                raise TimeoutError(f"API not responding within {timeout} seconds")
            
            if self.logger:
                self.logger.info(f"Received response from Gemini API in {elapsed_time:.2f}s")
            
            # Parse response
            result = self.parse_response(response.text)
            
            return result
            
        except NoQuestionsFoundError as e:
            # No questions found - not an error, just no results
            if self.logger:
                self.logger.info(f"No questions found: {str(e)}")
            raise
        
        except ValueError as e:
            # JSON parsing or validation error
            if self.logger:
                self.logger.error(f"Parse error: {str(e)}", exc_info=True)
            raise
        
        except TimeoutError as e:
            if self.logger:
                self.logger.error(f"Timeout error: {str(e)}")
            raise
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"API call failed: {str(e)}", exc_info=True)
            raise Exception(f"Error calling API: {str(e)}")
    
    def parse_response(self, response_text: str) -> QuizResult:
        """
        Parse JSON response from Gemini API into QuizResult
        
        Args:
            response_text: Response text from Gemini API
        
        Returns:
            QuizResult object
        
        Raises:
            ValueError: If response not valid JSON or missing required fields
        """
        try:
            # Log raw response for debugging
            if self.logger:
                self.logger.info(f"Raw response (first 500 chars): {response_text[:500]}")
            
            # Remove markdown code block if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]  # Remove ```json
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]  # Remove ```
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]  # Remove ```
            cleaned_text = cleaned_text.strip()
            
            if self.logger:
                self.logger.info(f"Cleaned response (first 500 chars): {cleaned_text[:500]}")
            
            # Parse JSON
            data = json.loads(cleaned_text)
            
            # Validate structure
            if "questions" not in data:
                raise ValueError("Response missing 'questions' field")
            
            if not isinstance(data["questions"], list):
                raise ValueError("'questions' field must be array")
            
            # Parse questions
            questions = []
            for q_data in data["questions"]:
                # Validate required fields
                if "number" not in q_data or "question" not in q_data or "answer" not in q_data:
                    if self.logger:
                        self.logger.error(f"Question missing required fields: {q_data}")
                    continue
                
                question = QuizQuestion(
                    number=str(q_data["number"]),
                    question=q_data["question"],
                    answer=q_data["answer"]
                )
                questions.append(question)
            
            if not questions:
                raise NoQuestionsFoundError("No valid questions found in response")
            
            # Create QuizResult
            result = QuizResult(
                questions=questions,
                timestamp=time.time()
            )
            
            if self.logger:
                self.logger.info(f"Successfully parsed {len(questions)} questions from response")
            
            return result
            
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"Failed to parse JSON response: {str(e)}", exc_info=True)
            raise ValueError(f"Response not valid JSON: {str(e)}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse response: {str(e)}", exc_info=True)
            raise ValueError(f"Error parsing response: {str(e)}")
