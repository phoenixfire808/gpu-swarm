@echo off
cd /d "%~dp0"
echo Starting GPU Pool stack in the background (no extra console windows)...
call scripts\_run_py.cmd scheduler --host 127.0.0.1 --port 8766
timeout /t 2 /nobreak >nul
call scripts\_run_py.cmd portal --host 0.0.0.0 --port 8767
timeout /t 1 /nobreak >nul
call scripts\_run_py.cmd worker --name Host-PC
call scripts\_run_py.cmd bot
echo.
echo Done. One app window if you also run GPUPool.exe or start-gpu-pool-app.cmd
echo Logs: %LOCALAPPDATA%\GPUPool\logs\
echo Portal: http://127.0.0.1:8767/portal
