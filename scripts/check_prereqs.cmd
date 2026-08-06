@echo off
setlocal
cd /d "%~dp0.."
set "ARGS="
:loop
if "%~1"=="" goto exec
if /I "%~1"=="--text" set "ARGS=%ARGS% -Text" & shift & goto loop
if /I "%~1"=="--json" set "ARGS=%ARGS% -Json" & shift & goto loop
if /I "%~1"=="--scheduler-url" (
    set "ARGS=%ARGS% -SchedulerUrl ""%~2"""
    shift & shift
    goto loop
)
if /I "%~1"=="--min-disk-gb" (
    set "ARGS=%ARGS% -MinDiskGb %~2"
    shift & shift
    goto loop
)
echo Unknown argument: %~1
exit /b 2
:exec
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_prereqs.ps1" %ARGS%
exit /b %ERRORLEVEL%