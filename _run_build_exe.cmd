@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1" -Clean
exit /b %ERRORLEVEL%
