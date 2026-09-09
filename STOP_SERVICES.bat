@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0STOP_SERVICES.ps1" %*
set "EWM_EXIT_CODE=%ERRORLEVEL%"

if not "%EWM_EXIT_CODE%"=="0" (
  echo.
  echo One or more project services could not be stopped safely.
  echo Run: npm run status
  if /I not "%EWM_NO_PAUSE%"=="1" pause
)

exit /b %EWM_EXIT_CODE%
