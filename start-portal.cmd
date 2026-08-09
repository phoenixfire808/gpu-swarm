@echo off
REM Web portal — runs hidden. Log: %LOCALAPPDATA%\GPUPool\logs\portal.log
call "%~dp0scripts\_run_py.cmd" portal --host 0.0.0.0 --port 8767
