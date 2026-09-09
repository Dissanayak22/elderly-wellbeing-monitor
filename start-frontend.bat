@echo off
REM Start frontend development server
REM Frontend runs on http://127.0.0.1:5173

cd /d "%~dp0frontend"

echo.
echo ================================================
echo Starting Frontend Server
echo ================================================
echo.

if not exist node_modules (
  echo WARNING: node_modules not found!
  echo Installing dependencies... (this may take a minute)
  call npm install
  if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm install failed!
    pause
    exit /b 1
  )
)

echo Starting Vite development server on http://127.0.0.1:5173
echo.

call npm run dev
