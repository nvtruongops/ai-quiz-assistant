"""
Windows Shortcut & Shell Integration Manager for AI Quiz Assistant 2.0
Handles:
- Discovering standard user directories (Desktop, Start Menu, Programs)
- Creating Windows .lnk shortcuts with official application icons
- Registering application in Windows Registry (Add or Remove Programs / Apps & Features)
- Registering App Paths (enabling launch via Win+R or Command Line)
- Generating clean uninstaller scripts
"""

import os
import sys
import base64
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional

try:
    from constants import APP_NAME, APP_VERSION, APP_DISPLAY_NAME, GITHUB_REPO_URL
except ImportError:
    APP_NAME = "AI Quiz Assistant"
    APP_VERSION = "2.0.0"
    APP_DISPLAY_NAME = f"{APP_NAME} {APP_VERSION}"
    GITHUB_REPO_URL = "https://github.com/nvtruongops/ai-quiz-assistant"


def get_default_install_dir() -> str:
    """Return standard user program directory (no admin rights needed):
    %LOCALAPPDATA%\\Programs\\AI Quiz Assistant
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(local_app_data, "Programs", APP_NAME)


def get_desktop_dir() -> str:
    """Query Desktop directory from Windows Registry or fallback to ~/Desktop."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        return os.path.expandvars(val)
    except Exception:
        return os.path.expanduser(r"~\Desktop")


def get_start_menu_dir() -> str:
    """Query Programs (Start Menu) directory from Windows Registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, "Programs")
        winreg.CloseKey(key)
        return os.path.expandvars(val)
    except Exception:
        return os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")


def create_windows_shortcut(
    target_path: str,
    shortcut_path: str,
    icon_path: Optional[str] = None,
    description: str = APP_DISPLAY_NAME,
    working_dir: Optional[str] = None
) -> Tuple[bool, str]:
    """Create a Windows .lnk shortcut with optional custom icon using PowerShell COM.
    Returns (success: bool, message: str)
    """
    target_path = os.path.abspath(target_path)
    shortcut_path = os.path.abspath(shortcut_path)
    
    if not os.path.exists(target_path):
        return False, f"Target file does not exist: {target_path}"

    os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)

    if not working_dir:
        working_dir = os.path.dirname(target_path)
    working_dir = os.path.abspath(working_dir)

    icon_clause = ""
    if icon_path and os.path.exists(icon_path):
        abs_icon = os.path.abspath(icon_path)
        icon_clause = f"$sc.IconLocation = '{abs_icon},0'"

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{shortcut_path}')
$sc.TargetPath = '{target_path}'
$sc.WorkingDirectory = '{working_dir}'
$sc.Description = '{description}'
{icon_clause}
$sc.Save()
"""
    try:
        ps_bytes = ps_script.strip().encode("utf-16le")
        b64 = base64.b64encode(ps_bytes).decode("ascii")
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if res.returncode == 0 and os.path.exists(shortcut_path):
            return True, f"Shortcut created successfully at {shortcut_path}"
        else:
            return False, f"Failed to create shortcut (code {res.returncode}): {res.stderr or res.stdout}"
    except Exception as e:
        return False, f"Error executing PowerShell shortcut command: {e}"


def register_windows_app(
    install_dir: str,
    exe_path: str,
    icon_path: Optional[str] = None,
    version: str = APP_VERSION,
    display_name: str = APP_DISPLAY_NAME,
    publisher: str = "nvtruongops"
) -> Tuple[bool, str]:
    """Register application in Windows Registry under:
    - HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AIQuizAssistant
    - HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\QuizAssistant.exe
    Returns (success: bool, message: str)
    """
    if sys.platform != "win32":
        return False, "Windows registry registration is only supported on Windows"

    try:
        import winreg
        install_dir = os.path.abspath(install_dir)
        exe_path = os.path.abspath(exe_path)
        
        # Calculate approximate installation size in KB
        size_kb = 60000
        try:
            total_bytes = sum(f.stat().st_size for f in Path(install_dir).glob("**/*") if f.is_file())
            if total_bytes > 0:
                size_kb = int(total_bytes / 1024)
        except Exception:
            pass

        # 1. Register in Uninstall (Apps & Features)
        uninstall_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AIQuizAssistant"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, display_name)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, publisher)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            
            icon_val = exe_path
            if icon_path and os.path.exists(icon_path):
                icon_val = f"{os.path.abspath(icon_path)},0"
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_val)

            uninstaller_path = os.path.join(install_dir, "uninstall.bat")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}"')
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, GITHUB_REPO_URL)
            winreg.SetValueEx(key, "HelpLink", 0, winreg.REG_SZ, f"{GITHUB_REPO_URL}#readme")
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

        # 2. Register in App Paths so user can run 'QuizAssistant' from Win+R
        app_paths_key = r"Software\Microsoft\Windows\CurrentVersion\App Paths\QuizAssistant.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_paths_key) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, exe_path)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, install_dir)

        return True, "Application registered successfully in Windows Registry"
    except Exception as e:
        return False, f"Failed to register in Windows Registry: {e}"


