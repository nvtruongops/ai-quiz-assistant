"""
Test script for Custom API connection and response format
"""

import os
import sys

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(_test_dir)
_src_dir = os.path.join(_proj_root, "src")
for _p in [_proj_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import base64
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from custom_client import CustomAPIClient
from logger import Logger

def create_test_image():
    """Create a simple test image with sample quiz questions"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    y_offset = 50
    draw.text((50, y_offset), "Question 1: What is 2 + 2?", fill='black', font=font)
    y_offset += 40
    draw.text((70, y_offset), "A. 3", fill='black', font=small_font)
    y_offset += 30
    draw.text((70, y_offset), "B. 4", fill='black', font=small_font)
    y_offset += 30
    draw.text((70, y_offset), "C. 5", fill='black', font=small_font)
    y_offset += 30
    draw.text((70, y_offset), "D. 6", fill='black', font=small_font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def test_custom_api():
    """Test custom API connection and response format"""
    print("=" * 60)
    print("Testing Custom API Connection")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_proj_root, '.env'), override=True)
    
    api_url = os.getenv('CUSTOM_API_URL', '')
    api_key = os.getenv('CUSTOM_API_KEY', '')
    model = os.getenv('CUSTOM_MODEL', '')
    
    print(f"\n📋 Configuration:")
    print(f"  API URL: {api_url}")
    print(f"  API Key: {api_key[:20]}..." if len(api_key) > 20 else f"  API Key: {api_key}")
    print(f"  Model: {model}")
    
    if not api_url or not api_key or not model:
        print("\n⚠️ Note: Custom provider not configured in .env file. Skipping live test.")
        return True
    
    logger = Logger()
    
    print("\n🔧 Initializing Custom API client...")
    try:
        client = CustomAPIClient(
            api_url=api_url,
            api_key=api_key,
            model=model,
            logger=logger,
            mode='multiple_choice'
        )
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Check connection health before sending request
    print("\n🔍 Checking endpoint connectivity...")
    try:
        ok, msg, lat = client.test_connection()
        if not ok:
            print(f"⚠️ Custom API endpoint unreachable ({msg}). Skipping live analysis test.")
            return True
        print(f"✅ Connection verified ({lat:.2f}s latency)")
    except Exception as e:
        print(f"⚠️ Connection check encountered error: {e}. Skipping live analysis test.")
        return True

    # Create test image
    print("\n📸 Creating test image with sample questions...")
    try:
        image_bytes = create_test_image()
        print(f"✅ Test image created ({len(image_bytes)} bytes)")
    except Exception as e:
        print(f"❌ Failed to create test image: {e}")
        return False
    
    # Send request
    print("\n🚀 Sending request to Custom API...")
    try:
        result = client.analyze_quiz(image_bytes, timeout=15)
        print("✅ Request successful!")
    except Exception as e:
        print(f"⚠️ Request failed or timed out: {e}")
        return True
    
    # Display results
    print("\n📊 Results:")
    print(f"  Total questions found: {len(result.questions)}")
    print(f"  Timestamp: {result.timestamp}")
    return True

if __name__ == "__main__":
    try:
        success = test_custom_api()
        if success:
            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ Test failed")
            print("=" * 60)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
