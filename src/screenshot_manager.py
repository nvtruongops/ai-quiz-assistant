"""
Screenshot Manager Module
Manages screen capture and image processing
"""

import io
import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from PIL import Image, ImageGrab
import screeninfo

_src_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_src_dir)


class ScreenshotManager:
    """Manages screen capture and image processing"""
    
    def __init__(self, logger=None, save_screenshots=True, screenshot_dir=None):
        """
        Initialize ScreenshotManager
        
        Args:
            logger: Logger instance (optional)
            save_screenshots: Whether to save screenshots to disk (default: True)
            screenshot_dir: Directory to save screenshots (default: logs/screenshots relative to PROJECT_ROOT)
        """
        self.logger = logger
        self.save_screenshots = save_screenshots
        if not screenshot_dir:
            screenshot_dir = os.path.join(PROJECT_ROOT, "logs", "screenshots")
        elif not os.path.isabs(screenshot_dir):
            screenshot_dir = os.path.join(PROJECT_ROOT, screenshot_dir)
        self.screenshot_dir = screenshot_dir
        
        # Create screenshot directory if saving is enabled
        if self.save_screenshots:
            os.makedirs(self.screenshot_dir, exist_ok=True)
        self.last_capture_bbox: Tuple[int, int, int, int] = (0, 0, 1920, 1080)
    
    def capture_screen(self) -> Optional[Image.Image]:
        """
        Capture entire primary screen
        
        Returns:
            PIL Image object if successful, None if failed
        """
        try:
            # Get primary monitor information
            monitor_info = self.get_primary_monitor()
            
            if self.logger:
                self.logger.info(f"Capturing screen from primary monitor: {monitor_info['width']}x{monitor_info['height']}")
            
            # Capture entire screen
            # ImageGrab.grab() will capture primary screen by default
            screenshot = ImageGrab.grab()
            
            if screenshot:
                self.last_capture_bbox = (
                    monitor_info.get('x', 0),
                    monitor_info.get('y', 0),
                    screenshot.width,
                    screenshot.height
                )

            if self.logger:
                self.logger.info("Screenshot captured successfully")
            
            return screenshot
            
        except PermissionError as e:
            if self.logger:
                self.logger.error(f"Permission denied when capturing screen: {str(e)}", exc_info=True)
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to capture screen: {str(e)}", exc_info=True)
            return None

    def get_last_capture_bbox(self) -> Tuple[int, int, int, int]:
        """Return (x, y, width, height) of the last captured screenshot"""
        if hasattr(self, 'last_capture_bbox') and self.last_capture_bbox:
            return self.last_capture_bbox
        mon = self.get_primary_monitor()
        return (mon.get('x', 0), mon.get('y', 0), mon.get('width', 1920), mon.get('height', 1080))
    
    def save_to_memory(self, image: Image.Image, save_to_disk=True) -> Optional[bytes]:
        """
        Convert Image to bytes (PNG format) for API sending
        Optionally save file to disk for later review
        
        Args:
            image: PIL Image object
            save_to_disk: Whether to save screenshot to disk (default: True)
            
        Returns:
            Image bytes if successful, None if failed
        """
        try:
            # Create BytesIO buffer to save image to memory
            buffer = io.BytesIO()
            
            # Save image as PNG to buffer
            image.save(buffer, format='PNG')
            
            # Get bytes from buffer
            image_bytes = buffer.getvalue()
            
            # Close buffer
            buffer.close()
            
            # Save to disk if enabled
            if save_to_disk and self.save_screenshots:
                self._save_screenshot_to_disk(image)
            
            if self.logger:
                self.logger.info(f"Image saved to memory: {len(image_bytes)} bytes")
            
            return image_bytes
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save image to memory: {str(e)}", exc_info=True)
            return None
    
    def _save_screenshot_to_disk(self, image: Image.Image) -> Optional[str]:
        """
        Save screenshot to disk with timestamp
        
        Args:
            image: PIL Image object
            
        Returns:
            Saved file path if successful, None if failed
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Save image
            image.save(filepath, format='PNG')
            
            if self.logger:
                self.logger.info(f"Screenshot saved to {filepath}")
            
            return filepath
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save screenshot to disk: {str(e)}", exc_info=True)
            return None
    
    def get_primary_monitor(self) -> dict:
        """
        Get primary monitor information
        
        Returns:
            Dictionary containing monitor info: width, height, x, y, is_primary
        """
        try:
            # Get list of all monitors
            monitors = screeninfo.get_monitors()
            
            # Find primary monitor
            primary_monitor = None
            for monitor in monitors:
                if monitor.is_primary:
                    primary_monitor = monitor
                    break
            
            # If no primary monitor found, use first monitor
            if primary_monitor is None and monitors:
                primary_monitor = monitors[0]
            
            if primary_monitor:
                monitor_info = {
                    'width': primary_monitor.width,
                    'height': primary_monitor.height,
                    'x': primary_monitor.x,
                    'y': primary_monitor.y,
                    'is_primary': primary_monitor.is_primary,
                    'name': primary_monitor.name
                }
                
                if self.logger:
                    self.logger.info(f"Primary monitor detected: {monitor_info}")
                
                return monitor_info
            else:
                # Fallback: use default information
                if self.logger:
                    self.logger.error("No monitor detected, using default values")
                
                return {
                    'width': 1920,
                    'height': 1080,
                    'x': 0,
                    'y': 0,
                    'is_primary': True,
                    'name': 'Unknown'
                }
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get monitor info: {str(e)}", exc_info=True)
            
            # Fallback: return default information
            return {
                'width': 1920,
                'height': 1080,
                'x': 0,
                'y': 0,
                'is_primary': True,
                'name': 'Unknown'
            }
    
    def capture_and_save(self) -> Optional[bytes]:
        """
        Capture screen and convert to bytes in one step
        Convenience method to simplify workflow
        
        Returns:
            Image bytes if successful, None if failed
        """
        try:
            # Capture screen
            screenshot = self.capture_screen()
            
            if screenshot is None:
                return None
            
            # Convert to bytes
            image_bytes = self.save_to_memory(screenshot)
            
            return image_bytes
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to capture and save screenshot: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def compute_image_hash(image: Image.Image) -> str:
        """
        Compute image fingerprint using perceptual dHash + SHA-256 digest.
        Allows fast comparison and deduplication in the current session.
        
        Args:
            image: PIL Image object
            
        Returns:
            Hex string hash representing the image
        """
        try:
            # Grayscale 32x32 thumbnail
            small = image.convert('L').resize((32, 32), Image.Resampling.BILINEAR)
            raw_bytes = small.tobytes()
            
            # Compute difference hash (dHash horizontal gradient)
            bits = []
            for row in range(32):
                row_offset = row * 32
                for col in range(31):
                    bits.append('1' if raw_bytes[row_offset + col] > raw_bytes[row_offset + col + 1] else '0')
            dhash_hex = hex(int(''.join(bits), 2))[2:]
            sha_hex = hashlib.sha256(raw_bytes).hexdigest()[:16]
            return f"{dhash_hex}_{sha_hex}"
        except Exception:
            try:
                return hashlib.sha256(image.tobytes()).hexdigest()[:32]
            except Exception:
                return ""

