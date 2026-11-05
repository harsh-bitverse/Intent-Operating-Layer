#!/usr/bin/env bash
# Intent Operating Layer (IOL) - Local Startup Script (Bash)
# Starts FastAPI backend (port 8000) and Next.js frontend (port 3000) with graceful trap exit.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BACKEND_PORT="${1:-8000}"
FRONTEND_PORT="${2:-3000}"

echo "============================================================"
echo " INTENT OPERATING LAYER (IOL) - LOCAL PRODUCTION LAUNCHER   "
echo "============================================================"

# 1. Ensure Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python 3.11+ is required but not found."
    exit 1
fi
PYTHON_BIN="$(command -v python3 || command -v python)"
echo "[1/4] Found Python: $PYTHON_BIN"

# 2. Ensure Node
if ! command -v node &> /dev/null; then
    echo "Error: Node.js 18+ is required but not found."
    exit 1
fi
echo "[2/4] Found Node.js: $(command -v node)"

# 3. Ensure Backend Data Directory
mkdir -p "$PROJECT_ROOT/backend/data"

# 4. Start Backend Process
echo "[3/4] Launching FastAPI Backend on http://127.0.0.1:${BACKEND_PORT}..."
export PYTHONUNBUFFERED=1
export IOL_HOST=127.0.0.1
export IOL_PORT="${BACKEND_PORT}"
export CORS_ORIGINS="http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}"

$PYTHON_BIN -m uvicorn backend.iol.api.app:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

# 5. Start Frontend Process
echo "[4/4] Launching Next.js Frontend on http://localhost:${FRONTEND_PORT}..."
cd "$PROJECT_ROOT/frontend"
npm run start -- -p "${FRONTEND_PORT}" &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping IOL services gracefully..."
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
    kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo "IOL shutdown complete."
}

trap cleanup SIGINT SIGTERM EXIT

echo "============================================================"
echo " IOL Services Active!"
echo " -> Backend API:  http://127.0.0.1:${BACKEND_PORT} (/docs)"
echo " -> Frontend UI:  http://localhost:${FRONTEND_PORT}"
echo " Press Ctrl+C to stop all services."
echo "============================================================"

wait
