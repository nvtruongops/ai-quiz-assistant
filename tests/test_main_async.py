"""
Tests for async processing in main application
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future

from src.main import QuizAssistantApp
from src.models import QuizResult, QuizQuestion


class TestAsyncProcessing(unittest.TestCase):
    """Test async processing functionality"""
    
    @patch('src.main.SystemTray')
    @patch('src.main.HotkeyListener')
    @patch('src.main.PopupManager')
    @patch('src.main.GeminiAPIClient')
    @patch('src.main.ScreenshotManager')
    @patch('src.main.ConfigManager')
    @patch('src.main.Logger')
    def setUp(self, mock_logger, mock_config, mock_screenshot, mock_gemini, 
              mock_popup, mock_hotkey, mock_tray):
        """Set up test fixtures"""
        # Configure mocks
        mock_config_instance = Mock()
        mock_config_instance.is_valid.return_value = True
        mock_config_instance.get.return_value = "test_api_key"
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Create app instance
        self.app = QuizAssistantApp()
        
    def test_thread_pool_initialized(self):
        """Test that thread pool is initialized"""
        self.assertIsNotNone(self.app._thread_pool)
        self.assertIsInstance(self.app._active_futures, dict)
        
    def test_on_api_success_callback(self):
        """Test success callback updates request manager"""
        # Create a request first
        self.app.request_manager.create_request()
        
        # Create mock result
        questions = [
            QuizQuestion(number="1", question="Test question", answer="A")
        ]
        result = QuizResult(questions=questions, timestamp=time.time())
        
        # Call success callback
        self.app._on_api_success(result, "test-request-id")
        
        # Verify request manager was updated
        status = self.app.request_manager.get_current_status()
        self.assertEqual(status['status'], 'COMPLETED')
        self.assertIsNotNone(status['result'])
        
    def test_on_api_error_callback(self):
        """Test error callback updates request manager"""
        # Create a request first
        self.app.request_manager.create_request()
        
        # Call error callback
        error_message = "Test error message"
        self.app._on_api_error(error_message, "test-request-id")
        
        # Verify request manager was updated
        status = self.app.request_manager.get_current_status()
        self.assertEqual(status['status'], 'ERROR')
        self.assertEqual(status['error'], error_message)
        
    def test_handle_thread_completion_with_exception(self):
        """Test thread completion handler catches exceptions"""
        # Create mock future with exception
        future = Mock(spec=Future)
        test_exception = Exception("Test exception")
        future.exception.return_value = test_exception
        
        # Create a request
        request_id = self.app.request_manager.create_request()
        self.app._active_futures[request_id] = future
        
        # Call completion handler
        self.app._handle_thread_completion(future, request_id)
        
        # Verify exception was handled
        status = self.app.request_manager.get_current_status()
        self.assertEqual(status['status'], 'ERROR')
        self.assertIn("Test exception", status['error'])
        
        # Verify future was removed from active futures
        self.assertNotIn(request_id, self.app._active_futures)
        
    def test_handle_thread_completion_success(self):
        """Test thread completion handler for successful completion"""
        # Create mock future without exception
        future = Mock(spec=Future)
        future.exception.return_value = None
        
        # Create a request
        request_id = self.app.request_manager.create_request()
        self.app._active_futures[request_id] = future
        
        # Call completion handler
        self.app._handle_thread_completion(future, request_id)
        
        # Verify future was removed from active futures
        self.assertNotIn(request_id, self.app._active_futures)


if __name__ == '__main__':
    unittest.main()
