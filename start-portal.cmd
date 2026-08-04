@echo off
cd /d "%~dp0"
REM Contributor portal on :8767 (scheduler stays on :8766; Robinhood uses :8765)
python -m gpu_swarm portal --host 127.0.0.1 --port 8767
