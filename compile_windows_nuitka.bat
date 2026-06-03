@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  PythonSoundHelix v0.4.3 - Nuitka onefile build
echo ============================================================
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Local venv missing. Running installer first...
    call install_windows.bat
    if errorlevel 1 exit /b 1
)
echo [1/2] Installing/updating Nuitka...
".venv\Scripts\python.exe" -m pip install --upgrade nuitka ordered-set zstandard
if errorlevel 1 goto fail
echo [2/2] Building onefile/no-console EXE...
".venv\Scripts\python.exe" -m nuitka ^
  --standalone ^
  --onefile ^
  --enable-plugin=pyqt6 ^
  --windows-console-mode=disable ^
  --include-data-dir=resources=resources ^
  --include-data-dir=presets=presets ^
  --output-dir=dist ^
  --output-filename=PythonSoundHelix.exe ^
  PythonSoundHelix.py
if errorlevel 1 goto fail
echo.
echo [OK] Build complete: dist\PythonSoundHelix.exe
pause
exit /b 0
:fail
echo [ERROR] Build failed.
pause
exit /b 1
