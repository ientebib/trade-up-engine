#!/bin/bash

echo "🚀 Starting Trade-Up Engine..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️ No virtual environment found - run ./setup.sh first"
    exit 1
fi

# Start the server
echo "🌐 Starting server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 