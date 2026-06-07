@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
call :color 0B "============================================================"
echo.
call :color 0A " PythonSoundHelix v0.7.8 - PyQt6 GPLv3 Windows installer"
echo.
call :color 0B "============================================================"
echo.
where py >nul 2>nul
if errorlevel 1 (
  call :color 0C "[ERROR] Python launcher 'py' not found. Install Python 3.10+ first."
  echo.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  call :color 0E "[1/3] Creating local virtual environment..."
  echo.
  py -3 -m venv .venv || exit /b 1
) else (
  call :color 0A "[1/3] Local virtual environment exists."
  echo.
)
call :color 0E "[2/3] Installing requirements..."
echo.
if exist "wheelhouse\*.whl" (
  ".venv\Scripts\python.exe" -m pip install --no-index --find-links "%CD%\wheelhouse" -r requirements.txt || exit /b 1
) else (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
)
call :color 0A "[3/3] PythonSoundHelix is ready."
echo.
choice /C YN /N /T 10 /D Y /M "Launch PythonSoundHelix now? Auto-yes in 10 seconds. [Y/n] "
if errorlevel 2 exit /b 0
call run_windows.bat
exit /b 0
:color
powershell -NoProfile -Command "Write-Host $env:MSG -ForegroundColor Cyan" >nul 2>nul
set "MSG=%~2"
powershell -NoProfile -Command "Write-Host $env:MSG -ForegroundColor Green" 2>nul || echo %~2
exit /b 0
