#!/bin/bash

echo "🧹 Cleaning up..."

# Check if lsof is available
if command -v lsof &> /dev/null; then
    # Kill ANY process using port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null
else
    echo "⚠️  lsof not found, trying alternative method..."
    # Alternative: Use ps and grep
    ps aux | grep -E "uvicorn.*8000" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null
fi

# Kill uvicorn processes
pkill -f uvicorn 2>/dev/null
sleep 2

# Check if port is still in use
if command -v lsof &> /dev/null && lsof -i:8000 &> /dev/null; then
    echo "❌ Error: Port 8000 is still in use!"
    echo "Please manually kill the process and try again."
    exit 1
fi

# Use real data
export USE_MOCK_DATA=false

echo "✅ Port 8000 is now free"
echo "🚀 Starting server..."
echo ""
echo "Access at: http://localhost:8000"
echo ""

# Start with minimal logging
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning