#!/bin/bash

# Kill any existing servers
echo "🛑 Stopping any existing servers..."
pkill -f "uvicorn.*app.main"
sleep 1

# Set environment for production-like performance
export ENVIRONMENT=production
export PYTHONUNBUFFERED=1

# Run without reload for maximum performance
echo "🚀 Starting optimized server without auto-reload..."
echo "📌 Server will run at http://localhost:8000"
echo ""

# Use multiple workers for better performance on multi-core systems
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --loop uvloop \
    --log-level warning \
    --access-log