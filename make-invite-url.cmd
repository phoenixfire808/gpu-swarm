@echo off
REM Usage: make-invite-url.cmd <CLIENT_ID>
REM Prints OAuth invite URL (no token). Permissions: View Channel + Send Messages + Embed Links + Read Message History.
setlocal
if "%~1"=="" (
  echo Usage: make-invite-url.cmd ^<CLIENT_ID^>
  exit /b 1
)
echo https://discord.com/oauth2/authorize?client_id=%~1^&permissions=84992^&scope=bot%%20applications.commands
exit /b 0
