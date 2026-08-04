@echo off
cd /d "%~dp0"
REM Contributor portal on 0.0.0.0:8767 for localhost + Tailscale/LAN (scheduler stays on :8766; Robinhood uses :8765)
REM Members use: http://100.85.165.84:8767/portal  (update Tailscale IP if it changes)
set PYTHONUNBUFFERED=1
python -m gpu_swarm portal --host 0.0.0.0 --port 8767
