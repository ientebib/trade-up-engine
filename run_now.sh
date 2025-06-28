#!/bin/bash

echo "🧹 Cleaning up..."
# Kill ANY process using port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null
pkill -f uvicorn 2>/dev/null
sleep 2

# Use real data
export USE_MOCK_DATA=false

echo "✅ Port 8000 is now free"
echo "🚀 Starting server..."
echo ""
echo "Access at: http://localhost:8000"
echo ""

# Start with minimal logging
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning