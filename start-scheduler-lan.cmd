@echo off
cd /d "%~dp0"
REM Bind all interfaces so Tailscale/LAN workers can reach the scheduler.
REM Members use: http://100.85.165.84:8766  (update Tailscale IP if it changes)
set PYTHONUNBUFFERED=1
C:\Python313\python.exe -m gpu_swarm scheduler --host 0.0.0.0 --port 8766
