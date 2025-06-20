#!/usr/bin/env bash
# ------------------------------------------------------------
# run_local.sh – zero-config local launcher for Trade-Up Engine
# ------------------------------------------------------------
# 1) Creates a Python venv in ./venv if it doesn't exist
# 2) Installs requirements (skipped if already installed)
# 3) Exports flags so the app never touches Redshift / VPN
# 4) Starts the FastAPI dev server on http://localhost:8000
# ------------------------------------------------------------
# Usage: ./run_local.sh [setup|dev|prod]
#   setup -> create venv + install deps, then exit (good for CI)
#   dev   -> start dev server with mock/CSV data (default)
#   prod  -> start server with real Redshift / CSV data and respect .env

set -euo pipefail

MODE=${1:-dev}

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

# -------------------------
# Environment selection
# -------------------------
if [ "$MODE" = "dev" ]; then
  # Disable any external calls so no VPN / Redshift is required
  export DISABLE_EXTERNAL_CALLS=true
  export USE_MOCK_DATA=true
  export ENVIRONMENT=development
else
  # Production / local-real mode – rely on .env for credentials
  # Load .env if present (silently continues if file missing)
  if [ -f .env ]; then
    echo "🔑 Loading environment variables from .env …"
    # shellcheck source=/dev/null
    set -a; source .env; set +a
  fi

  export DISABLE_EXTERNAL_CALLS=${DISABLE_EXTERNAL_CALLS:-false}
  export USE_MOCK_DATA=${USE_MOCK_DATA:-false}
  export ENVIRONMENT=${ENVIRONMENT:-production}
fi

# Exit here for pure setup mode (used by CI)
if [ "$MODE" = "setup" ]; then
  echo "✅ Environment prepared – exiting as requested (setup mode)"
  exit 0
fi

# -------------------------
# Launch appropriate server
# -------------------------
if [ "$MODE" = "dev" ]; then
  echo "🚀 Launching Trade-Up Engine (DEV) at http://localhost:8000 …"
  uvicorn main_dev:app --host 0.0.0.0 --port 8000 --reload
else
  echo "🚀 Launching Trade-Up Engine (PROD) at http://localhost:8000 …"
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
