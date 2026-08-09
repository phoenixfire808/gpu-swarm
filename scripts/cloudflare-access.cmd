@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set PYTHONUNBUFFERED=1
where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is required for the source Cloudflare helper.
  echo Use GPUPool.exe for the guided installer path.
  exit /b 1
)
python -m gpu_swarm.cloudflare_access %*
exit /b %ERRORLEVEL%
