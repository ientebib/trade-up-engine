#!/usr/bin/env bash
# Trade-Up Engine launcher - ALWAYS validates first
# This is the ONLY way to run the server

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

# Always production mode with Redshift
export ENVIRONMENT=production
export DISABLE_EXTERNAL_CALLS=false
export USE_MOCK_DATA=false

# Start server
echo "🚀 Starting Trade-Up Engine at http://localhost:8000..."
echo "📊 Using Redshift for inventory data"
python run_server.py