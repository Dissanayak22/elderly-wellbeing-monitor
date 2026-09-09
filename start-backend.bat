@echo off
REM Start Progress-1 backend from project root
REM Backend API runs on http://127.0.0.1:8000

cd /d "%~dp0"
set PYTHONPATH=%cd%

echo.
echo ================================================
echo Starting Backend API
echo ================================================
echo.

if exist backend\.venv\Scripts\activate.bat (
  call backend\.venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
) else (
  echo ERROR: Virtual environment not found!
  echo Please run: python -m venv .venv
  pause
  exit /b 1
)

echo Starting FastAPI server on http://127.0.0.1:8000
echo API Documentation: http://127.0.0.1:8000/docs
echo.

uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

