#!/bin/bash
# GitHub Codespaces setup script for Trade-Up Engine

echo "🚀 Setting up Trade-Up Engine development environment..."

# Install Python dependencies
pip install -r requirements.txt

# Create .env from example (for development/testing only)
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
fi

# Create necessary directories
mkdir -p logs/financial_audit
mkdir -p data

# Download sample data if not present
if [ ! -f data/customers_data_tradeup.csv ]; then
    echo "⚠️  No customer data found. Using mock data mode."
    # Could download test data from a public URL here
fi

# Set environment for testing
export USE_MOCK_DATA=true
export ENVIRONMENT=test

echo "✅ Setup complete! Trade-Up Engine is ready for development."
echo "📝 Note: Running in MOCK DATA mode (no real Redshift connection needed)"