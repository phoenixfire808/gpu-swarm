@echo off
setlocal
REM Compatibility shim for older commands.
REM Canonical hidden launch path: scripts\_run_py.cmd -> scripts.start_hidden
REM Usage: scripts\run-hidden.cmd <gpu_swarm-subcommand> [args...]
if "%~1"=="" (
  echo Usage: %~nx0 ^<gpu_swarm-subcommand^> [args...]
  exit /b 2
)
call "%~dp0_run_py.cmd" %*
exit /b %ERRORLEVEL%
