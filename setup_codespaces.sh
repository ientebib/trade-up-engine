#!/usr/bin/env bash
# Trade-Up Engine SETUP ONLY for GitHub Codespaces (doesn't start server)

set -euo pipefail

echo "🚀 Setting up Trade-Up Engine for GitHub Codespaces..."

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

# Create a .env file if it doesn't exist
if [ ! -f .env ]; then
  echo "📝 Creating .env file with mock data configuration..."
  cat > .env << EOF
# Mock data mode for GitHub Codespaces
USE_MOCK_DATA=true

# Dummy Redshift credentials (not used in mock mode)
REDSHIFT_HOST=dummy.redshift.amazonaws.com
REDSHIFT_DATABASE=dummy
REDSHIFT_USER=dummy
REDSHIFT_PASSWORD=dummy
REDSHIFT_PORT=5439

# Environment Configuration
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# Logging Configuration
LOG_LEVEL=INFO
EOF
  echo "✅ Created .env file with mock data settings"
else
  echo "⚠️  .env file already exists - updating USE_MOCK_DATA..."
  # Update or add USE_MOCK_DATA
  if grep -q "USE_MOCK_DATA" .env; then
    sed -i.bak 's/USE_MOCK_DATA=.*/USE_MOCK_DATA=true/' .env
  else
    echo "USE_MOCK_DATA=true" >> .env
  fi
fi

echo ""
echo "✅ ============================================="
echo "✅ SETUP COMPLETE! Environment is ready."
echo "✅ ============================================="
echo ""
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "Or use the original script to setup AND start:"
echo "  ./run_codespaces.sh"