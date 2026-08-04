@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
C:\Python313\python.exe -m gpu_swarm worker --name Drew-Home --discord-user Drew
