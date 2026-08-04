@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
if not defined GPU_SWARM_SCHEDULER_URL set GPU_SWARM_SCHEDULER_URL=http://127.0.0.1:8766
echo.
echo  Local Pool Endpoint — OpenAI-compatible model on localhost
echo  Paste into Open WebUI / LM Studio / Continue / Cursor:
echo    OPENAI_BASE_URL=http://127.0.0.1:8080/v1
echo  (If 8080 is busy, the service may bind 11434 — check the log lines below.)
echo  Docs: LOCAL_MODEL.md
echo.
C:\Python313\python.exe -m gpu_swarm local-endpoint --host 127.0.0.1 %*
