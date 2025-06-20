#!/bin/bash

echo "🚀 Setting up Trade-Up Engine for virtual agent environment..."
echo "📦 This script will install all dependencies and configure the application"
echo ""

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $python_version found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"

# Install dependencies
echo "📦 Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p data app/static/css app/static/js app/templates core docs

# Create development environment file
echo "🔧 Creating development environment configuration..."
cat > .env << 'EOF'
# Development Environment - Virtual Agent Compatible
ENVIRONMENT=development
DISABLE_EXTERNAL_CALLS=true
USE_MOCK_DATA=true
DEBUG=true

# Database settings (not used in development)
REDSHIFT_HOST=localhost
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=dev_db
REDSHIFT_USER=dev_user
REDSHIFT_PASSWORD=dev_password
EOF

# Create sample customer data
echo "📊 Creating sample customer data..."
cat > customer_data.csv << 'EOF'
customer_id,risk_profile,monthly_payment,current_balance,vehicle_year,vehicle_make,vehicle_model
TMCJ33A32GJ053451,Low,8500,150000,2020,Tesla,Model 3
MEX5G2607HT063991,Medium,12000,200000,2019,BMW,X3
WAUAYJ8V9G1017027,High,15000,250000,2018,Audi,A4
JTDKARFU0J1234567,Low,9000,160000,2021,Toyota,Camry
1HGBH41JXMN109186,Medium,11000,180000,2020,Honda,Accord
EOF

# Create sample inventory data
echo "📦 Creating sample inventory data..."
cat > inventory_data.csv << 'EOF'
car_id,model,sales_price,region,kilometers,color,has_promotion,price_difference,hub_name,region_growth
INV001,Tesla Model 3 2023 Standard Range,850000,CDMX,15000,White,true,50000,Kavak CDMX Centro,0.15
INV002,BMW X3 2022 xDrive30i,1200000,Monterrey,25000,Black,false,0,Kavak Monterrey,0.12
INV003,Audi A4 2021 Premium Plus,950000,Guadalajara,30000,Silver,true,75000,Kavak Guadalajara,0.18
INV004,Toyota Camry 2023 XSE,750000,CDMX,12000,Blue,false,0,Kavak CDMX Sur,0.15
INV005,Honda Accord 2022 Touring,680000,Querétaro,18000,Red,true,45000,Kavak Querétaro,0.10
EOF

# Create engine configuration
echo "⚙️ Creating engine configuration..."
cat > engine_config.json << 'EOF'
{
    "use_custom_params": false,
    "use_range_optimization": false,
    "include_kavak_total": true,
    "service_fee_pct": 0.05,
    "cxa_pct": 0.04,
    "cac_bonus": 5000.0,
    "insurance_amount": 10999.0,
    "gps_fee": 350.0,
    "service_fee_range": [0.0, 5.0],
    "cxa_range": [0.0, 4.0],
    "cac_bonus_range": [0.0, 10000.0],
    "service_fee_step": 0.1,
    "cxa_step": 0.1,
    "cac_bonus_step": 100.0,
    "max_offers_per_tier": 50,
    "payment_delta_tiers": {
        "refresh": [-0.05, 0.05],
        "upgrade": [0.0501, 0.25],
        "max_upgrade": [0.2501, 1.0]
    },
    "term_priority": "standard",
    "min_npv_threshold": 5000.0,
    "development_mode": true
}
EOF

# Create startup script
echo "🚀 Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Trade-Up Engine in development mode..."
echo "🔧 External network calls disabled"
echo "📁 Using sample data"
echo ""

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export ENVIRONMENT=development
export DISABLE_EXTERNAL_CALLS=true
export USE_MOCK_DATA=true

# Start the application
echo "🌐 Server starting at http://localhost:8000"
echo "📊 Health check: http://localhost:8000/health"
echo ""

python main_dev.py
EOF

chmod +x start.sh

# Create test script
echo "🧪 Creating test script..."
cat > test.py << 'EOF'
#!/usr/bin/env python3
import sys
import os

print("🧪 Testing Trade-Up Engine setup...")

# Test imports
try:
    import fastapi
    import uvicorn
    import pandas
    print("✅ All packages imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test files
files = ["main_dev.py", "customer_data.csv", "inventory_data.csv", "engine_config.json", ".env"]
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file} - missing")

print("\n🎉 Setup complete!")
print("📋 To start: ./start.sh")
print("🌐 Access: http://localhost:8000")
print("🔧 Development mode: No Redshift connection required")
EOF

chmod +x test.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Available commands:"
echo "   ./test.py     - Test the setup"
echo "   ./start.sh    - Start the application"
echo ""
echo "🔧 Development mode features:"
echo "   - External network calls disabled"
echo "   - Sample data used"
echo "   - Virtual agent compatible"
echo ""
echo "🌐 Access the application at: http://localhost:8000" 
