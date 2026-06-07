@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" PythonSoundHelix.py
) else (
  py -3 PythonSoundHelix.py
)
