@echo off
cd /d "%~dp0"
REM Local-only bind. For Tailscale/LAN members use start-scheduler-lan.cmd
set PYTHONUNBUFFERED=1
C:\Python313\python.exe -m gpu_swarm scheduler --host 127.0.0.1 --port 8766
