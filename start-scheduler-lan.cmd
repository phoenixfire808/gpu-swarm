@echo off
REM Scheduler for Tailscale/LAN — runs hidden (no console spam). Log: %LOCALAPPDATA%\GPUPool\logs\scheduler.log
call "%~dp0scripts\run-hidden.cmd" scheduler --host 0.0.0.0 --port 8766
