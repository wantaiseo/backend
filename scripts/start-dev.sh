#!/bin/bash
# ============================================
# Start Development Server
# ============================================

echo "Starting GEO Compiler API in development mode..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your values"
    exit 1
fi

# Check Redis
if ! redis-cli ping &>/dev/null; then
    echo "⚠️  Redis not running!"
    echo "   Start with: docker run -d -p 6379:6379 redis:alpine"
    echo ""
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A celery_app worker --loglevel=info &
CELERY_PID=$!

# Trap to cleanup on exit
trap "kill $CELERY_PID 2>/dev/null" EXIT

# Start API server
echo "Starting API server..."
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
