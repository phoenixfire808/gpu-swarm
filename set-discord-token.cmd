@echo off
REM Usage: set-discord-token.cmd <BOT_TOKEN>
REM Writes DISCORD_BOT_TOKEN into .env without printing the token.
setlocal EnableExtensions
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: set-discord-token.cmd ^<BOT_TOKEN^>
  echo Create app at https://discord.com/developers/applications then paste Bot token.
  exit /b 1
)
C:\Python313\python.exe -c "from pathlib import Path; import re,sys; p=Path('.env'); t=p.read_text(encoding='utf-8') if p.exists() else open('.env.example',encoding='utf-8').read(); tok=sys.argv[1].strip(); assert tok and len(tok)>=50, 'token looks too short'; nl='DISCORD_BOT_TOKEN='+tok; t2=re.sub(r'(?m)^DISCORD_BOT_TOKEN=.*$', nl, t) if re.search(r'(?m)^DISCORD_BOT_TOKEN=', t) else t.rstrip()+'\n'+nl+'\n'; p.write_text(t2, encoding='utf-8'); print('Wrote DISCORD_BOT_TOKEN last4='+tok[-4:]+' len='+str(len(tok)))" "%~1"
if errorlevel 1 exit /b 1
echo Done. Next: start-bot.cmd
exit /b 0
