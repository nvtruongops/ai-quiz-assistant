"""
Run Quiz Assistant without console window
Double-click this file to run the application
"""
import sys
import os

# Hide console window on Windows
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run
try:
    from src.main import main
except ImportError:
    from main import main

if __name__ == "__main__":
    main()
