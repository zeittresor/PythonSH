@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo  PythonSoundHelix v0.6.5 - wheelhouse updater
echo ============================================================
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip
if not exist wheelhouse mkdir wheelhouse
".venv\Scripts\python.exe" -m pip download -r requirements.txt -d wheelhouse
".venv\Scripts\python.exe" -m pip install --no-index --find-links "%CD%\wheelhouse" -r requirements.txt
echo [OK] Update complete. Copy this folder including wheelhouse for offline installs.
