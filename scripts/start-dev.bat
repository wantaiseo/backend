@echo off
REM ============================================
REM Start Development Server (Windows)
REM ============================================

echo Starting GEO Compiler API in development mode...
echo.

REM Check .env
if not exist .env (
    echo [WARNING] .env file not found!
    echo    copy .env.example .env
    echo    Then edit .env with your values
    exit /b 1
)

REM Create venv if needed
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

REM Start Celery worker in new window
echo Starting Celery worker...
start "Celery Worker" cmd /k "call .venv\Scripts\activate && celery -A celery_app worker --loglevel=info --pool=solo"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start API server
echo Starting API server...
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
