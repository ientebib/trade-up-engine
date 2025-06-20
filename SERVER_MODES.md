# Trade-Up Engine Server Modes

## Overview

The Trade-Up Engine supports two different server modes, each optimized for different use cases:

## Development Server (`main_dev.py`)

**Purpose**: Virtual agent environments and development testing

**How to start**: 
```bash
./start.sh
# OR
python main_dev.py
```

**Features**:
- ✅ All API endpoints (now matches production)
- ✅ Mock data support (no external database required)
- ✅ Disabled external network calls
- ✅ Fast startup with sample data
- ✅ Compatible with frontend JavaScript
- ✅ Scenario analysis with mock results

**API Endpoints** (Updated - Now Production Compatible):
- `GET /api/customers` - List all customers
- `GET /api/customer/{id}` - Get specific customer
- `POST /api/generate-offers` - Generate offers (JSON body format)
- `POST /api/amortization-table` - Get payment schedule
- `GET /api/inventory` - List available inventory
- `GET /api/config` - Get current configuration
- `GET /api/config-status` - Get configuration status
- `POST /api/save-config` - Save configuration
- `POST /api/scenario-analysis` - Run scenario analysis
- `GET /health` - Health check
- `GET /dev-info` - Development mode information

## Production Server (`main.py`)

**Purpose**: Full production deployment with real data

**How to start**:
```bash
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Features**:
- ✅ Real Redshift database connection
- ✅ Full engine functionality
- ✅ Real scenario analysis
- ✅ Production-grade performance
- ✅ All API endpoints

## API Compatibility

Both servers now expose **identical API interfaces**:

### Generate Offers Endpoint
```http
POST /api/generate-offers
Content-Type: application/json

{
  "customer_data": {
    "customer_id": "string",
    "current_monthly_payment": 8500,
    "vehicle_equity": 50000,
    "current_car_price": 200000,
    "risk_profile_name": "Low",
    "risk_profile_index": 0
  },
  "inventory": [
    {
      "car_id": 2001,
      "model": "Honda Civic 2024",
      "sales_price": 290596.69
    }
  ],
  "engine_config": {
    "include_kavak_total": true,
    "use_custom_params": false
  }
}
```

### Scenario Analysis Endpoint
```http
POST /api/scenario-analysis
Content-Type: application/json

{
  "use_custom_params": false,
  "use_range_optimization": false,
  "include_kavak_total": true,
  "service_fee_pct": 0.05,
  "cxa_pct": 0.04,
  "cac_bonus": 5000.0,
  "payment_delta_tiers": {
    "refresh": [-0.05, 0.05],
    "upgrade": [0.0501, 0.25],
    "max_upgrade": [0.2501, 1.00]
  }
}
```

## Frontend Compatibility

The frontend JavaScript (`main.js`) works with **both servers** now:
- ✅ Calls `/api/generate-offers` with JSON body
- ✅ Calls `/api/scenario-analysis` for global config
- ✅ Handles offer generation and display
- ✅ Manages configuration changes

## When to Use Which

### Use Development Server (`./start.sh`) When:
- Working in virtual agent environments
- No database access available
- Quick testing and development
- Demonstrating functionality with sample data
- Learning the system

### Use Production Server (`python main.py`) When:
- Connecting to real Redshift database
- Processing real customer data
- Production deployment
- Full performance testing
- Generating real business results

## Migration Guide

If you were previously running into API compatibility issues:

1. **For Development**: Use `./start.sh` - all endpoints now work
2. **For Production**: Use `python main.py` - unchanged
3. **Frontend**: No changes needed - works with both servers

Both servers now provide consistent API behavior, so you can develop with the dev server and deploy to production without frontend changes. 