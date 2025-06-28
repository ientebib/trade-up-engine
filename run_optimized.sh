#!/bin/bash

echo "🚀 Starting Optimized Trade-Up Engine Server"
echo "============================================"

# 1. Kill any existing servers
echo "🛑 Stopping any existing servers..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python.*app.main" 2>/dev/null || true
sleep 2

# 2. Set environment for REAL data with optimizations
export USE_MOCK_DATA=false
export DISABLE_EXTERNAL_CALLS=false
export PYTHONUNBUFFERED=1

# 3. Ensure required directories exist
mkdir -p logs/financial_audit 2>/dev/null
mkdir -p data 2>/dev/null

# 4. Check if customer data exists
if [ ! -f "customers_data_tradeup.csv" ] && [ -f "data/customers_data_tradeup.csv" ]; then
    echo "📁 Creating symlink to customer data..."
    ln -sf data/customers_data_tradeup.csv customers_data_tradeup.csv
fi

# 5. Clear Python cache for fresh start
echo "🗑️ Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 6. Start server with optimized settings
echo ""
echo "🌟 Server starting with:"
echo "   - Real customer data (CSV)"
echo "   - Real inventory data (Redshift - cached 4 hours)"
echo "   - Limited inventory query (10k records max)"
echo "   - No auto-reload"
echo "   - Optimized Deal Architect"
echo ""
echo "📌 Access points:"
echo "   - Dashboard: http://localhost:8000"
echo "   - Deal Architect: http://localhost:8000/deal-architect"
echo "   - Scenarios: http://localhost:8000/scenarios"
echo "   - Pipeline: http://localhost:8000/pipeline"
echo ""
echo "⚡ Performance optimizations applied:"
echo "   - Fast connection test (no COUNT)"
echo "   - 4-hour inventory caching"
echo "   - Limited inventory load (10k records)"
echo "   - No search on page load"
echo ""

# Run server with proper settings
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log