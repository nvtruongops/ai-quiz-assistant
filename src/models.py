"""
Data models for AI Quiz Assistant application.

This module contains dataclasses for representing quiz questions, results, and requests.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class QuizQuestion:
    """Represents a single quiz question with its answer and optional explanation.

    Attributes:
        number: Sequential question number (e.g., "1", "2", "3")
        question: The question text content
        answer: The answer (e.g., "B. Carbon Dioxide", "A", or detailed explanation)
        option_letter: Option letter (e.g. "B")
        option_text: Option text (e.g. "Carbon Dioxide")
        exam_number: Original number from exam screen if different
        explanation: Detailed reasoning / explanation for the chosen answer
    """
    number: str
    question: str
    answer: str
    option_letter: str = ""
    option_text: str = ""
    exam_number: str = ""
    explanation: str = ""

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


@dataclass
class QuizResult:
    """Represents the result of a quiz analysis containing multiple questions.

    Attributes:
        questions: List of QuizQuestion objects
        timestamp: Unix timestamp when the result was created
        total_questions: Total number of questions detected in the image
        provider_name: Provider that generated the result (e.g., "Gemini", "Custom")
        model_name: Model used (e.g., "gemini-3.5-flash-lite", "claude-sonnet-4.5")
        mode: Question mode ("multiple_choice", "multiple_choice_explanation", or "essay")
    """
    questions: List[QuizQuestion]
    timestamp: float = field(default_factory=time.time)
    total_questions: int = 0
    provider_name: str = "AI"
    model_name: str = ""
    mode: str = "multiple_choice"

    def format_display(self, include_explanation: bool = False) -> str:
        """Format the quiz result for display in popup window.

        Args:
            include_explanation: Whether to append full explanation text

        Returns:
            Formatted string with questions and answers
        """
        lines = []
        is_essay = (self.mode == "essay")

        for q in self.questions:
            if is_essay:
                lines.append(f"Question {q.number}: {q.question}")
                lines.append(f"💡 Answer / Solution:\n{q.answer}\n")
            else:
                lines.append(f"Question {q.number}: {q.question}")
                lines.append(f"→ Answer: {q.answer}")
                if include_explanation and q.explanation:
                    lines.append(f"💡 Explanation: {q.explanation}\n")

        return "\n".join(lines).strip()

    def format_copy(self, include_explanation: bool = True) -> str:
        """Format the quiz result for clipboard copying.

        Returns:
            Clean text representation for pasting
        """
        lines = []
        mode_label = "Essay" if self.mode == "essay" else ("Multiple Choice + Exp" if self.mode == "multiple_choice_explanation" else "Multiple Choice")
        lines.append(f"=== QUIZ ANALYSIS RESULT ({self.provider_name} | {mode_label} - {len(self.questions)} questions) ===")
        for q in self.questions:
            lines.append(f"\nQuestion {q.number}: {q.question}")
            lines.append(f"Answer: {q.answer}")
            if include_explanation and q.explanation:
                lines.append(f"Explanation: {q.explanation}")
        return "\n".join(lines).strip()


@dataclass
class Request:
    """Represents a quiz analysis request with its status and result."""
    id: str
    status: str  # PROCESSING, COMPLETED, ERROR, NONE
    created_at: float
    result: Optional[QuizResult] = None
    error: Optional[str] = None

    def get_elapsed_time(self) -> float:
        """Calculate the elapsed time since the request was created."""
        return time.time() - self.created_at
