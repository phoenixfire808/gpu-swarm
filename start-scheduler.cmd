@echo off
REM Local-only scheduler — runs hidden. Log: %LOCALAPPDATA%\GPUPool\logs\scheduler.log
call "%~dp0scripts\_run_py.cmd" scheduler --host 127.0.0.1 --port 8766
