@echo off
REM Local-only scheduler — runs hidden. Log: %LOCALAPPDATA%\GPUPool\logs\scheduler.log
call "%~dp0scripts\run-hidden.cmd" scheduler --host 127.0.0.1 --port 8766
