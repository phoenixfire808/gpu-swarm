@echo off
setlocal EnableExtensions
REM GPU Pool — install the optional Cloudflare connector into GPUPool tools.
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_cloudflared.ps1" %*
exit /b %ERRORLEVEL%
