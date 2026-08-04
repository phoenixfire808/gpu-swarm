@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
echo GPU Pool Discord bot — requires GPU Pool app token in .env (NOT Hermes Jarvis).
echo Portal: https://discord.com/developers/applications  (app: GPU Pool)
echo Helper: set-discord-token.cmd ^<token^>   then invite via make-invite-url.cmd ^<client_id^>
echo.
C:\Python313\python.exe -m gpu_swarm bot
