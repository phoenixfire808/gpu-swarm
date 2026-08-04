@echo off
cd /d "%~dp0"
REM Public HTTPS access for friends (no Tailscale) via Cloudflare quick tunnel.
REM Prerequisites: start-scheduler-lan.cmd + start-portal.cmd already running.
REM One public URL → portal UI; /pool-api proxies the scheduler (allowlisted jobs).
REM Invite code auth stays on. Leave this window open while friends need access.
setlocal
echo.
echo [GPU Pool] Starting public access tunnel (cloudflared quick tunnel)...
echo [GPU Pool] Ensure portal is up: start-portal.cmd  (http://127.0.0.1:8767)
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_public_tunnel.ps1" %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo.
  echo [GPU Pool] Tunnel failed (exit %ERR%). See data\cloudflared_portal.log
  echo Fallback: ngrok http 8767  — then paste the https URL into data\public_endpoints.json
  pause
  exit /b %ERR%
)
pause
endlocal
