#!/bin/bash

# Trade-Up Engine Setup Script for Virtual Agent (Setup Only - No Server Start)
# This script sets up the application but doesn't start the server

echo "🚀 Setting up Trade-Up Engine for Virtual Agent (Setup Only)..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up development environment variables
echo "🔧 Setting up development environment..."
export DISABLE_EXTERNAL_CALLS=true
export USE_MOCK_DATA=true
export ENVIRONMENT=development

# Run setup script if exists
echo "⚙️ Running setup script..."
chmod +x setup.sh
./setup.sh

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🌐 To start the server manually, run:"
echo "   source venv/bin/activate"
echo "   uvicorn main_dev:app --host 0.0.0.0 --port 8000"
echo ""
echo "📋 Or use the background version:"
echo "   nohup uvicorn main_dev:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &"
echo ""
echo "🔧 Development mode features:"
echo "   - External network calls disabled"
echo "   - Sample data used"
echo "   - Virtual agent compatible" 