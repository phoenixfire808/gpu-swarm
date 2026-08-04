@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
echo Starting GPU Pool desktop joiner…
echo Web portal (easiest remote path): http://100.85.165.84:8767/portal
echo This app is the power-user native joiner.
C:\Python313\python.exe -m gpu_swarm.app
if errorlevel 1 (
  echo.
  echo App exited with an error. Ensure customtkinter is installed:
  echo   C:\Python313\python.exe -m pip install --user customtkinter
  pause
)
