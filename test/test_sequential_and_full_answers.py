"""Regression checks for latest-answer formatting and sequential history labels."""

import time

from models import QuizQuestion, QuizResult


def test_sequential_and_full_answers():
    first_result = QuizResult(questions=[
        QuizQuestion(number="1", question="What is 7 multiplied by 8?", answer="B. 56")
    ])
    second_result = QuizResult(questions=[
        QuizQuestion(
            number="2",
            question="Which gas do plants primarily absorb during photosynthesis?",
            answer="B. Carbon Dioxide",
        )
    ])

    answer_history = []
    latest_result = None
    for result in (first_result, second_result):
        start_num = len(answer_history) + 1
        for idx, question in enumerate(result.questions):
            question.exam_number = "3" if start_num == 1 else "19"
            question.number = str(start_num + idx)
            answer_history.append({
                "number": question.number,
                "exam_number": question.exam_number,
                "question": question.question,
                "answer": question.answer,
            })
        latest_result = result

    latest_display = latest_result.format_display()
    assert "Question 2:" in latest_display
    assert "Carbon Dioxide" in latest_display

    history_lines = [f"=== HISTORY (1 to {len(answer_history)}) ==="]
    for idx, answer in enumerate(answer_history, 1):
        history_lines.append(f"Question {idx}: {answer['question']}\nAnswer: {answer['answer']}")
    history_display = "\n\n".join(history_lines)

    assert "Question 1: What is 7 multiplied by 8?" in history_display
    assert "Question 2: Which gas do plants primarily absorb during photosynthesis?" in history_display
    assert "Question 3:" not in history_display
    assert "Question 19:" not in history_display
    assert "B. 56" in history_display
    assert "B. Carbon Dioxide" in history_display
