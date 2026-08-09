@echo off
setlocal
cd /d "%~dp0"
set "PY=C:\Python313\python.exe"
if not exist "%PY%" set "PY=python.exe"
"%PY%" -m scripts.launch_public %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [GPU Pool] Launch failed with exit %ERR%.
  echo Review data\launch_public.log and data\cloudflared_portal.log
  pause
)
exit /b %ERR%
