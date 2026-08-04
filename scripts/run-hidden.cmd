@echo off
setlocal EnableExtensions
REM run-hidden.cmd <gpu_swarm-subcommand> [args...]
REM Starts a gpu_swarm module in a hidden background process (no console spam).
REM Logs: %%LOCALAPPDATA%%\GPUPool\logs\<subcommand>.log

set "ROOT=%~dp0.."
if /I not "%~1"=="__hidden__" (
  powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command ^
    "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c','\"%~f0\"','__hidden__',%* -WorkingDirectory '%ROOT%'"
  echo Started %1 in the background. Log: %LOCALAPPDATA%\GPUPool\logs\%1.log
  exit /b 0
)

shift
set "MODULE=%~1"
shift
set "PYTHONUNBUFFERED=1"
cd /d "%ROOT%"

set "PY=C:\Python313\pythonw.exe"
if not exist "%PY%" set "PY=C:\Python313\python.exe"
if not exist "%PY%" (
  for /f "delims=" %%I in ('where pythonw 2^>nul') do set "PY=%%I" & goto :found
  for /f "delims=" %%I in ('where python 2^>nul') do set "PY=%%I"
)
:found
if not defined PY (
  echo ERROR: Python not found for hidden service start.
  exit /b 1
)

set "LOGDIR=%LOCALAPPDATA%\GPUPool\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\%MODULE%.log"

echo --- start %DATE% %TIME% module=%MODULE% --->> "%LOG%"
"%PY%" -m gpu_swarm %MODULE% %* >> "%LOG%" 2>&1
