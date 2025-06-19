#!/bin/bash

# Trade-Up Engine Setup Script for Virtual Agent
# This script sets up the application in a virtual agent environment with network restrictions

echo "🚀 Setting up Trade-Up Engine for Virtual Agent..."

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

# Start the development server
echo "🌐 Starting development server..."
echo "Application will be available at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo "Development info: http://localhost:8000/dev-info"
echo ""
echo "🔧 Development mode features:"
echo "- External network calls disabled"
echo "- Using CSV files and sample data"
echo "- No Redshift connection required"
echo "- Virtual agent compatible"
echo ""

# Start the server (use port 8000 as specified in original discussion)
uvicorn main_dev:app --host 0.0.0.0 --port 8000 --reload 