@echo off
setlocal
REM GPU Pool prerequisite probe (JSON by default)
REM Usage: scripts\check_prereqs.cmd [--text] [--scheduler-url URL]
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "ARGS="
:parse
if "%~1"=="" goto run
if /I "%~1"=="--text" set "ARGS=%ARGS% -Text" & shift & goto parse
if /I "%~1"=="--json" set "ARGS=%ARGS% -Json" & shift & goto parse
if /I "%~1"=="--scheduler-url" (
  set "ARGS=%ARGS% -SchedulerUrl ""%~2"""
  shift & shift & goto parse
)
if /I "%~1"=="--min-disk-gb" (
  set "ARGS=%ARGS% -MinDiskGb %~2"
  shift & shift & goto parse
)
echo Unknown arg: %~1
exit /b 2
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%check_prereqs.ps1" %ARGS%
exit /b %ERRORLEVEL%
