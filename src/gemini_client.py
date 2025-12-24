"""
Gemini API Client Module
Communicate with Google Gemini API to analyze quiz questions
Using new google-genai package
"""

import json
import time
import base64
from typing import Optional
from google import genai
from google.genai import types
from models import QuizResult, QuizQuestion
from logger import Logger


# Question modes
MODE_MULTIPLE_CHOICE = "multiple_choice"
MODE_ESSAY = "essay"


class NoQuestionsFoundError(Exception):
    """Exception raised when no questions are found in the response"""
    pass


class GeminiAPIClient:
    """Client to communicate with Gemini API"""
    
    def __init__(self, api_key: str, logger: Optional[Logger] = None, mode: str = MODE_MULTIPLE_CHOICE):
        """
        Initialize Gemini API Client
        
        Args:
            api_key: Google Gemini API key
            logger: Logger instance (optional)
            mode: Question mode - "multiple_choice" or "essay"
        
        Raises:
            ValueError: If API key is empty or invalid
        """
        if not api_key or api_key.strip() == '':
            raise ValueError("API key cannot be empty")
        
        self.api_key = api_key
        self.client = None
        self.logger = logger
        self.mode = mode
        self.model_name = "gemini-2.0-flash"
        self.initialize()
    
    def set_mode(self, mode: str) -> None:
        """Set question answering mode"""
        if mode in [MODE_MULTIPLE_CHOICE, MODE_ESSAY]:
            self.mode = mode
            if self.logger:
                self.logger.info(f"Mode changed to: {mode}")
    
    def initialize(self) -> None:
        """
        Initialize Gemini client with API key
        
        Raises:
            Exception: If unable to initialize client
        """
        try:
            self.client = genai.Client(api_key=self.api_key)
            
            if self.logger:
                self.logger.info("Gemini API client initialized successfully")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize Gemini API: {str(e)}", exc_info=True)
            raise
    
    def build_prompt(self) -> str:
        """
        Create prompt template based on current mode
        
        Returns:
            Prompt string to send to Gemini API
        """
        if self.mode == MODE_ESSAY:
            return self._build_essay_prompt()
        else:
            return self._build_multiple_choice_prompt()
    
    def _build_multiple_choice_prompt(self) -> str:
        """Build prompt for multiple choice questions"""
        return """You are an assistant that answers multiple-choice questions. Analyze this image and:

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
    
    def _build_essay_prompt(self) -> str:
        """Build prompt for essay/open-ended questions"""
        return """You are an intelligent assistant that answers questions. Analyze this image and:

IDENTIFY any questions in the image:
- Essay questions, open-ended questions
- Short answer questions
- Problem-solving questions
- Any text that asks for an explanation or solution

For each question found, provide a COMPLETE and DETAILED answer.

If NO questions found, return:
{
  "questions": []
}

If questions found, return JSON:
{
  "questions": [
    {
      "number": "1",
      "question": "Brief summary of the question",
      "answer": "Complete detailed answer with explanation"
    }
  ]
}

IMPORTANT:
- Provide thorough, educational answers
- Include explanations and reasoning
- If it's a math/science problem, show the solution steps
- Keep answers concise but complete

Return only JSON, no other text."""

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
        if not self.client:
            raise Exception("Gemini client not initialized")
        
        try:
            if self.logger:
                self.logger.info("Sending request to Gemini API")
            
            start_time = time.time()
            
            # Create prompt
            prompt = self.build_prompt()
            
            # Prepare image as base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create content with image and text
            contents = [
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                types.Part.from_text(text=prompt)
            ]
            
            # Send request to Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95,
                )
            )
            
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
            if self.logger:
                self.logger.info(f"No questions found: {str(e)}")
            raise
        
        except ValueError as e:
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
            if self.logger:
                self.logger.info(f"Received response with {len(response_text)} characters")
            
            # Remove markdown code block if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
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
