"""
Data models for AI Quiz Assistant application.

This module contains dataclasses for representing quiz questions, results, and requests.
"""

from dataclasses import dataclass
from typing import List, Optional
import time


@dataclass
class QuizQuestion:
    """Represents a single quiz question with its answer.
    
    Attributes:
        number: Question number (e.g., "1", "2", "3")
        question: The question text content
        answer: The answer (e.g., "A", "B", "C", "D", "True", "False")
    """
    number: str
    question: str
    answer: str


@dataclass
class QuizResult:
    """Represents the result of a quiz analysis containing multiple questions.
    
    Attributes:
        questions: List of QuizQuestion objects
        timestamp: Unix timestamp when the result was created
        total_questions: Total number of questions detected in the image
    """
    questions: List[QuizQuestion]
    timestamp: float
    total_questions: int = 0  # Number of questions in the image
    
    def format_display(self) -> str:
        """Format the quiz result for display in popup window.
        
        Returns:
            Formatted string with questions and answers - compact format
        """
        lines = []
        
        # NO HEADER - Only show questions and answers
        for q in self.questions:
            # Shorten question: only take first 7 words
            question_words = q.question.split()[:7]
            short_question = " ".join(question_words) + ("..." if len(q.question.split()) > 7 else "")
            
            # Display: "Question 13: ... → A"
            lines.append(f"Question {q.number}: {short_question}")
            lines.append(f"→ {q.answer}")
        return "\n".join(lines).strip()


@dataclass
class Request:
    """Represents a quiz analysis request with its status and result.
    
    Attributes:
        id: Unique identifier for the request
        status: Current status - "PROCESSING", "COMPLETED", "ERROR", or "NONE"
        created_at: Unix timestamp when the request was created
        result: QuizResult object if completed, None otherwise
        error: Error message if status is ERROR, None otherwise
    """
    id: str
    status: str  # PROCESSING, COMPLETED, ERROR, NONE
    created_at: float
    result: Optional[QuizResult]
    error: Optional[str]
    
    def get_elapsed_time(self) -> float:
        """Calculate the elapsed time since the request was created.
        
        Returns:
            Time elapsed in seconds as a float
        """
        return time.time() - self.created_at
