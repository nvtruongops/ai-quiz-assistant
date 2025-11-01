"""
Screenshot Manager Module
Manages screen capture and image processing
"""

import io
from typing import Optional, Tuple
from PIL import Image, ImageGrab
import screeninfo


class ScreenshotManager:
    """Manages screen capture and image processing"""
    
    def __init__(self, logger=None):
        """
        Initialize ScreenshotManager
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger
    
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
    
    def save_to_memory(self, image: Image.Image) -> Optional[bytes]:
        """
        Convert Image to bytes (PNG format) for API sending
        Don't save file to disk for speed improvement
        
        Args:
            image: PIL Image object
            
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
            
            if self.logger:
                self.logger.info(f"Image saved to memory: {len(image_bytes)} bytes")
            
            return image_bytes
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save image to memory: {str(e)}", exc_info=True)
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
