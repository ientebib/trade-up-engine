#!/bin/bash

echo "🔧 Fixing performance issues..."

# 1. Use REAL data from Redshift
export USE_MOCK_DATA=false
export DISABLE_EXTERNAL_CALLS=false

# 2. Kill any existing servers
echo "🛑 Stopping existing servers..."
pkill -f "uvicorn" 2>/dev/null || true
sleep 1

# 3. Clear any cache that might be corrupted
echo "🗑️ Clearing cache..."
rm -rf __pycache__ app/__pycache__ 2>/dev/null || true

# 4. Start server without reload and with minimal logging
echo "🚀 Starting server (mock data mode for speed)..."
echo "📌 Access at: http://localhost:8000"
echo ""

# Run with single worker, no reload
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level error \
    --no-access-log