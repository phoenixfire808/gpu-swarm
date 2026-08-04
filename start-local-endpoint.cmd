@echo off
cd /d "%~dp0"
if not defined GPU_SWARM_SCHEDULER_URL set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
REM Local model API — runs hidden. Log: %LOCALAPPDATA%\GPUPool\logs\local-endpoint.log
call "%~dp0scripts\run-hidden.cmd" local-endpoint --host 127.0.0.1 %*
