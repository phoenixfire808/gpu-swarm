@echo off
cd /d "%~dp0"
start "gpu-swarm-scheduler" cmd /k "%~dp0start-scheduler.cmd"
timeout /t 2 /nobreak >nul
start "gpu-swarm-worker" cmd /k "%~dp0start-worker.cmd"
timeout /t 1 /nobreak >nul
start "gpu-swarm-bot" cmd /k "%~dp0start-bot.cmd"
echo Started scheduler, worker, and bot windows.
