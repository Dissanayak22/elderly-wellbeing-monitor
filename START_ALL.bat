@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_ALL.ps1" %*
set "EWM_EXIT_CODE=%ERRORLEVEL%"

if not "%EWM_EXIT_CODE%"=="0" (
  echo.
  echo Startup failed. Review the message above or run: npm run status
  if /I not "%EWM_NO_PAUSE%"=="1" pause
)

exit /b %EWM_EXIT_CODE%
