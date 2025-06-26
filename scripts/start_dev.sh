#!/usr/bin/env bash
# Development server startup script
# Uses new configuration system automatically

# Exit on error
set -e

# Change to project root
cd "$(dirname "$0")/.."

# Ensure USE_NEW_CONFIG is set (redundant now since it's in .env, but explicit is good)
export USE_NEW_CONFIG=true

# Kill any existing server
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 2

# Start server in background
echo "🚀 Starting Trade-Up Engine development server..."
nohup ./run_local.sh > server.log 2>&1 &
SERVER_PID=$!

echo "✅ Server running (PID: $SERVER_PID)"
echo "📋 Logs: tail -f server.log"
echo "🌐 URL: http://localhost:8000"
echo ""
echo "To stop: kill $SERVER_PID or pkill -f 'uvicorn app.main:app'"