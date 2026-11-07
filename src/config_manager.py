"""
Config Manager Module
Manages application configuration from .env and config.json
"""

import os
import json
from typing import Any, Optional

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
            'CUSTOM_API_URL': os.getenv('CUSTOM_API_URL', 'http://localhost:11434/v1'),
            'CUSTOM_API_KEY': os.getenv('CUSTOM_API_KEY', ''),
            'CUSTOM_MODEL': os.getenv('CUSTOM_MODEL', ''),
            'POPUP_POSITION': os.getenv('POPUP_POSITION', 'cursor'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        }

        # Check config.json for fallback / stored keys
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    json_config = json.load(f)
                    if not self.config['GEMINI_API_KEY'] and 'gemini_api_key' in json_config:
                        import base64
                        try:
                            decoded = base64.b64decode(json_config['gemini_api_key']).decode()
                            self.config['GEMINI_API_KEY'] = decoded
                            os.environ['GEMINI_API_KEY'] = decoded
                        except Exception:
                            pass
            except Exception:
                pass

    def reload(self) -> None:
        """Reload configuration from disk"""
        self.load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def is_valid(self) -> bool:
        """Check if active provider has valid credentials configured"""
        provider = self.get('API_PROVIDER', 'gemini')
        if provider == 'custom':
            return bool(self.get('CUSTOM_API_URL') and self.get('CUSTOM_MODEL'))
        return bool(self.get('GEMINI_API_KEY'))
