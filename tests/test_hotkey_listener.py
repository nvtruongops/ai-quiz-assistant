"""
Unit tests for Hotkey Listener
"""

import unittest
import time
from unittest.mock import Mock, patch
from src.hotkey_listener import HotkeyListener
from pynput import keyboard


class TestHotkeyListener(unittest.TestCase):
    """Test cases for HotkeyListener"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.on_capture_mock = Mock()
        self.on_check_mock = Mock()
        self.on_hide_mock = Mock()
        self.on_exit_mock = Mock()
        self.on_clear_logs_mock = Mock()
        self.on_show_answers_mock = Mock()
        self.on_reset_answers_mock = Mock()
        self.on_switch_provider_mock = Mock()
        
        self.listener = HotkeyListener(
            on_capture_key=self.on_capture_mock,
            on_check_key=self.on_check_mock,
            on_hide_key=self.on_hide_mock,
            on_exit_key=self.on_exit_mock,
            on_clear_logs=self.on_clear_logs_mock,
            on_show_answers=self.on_show_answers_mock,
            on_reset_answers=self.on_reset_answers_mock,
            on_switch_provider=self.on_switch_provider_mock
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.listener.keyboard_listener:
            self.listener.stop()
    
    def test_init(self):
        """Test initialization"""
        self.assertEqual(self.listener.on_capture_key, self.on_capture_mock)
        self.assertEqual(self.listener.on_check_key, self.on_check_mock)
        self.assertEqual(self.listener.on_hide_key, self.on_hide_mock)
        self.assertEqual(self.listener.on_exit_key, self.on_exit_mock)
        self.assertIsNone(self.listener.keyboard_listener)
        self.assertIsNone(self.listener.mouse_listener)
    
    def test_start(self):
        """Test starting the listener"""
        self.listener.start()
        
        self.assertIsNotNone(self.listener.keyboard_listener)
        self.assertIsNotNone(self.listener.mouse_listener)
        self.assertTrue(self.listener.keyboard_listener.is_alive())
        self.assertTrue(self.listener.mouse_listener.is_alive())
        
        self.listener.stop()
    
    def test_stop(self):
        """Test stopping the listener"""
        self.listener.start()
        self.assertIsNotNone(self.listener.keyboard_listener)
        self.assertIsNotNone(self.listener.mouse_listener)
        
        self.listener.stop()
        self.assertIsNone(self.listener.keyboard_listener)
        self.assertIsNone(self.listener.mouse_listener)
    
    def test_on_key_press_capture(self):
        """Test handling capture key (Alt+Z)"""
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        self.listener.on_key_press(alt_key)
        
        # Simulate Z key press
        mock_key = Mock()
        mock_key.char = 'z'
        
        self.listener.on_key_press(mock_key)
        
        self.on_capture_mock.assert_called_once()
        self.on_check_mock.assert_not_called()
        self.on_hide_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
    
    def test_on_key_press_check(self):
        """Test handling check key (Alt+X)"""
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        self.listener.on_key_press(alt_key)
        
        # Simulate X key press
        mock_key = Mock()
        mock_key.char = 'x'
        
        self.listener.on_key_press(mock_key)
        
        self.on_check_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_hide_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
    
    def test_on_key_press_show_answers(self):
        """Test handling show answers key (Alt+C)"""
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        self.listener.on_key_press(alt_key)
        
        # Simulate C key press
        mock_key = Mock()
        mock_key.char = 'c'
        
        self.listener.on_key_press(mock_key)
        
        self.on_show_answers_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
    
    def test_on_key_press_exit(self):
        """Test handling exit key (`)"""
        mock_key = Mock()
        mock_key.char = '`'
        
        self.listener.on_key_press(mock_key)
        
        self.on_exit_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_hide_mock.assert_not_called()
    
    def test_on_key_press_other_key(self):
        """Test handling other keys (should be ignored)"""
        mock_key = Mock()
        mock_key.char = 'a'
        
        self.listener.on_key_press(mock_key)
        
        # No callbacks should be called
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_hide_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
        self.on_show_answers_mock.assert_not_called()
        self.on_reset_answers_mock.assert_not_called()
        self.on_switch_provider_mock.assert_not_called()
    
    def test_on_key_press_error_handling(self):
        """Test error handling in on_key_press"""
        # Create a callback that raises an exception
        def error_callback():
            raise Exception("Test error")
        
        listener = HotkeyListener(
            on_capture_key=error_callback,
            on_check_key=self.on_check_mock,
            on_hide_key=self.on_hide_mock,
            on_exit_key=self.on_exit_mock
        )
        
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        listener.on_key_press(alt_key)
        
        # Simulate Z key press
        mock_key = Mock()
        mock_key.char = 'z'
        
        # Should not raise exception
        try:
            listener.on_key_press(mock_key)
        except Exception:
            self.fail("on_key_press should handle exceptions gracefully")
    
    def test_start_already_running(self):
        """Test starting listener when already running"""
        self.listener.start()
        
        # Try to start again
        self.listener.start()
        
        # Should still have listeners
        self.assertIsNotNone(self.listener.keyboard_listener)
        self.assertIsNotNone(self.listener.mouse_listener)
        
        self.listener.stop()
    
    def test_on_key_press_reset_answers(self):
        """Test handling reset answers key (Alt+R)"""
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        self.listener.on_key_press(alt_key)
        
        # Simulate R key press
        mock_key = Mock()
        mock_key.char = 'r'
        
        self.listener.on_key_press(mock_key)
        
        self.on_reset_answers_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
    
    def test_on_key_press_switch_provider(self):
        """Test handling switch provider key (Alt+S)"""
        # Simulate Alt key press
        alt_key = keyboard.Key.alt
        self.listener.on_key_press(alt_key)
        
        # Simulate S key press
        mock_key = Mock()
        mock_key.char = 's'
        
        self.listener.on_key_press(mock_key)
        
        self.on_switch_provider_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
    
    def test_on_key_press_clear_logs(self):
        """Test handling clear logs key (Delete)"""
        delete_key = keyboard.Key.delete
        
        self.listener.on_key_press(delete_key)
        
        self.on_clear_logs_mock.assert_called_once()
        self.on_capture_mock.assert_not_called()
        self.on_check_mock.assert_not_called()
        self.on_exit_mock.assert_not_called()
