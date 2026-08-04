@echo off
setlocal
REM GPU Pool — idempotent joiner deps installer (wrapper for PowerShell)
REM Usage: install_joiner_deps.cmd [--with-torch-cuda] [--force] [--quiet]
cd /d "%~dp0.."
set "ARGS="
:parse
if "%~1"=="" goto run
if /I "%~1"=="--with-torch-cuda" set "ARGS=%ARGS% -WithTorchCuda" & shift & goto parse
if /I "%~1"=="-WithTorchCuda" set "ARGS=%ARGS% -WithTorchCuda" & shift & goto parse
if /I "%~1"=="--force" set "ARGS=%ARGS% -Force" & shift & goto parse
if /I "%~1"=="--quiet" set "ARGS=%ARGS% -Quiet" & shift & goto parse
echo Unknown arg: %~1
exit /b 2
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_joiner_deps.ps1" %ARGS%
exit /b %ERRORLEVEL%
