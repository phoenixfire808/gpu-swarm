@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
set "REPO=%CD%"

echo ============================================
echo  GPU Pool — one-stop desktop joiner
echo ============================================
echo Repo: %REPO%
echo Web portal (easiest remote path):
echo   http://127.0.0.1:8767/portal
echo   http://100.85.165.84:8767/portal
echo Invite code: glitch-factor
echo   (pool password stays in .env — not printed here)
echo.

REM Prefer py launcher, then python on PATH, then common install paths.
set "PYEXE="
where py >nul 2>&1 && (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
)
if not defined PYEXE (
  where python >nul 2>&1 && (
    for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
  )
)
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "C:\Python313\python.exe" set "PYEXE=C:\Python313\python.exe"
if not defined PYEXE if exist "C:\Python312\python.exe" set "PYEXE=C:\Python312\python.exe"

if not defined PYEXE (
  echo ERROR: Python 3.10+ not found.
  echo.
  echo FIX:
  echo   1^) Install from https://www.python.org/downloads/windows/
  echo   2^) Check "Add python.exe to PATH"
  echo   3^) Re-run this script ^(double-click start-gpu-pool-app.cmd^)
  echo.
  pause
  exit /b 1
)

echo Using: %PYEXE%
"%PYEXE%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)"
if errorlevel 1 (
  echo ERROR: Need Python 3.10+. Found:
  "%PYEXE%" -c "import sys; print(sys.version)"
  echo FIX: Install Python 3.10+ and re-run.
  pause
  exit /b 1
)

REM Ensure joiner UI deps exist (skip if already importable).
"%PYEXE%" -c "import customtkinter, httpx, psutil" 1>nul 2>nul
if errorlevel 1 (
  echo Installing missing packages from requirements.txt ...
  "%PYEXE%" -m pip install --user -r "%REPO%\requirements.txt"
  if errorlevel 1 (
    echo FIX: "%PYEXE%" -m pip install --user -r requirements.txt
    pause
    exit /b 1
  )
)

echo Starting GPU Pool app...
"%PYEXE%" -m gpu_swarm.app
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo App exited with error code %EC%.
  echo FIX: "%PYEXE%" -m pip install --user customtkinter httpx psutil
  echo Then re-run start-gpu-pool-app.cmd
  pause
)
exit /b %EC%
