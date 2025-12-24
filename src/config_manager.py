"""
Config Manager Module
Manage configuration from config.json file (from setup.py) or .env (fallback)
"""

import os
import json
from typing import Any, Optional
from dotenv import load_dotenv


class ConfigManager:
    """Manage application configuration from config.json or .env file"""

    def __init__(self, config_file: str = "config.json", env_file: str = ".env"):
        """
        Initialize ConfigManager

        Args:
            config_file: Path to config.json file (preferred)
            env_file: Path to .env file (fallback)
        """
        self.config_file = config_file
        self.env_file = env_file
        self.config = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Read configuration from config.json file (preferred) or .env (fallback)
        If no files exist, create .env.example template
        """
        # Prefer reading from config.json (from setup.py)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)

                # Map from config.json to old format for compatibility
                self.config = {
                    'POPUP_POSITION': 'cursor',  # Default
                    'LOG_LEVEL': 'INFO',  # Default
                }

                print("✅ Configuration loaded from config.json")
                return

            except Exception as e:
                print(f"⚠️  Error reading config.json: {e}, fallback to .env")

        # Fallback to .env if no config.json
        # Create .env.example if not exists
        if not os.path.exists(".env.example"):
            self.create_default_config()

        # Load .env file if exists
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)

            # Save values to dictionary for easy access
            self.config = {
                'POPUP_POSITION': os.getenv('POPUP_POSITION', 'cursor'),
                'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            }
        else:
            # If no .env file, use default values
            self.config = {
                'POPUP_POSITION': 'cursor',
                'LOG_LEVEL': 'INFO',
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Lấy giá trị cấu hình
        
        Args:
            key: Tên key cấu hình
            default: Giá trị mặc định nếu key không tồn tại
            
        Returns:
            Giá trị cấu hình hoặc default
        """
        return self.config.get(key, default)
    
    def create_default_config(self) -> None:
        """
        Tạo file .env.example với template cấu hình mẫu
        """
        default_config = """# Gemini API Configuration
# Set GEMINI_API_KEY environment variable or run: python setup.py
# Do NOT put your real API key in this file!

# Popup Configuration
# Options: "cursor" or "fixed:x,y" (e.g., "fixed:100,100")
POPUP_POSITION=cursor

# Logging Configuration
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
"""
        
        with open(".env.example", "w", encoding="utf-8") as f:
            f.write(default_config)
    
    def _validate_api_key(self) -> None:
        """
        Validate Gemini API key (silent - no console prompt)

        Raises:
            ValueError: If API key is invalid
        """
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key or api_key.strip() == '' or api_key == 'YOUR_GEMINI_API_KEY_HERE':
            raise ValueError("GEMINI_API_KEY is invalid or not configured")
    
    def get_gemini_api_key(self) -> str:
        """
        Get Gemini API key from environment variable
        
        Returns:
            Gemini API key or empty string if not found
        """
        api_key = os.getenv('GEMINI_API_KEY', '')
        if api_key and api_key.strip() != '' and api_key != 'YOUR_GEMINI_API_KEY_HERE':
            return api_key
        return ''
    
    def is_valid(self) -> bool:
        """
        Check if configuration is valid
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            self._validate_api_key()
            return True
        except ValueError:
            return False
    
    def reload(self) -> None:
        """
        Reload configuration from .env file
        Useful when .env file changes without restarting the application
        """
        self.load_config()
