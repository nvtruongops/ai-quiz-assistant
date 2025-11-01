"""
Logger module for AI Quiz Assistant
Provides logging functionality with file rotation
"""

import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    """Logger class with rotating file handler"""
    
    def __init__(self, log_file: str = "logs/app.log"):
        """
        Initialize logger with rotating file handler
        
        Args:
            log_file: Path to log file (default: logs/app.log)
        """
        self.logger = None
        self.log_file = log_file
        self.setup_logger(log_file)
    
    def setup_logger(self, log_file: str):
        """
        Configure logger with RotatingFileHandler (max 10MB)
        Creates logs directory if it doesn't exist
        
        Args:
            log_file: Path to log file
        """
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create logger
        self.logger = logging.getLogger("QuizAssistant")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create rotating file handler (max 10MB, keep 3 backup files)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Create console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        """
        Log info level message
        
        Args:
            message: Message to log
        """
        if self.logger:
            self.logger.info(message)
    
    def error(self, message: str, exc_info=None):
        """
        Log error level message
        
        Args:
            message: Error message to log
            exc_info: Exception info (optional)
        """
        if self.logger:
            self.logger.error(message, exc_info=exc_info)