def unregister_windows_app(remove_shortcuts: bool = True) -> Tuple[bool, str]:
    """Unregister application from Windows Registry and remove Desktop / Start Menu shortcuts."""
    if sys.platform != "win32":
        return False, "Windows registry is only supported on Windows"

    try:
        import winreg

        # 1. Remove Uninstall key
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AIQuizAssistant")
        except FileNotFoundError:
            pass
        except Exception:
            pass

        # 2. Remove App Paths key
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\QuizAssistant.exe")
        except FileNotFoundError:
            pass
        except Exception:
            pass

        # 3. Remove shortcuts if requested
        if remove_shortcuts:
            desktop_lnk = os.path.join(get_desktop_dir(), f"{APP_NAME}.lnk")
            if os.path.exists(desktop_lnk):
                try:
                    os.remove(desktop_lnk)
                except Exception:
                    pass

            start_menu_lnk = os.path.join(get_start_menu_dir(), f"{APP_NAME}.lnk")
            if os.path.exists(start_menu_lnk):
                try:
                    os.remove(start_menu_lnk)
                except Exception:
                    pass

        return True, "Application unregistered from Windows successfully"
    except Exception as e:
        return False, f"Failed to unregister: {e}"


def create_desktop_and_start_menu_shortcuts(
    exe_path: str,
    icon_path: Optional[str] = None,
    app_name: str = APP_NAME
) -> Tuple[bool, str]:
    """Create both Desktop and Start Menu shortcuts pointing to exe_path with icon_path."""
    desktop_lnk = os.path.join(get_desktop_dir(), f"{app_name}.lnk")
    start_menu_lnk = os.path.join(get_start_menu_dir(), f"{app_name}.lnk")

    ok1, msg1 = create_windows_shortcut(exe_path, desktop_lnk, icon_path=icon_path)
    ok2, msg2 = create_windows_shortcut(exe_path, start_menu_lnk, icon_path=icon_path)

    if ok1 and ok2:
        return True, f"Created shortcuts on Desktop and Start Menu"
    elif ok1:
        return True, f"Created Desktop shortcut ({msg2})"
    elif ok2:
        return True, f"Created Start Menu shortcut ({msg1})"
    else:
        return False, f"Failed to create shortcuts: {msg1}; {msg2}"


def generate_uninstaller_script(install_dir: str) -> str:
    """Generate a clean uninstall.bat batch script inside the installation directory."""
    uninstaller_path = os.path.join(install_dir, "uninstall.bat")
    desktop_lnk = os.path.join(get_desktop_dir(), f"{APP_NAME}.lnk")
    start_menu_lnk = os.path.join(get_start_menu_dir(), f"{APP_NAME}.lnk")

    bat_content = f"""@echo off
setlocal
title Uninstall {APP_DISPLAY_NAME}
echo ==============================================================================
echo   UNINSTALL {APP_DISPLAY_NAME.upper()}
echo ==============================================================================
echo.
echo Are you sure you want to uninstall {APP_DISPLAY_NAME}?
set /p confirm="Type Y to continue, or N to cancel [Y/n]: "
if /i "%confirm%"=="n" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo [*] Terminating running instances of QuizAssistant.exe...
taskkill /f /im QuizAssistant.exe >nul 2>&1

echo [*] Removing shortcuts...
if exist "{desktop_lnk}" del /f /q "{desktop_lnk}"
if exist "{start_menu_lnk}" del /f /q "{start_menu_lnk}"

echo [*] Removing Windows Registry entries...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AIQuizAssistant" /f >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\QuizAssistant.exe" /f >nul 2>&1

echo.
echo [*] {APP_DISPLAY_NAME} has been uninstalled.
echo Note: User configuration and log files in this folder were preserved.
echo To completely remove all files, delete this directory:
echo   {install_dir}
echo.
pause
"""
    with open(uninstaller_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    return uninstaller_path
