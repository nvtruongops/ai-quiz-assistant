"""
Run Quiz Assistant without console window
Double-click this file to run the application
"""
import sys
import os
import subprocess

# Set working directory to project root
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir and os.path.exists(project_dir):
    os.chdir(project_dir)

# Add src to path
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, 'src'))


def ensure_dependencies():
    """Verify core dependencies are installed; auto-install via pip if missing"""
    required = [
        ('google-genai', 'google.genai'),
        ('pynput', 'pynput'),
        ('Pillow', 'PIL'),
        ('requests', 'requests'),
        ('python-dotenv', 'dotenv'),
        ('screeninfo', 'screeninfo'),
        ('pystray', 'pystray'),
    ]
    missing = []
    for pkg_name, mod_name in required:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        req_path = os.path.join(project_dir, 'requirements.txt')
        if os.path.exists(req_path):
            try:
                # Install missing requirements
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_path],
                    check=True,
                    cwd=project_dir
                )
            except Exception as e:
                try:
                    import tkinter as tk
                    from tkinter import messagebox
                    r = tk.Tk()
                    r.withdraw()
                    messagebox.showerror(
                        "Dependencies Error",
                        f"Could not auto-install required packages ({', '.join(missing)}):\n{e}\n\nPlease run 'python setup.py --install-deps' manually."
                    )
                    r.destroy()
                except Exception:
                    pass
                sys.exit(1)


# Check dependencies before hiding console (only when running from Python source)
if not getattr(sys, 'frozen', False):
    ensure_dependencies()

# Configure Windows process properties: hide console & set Per-Monitor DPI awareness
if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass
    try:
        # Per-Monitor V2 DPI awareness (prevents windows from unexpectedly scaling/shrinking)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

# Import and run
try:
    from src.main import main
except ImportError:
    from main import main

if __name__ == "__main__":
    main()
