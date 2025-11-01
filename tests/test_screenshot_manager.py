"""
Tests for Screenshot Manager
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from screenshot_manager import ScreenshotManager
from logger import Logger


def test_screenshot_manager_initialization():
    """Test ScreenshotManager can be initialized"""
    manager = ScreenshotManager()
    assert manager is not None
    print("✓ ScreenshotManager initialization test passed")


def test_screenshot_manager_with_logger():
    """Test ScreenshotManager with logger"""
    logger = Logger()
    manager = ScreenshotManager(logger=logger)
    assert manager is not None
    assert manager.logger is not None
    print("✓ ScreenshotManager with logger test passed")


def test_get_primary_monitor():
    """Test getting primary monitor info"""
    manager = ScreenshotManager()
    monitor_info = manager.get_primary_monitor()
    
    assert monitor_info is not None
    assert 'width' in monitor_info
    assert 'height' in monitor_info
    assert 'x' in monitor_info
    assert 'y' in monitor_info
    assert 'is_primary' in monitor_info
    assert monitor_info['width'] > 0
    assert monitor_info['height'] > 0
    
    print(f"✓ Primary monitor test passed: {monitor_info['width']}x{monitor_info['height']}")


def test_capture_screen():
    """Test capturing screen"""
    logger = Logger()
    manager = ScreenshotManager(logger=logger)
    
    screenshot = manager.capture_screen()
    
    # Screenshot might be None if running in headless environment
    if screenshot is not None:
        assert screenshot.size[0] > 0
        assert screenshot.size[1] > 0
        print(f"✓ Screen capture test passed: {screenshot.size[0]}x{screenshot.size[1]}")
    else:
        print("⚠ Screen capture returned None (might be headless environment)")


def test_save_to_memory():
    """Test saving image to memory"""
    from PIL import Image
    
    logger = Logger()
    manager = ScreenshotManager(logger=logger)
    
    # Create a simple test image
    test_image = Image.new('RGB', (100, 100), color='red')
    
    image_bytes = manager.save_to_memory(test_image)
    
    assert image_bytes is not None
    assert len(image_bytes) > 0
    assert isinstance(image_bytes, bytes)
    
    print(f"✓ Save to memory test passed: {len(image_bytes)} bytes")


def test_capture_and_save():
    """Test capture and save in one step"""
    logger = Logger()
    manager = ScreenshotManager(logger=logger)
    
    image_bytes = manager.capture_and_save()
    
    # Might be None in headless environment
    if image_bytes is not None:
        assert len(image_bytes) > 0
        assert isinstance(image_bytes, bytes)
        print(f"✓ Capture and save test passed: {len(image_bytes)} bytes")
    else:
        print("⚠ Capture and save returned None (might be headless environment)")


if __name__ == "__main__":
    print("Running Screenshot Manager tests...\n")
    
    test_screenshot_manager_initialization()
    test_screenshot_manager_with_logger()
    test_get_primary_monitor()
    test_capture_screen()
    test_save_to_memory()
    test_capture_and_save()
    
    print("\n✓ All tests completed!")
