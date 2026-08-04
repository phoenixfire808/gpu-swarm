@echo off
setlocal
REM GPU Pool idempotent joiner deps -> %LOCALAPPDATA%\GPUPool\venv
REM Verbose by default: step labels + pip progress (see install_joiner_deps.ps1)
REM Usage: scripts\install_joiner_deps.cmd [--with-torch-cuda] [--force] [--quiet] [--bootstrap-portable]
echo.
echo GPU Pool — preparing isolated Python (verbose progress below^)
echo What for: Contribute (share spare GPU/CPU^) or Utilize (run jobs^). No Docker.
echo.
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "ARGS="
:parse
if "%~1"=="" goto run
if /I "%~1"=="--with-torch-cuda" set "ARGS=%ARGS% -WithTorchCuda" & shift & goto parse
if /I "%~1"=="-WithTorchCuda" set "ARGS=%ARGS% -WithTorchCuda" & shift & goto parse
if /I "%~1"=="--force" set "ARGS=%ARGS% -Force" & shift & goto parse
if /I "%~1"=="--quiet" set "ARGS=%ARGS% -Quiet" & shift & goto parse
if /I "%~1"=="--bootstrap-portable" set "ARGS=%ARGS% -BootstrapPortable" & shift & goto parse
echo Unknown arg: %~1
exit /b 2
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_joiner_deps.ps1" %ARGS%
exit /b %ERRORLEVEL%
