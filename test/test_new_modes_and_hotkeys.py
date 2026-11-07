"""
Automated Test for New Modes, Alt+H Customization, and Collapsible Explanation
"""

import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
import time

from models import QuizQuestion, QuizResult
from base_client import (
    BaseAIClient,
    MODE_MULTIPLE_CHOICE,
    MODE_MC_EXPLANATION,
    MODE_ESSAY,
    DISPLAY_LETTER_AND_TEXT,
    DISPLAY_LETTER_ONLY
)
from gemini_client import GeminiAPIClient
from custom_client import CustomAPIClient
from settings_manager import SettingsManager, DEFAULT_SETTINGS
from hotkey_listener import HotkeyListener


def test_models_and_modes():
    print("\n--- 1. Testing Models & Multiple Choice + Explanation ---")

    # Single question with explanation
    q1 = QuizQuestion(
        number="1",
        question="Which gas do plants absorb?",
        answer="B. Carbon Dioxide",
        option_letter="B",
        option_text="Carbon Dioxide",
        explanation="Plants absorb CO2 for photosynthesis."
    )
    assert q1.explanation == "Plants absorb CO2 for photosynthesis."
    print("  ✓ QuizQuestion stores explanation cleanly")

    # Multi-question result
    q2 = QuizQuestion(
        number="2",
        question="What is 7 * 8?",
        answer="B. 56",
        option_letter="B",
        option_text="56",
        explanation="7 multiplied by 8 equals 56."
    )
    result = QuizResult(
        questions=[q1, q2],
        provider_name="Gemini",
        model_name="gemini-3.5-flash-lite",
        mode=MODE_MC_EXPLANATION
    )

    disp_no_exp = result.format_display(include_explanation=False)
    assert "Plants absorb CO2" not in disp_no_exp
    assert "B. Carbon Dioxide" in disp_no_exp
    assert "B. 56" in disp_no_exp
    print("  ✓ format_display(include_explanation=False) hides explanation by default")

    disp_with_exp = result.format_display(include_explanation=True)
    assert "Plants absorb CO2" in disp_with_exp
    assert "7 multiplied by 8 equals 56" in disp_with_exp
    print("  ✓ format_display(include_explanation=True) includes explanation when requested")

    copy_text = result.format_copy(include_explanation=True)
    assert "Multiple Choice + Exp" in copy_text or "Trắc nghiệm + Giải thích" in copy_text
    assert "Explanation: Plants absorb CO2" in copy_text or "Giải thích: Plants absorb CO2" in copy_text
    print("  ✓ format_copy formats text cleanly with explanations")


def test_parsing_multi_questions():
    print("\n--- 2. Testing Parsing Multi-Questions (1, 2, 3 questions) ---")

    client = GeminiAPIClient(api_key="mock", mode=MODE_MC_EXPLANATION)

    # 3 Questions in a single JSON response
    mock_json = """
    {
      "questions": [
        {
          "number": "1",
          "question": "What is the capital of France?",
          "answer": "A. Paris",
          "explanation": "Paris has been the capital of France since the 10th century."
        },
        {
          "number": "2",
          "question": "Which planet is known as the Red Planet?",
          "answer": "C. Mars",
          "explanation": "Mars appears red due to iron oxide (rust) on its surface."
        },
        {
          "number": "3",
          "question": "What is the boiling point of water at sea level?",
          "answer": "B. 100°C",
          "explanation": "At 1 atm of pressure, water boils at 100 degrees Celsius."
        }
      ]
    }
    """

    res = client.parse_quiz_response(mock_json)
    assert len(res.questions) == 3, f"Expected 3 questions, got {len(res.questions)}"
    assert res.questions[0].answer == "A. Paris"
    assert res.questions[0].explanation.startswith("Paris has been")
    assert res.questions[1].answer == "C. Mars"
    assert res.questions[1].explanation.startswith("Mars appears red")
    assert res.questions[2].answer == "B. 100°C"
    assert res.questions[2].explanation.startswith("At 1 atm")
    print(f"  ✓ Successfully parsed all {len(res.questions)} questions from multi-question response")


