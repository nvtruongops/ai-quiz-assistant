@echo off
setlocal
echo ==============================================================================
echo   AI QUIZ ASSISTANT 2.0 - WINDOWS PRODUCTION BUILD
echo ==============================================================================
echo.

cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in system PATH!
    echo Please install Python 3.10+ and make sure it is added to your PATH.
    pause
    exit /b 1
)

echo [*] Launching Python Build Pipeline (build_exe.py)...
echo.
python build_exe.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! Check the output above for details.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] Build completed successfully!
echo Press any key to open the dist folder...
pause >nul
explorer "%~dp0dist"
