#!/bin/bash

echo "🚀 Setting up Trade-Up Engine..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing Python packages..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Check if customer data exists
if [ ! -f "customer_data.csv" ]; then
    echo "⚠️ Warning: customer_data.csv not found - will use sample data"
fi

# Check if engine config exists
if [ ! -f "engine_config.json" ]; then
    echo "⚠️ Warning: engine_config.json not found - will use defaults"
fi

# Make sure required directories exist
mkdir -p data
mkdir -p app/static
mkdir -p app/templates

echo "✅ Setup complete!"
echo ""
echo "🌟 To start the application:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "🔗 Dashboard: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/api/config-status"
echo ""
echo "⚠️ Known issues to debug:"
echo "   1. Redshift connection failing (inventory will be limited)"
echo "   2. No offers generating for customers (engine logic issue)"
echo "" 