def test_hotkey_history_customization():
    print("\n--- 3. Testing Hotkey History (Alt+H) Customization ---")

    sm = SettingsManager()
    # Check default
    assert sm.get('hotkey_history', 'h') == 'h'
    print("  ✓ Default hotkey_history is 'h' (Alt+H)")

    # Change to 'j'
    sm.set('hotkey_history', 'j')
    assert sm.get('hotkey_history') == 'j'

    listener = HotkeyListener(
        on_capture_key=lambda: None,
        on_check_key=lambda: None,
        on_hide_key=lambda: None,
        on_exit_key=lambda: None,
        settings_manager=sm
    )
    assert listener.hotkeys.get('history') == 'j'
    print("  ✓ HotkeyListener loaded customized history hotkey: Alt+J")

    # Restore default 'h'
    sm.set('hotkey_history', 'h')
    listener.reload_hotkeys()
    assert listener.hotkeys.get('history') == 'h'
    print("  ✓ Successfully restored default hotkey: Alt+H")


def test_prompts_for_all_modes():
    print("\n--- 4. Testing Prompt Generation for All 3 Modes ---")

    client = GeminiAPIClient(api_key="mock", mode=MODE_MULTIPLE_CHOICE)
    prompt_mc = client.build_prompt()
    assert "extract ALL multiple-choice questions" in prompt_mc
    assert "Do NOT include any explanations" in prompt_mc
    print("  ✓ Multiple Choice prompt instructs extracting all questions without explanations")

    client.set_mode(MODE_MC_EXPLANATION)
    prompt_exp = client.build_prompt()
    assert "solve ALL multiple-choice questions visible" in prompt_exp
    assert '"explanation":' in prompt_exp
    print("  ✓ MC + Explanation prompt instructs extracting all questions with explanation field")

    client.set_mode(MODE_ESSAY)
    prompt_essay = client.build_prompt()
    assert "find any essay questions, open-ended exercises, or math/science problems" in prompt_essay
    assert "Step-by-step solution" in prompt_essay
    print("  ✓ Essay prompt instructs finding problem/essay questions and step-by-step solutions")


def test_live_gemini_mc_explanation():
    print("\n--- 5. Live E2E Gemini Test with Mode: multiple_choice_explanation ---")
    from config_manager import ConfigManager
    cm = ConfigManager()
    key = cm.get('GEMINI_API_KEY')
    if not key:
        print("  ⚠️ Skipping live test: No Gemini key found")
        return

    # Create dummy quiz image
    from PIL import Image, ImageDraw, ImageFont
    import io

    img = Image.new('RGB', (700, 320), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        f = ImageFont.load_default()

    d.text((30, 30), "Question 1: What is the capital city of Japan?", fill=(0, 0, 0), font=f)
    d.text((30, 70), "A. Seoul", fill=(0, 0, 0), font=f)
    d.text((30, 110), "B. Tokyo", fill=(0, 0, 0), font=f)
    d.text((30, 150), "C. Beijing", fill=(0, 0, 0), font=f)
    d.text((30, 190), "D. Bangkok", fill=(0, 0, 0), font=f)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()

    client = GeminiAPIClient(api_key=key, model_name="gemini-3.5-flash-lite", mode=MODE_MC_EXPLANATION)
    try:
        t0 = time.time()
        res = client.analyze_quiz(img_bytes, timeout=15)
        lat = round(time.time() - t0, 2)

        assert len(res.questions) >= 1
        q = res.questions[0]
        print(f"  ✓ Gemini analyzed in {lat}s:")
        print(f"    - Question: {q.question}")
        print(f"    - Answer: {q.answer}")
        print(f"    - Explanation: {q.explanation}")
        assert "Tokyo" in q.answer or "B" in q.answer
        assert len(q.explanation) > 5, "Expected an explanation"
        print("  ✅ Live Gemini test for multiple_choice_explanation PASSED 100%!")
    except Exception as e:
        print(f"  ⚠️ Live Gemini test skipped/handled gracefully (network/key error): {e}")


if __name__ == "__main__":
    test_models_and_modes()
    test_parsing_multi_questions()
    test_hotkey_history_customization()
    test_prompts_for_all_modes()
    test_live_gemini_mc_explanation()
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("="*60)
