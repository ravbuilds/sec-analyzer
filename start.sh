#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║       SEC Financial Explorer — Setup         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Backend
echo "▶ Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

echo ""
echo "▶ Starting FastAPI backend on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✓ Backend PID: $BACKEND_PID"

sleep 2

# Frontend
cd ../frontend
echo ""
echo "▶ Starting frontend on http://localhost:3000"

# Use Python's HTTP server
python3 -m http.server 3000 &
FRONTEND_PID=$!
echo "✓ Frontend PID: $FRONTEND_PID"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✓ App running!                              ║"
echo "║                                              ║"
echo "║  Frontend: http://localhost:3000             ║"
echo "║  Backend:  http://localhost:8000             ║"
echo "║  API Docs: http://localhost:8000/docs        ║"
echo "║                                              ║"
echo "║  Press Ctrl+C to stop both servers           ║"
echo "╚══════════════════════════════════════════════╝"

# Wait for either process to exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
