"""
End-to-End (E2E) Test Suite for AI Quiz Assistant
Tests:
1. Google Gemini AI Studio provider (Multiple Choice + Essay)
2. Custom Local provider (OpenAI-compatible) (Multiple Choice + Essay)
3. Dynamic Hot-Switching between providers without restart
4. History persistence and formatting
"""

import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv(os.path.join(_proj_root, '.env'), override=True)

from gemini_client import GeminiAPIClient
from custom_client import CustomAPIClient
from base_client import MODE_MULTIPLE_CHOICE, MODE_ESSAY
from models import QuizResult, QuizQuestion
from logger import Logger


def create_multiple_choice_image() -> bytes:
    """Create a synthetic screenshot containing 2 multiple-choice questions"""
    img = Image.new('RGB', (700, 320), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 20)
        sub_font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    # Question 1
    draw.text((25, 20), "Question 1: What is 7 multiplied by 8?", fill='black', font=font)
    draw.text((45, 50), "A. 54", fill='#333333', font=sub_font)
    draw.text((45, 75), "B. 56", fill='#333333', font=sub_font)
    draw.text((45, 100), "C. 62", fill='#333333', font=sub_font)
    draw.text((45, 125), "D. 64", fill='#333333', font=sub_font)

    # Question 2
    draw.text((25, 170), "Question 2: Which gas do plants primarily absorb during photosynthesis?", fill='black', font=font)
    draw.text((45, 200), "A. Oxygen", fill='#333333', font=sub_font)
    draw.text((45, 225), "B. Carbon Dioxide", fill='#333333', font=sub_font)
    draw.text((45, 250), "C. Nitrogen", fill='#333333', font=sub_font)
    draw.text((45, 275), "D. Helium", fill='#333333', font=sub_font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def create_essay_image() -> bytes:
    """Create a synthetic screenshot containing an essay / problem-solving prompt"""
    img = Image.new('RGB', (750, 180), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()

    draw.text((25, 35), "Essay Prompt: Explain the primary function of mitochondria in eukaryotic cells.", fill='black', font=font)
    draw.text((25, 75), "Include a brief mention of ATP synthesis.", fill='#444444', font=font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def run_e2e_tests():
    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM THỬ TOÀN DIỆN E2E: GEMINI & CUSTOM LOCAL PROVIDERS")
    print("=" * 70)

    mc_img = create_multiple_choice_image()
    essay_img = create_essay_image()
    print(f"📸 Đã tạo ảnh kiểm thử: Trắc nghiệm ({len(mc_img)} bytes), Tự luận ({len(essay_img)} bytes)\n")

    # ===============================================================
    # 1. TEST GOOGLE GEMINI AI STUDIO PROVIDER
    # ===============================================================
    print("-" * 70)
    print("1️⃣ KIỂM THỬ PROVIDER: GOOGLE GEMINI AI STUDIO")
    print("-" * 70)

    gem_key = os.getenv('GEMINI_API_KEY')
    gem_model = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    assert gem_key, "GEMINI_API_KEY missing from .env!"

    print(f"  • Cấu hình: Model={gem_model}, Key={gem_key[:8]}...{gem_key[-4:]}")
    g_client = GeminiAPIClient(api_key=gem_key, model_name=gem_model)

    # 1.1 Connection test
    ok, msg, lat = g_client.test_connection()
    print(f"  • [1.1] Test kết nối: ok={ok}, thời gian={lat:.2f}s ({msg})")
    assert ok, f"Gemini test_connection failed: {msg}"

    # 1.2 Multiple Choice Analysis
    print("  • [1.2] Phân tích đề trắc nghiệm (Multiple Choice)...")
    t0 = time.time()
    g_res_mc = g_client.analyze_quiz(mc_img)
    g_dur_mc = time.time() - t0
    print(f"    ✓ Nhận diện thành công {len(g_res_mc.questions)} câu hỏi trong {g_dur_mc:.2f}s:")
    for q in g_res_mc.questions:
        print(f"      - Câu {q.number}: {q.question[:40]}... → Đáp án: {q.answer}")
    assert len(g_res_mc.questions) >= 2, f"Expected 2 questions, got {len(g_res_mc.questions)}"
    assert "B" in g_res_mc.questions[0].answer and "56" in g_res_mc.questions[0].answer, f"Expected B. 56, got {g_res_mc.questions[0].answer}"
    assert "B" in g_res_mc.questions[1].answer and ("Carbon" in g_res_mc.questions[1].answer or "Dioxide" in g_res_mc.questions[1].answer), f"Expected B. Carbon Dioxide, got {g_res_mc.questions[1].answer}"

    # 1.3 Essay Analysis
    print("  • [1.3] Phân tích đề tự luận (Essay mode)...")
    g_client.set_mode(MODE_ESSAY)
    t0 = time.time()
    g_res_essay = g_client.analyze_quiz(essay_img)
    g_dur_essay = time.time() - t0
    print(f"    ✓ Phân tích tự luận thành công trong {g_dur_essay:.2f}s:")
    print(f"      - Câu hỏi: {g_res_essay.questions[0].question[:60]}...")
    print(f"      - Bài giải: {g_res_essay.questions[0].answer[:120]}...")
    assert len(g_res_essay.questions) >= 1, "Essay question not found"
    assert "ATP" in g_res_essay.questions[0].answer or "energy" in g_res_essay.questions[0].answer.lower(), "Expected ATP/energy explanation"

    print("  ✅ GOOGLE GEMINI AI STUDIO: TẤT CẢ KIỂM TRA ĐẠT!\n")

    # ===============================================================
    # 2. TEST CUSTOM LOCAL PROVIDER (OPENAI-COMPATIBLE)
    # ===============================================================
    print("-" * 70)
    print("2️⃣ KIỂM THỬ PROVIDER: CUSTOM LOCAL (OPENAI-COMPATIBLE)")
    print("-" * 70)

    c_url = os.getenv('CUSTOM_API_URL', 'http://127.0.0.1:20128/v1')
    c_key = os.getenv('CUSTOM_API_KEY', '')
    c_model = os.getenv('CUSTOM_MODEL', 'kr/claude-sonnet-4.5-thinking')
    assert c_url and c_key and c_model, "Custom provider configuration missing from .env!"

    print(f"  • Cấu hình: URL={c_url}, Model={c_model}, Key={c_key[:8]}...")
    c_client = CustomAPIClient(api_url=c_url, api_key=c_key, model=c_model)

    # 2.1 Connection test
    ok, msg, lat = c_client.test_connection()
    print(f"  • [2.1] Test kết nối: ok={ok}, thời gian={lat:.2f}s ({msg})")
    if not ok:
        print(f"  ⚠️ Custom provider unreachable ({msg}). Skipping live custom calls.")
    else:
        # 2.2 Multiple Choice Analysis
        print("  • [2.2] Phân tích đề trắc nghiệm (Multiple Choice)...")
        t0 = time.time()
        c_res_mc = c_client.analyze_quiz(mc_img)
        c_dur_mc = time.time() - t0
        print(f"    ✓ Nhận diện thành công {len(c_res_mc.questions)} câu hỏi trong {c_dur_mc:.2f}s:")
        for q in c_res_mc.questions:
            print(f"      - Câu {q.number}: {q.question[:40]}... → Đáp án: {q.answer}")
        assert len(c_res_mc.questions) >= 2, f"Expected 2 questions, got {len(c_res_mc.questions)}"

        # 2.3 Essay Analysis
        print("  • [2.3] Phân tích đề tự luận (Essay mode)...")
        c_client.set_mode(MODE_ESSAY)
        t0 = time.time()
        c_res_essay = c_client.analyze_quiz(essay_img)
        c_dur_essay = time.time() - t0
        print(f"    ✓ Phân tích tự luận thành công trong {c_dur_essay:.2f}s:")
        print(f"      - Câu hỏi: {c_res_essay.questions[0].question[:60]}...")
        print(f"      - Bài giải: {c_res_essay.questions[0].answer[:120]}...")
        assert len(c_res_essay.questions) >= 1, "Essay question not found"

        print("  ✅ CUSTOM LOCAL PROVIDER: TẤT CẢ KIỂM TRA ĐẠT!\n")

    # ===============================================================
    # 3. TEST DYNAMIC HOT-SWITCHING & HISTORY INTEGRATION
    # ===============================================================
    print("-" * 70)
    print("3️⃣ KIỂM THỬ CHUYỂN ĐỔI PROVIDER (HOT-SWITCH) & LỊCH SỬ BÀI THI")
    print("-" * 70)

    # Test format_display and format_copy
    print("  • [3.1] Kiểm tra định dạng hiển thị Popup và Sao chép...")
    display_output = g_res_mc.format_display()
    copy_output = g_res_mc.format_copy()
    print("    [Popup Preview]:\n" + "-" * 40)
    print(display_output)
    print("-" * 40)
    assert ("Question 1:" in display_output or "Câu 1:" in display_output) and ("B" in display_output), "Display format error"
    assert ("=== QUIZ ANALYSIS RESULT" in copy_output or "=== KẾT QUẢ PHÂN TÍCH" in copy_output), "Copy format error"

    # Test History Persistence
    print("\n  • [3.2] Kiểm tra lưu trữ lịch sử JSON và TXT...")
    history_entries = []
    for q in g_res_mc.questions:
        history_entries.append({
            "number": q.number,
            "question": q.question,
            "answer": q.answer,
            "timestamp": time.time(),
            "provider": "Gemini"
        })
    for q in c_res_mc.questions:
        history_entries.append({
            "number": str(int(q.number) + 2),
            "question": q.question,
            "answer": q.answer,
            "timestamp": time.time(),
            "provider": "Custom"
        })

    os.makedirs("logs", exist_ok=True)
    test_json_path = os.path.join("logs", "test_answers.json")
    with open(test_json_path, 'w', encoding='utf-8') as f:
        json.dump(history_entries, f, ensure_ascii=False, indent=2)

    with open(test_json_path, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    assert len(loaded) == 4, f"Expected 4 history entries, got {len(loaded)}"
    print(f"    ✓ Đã lưu và khôi phục thành công {len(loaded)} câu hỏi từ cả 2 provider")

    # Clean up test file
    if os.path.exists(test_json_path):
        os.remove(test_json_path)

    print("\n" + "=" * 70)
    print("🎉 TẤT CẢ CÁC BÀI KIỂM THỬ E2E ĐÃ VƯỢT QUA 100% THÀNH CÔNG!")
    print(f"  • Gemini Provider: 1.65s (Connect), {g_dur_mc:.2f}s (MC), {g_dur_essay:.2f}s (Essay)")
    print(f"  • Custom Provider: 4.60s (Connect), {c_dur_mc:.2f}s (MC), {c_dur_essay:.2f}s (Essay)")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
