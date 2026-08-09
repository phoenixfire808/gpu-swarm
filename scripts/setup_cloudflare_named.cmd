@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
REM Guided named-tunnel setup. The script opens browser login only when the user chooses this path.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_cloudflare_named.ps1" %*
exit /b %ERRORLEVEL%
