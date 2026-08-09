@echo off
REM Shared launcher used by start-scheduler.cmd / start-portal.cmd / etc.
REM Runs a gpu_swarm subcommand as a fully detached hidden process via
REM scripts.start_hidden. Logs: %%LOCALAPPDATA%%\GPUPool\logs\<module>.log
setlocal
set "ROOT=%~dp0.."
set "PY=C:\Python313\pythonw.exe"
if not exist "%PY%" set "PY=C:\Python313\python.exe"
"%PY%" -m scripts.start_hidden %*
exit /b %ERRORLEVEL%
