"""
AWS Bedrock API Client Module
Communicates with AWS Bedrock API (Claude) to analyze multiple-choice questions
"""

import json
import base64
import time
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from models import QuizResult, QuizQuestion
from logger import Logger


class NoQuestionsFoundError(Exception):
    """Exception raised when no questions are found in the response"""
    pass


class BedrockAPIClient:
    """Client to communicate with AWS Bedrock API (Claude)"""
    
    def __init__(self, region: str = "us-east-1", model_id: Optional[str] = None, logger: Optional[Logger] = None):
        """
        Initialize Bedrock API Client
        
        Args:
            region: AWS region (default: us-east-1)
            model_id: Model ID to use (optional, auto-detect from env)
            logger: Logger instance (optional)
        
        Note:
            Need to setup AWS credentials first:
            - AWS_ACCESS_KEY_ID
            - AWS_SECRET_ACCESS_KEY
            - AWS_SESSION_TOKEN (optional)
        """
        self.region = region
        self.logger = logger
        self.client = None
        
        # Get model from env or use cross-region inference profile (higher quota)
        if model_id:
            self.model_id = model_id
        else:
            import os
            # Use cross-region inference profile for higher quota (4 req/min vs 1 req/min)
            self.model_id = os.getenv('AWS_BEDROCK_MODEL', 'us.anthropic.claude-3-5-sonnet-20240620-v1:0')
        
        self.initialize()
    
    def initialize(self) -> None:
        """
        Initialize Bedrock client
        
        Raises:
            Exception: If cannot initialize client
        """
        try:
            self.client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region
            )
            if self.logger:
                self.logger.info(f"Bedrock API client initialized successfully (region: {self.region})")
        except Exception as e:
            error_msg = f"Failed to initialize Bedrock client: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_prompt(self) -> str:
        """
        Create prompt for Claude to analyze multiple-choice questions
        
        Returns:
            Prompt string
        """
        return """Analyze this image and extract ALL multiple-choice questions.

IMPORTANT:
- Identify EXACTLY the question numbers from the image (e.g., "13.", "14.", "Question 15")
- If no clear numbering, number from 1, 2, 3...
- Extract ALL questions completely, don't miss any
- Each question must have: question_number, question, options, correct_answer
- If no questions found, return empty array

JSON Format:
{
  "total_questions": 3,
  "questions": [
    {
      "question_number": "13",
      "question": "Full question content",
      "options": {
        "A": "Option A",
        "B": "Option B", 
        "C": "Option C",
        "D": "Option D"
      },
      "correct_answer": "A"
    },
    {
      "question_number": "14",
      "question": "Next question",
      "options": {
        "A": "Option A",
        "B": "Option B"
      },
      "correct_answer": "B"
    }
  ]
}

RETURN ONLY JSON, no additional text."""
    
    def analyze_quiz(self, image_data: bytes) -> QuizResult:
        """
        Send image to Claude to analyze multiple-choice questions
        
        Args:
            image_data: Image data as bytes
            
        Returns:
            QuizResult object containing list of questions
            
        Raises:
            Exception: If error calling API or parsing response
        """
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": self._create_prompt()
                            }
                        ]
                    }
                ]
            }
            
            if self.logger:
                self.logger.info("Sending request to Bedrock API (Claude)")
            
            start_time = time.time()
            
            # Call Bedrock API
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            elapsed_time = time.time() - start_time
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if self.logger:
                self.logger.info(f"Received response from Bedrock API in {elapsed_time:.2f}s")
            
            # Extract text from Claude response
            content = response_body.get('content', [])
            if not content:
                raise ValueError("Empty response from Claude")
            
            text_content = content[0].get('text', '')
            
            if self.logger:
                self.logger.info(f"Raw response (first 500 chars): {text_content[:500]}")
            
            # Parse JSON response
            return self.parse_response(text_content)
            
        except ClientError as e:
            error_msg = f"AWS Bedrock API error: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error analyzing quiz: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def parse_response(self, response_text: str) -> QuizResult:
        """
        Parse response from Claude into QuizResult
        
        Args:
            response_text: Text response from Claude
            
        Returns:
            QuizResult object
            
        Raises:
            ValueError: If cannot parse or no questions found
        """
        try:
            # Clean response - remove markdown code blocks
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            if self.logger:
                self.logger.info(f"Cleaned response (first 500 chars): {cleaned[:500]}")
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate structure
            if 'questions' not in data:
                raise ValueError("Response missing 'questions' field")
            
            questions_data = data['questions']
            
            if not isinstance(questions_data, list):
                raise ValueError("'questions' field must be an array")
            
            if len(questions_data) == 0:
                if self.logger:
                    self.logger.error("Failed to parse response: No valid questions found in response")
                raise NoQuestionsFoundError("No valid questions found in response")
            
            # Get total_questions from response (if available)
            total_questions = data.get('total_questions', len(questions_data))
            
            # Convert to QuizQuestion objects
            questions = []
            for idx, q_data in enumerate(questions_data, 1):
                try:
                    # Get question number from response (if available), fallback to idx
                    question_number = q_data.get('question_number', str(idx))
                    
                    # Format: number, question, answer (matching QuizQuestion model)
                    question = QuizQuestion(
                        number=str(question_number),
                        question=q_data.get('question', ''),
                        answer=q_data.get('correct_answer', '')
                    )
                    questions.append(question)
                except Exception as e:
                    if self.logger:
                        self.logger.warn(f"Skipping invalid question: {str(e)}")
                    continue
            
            if len(questions) == 0:
                raise NoQuestionsFoundError("No valid questions after parsing")
            
            # Log number of questions
            if self.logger:
                self.logger.info(f"Parsed {len(questions)} questions successfully (total in image: {total_questions})")
                for i, q in enumerate(questions, 1):
                    self.logger.info(f"  Q{i}: {q.question[:50]}... -> Answer: {q.answer}")
            
            # Add timestamp
            import time
            return QuizResult(
                questions=questions, 
                timestamp=time.time(),
                total_questions=total_questions
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse error: {str(e)}"
            if self.logger:
                self.logger.error(f"Parse error: {error_msg}")
            raise ValueError(error_msg)
        except NoQuestionsFoundError:
            raise
        except Exception as e:
            error_msg = f"Error parsing response: {str(e)}"
            if self.logger:
                self.logger.error(f"Parse error: {error_msg}")
            raise ValueError(error_msg)
