"""
Base AI Client Module
Abstract base class for all AI vision providers (Gemini, OpenAI-compatible, etc.)
"""

import abc
import json
import re
import time
from typing import Optional, List, Tuple

try:
    from models import QuizResult, QuizQuestion
    from logger import Logger
except ImportError:
    from src.models import QuizResult, QuizQuestion
    from src.logger import Logger

# Standard question modes
MODE_MULTIPLE_CHOICE = "multiple_choice"
MODE_MC_EXPLANATION = "multiple_choice_explanation"
MODE_ESSAY = "essay"

VALID_MODES = [MODE_MULTIPLE_CHOICE, MODE_MC_EXPLANATION, MODE_ESSAY]

# Answer display modes
DISPLAY_LETTER_AND_TEXT = "letter_and_text"  # e.g. "B. Carbon Dioxide"
DISPLAY_LETTER_ONLY = "letter_only"          # e.g. "B"


class AIClientError(Exception):
    """Base exception for AI client errors"""
    pass


class AuthenticationError(AIClientError):
    """Authentication or invalid API key error"""
    pass


class NoQuestionsFoundError(AIClientError):
    """Exception raised when no quiz questions are found in the image"""
    pass


class BaseAIClient(abc.ABC):
    """Abstract base class for AI quiz analysis clients"""

    def __init__(
        self,
        logger: Optional[Logger] = None,
        mode: str = MODE_MULTIPLE_CHOICE,
        answer_display_mode: str = DISPLAY_LETTER_AND_TEXT
    ):
        self.logger = logger
        self.mode = mode if mode in VALID_MODES else MODE_MULTIPLE_CHOICE
        self.answer_display_mode = (
            answer_display_mode
            if answer_display_mode in [DISPLAY_LETTER_AND_TEXT, DISPLAY_LETTER_ONLY]
            else DISPLAY_LETTER_AND_TEXT
        )

    def set_mode(self, mode: str) -> None:
        """Set question answering mode (multiple_choice, multiple_choice_explanation, or essay)"""
        if mode in VALID_MODES:
            self.mode = mode
            if self.logger:
                self.logger.info(f"Question mode switched to: {mode}")

    def set_answer_display_mode(self, display_mode: str) -> None:
        """Set answer format: letter_and_text (e.g. 'B. 56') or letter_only ('B')"""
        if display_mode in [DISPLAY_LETTER_AND_TEXT, DISPLAY_LETTER_ONLY]:
            self.answer_display_mode = display_mode
            if self.logger:
                self.logger.info(f"Answer display mode set to: {display_mode}")

    def build_prompt(self) -> str:
        """Generate prompt text based on the active mode"""
        if self.mode == MODE_ESSAY:
            return self._build_essay_prompt()
        elif self.mode == MODE_MC_EXPLANATION:
            return self._build_mc_explanation_prompt()
        return self._build_multiple_choice_prompt()

    def _build_multiple_choice_prompt(self) -> str:
        """Prompt template for multiple choice quizzes without explanation.
        Handles extracting 1, 2, 3 or more questions visible in the image,
        including single-choice, multi-select (choose 2, 3 or more options), and True/False questions.
        """
        return """You are an expert AI quiz assistant with spatial vision. Analyze this image and extract ALL multiple-choice questions visible, solve them accurately, and find the exact clickable target on screen for each answer choice.

CRITICAL RULES:
1. Extract EVERY real multiple-choice question in the image (there may be 1, 2, 3 or more questions visible on screen).
   - Ignore navigation UI ("Question 1/50", "Submit", "Next", buttons, timer, interface labels).
   - Ignore blank areas, loading screens, or non-quiz text.
2. If NO real quiz question is visible, return:
   {"questions": []}
3. FOR EACH QUESTION:
   - Identify the question text accurately.
   - MANDATORY ANSWER: Even if the quiz on screen is unanswered (no radio button selected or 0% progress), YOU MUST SOLVE IT YOURSELF and provide the correct option.
   - The "answer" field is STRICTLY MANDATORY. NEVER omit "answer" and NEVER leave it blank.
   - FORMAT OF "answer":
     * Single-choice: strictly "<Letter>. <Option Text>" (e.g. "B. Carbon Dioxide", "A. Paris", "B. 56").
     * Multi-select questions (e.g. choose 2 or 3 correct answers / select all that apply): list ALL correct options (e.g. "A, C" or "A. Text 1, C. Text 2" or "A, B, D").
     * True/False questions (Đúng/Sai, True/False): provide the truth value (e.g. "A. Đúng", "B. Sai", "Đúng", "Sai", or for multiple statements: "1-Đúng, 2-Sai, 3-Đúng").
   - CLICK TARGETS ("clicks"):
     * Locate the exact clickable target on the screen (the radio button circle, checkbox, or option letter/text) for the correct answer choice.
     * Provide normalized coordinates [y, x] in range 0 to 1000 (0,0 is top-left, 1000,1000 is bottom-right).
     * If multi-select, include a click point for every selected choice.
   - Do NOT include any explanations or commentary in this mode.

Return STRICT JSON format:
{
  "questions": [
    {
      "number": "1",
      "question": "Exact question text here",
      "answer": "B. Carbon Dioxide",
      "clicks": [
        {"option": "B", "point": [234, 88]}
      ]
    }
  ]
}

Return ONLY valid JSON, without surrounding markdown or conversational text."""

    def _build_mc_explanation_prompt(self) -> str:
        """Prompt template for multiple choice quizzes WITH concise explanation.
        Handles extracting 1, 2, 3 or more questions with clean answer, coordinates, and separate explanation,
        including single-choice, multi-select, and True/False questions.
        """
        return """You are an expert AI academic tutor with spatial vision. Analyze this image and solve ALL multiple-choice questions visible, locating click targets for each answer.

CRITICAL RULES:
1. Extract EVERY real multiple-choice question in the image (there may be 1, 2, 3 or more questions visible on screen).
   - Ignore navigation UI, timer, buttons, interface labels.
2. If NO real quiz question is visible, return:
   {"questions": []}
3. FOR EACH QUESTION:
   - "number": Sequential number ("1", "2", ...).
   - "question": Exact question text.
   - MANDATORY ANSWER: Even if the quiz on screen is unanswered, YOU MUST SOLVE IT YOURSELF. The "answer" field is STRICTLY MANDATORY and cannot be omitted or blank.
   - FORMAT OF "answer":
     * Single-choice: "<Letter>. <Option Text>" (e.g. "B. Carbon Dioxide", "B. 56").
     * Multi-select questions (choose 2 or 3 options): list ALL correct options (e.g. "A, C" or "A. Text 1, C. Text 2").
     * True/False questions (Đúng/Sai, True/False): provide the choice or truth value (e.g. "A. Đúng", "Đúng", "Sai").
   - CLICK TARGETS ("clicks"):
     * Locate the exact clickable target on the screen (the radio button circle, checkbox, or option letter/text) for the correct answer choice.
     * Provide normalized coordinates [y, x] in range 0 to 1000 (0,0 is top-left, 1000,1000 is bottom-right).
     * If multi-select, include a click point for every selected choice.
   - "explanation": A clear, concise explanation (1-3 sentences) explaining WHY this answer is correct.

Return STRICT JSON format:
{
  "questions": [
    {
      "number": "1",
      "question": "Exact question text here",
      "answer": "B. Carbon Dioxide",
      "clicks": [
        {"option": "B", "point": [234, 88]}
      ],
      "explanation": "Clear and concise explanation of why this option is correct."
    }
  ]
}

Return ONLY valid JSON, without surrounding markdown or commentary."""

    def _build_essay_prompt(self) -> str:
        """Prompt template for essay / open-ended questions"""
        return """You are an expert AI academic tutor. Analyze this image and find any essay questions, open-ended exercises, or math/science problems.

CRITICAL RULES:
1. Identify all essay or problem questions visible in the image (whether 1, 2, or more questions).
2. If no questions are found, return:
   {"questions": []}
3. For each question:
   - "number": Sequential number ("1", "2", ...)
   - "question": Clear summary or statement of the question/problem.
   - MANDATORY ANSWER: The "answer" field is MANDATORY. Provide step-by-step solution, detailed explanation, or comprehensive answer.

Return STRICT JSON format:
{
  "questions": [
    {
      "number": "1",
      "question": "Brief summary or statement of the problem",
      "answer": "Step-by-step solution or detailed explanation"
    }
  ]
}

Return ONLY valid JSON, without surrounding markdown or commentary."""

    def clean_json_response(self, text: str) -> str:
        """Remove markdown code fences, think/thought tags, and whitespace"""
        if not text:
            return "{}"

        cleaned = text.strip()

        # Remove <thinking>...</thinking>, <thought>...</thought>, <think>...</think> blocks
        cleaned = re.sub(r'<(?:thinking|thought|think)>[\s\S]*?</(?:thinking|thought|think)>', '', cleaned, flags=re.IGNORECASE).strip()
        # Clean unclosed thinking tags if any
        cleaned = re.sub(r'<(?:thinking|thought|think)>[\s\S]*$', '', cleaned, flags=re.IGNORECASE).strip()

        # Remove markdown code block markers
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned.strip()

    @staticmethod
    def parse_mc_answer(raw: str) -> Tuple[str, str, str]:
        """
        Parse raw multiple choice answer into (letter(s), text, full).
        Supports:
        - Single choice: 'B. Carbon Dioxide' -> ('B', 'Carbon Dioxide', 'B. Carbon Dioxide')
        - Multi-select (choose 2, 3 or more): 'A, C' -> ('A, C', '', 'A, C')
          'A và B' -> ('A, B', '', 'A và B')
          'A, C. Paris, Lyon' -> ('A, C', 'Paris, Lyon', 'A, C. Paris, Lyon')
        - True / False (Đúng/Sai, True/False): 'Đúng' -> ('Đúng', '', 'Đúng')
          'A. Đúng' -> ('A', 'Đúng', 'A. Đúng')
        """
        raw = raw.strip()

        # Multi-select letter check (e.g. 'A, C', 'A, B, D', 'A và B', 'A & C', 'A, C. Paris, Lyon')
        sep_pattern = r'(?:\s*(?:[,;&\+]|\bvà\b|\band\b)\s*)'
        m_multi = re.match(r'^([A-E]' + sep_pattern + r'[A-E](?:' + sep_pattern + r'[A-E])*)(?:[\.\:\-\s]+(.*))?$', raw, re.IGNORECASE)
        if m_multi:
            letters = re.findall(r'\b[A-E]\b', m_multi.group(1), re.IGNORECASE)
            letter_str = ', '.join(l.upper() for l in letters)
            text = (m_multi.group(2) or '').strip()
            full = f"{letter_str}. {text}" if text else raw
            return (letter_str, text, full)

        # Single letter with text (e.g. 'B. Carbon Dioxide', 'A - Đúng', 'B. 56')
        m_single = re.match(r'^([A-E])[\.\:\-\s\)]+(.*)$', raw, re.DOTALL)
        if m_single:
            letter = m_single.group(1).upper()
            text = m_single.group(2).strip()
            full = f"{letter}. {text}" if text else letter
            return (letter, text, full)

        # Single letter fallback (e.g. 'B')
        if re.match(r'^[A-E]$', raw, re.IGNORECASE):
            return (raw.upper(), "", raw.upper())

        # Standalone True/False fallback (e.g. 'Đúng', 'Sai', 'True', 'False')
        if re.match(r'^(Đúng|Sai|True|False)$', raw, re.IGNORECASE):
            norm = raw.capitalize()
            return (norm, "", norm)

        return ("", raw, raw)

    def parse_quiz_response(self, response_text: str) -> QuizResult:
        """
        Parse raw JSON response from AI model into QuizResult
        """
        cleaned_json = self.clean_json_response(response_text)

        try:
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            # Fallback regex extraction of JSON object
            m = re.search(r'(\{[\s\S]*\})', cleaned_json)
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    if self.logger:
                        self.logger.error(f"Failed to parse JSON response: {e}, raw text: {response_text[:200]}")
                    raise ValueError(f"Response not valid JSON: {str(e)}")
            else:
                if self.logger:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                raise ValueError(f"Response not valid JSON: {str(e)}")

        if "questions" not in data or not isinstance(data["questions"], list):
            raise ValueError("Response missing 'questions' list")

        parsed_questions: List[QuizQuestion] = []
        for q_data in data["questions"]:
            if not isinstance(q_data, dict):
                continue
            num = str(q_data.get("number", len(parsed_questions) + 1)).strip()
            q_text = str(q_data.get("question", "")).strip()
            # Strip redundant question number prefixes from question text (e.g. 'Câu 3: What is...')
            clean_q = re.sub(r'^(?:Câu|Question|Bài|Item)\s*\d+[\s\:\.\-]+', '', q_text, flags=re.IGNORECASE).strip()
            if clean_q:
                q_text = clean_q
            raw_ans = str(q_data.get("answer", "")).strip()
            explanation = str(q_data.get("explanation", "")).strip()

            # Robust fallback if model omitted 'answer' field
            if not raw_ans:
                for alt_key in ["solution", "correct_answer", "choice", "option", "result"]:
                    val = str(q_data.get(alt_key, "")).strip()
                    if val:
                        raw_ans = val
                        break

            # If still empty but explanation exists, attempt regex search in explanation
            if not raw_ans and explanation:
                m_ans = re.search(
                    r'(?:đáp án|đáp án đúng|lựa chọn|chọn|câu|answer|choice|option)\s*(?:đúng|chính xác)?\s*(?:là|is)?\s*[:\-]?\s*([A-Ea-e])\b',
                    explanation,
                    re.IGNORECASE
                )
                if m_ans:
                    raw_ans = m_ans.group(1).upper()

            # Ignore pure junk items where both question and answer are absent
            if not q_text and not raw_ans:
                continue

            # If question exists but answer could not be determined at all, avoid blank UI
            if not raw_ans:
                raw_ans = "[Answer not identified - review screenshot]"

            opt_letter = ""
            opt_text = ""

            if self.mode in [MODE_MULTIPLE_CHOICE, MODE_MC_EXPLANATION]:
                letter, text, full = self.parse_mc_answer(raw_ans)
                opt_letter = letter
                opt_text = text

                if self.answer_display_mode == DISPLAY_LETTER_ONLY:
                    final_ans = letter if letter else raw_ans
                else:
                    # DISPLAY_LETTER_AND_TEXT: "B. Carbon Dioxide"
                    final_ans = full if full else raw_ans
            else:
                # Essay mode: keep full explanation
                final_ans = raw_ans

            if not final_ans or not final_ans.strip():
                final_ans = "[Answer not identified]"

            # Parse spatial click targets for auto-fill
            raw_clicks = q_data.get('clicks', [])
            clicks = []
            if isinstance(raw_clicks, list):
                for c in raw_clicks:
                    if isinstance(c, dict):
                        pt = c.get('point') or c.get('click_point') or c.get('coords')
                        if pt and len(pt) >= 2:
                            clicks.append({
                                'option': str(c.get('option', opt_letter)),
                                'point': [float(pt[0]), float(pt[1])]
                            })
                    elif isinstance(c, (list, tuple)) and len(c) >= 2:
                        clicks.append({
                            'option': opt_letter,
                            'point': [float(c[0]), float(c[1])]
                        })
            elif 'click_point' in q_data or 'point' in q_data:
                pt = q_data.get('click_point') or q_data.get('point')
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    clicks.append({
                        'option': opt_letter,
                        'point': [float(pt[0]), float(pt[1])]
                    })
            elif 'box_2d' in q_data and len(q_data['box_2d']) >= 4:
                b = q_data['box_2d']
                cy = (float(b[0]) + float(b[2])) / 2.0
                cx = (float(b[1]) + float(b[3])) / 2.0
                clicks.append({
                    'option': opt_letter,
                    'point': [cy, cx]
                })

            parsed_questions.append(QuizQuestion(
                number=num,
                question=q_text,
                answer=final_ans,
                option_letter=opt_letter,
                option_text=opt_text,
                exam_number=num,
                explanation=explanation,
                clicks=clicks
            ))

        if not parsed_questions:
            raise NoQuestionsFoundError("No valid quiz questions found in image")

        return QuizResult(
            questions=parsed_questions,
            timestamp=time.time(),
            total_questions=len(parsed_questions),
            mode=self.mode
        )

    @abc.abstractmethod
    def analyze_quiz(self, image_bytes: bytes, timeout: int = 45) -> QuizResult:
        """Send image to AI provider and return parsed QuizResult"""
        pass

    @abc.abstractmethod
    def test_connection(self) -> Tuple[bool, str, float]:
        """
        Test provider connectivity
        Returns: (success: bool, message: str, latency_seconds: float)
        """
        pass
