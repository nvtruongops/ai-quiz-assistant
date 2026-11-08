"""
Config Manager Module
Manages application configuration from .env and config.json
"""

import os
import json
from typing import Any, Optional

try:
    from path_utils import get_app_dir
    PROJECT_ROOT = get_app_dir()
except ImportError:
    try:
        from src.path_utils import get_app_dir
        PROJECT_ROOT = get_app_dir()
    except ImportError:
        _src_dir = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.dirname(_src_dir)

try:
    from dotenv import load_dotenv
except ImportError:
    # Built-in fallback parser if python-dotenv is not installed
    def load_dotenv(path: str = ".env", override: bool = True) -> bool:
        if not os.path.isabs(path):
            path = os.path.join(PROJECT_ROOT, path)
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if override or k not in os.environ:
                        os.environ[k] = v
            return True
        except Exception:
            return False


class ConfigManager:
    """Manage application configuration from config.json or .env file"""

    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        if not config_file:
            config_file = os.path.join(PROJECT_ROOT, "config.json")
        elif not os.path.isabs(config_file):
            config_file = os.path.join(PROJECT_ROOT, config_file)

        if not env_file:
            env_file = os.path.join(PROJECT_ROOT, ".env")
        elif not os.path.isabs(env_file):
            env_file = os.path.join(PROJECT_ROOT, env_file)

        self.config_file = config_file
        self.env_file = env_file
        self.config = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Read configuration from .env (primary for credentials) and config.json (for UI/hotkeys)
        """
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file, override=True)

        self.config = {
            'API_PROVIDER': os.getenv('API_PROVIDER', 'gemini'),
            'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
            'GEMINI_MODEL': os.getenv('GEMINI_MODEL', ''),
            'CUSTOM_API_URL': (os.getenv('CUSTOM_API_URL') or '').strip() or 'http://localhost:11434/v1',
            'CUSTOM_API_KEY': os.getenv('CUSTOM_API_KEY', ''),
            'CUSTOM_MODEL': os.getenv('CUSTOM_MODEL', ''),
            'POPUP_POSITION': os.getenv('POPUP_POSITION', 'cursor'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        }

    def reload(self) -> None:
        """Reload configuration from disk"""
        self.load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def is_valid(self) -> bool:
        """Check if active provider has valid credentials configured"""
        provider = self.get('API_PROVIDER', 'gemini')
        return self.is_provider_configured(provider)

    def is_provider_configured(self, provider: str) -> bool:
        """Check if a specific provider has valid configuration"""
        p = (provider or '').strip().lower()
        if p == 'custom':
            return bool(self.get('CUSTOM_API_URL') and self.get('CUSTOM_MODEL'))
        elif p == 'gemini':
            return bool(self.get('GEMINI_API_KEY'))
        return False

    def get_alternate_provider(self, current_provider: Optional[str] = None) -> Optional[str]:
        """
        Get alternate provider name if it is configured and ready as a fallback.
        E.g. If current is 'gemini', checks if 'custom' is configured; if current is 'custom', checks 'gemini'.
        """
        curr = (current_provider or self.get('API_PROVIDER', 'gemini')).strip().lower()
        alt = 'custom' if curr == 'gemini' else 'gemini'
        if self.is_provider_configured(alt):
            return alt
        return None
