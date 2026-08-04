@echo off
setlocal
REM GPU Pool — detect/install Tailscale + optional VirtualBox/Vagrant
REM Usage:
REM   scripts\install-prereqs.cmd
REM   scripts\install-prereqs.cmd -DetectOnly
REM   scripts\install-prereqs.cmd -SkipVirtualBox -SkipVagrant
REM   scripts\install-prereqs.cmd -ConnectTailscale
REM Auth key (optional, never commit): set GPU_SWARM_TAILSCALE_AUTHKEY=tskey-...
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install-prereqs.ps1" %*
exit /b %ERRORLEVEL%
