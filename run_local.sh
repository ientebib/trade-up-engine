#!/usr/bin/env bash
# Trade-Up Engine launcher (production mode only)

set -euo pipefail

# Validation file was removed during cleanup
# echo "🔍 Running pre-flight validation..."
# if ! python validate.py; then
#     echo "❌ Validation failed! Fix the issues above before running."
#     exit 1
# fi

# Create venv if needed
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "🔧 Installing Python packages..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# Load .env for Redshift credentials
if [ -f .env ]; then
  echo "🔑 Loading Redshift credentials from .env..."
  set -a; source .env; set +a
else
  echo "⚠️  No .env file found - using environment variables for Redshift"
fi

# Set Python path (project root)
export PYTHONPATH="$(pwd)"

export KAVAK_CXA_PCT=0.0399
export KAVAK_TOTAL_AMOUNT=17599

# Force production environment
export ENVIRONMENT=production

echo "🚀 Starting Trade-Up Engine (production mode) at http://localhost:8000..."

# Run with multiple workers for better performance
python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info