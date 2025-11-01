"""
Unit tests for Request Manager
"""

import unittest
import time
import threading
from src.request_manager import RequestManager
from src.models import QuizResult, QuizQuestion


class TestRequestManager(unittest.TestCase):
    """Test cases for RequestManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = RequestManager()
    
    def test_init(self):
        """Test initialization"""
        self.assertIsNone(self.manager.current_request)
        self.assertIsNotNone(self.manager.lock)
    
    def test_create_request(self):
        """Test creating a new request"""
        request_id = self.manager.create_request()
        
        self.assertIsNotNone(request_id)
        self.assertIsNotNone(self.manager.current_request)
        self.assertEqual(self.manager.current_request.id, request_id)
        self.assertEqual(self.manager.current_request.status, "PROCESSING")
        self.assertIsNone(self.manager.current_request.result)
        self.assertIsNone(self.manager.current_request.error)
    
    def test_update_status(self):
        """Test updating request status"""
        self.manager.create_request()
        self.manager.update_status("COMPLETED")
        
        self.assertEqual(self.manager.current_request.status, "COMPLETED")
    
    def test_set_result(self):
        """Test setting request result"""
        self.manager.create_request()
        
        quiz_result = QuizResult(
            questions=[
                QuizQuestion(number="1", question="Test question", answer="A")
            ],
            timestamp=time.time()
        )
        
        self.manager.set_result(quiz_result)
        
        self.assertEqual(self.manager.current_request.status, "COMPLETED")
        self.assertEqual(self.manager.current_request.result, quiz_result)
    
    def test_set_error(self):
        """Test setting request error"""
        self.manager.create_request()
        error_msg = "API timeout"
        
        self.manager.set_error(error_msg)
        
        self.assertEqual(self.manager.current_request.status, "ERROR")
        self.assertEqual(self.manager.current_request.error, error_msg)
    
    def test_get_current_status_none(self):
        """Test getting status when no request exists"""
        status = self.manager.get_current_status()
        
        self.assertEqual(status["status"], "NONE")
        self.assertIsNone(status["result"])
        self.assertIsNone(status["error"])
        self.assertIsNone(status["elapsed_time"])
    
    def test_get_current_status_processing(self):
        """Test getting status for processing request"""
        self.manager.create_request()
        time.sleep(0.1)  # Small delay to ensure elapsed time > 0
        
        status = self.manager.get_current_status()
        
        self.assertEqual(status["status"], "PROCESSING")
        self.assertIsNone(status["result"])
        self.assertIsNone(status["error"])
        self.assertIsNotNone(status["elapsed_time"])
        self.assertGreater(status["elapsed_time"], 0)
    
    def test_get_current_status_completed(self):
        """Test getting status for completed request"""
        self.manager.create_request()
        
        quiz_result = QuizResult(
            questions=[
                QuizQuestion(number="1", question="Test", answer="B")
            ],
            timestamp=time.time()
        )
        self.manager.set_result(quiz_result)
        
        status = self.manager.get_current_status()
        
        self.assertEqual(status["status"], "COMPLETED")
        self.assertEqual(status["result"], quiz_result)
        self.assertIsNone(status["error"])
        self.assertIsNone(status["elapsed_time"])
    
    def test_clear_request(self):
        """Test clearing current request"""
        self.manager.create_request()
        self.assertIsNotNone(self.manager.current_request)
        
        self.manager.clear_request()
        self.assertIsNone(self.manager.current_request)
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        results = []
        
        def create_requests():
            for _ in range(10):
                request_id = self.manager.create_request()
                results.append(request_id)
        
        threads = [threading.Thread(target=create_requests) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should complete without errors
        self.assertEqual(len(results), 50)
        self.assertIsNotNone(self.manager.current_request)


if __name__ == '__main__':
    unittest.main()

