@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
set "REPO=%CD%"
set "GPU_HOME=%LOCALAPPDATA%\GPUPool"
set "VENV_PY=%GPU_HOME%\venv\Scripts\python.exe"
set "PORTABLE_PY=%GPU_HOME%\python\python.exe"

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
echo Isolated Python home: %GPU_HOME%
echo.

REM Prefer: GPU_SWARM_PYTHON → isolated venv → portable → py launcher → PATH.
set "PYEXE="
if defined GPU_SWARM_PYTHON if exist "%GPU_SWARM_PYTHON%" set "PYEXE=%GPU_SWARM_PYTHON%"
if not defined PYEXE if exist "%VENV_PY%" set "PYEXE=%VENV_PY%"
if not defined PYEXE if exist "%PORTABLE_PY%" set "PYEXE=%PORTABLE_PY%"

if not defined PYEXE (
  where py >nul 2>&1 && (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
  )
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
  echo No system Python found — bootstrapping portable Python into %%LOCALAPPDATA%%\GPUPool ...
  where py >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ERROR: Need any Python once to bootstrap, OR use GPUPool.exe from Releases.
    echo FIX:
    echo   1^) Download GPUPool.exe from GitHub Releases ^(no Python needed^)
    echo   2^) Or install Python 3.10+ from https://www.python.org/downloads/windows/
    echo   3^) Or ask the host — Submit diagnostics from a machine that can run the EXE
    echo.
    pause
    exit /b 1
  )
  REM Use py -3 to run bootstrap helper if we somehow have launcher but no exe resolved
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
)

if not defined PYEXE (
  echo ERROR: Python 3.10+ not found.
  echo Prefer GPUPool.exe ^(portable bootstrap on first run^) or install Python 3.10+.
  pause
  exit /b 1
)

echo Using: %PYEXE%
"%PYEXE%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)"
if errorlevel 1 (
  echo WARNING: System Python is below 3.10 — bootstrapping portable Python...
  "%PYEXE%" -c "from gpu_swarm.portable_python import ensure_portable_python; import json; print(json.dumps(ensure_portable_python(with_venv=True, with_requirements=True)))"
  if exist "%VENV_PY%" (
    set "PYEXE=%VENV_PY%"
    set "GPU_SWARM_PYTHON=%VENV_PY%"
    echo Switched to isolated venv: %PYEXE%
  ) else (
    echo ERROR: Portable bootstrap failed. Use GPUPool.exe or fix system Python.
    pause
    exit /b 1
  )
)

REM Quick smoke: if interpreter is broken, bootstrap portable instead of fighting it.
"%PYEXE%" -c "import pip, venv" 1>nul 2>nul
if errorlevel 1 (
  echo WARNING: Python pip/venv broken — bootstrapping portable isolate...
  "%PYEXE%" -c "from gpu_swarm.portable_python import ensure_portable_python; ensure_portable_python(with_venv=True, with_requirements=True)" 2>nul
  if exist "%VENV_PY%" (
    set "PYEXE=%VENV_PY%"
    set "GPU_SWARM_PYTHON=%VENV_PY%"
  )
)

set "GPU_SWARM_PYTHON=%PYEXE%"

REM Ensure joiner UI deps exist (skip if already importable). Prefer venv installs (no --user).
"%PYEXE%" -c "import customtkinter, httpx, psutil" 1>nul 2>nul
if errorlevel 1 (
  echo Installing missing packages from requirements.txt into isolated env ...
  echo %PYEXE% | find /I "\GPUPool\venv\" >nul
  if not errorlevel 1 (
    "%PYEXE%" -m pip install -r "%REPO%\requirements.txt"
  ) else (
    "%PYEXE%" -m pip install --user -r "%REPO%\requirements.txt"
  )
  if errorlevel 1 (
    echo FIX: Bootstrap portable Python in the wizard, or:
    echo   "%PYEXE%" -m pip install -r requirements.txt
    echo Then use Copy log / Submit diagnostics if it still fails.
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
  echo Use the wizard Copy log / Submit diagnostics, or:
  echo   "%PYEXE%" -m pip install customtkinter httpx psutil
  echo Logs: %GPU_HOME%\logs\
  pause
)
exit /b %EC%
