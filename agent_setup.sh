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

# Start the development server in background
echo "🌐 Starting development server in background..."
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

# Start the server in background and save PID
nohup uvicorn main_dev:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &
SERVER_PID=$!
echo "✅ Server started in background (PID: $SERVER_PID)"
echo "📋 Server logs: tail -f server.log"
echo ""

# Wait a moment for server to start
sleep 3

# Test if server is responding
echo "🧪 Testing server connection..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is responding successfully!"
    echo "🎉 Setup complete! Your Trade-Up Engine is ready."
else
    echo "⚠️  Server may still be starting up. Check server.log for details."
fi

echo ""
echo "📋 Quick commands:"
echo "   curl http://localhost:8000/health     - Health check"
echo "   curl http://localhost:8000/dev-info  - Development info"
echo "   tail -f server.log                   - View server logs"
echo "   kill $SERVER_PID                     - Stop server" 