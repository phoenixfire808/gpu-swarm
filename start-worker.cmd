@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
REM Worker — runs hidden. Log: %LOCALAPPDATA%\GPUPool\logs\worker.log
call "%~dp0scripts\run-hidden.cmd" worker --name Drew-Home --discord-user Drew
