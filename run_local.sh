#!/usr/bin/env bash
# ------------------------------------------------------------
# run_local.sh – zero-config local launcher for Trade-Up Engine
# ------------------------------------------------------------
# 1) Creates a Python venv in ./venv if it doesn't exist
# 2) Installs requirements (skipped if already installed)
# 3) Exports flags so the app never touches Redshift / VPN
# 4) Starts the FastAPI dev server on http://localhost:8000
# ------------------------------------------------------------
set -euo pipefail

# Create venv once
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment …"
  python3 -m venv venv
fi

# Activate it
source venv/bin/activate

# Install dependencies (always run — quick and reliable)
echo "🔧 Installing Python packages …"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Disable any external calls so no VPN / Redshift is required
export DISABLE_EXTERNAL_CALLS=true
export USE_MOCK_DATA=true
export ENVIRONMENT=development

# Fire up the dev server
echo "🚀 Launching Trade-Up Engine (dev mode) at http://localhost:8000 …"
uvicorn main_dev:app --host 0.0.0.0 --port 8000 --reload 