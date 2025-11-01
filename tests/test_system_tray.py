"""
Unit tests for System Tray
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from src.system_tray import SystemTray


class TestSystemTray(unittest.TestCase):
    """Test cases for SystemTray"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app_mock = Mock()
        self.app_mock.stop = Mock()
        self.system_tray = SystemTray(self.app_mock)
    
    def tearDown(self):
        """Clean up after tests"""
        if self.system_tray.icon:
            try:
                self.system_tray.stop()
            except:
                pass
    
    def test_init(self):
        """Test initialization"""
        self.assertEqual(self.system_tray.app, self.app_mock)
        self.assertIsNone(self.system_tray.icon)
        self.assertFalse(self.system_tray._running)
    
    def test_create_icon(self):
        """Test creating icon image"""
        icon_image = self.system_tray.create_icon()
        
        # Verify it's a PIL Image
        self.assertIsInstance(icon_image, Image.Image)
        
        # Verify size
        self.assertEqual(icon_image.size, (64, 64))
        
        # Verify it's RGB mode
        self.assertEqual(icon_image.mode, 'RGB')
    
    def test_create_menu(self):
        """Test creating menu"""
        menu = self.system_tray.create_menu()
        
        # Verify menu is created
        self.assertIsNotNone(menu)
    
    def test_on_quit_stops_icon(self):
        """Test on_quit stops icon"""
        # Mock icon
        self.system_tray.icon = Mock()
        self.system_tray.icon.stop = Mock()
        
        self.system_tray.on_quit()
        
        # Verify icon.stop was called
        self.system_tray.icon.stop.assert_called_once()
    
    def test_on_quit_stops_app(self):
        """Test on_quit stops application"""
        self.system_tray.icon = Mock()
        
        self.system_tray.on_quit()
        
        # Verify app.stop was called
        self.app_mock.stop.assert_called_once()
    
    def test_show_notification_with_icon(self):
        """Test showing notification when icon exists"""
        # Mock icon with notify method
        self.system_tray.icon = Mock()
        self.system_tray.icon.visible = True
        self.system_tray.icon.notify = Mock()
        
        self.system_tray.show_notification("Test Title", "Test Message")
        
        # Verify notify was called
        self.system_tray.icon.notify.assert_called_once_with("Test Message", "Test Title")
    
    def test_show_notification_without_icon(self):
        """Test showing notification when icon doesn't exist"""
        self.system_tray.icon = None
        
        # Should not raise exception
        try:
            self.system_tray.show_notification("Test Title", "Test Message")
        except Exception:
            self.fail("show_notification should handle missing icon gracefully")
    
    def test_show_notification_error_handling(self):
        """Test notification error handling"""
        # Mock icon that raises exception on notify
        self.system_tray.icon = Mock()
        self.system_tray.icon.visible = True
        self.system_tray.icon.notify = Mock(side_effect=Exception("Notification not supported"))
        
        # Should not raise exception
        try:
            self.system_tray.show_notification("Test Title", "Test Message")
        except Exception:
            self.fail("show_notification should handle exceptions gracefully")
    
    @patch('src.system_tray.Thread')
    def test_start(self, mock_thread):
        """Test starting system tray"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        self.system_tray.start()
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    @patch('src.system_tray.Thread')
    def test_start_already_running(self, mock_thread):
        """Test starting when already running"""
        self.system_tray._running = True
        
        self.system_tray.start()
        
        # Thread should not be created
        mock_thread.assert_not_called()
    
    def test_stop(self):
        """Test stopping system tray"""
        # Mock icon
        self.system_tray.icon = Mock()
        self.system_tray.icon.stop = Mock()
        self.system_tray._running = True
        
        self.system_tray.stop()
        
        # Verify icon.stop was called
        self.system_tray.icon.stop.assert_called_once()
        self.assertFalse(self.system_tray._running)
    
    def test_stop_without_icon(self):
        """Test stopping when icon doesn't exist"""
        self.system_tray.icon = None
        self.system_tray._running = True
        
        # Should not raise exception
        try:
            self.system_tray.stop()
        except Exception:
            self.fail("stop should handle missing icon gracefully")
        
        self.assertFalse(self.system_tray._running)


if __name__ == '__main__':
    unittest.main()
