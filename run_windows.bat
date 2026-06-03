@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Local venv missing. Running installer first...
    call install_windows.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" PythonSoundHelix.py
endlocal
