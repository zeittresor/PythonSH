@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  PythonSoundHelix v0.4.9 - PyQt6 GPLv3 Windows installer
echo ============================================================
where py >nul 2>nul
if %errorlevel%==0 (
    set PY=py -3
) else (
    set PY=python
)
%PY% --version
if errorlevel 1 (
    echo [ERROR] Python 3 was not found. Install Python 3.10+ first.
    pause
    exit /b 1
)
if not exist ".venv" (
    echo [1/3] Creating local virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto fail
)
echo [2/3] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto fail
echo [3/3] Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo [OK] Installation complete. Start with run_windows.bat
echo.
choice /C YN /N /T 10 /D Y /M "Launch PythonSoundHelix now? [Y/n] "
if errorlevel 2 exit /b 0
".venv\Scripts\python.exe" PythonSoundHelix.py
exit /b 0
:fail
echo [ERROR] Installation failed.
pause
exit /b 1
