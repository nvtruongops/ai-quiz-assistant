"""
Request Manager for AI Quiz Assistant application.

This module manages the state of quiz analysis requests, providing thread-safe
operations for creating, updating, and querying request status.
"""

import threading
import uuid
import time
from typing import Optional, Dict
from models import Request, QuizResult


class RequestManager:
    """Manages quiz analysis requests with thread-safe operations.
    
    This class handles the lifecycle of requests from creation through completion,
    maintaining the current request state and providing thread-safe access to
    request information.
    
    Attributes:
        current_request: The currently active Request object, or None
        lock: Threading lock for thread-safe operations
    """
    
    def __init__(self):
        """Initialize the RequestManager with no active request."""
        self.current_request: Optional[Request] = None
        self.lock = threading.Lock()
    
    def create_request(self) -> str:
        """Create a new request and set it as the current request.
        
        This method is thread-safe and will replace any existing request.
        The new request starts with status "PROCESSING".
        
        Returns:
            The unique ID of the newly created request
        """
        with self.lock:
            request_id = str(uuid.uuid4())
            self.current_request = Request(
                id=request_id,
                status="PROCESSING",
                created_at=time.time(),
                result=None,
                error=None
            )
            return request_id
    
    def update_status(self, status: str) -> None:
        """Update the status of the current request.
        
        Args:
            status: New status value (e.g., "PROCESSING", "COMPLETED", "ERROR")
        
        Note:
            This method is thread-safe. If no current request exists, this is a no-op.
        """
        with self.lock:
            if self.current_request:
                self.current_request.status = status
    
    def set_result(self, result: QuizResult) -> None:
        """Set the result for the current request and mark it as completed.
        
        Args:
            result: QuizResult object containing the analyzed questions and answers
        
        Note:
            This method automatically updates the status to "COMPLETED".
            If no current request exists, this is a no-op.
        """
        with self.lock:
            if self.current_request:
                self.current_request.result = result
                self.current_request.status = "COMPLETED"
    
    def set_error(self, error_message: str) -> None:
        """Set an error message for the current request and mark it as failed.
        
        Args:
            error_message: Description of the error that occurred
        
        Note:
            This method automatically updates the status to "ERROR".
            If no current request exists, this is a no-op.
        """
        with self.lock:
            if self.current_request:
                self.current_request.error = error_message
                self.current_request.status = "ERROR"
    
    def get_current_status(self) -> Dict:
        """Get the current status and information about the active request.
        
        Returns:
            Dictionary containing:
                - status: Current status ("NONE", "PROCESSING", "COMPLETED", "ERROR")
                - result: QuizResult object if completed, None otherwise
                - error: Error message if status is ERROR, None otherwise
                - elapsed_time: Time elapsed since request creation (only if processing)
        
        Note:
            This method is thread-safe and returns a snapshot of the current state.
        """
        with self.lock:
            if not self.current_request:
                return {
                    "status": "NONE",
                    "result": None,
                    "error": None,
                    "elapsed_time": None
                }
            
            status_info = {
                "status": self.current_request.status,
                "result": self.current_request.result,
                "error": self.current_request.error,
                "elapsed_time": None
            }
            
            # Include elapsed time if request is still processing
            if self.current_request.status == "PROCESSING":
                status_info["elapsed_time"] = self.current_request.get_elapsed_time()
            
            return status_info
    
    def clear_request(self) -> None:
        """Clear the current request.
        
        This method is thread-safe and can be used to reset the request state.
        """
        with self.lock:
            self.current_request = None
