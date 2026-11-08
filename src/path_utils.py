"""
Path Resolution Utilities
Handles environment pathing for development and PyInstaller frozen executable environments.
"""

import sys
import os

def is_frozen() -> bool:
    """Return True if running in a PyInstaller frozen executable bundle."""
    return getattr(sys, 'frozen', False)

def get_app_dir() -> str:
    """
    Get the persistent application root directory where user files reside.
    - When running as an .exe: Directory containing QuizAssistant.exe
    - When running from source: Repository root directory
    All persistent files (.env, config.json, logs/) are saved here.
    """
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    # path_utils.py is inside src/, so root is parent of src/
    src_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(src_dir)

def get_resource_path(relative_path: str = "") -> str:
    """
    Get the absolute path to a bundled read-only resource asset.
    - When frozen: Extracted to sys._MEIPASS temporary directory
    - When in source: Located under application root directory
    Used for icons, images, and pre-bundled templates.
    """
    if is_frozen():
        base_dir = getattr(sys, '_MEIPASS', get_app_dir())
    else:
        base_dir = get_app_dir()

    if relative_path:
        return os.path.normpath(os.path.join(base_dir, relative_path))
    return os.path.normpath(base_dir)

def ensure_dir(path: str) -> str:
    """Ensure a directory exists; creates parent directories if needed."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path
