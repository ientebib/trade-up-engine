#!/bin/bash

# Kill any existing processes
pkill -f uvicorn 2>/dev/null
sleep 1

# Production mode - no mock data
# Start server directly
echo "Starting server on http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000