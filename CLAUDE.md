# CLAUDE.md - AI Coding Assistant Guide

This file helps AI assistants (like Claude) work effectively with the Trade-Up Engine codebase.

## ⚠️ CRITICAL: ALWAYS VERIFY CHANGES ARE VISIBLE

## 🔴 DO NOT MODIFY: Excel-Compatible Amortization Format

The amortization table calculation in `engine/calculator.py` has been carefully calibrated to match Excel's display format EXACTLY:

1. **Capital** = Sum of all PPMT components + GPS installation WITH IVA ($870 in month 1)
2. **Interés** = Sum of all IPMT components (without IVA)
3. **Cargos** = GPS monthly fee WITHOUT IVA ($350 only, no installation)
4. **IVA** = (Interés + Cargos) × 16% (NO separate GPS installation IVA)
5. **Exigible** = Total payment

**CRITICAL**: 
- GPS installation ($870 with IVA) goes in Capital for month 1
- IVA column does NOT include GPS installation IVA separately
- Columns MUST add up exactly: Capital + Interés + Cargos + IVA = Exigible

**DO NOT CHANGE** this calculation. It has been verified to match Excel exactly with both 18% and 21% interest rates.

## ⚠️ CRITICAL: ALWAYS VERIFY CHANGES ARE VISIBLE

**BEFORE claiming something is fixed, ALWAYS verify:**
1. Check if your changes affect the actual display/calculation
2. Run test scripts to confirm values change as expected
3. If editing templates, ensure you're editing the RIGHT template that's actually used
4. Test with different config values to ensure they're applied

**Common pitfalls to avoid:**
- Editing `amortization_table.html` when the actual display is in `modern_customer_detail_enhanced.html`
- Using `value || default` in JavaScript which treats 0 as falsy
- Assuming backend changes automatically reflect in frontend
- Not testing that custom config values actually affect calculations

## 🎯 Project Overview

**Trade-Up Engine** is a FastAPI web application that calculates optimal vehicle trade-up offers for Kavak customers in Mexico. It analyzes customer financial data and vehicle inventory to generate profitable upgrade proposals.

### Core Business Logic
- Customers have existing car loans with monthly payments
- System finds cars they can upgrade to with similar payments
- Offers are categorized into 3 tiers based on payment change:
  - **Refresh**: -5% to +5% payment change
  - **Upgrade**: +5% to +25% payment change  
  - **Max Upgrade**: +25% to +100% payment change

## 🏗️ Architecture

### Modern Service-Oriented Architecture (After Major Refactor)

```
app/
├── main.py              # FastAPI entry point
├── models.py            # Request/response models
├── api/                 # REST endpoints (thin controllers)
│   ├── customers.py     # Customer endpoints
│   ├── offers.py        # Offer generation endpoints
│   ├── cache.py         # Cache management endpoints
│   └── config.py        # Configuration endpoints
├── services/            # Business logic layer (NEW!)
│   ├── offer_service.py      # All offer-related logic
│   ├── customer_service.py   # All customer-related logic
│   ├── search_service.py     # Smart search functionality
│   └── config_service.py     # Configuration management
├── routes/              # Web page routes (thin controllers)
├── core/                # App initialization
│   └── startup.py       # Application startup (no dataframe loading!)
└── presenters/          # Data presentation layer

engine/                  # Core calculation engine
├── basic_matcher.py     # Main offer calculation
├── calculator.py        # NPV & amortization
├── payment_utils.py     # Payment calculations
└── smart_search.py      # Advanced search algorithms

config/                  # Configuration
├── config.py            # Business rules & rates
├── engine_config.json   # Runtime configuration
└── cache_config.py      # Cache settings

data/                    # Data access layer (COMPLETELY REDESIGNED!)
├── database.py          # Direct queries - NO GLOBAL STATE!
├── cache_manager.py     # Smart caching with TTL
└── loader.py            # CSV/Redshift loaders (used by database.py)
```

### Key Architectural Changes:
1. **NO MORE GLOBAL DATAFRAMES** - Everything queries on-demand
2. **Service Layer** - All business logic in `app/services/`
3. **Smart Caching** - 4-hour TTL for inventory, fresh customers
4. **Two-Stage Filtering** - Pre-filters at database level for 85-92% performance gain
5. **Clean Separation** - Routes → Services → Database → Engine

## 💰 Critical Financial Formulas

### Monthly Payment Calculation
Location: `engine/payment_utils.py`

```python
# Mexican loan with IVA (16% tax) on interest
monthly_rate = annual_rate / 12
monthly_rate_with_iva = (annual_rate * 1.16) / 12

# Payment includes:
# 1. Principal payment (calculated with IVA-inclusive rate)
# 2. Interest payment (calculated with base rate, then IVA applied)
# 3. GPS monthly fee: 350 * 1.16 = 406
# 4. GPS installation (first month only): 750 * 1.16 = 870
```

### NPV Calculation
Location: `engine/calculator.py`

```python
# NPV uses contractual interest for cash flows
# Then discounts at IVA-inclusive rate
# This is the audited method from risk team
```

### Key Constants
- **IVA_RATE**: 0.16 (16% tax, NOT 1.16!)
- **GPS_MONTHLY**: 350 MXN (before IVA)
- **GPS_INSTALLATION**: 750 MXN (before IVA)
- **Insurance**: 10,999 MXN/year (financed in 12-month cycles)

## 🔄 Data Access Patterns (NEW!)

### Direct Database Queries (No Global State)
```python
# OLD WAY (Global DataFrame) - DO NOT USE!
# customer = customers_df[customers_df["customer_id"] == id]

# NEW WAY (Direct Query)
from data import database
customer = database.get_customer_by_id(customer_id)  # Always fresh!
```

### Two-Stage Filtering for Performance
```python
# Stage 1: Pre-filter at database level (4000+ → ~300-500 cars)
inventory = database.get_tradeup_inventory_for_customer(customer)

# Stage 2: Apply business logic
offers = basic_matcher.find_all_viable(customer, inventory)
```

### Cache Management
```python
# Check cache status
GET /api/cache/status

# Force refresh all cached data
POST /api/cache/refresh

# Toggle cache on/off
POST /api/cache/toggle?enabled=false

# Update cache TTL
POST /api/cache/ttl?hours=6
```

## 🔧 Common Development Tasks

### 🎛️ Configuration Management (NEW!)

The application now uses a comprehensive configuration management system. ALL business parameters are configurable without code changes.

#### Change Configuration at Runtime
```python
from config.facade import get, get_decimal, set

# Get configuration values
gps_monthly = get_decimal("fees.gps.monthly")  # Returns Decimal('350.0')
interest_rate = get("rates.A1")  # Returns "0.1949"

# Change configuration at runtime
set("fees.gps.monthly", "400.0")  # Change to 400 MXN
set("rates.A1", "0.21")  # 21% for A1 profile
set("tiers.refresh.min", "-0.10")  # Allow 10% decrease

# Changes persist to engine_config.json
```

#### Configuration Sources (Priority Order)
1. **Database** (highest) - Future implementation
2. **JSON Files** - `config/engine_config.json` (overrides)
3. **Environment Variables** - For deployment
4. **Default Values** - `config/base_config.json`

#### Key Configuration Paths
- **Financial**: `financial.iva_rate`, `financial.max_loan_amount`
- **GPS Fees**: `fees.gps.monthly`, `fees.gps.installation`
- **Insurance**: `fees.insurance.amount`, `fees.insurance.term_months`
- **Service Fees**: `fees.service.percentage`, `fees.cxa.percentage`
- **Kavak Total**: `fees.kavak_total.amount`, `fees.kavak_total.cycle_months`
- **Payment Tiers**: `tiers.refresh.min/max`, `tiers.upgrade.min/max`
- **Interest Rates**: `rates.A1`, `rates.B2`, etc.
- **Features**: `features.enable_decimal_precision`, `features.enable_audit_logging`

### 📊 Financial Audit Trail (NEW!)

All financial calculations are now logged for compliance and debugging:

```python
# View recent calculations
from engine.financial_audit import get_audit_logger
audit = get_audit_logger()

# Get recent entries
recent = audit.get_recent_entries(100)

# Search by customer
entries = audit.search_entries(customer_id="TMCJ33A32GJ053451")

# Generate audit report
report = audit.generate_audit_report(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    output_file="audit_report_2024.json"
)
```

Audit logs are stored in `logs/financial_audit/` as JSON Lines files.

### 💰 Decimal Precision (NEW!)

Financial calculations now use Decimal type for precision:

```python
# Enable/disable Decimal precision
config.set("features.enable_decimal_precision", True)

# All monetary values automatically use Decimal when enabled
# No more floating-point rounding errors!
```

### Add New Risk Profile
1. Add rate to configuration: `config.set("rates.NEW_PROFILE", "0.25")`
2. Add to down payment matrix if needed
3. Update risk profile mapping in code

### Manage Cache Settings
```python
# Location: config/cache_config.py
CACHE_CONFIG = {
    "enabled": True,              # Master switch
    "default_ttl_hours": 4.0,     # Default 4-hour cache
    "inventory_ttl_hours": 4.0,   # Inventory-specific TTL
}
```

### Monitor Cache Performance
1. Go to http://localhost:8000/ (dashboard)
2. Check cache status indicators
3. Click "Force Refresh" to clear cache
4. Monitor hit rate for effectiveness

## 🚨 Critical Gotchas

### 0. Frontend/Backend Sync Issues
**ALWAYS check these are in sync:**
- API endpoints exist that frontend calls
- Request parameters match what backend expects
- Response structure matches what frontend uses
- Custom config values are actually used in calculations

**Known Issues Fixed:**
- `/api/generate-offers` → `/api/generate-offers-basic`
- `kavak_total_enabled` (boolean) → `kavak_total_amount` (number)
- Amortization display in `modern_customer_detail_enhanced.html` NOT `amortization_table.html`
- JavaScript `||` operator treating 0 as falsy (use `!== undefined` instead)

### 1. Car ID Types
**ALWAYS use strings for car IDs!**
```python
# ✅ CORRECT
car_id = str(inventory_df['car_id'])

# ❌ WRONG - Will cause 422 errors
car_id = inventory_df['car_id']  # If it's an integer
```

### 2. IVA Application
**IVA is 16% (0.16), not 116% (1.16)!**
```python
# ✅ CORRECT
gps_with_iva = GPS_MONTHLY * (1 + IVA_RATE)  # 350 * 1.16

# ❌ WRONG
gps_with_iva = GPS_MONTHLY * IVA_RATE  # Would give 350 * 0.16 = 56
```

### 3. Data Source
- **Production**: Always uses Redshift for inventory
- **Customer data**: From CSV file `customers_data_tradeup.csv`
- Never mock data in production

### 4. Column Names
The data loader expects these exact CSV columns:
- `CONTRATO` → customer_id
- `current_monthly_payment`
- `vehicle_equity`
- `saldo insoluto` → outstanding_balance
- `risk_profile` (e.g., A1, B2, C3)

### 5. Always Use Database Module
**IMPORTANT**: All data access must go through the database module!
```python
# ✅ ALWAYS USE THIS
from data import database
customer = database.get_customer_by_id(id)
inventory = database.get_tradeup_inventory_for_customer(customer)
```
The new architecture queries data on-demand through `data/database.py` for better performance and scalability. Never store dataframes globally!

## 📝 Making Changes

### Before Changing Financial Math
1. Check `engine/payment_utils.py` for payment logic
2. Check `engine/calculator.py` for NPV/amortization
3. Run test calculations to verify

### Before Changing Configuration
1. Check if it's in `config/config.py` (static)
2. Check if it's in `engine_config.json` (runtime)
3. Use the `/config` web page to test changes

### Before Adding Features
1. Check if similar functionality exists
2. Follow existing patterns (look at nearby code)
3. Update this file if you add critical logic

## 🧪 Testing Changes

### Quick Test Flow
```bash
# 1. Start server
./run_local.sh

# 2. Test health
curl http://localhost:8000/api/health

# 3. Test customer
curl http://localhost:8000/api/customers?limit=1

# 4. Test offer generation
curl -X POST http://localhost:8000/api/generate-offers-basic \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "TMCJ33A32GJ053451"}'
```

### Verify Calculations
1. Go to http://localhost:8000/customers
2. Click on a customer
3. Click "Generate Offers"
4. Click "View Amortization Table" on any offer
5. Verify payment matches displayed monthly payment
6. **VERIFY COLUMNS ADD UP**: Capital + Interés + IVA + Cargos = Exigible

### Verify Custom Config Works
1. Toggle Kavak Total ON → Generate → Note payment
2. Toggle Kavak Total OFF → Generate → Payment should be ~$772 less
3. Check offer details modal shows correct Kavak Total amount (0 or 25000)
4. Change service fee % → Verify it affects the service fee amount
5. Add CAC bonus → Verify it increases effective equity

## 🔍 Debugging Tips

### Common Errors

**422 Unprocessable Entity**
- Usually car_id type mismatch (should be string)
- Check request payload format

**NaN in Amortization Table**
- Check field names match between backend/frontend
- Verify all numeric calculations have valid inputs

**Wrong Monthly Payment**
- Check IVA_RATE = 0.16 (not 1.16)
- Verify GPS installation included in first month
- Check interest rate for customer's risk profile

### Useful Log Locations
- Server logs: `server.log`
- Look for "🚀", "✅", "❌" emojis for key events
- Search for customer_id to trace specific requests

## 🚀 Performance Notes

### Two-Stage Filtering Optimization
- **Stage 1**: Database pre-filtering reduces 4000+ cars to ~300-500 (85-92% reduction!)
- **Stage 2**: Business logic only processes pre-filtered candidates

### Smart Caching
- **Inventory**: Cached for 4 hours (configurable)
- **Customers**: Always fresh from database
- **First request**: ~2 seconds (queries Redshift)
- **Cached requests**: <50ms

### Parallel Processing
- Offer generation uses ThreadPoolExecutor (CPU count threads)
- Bulk operations load data once, filter per customer in memory
- Typical response time: <500ms for single customer (with cache)

## 🔐 Security Notes

- Never commit Redshift credentials
- Use `.env` file for local development
- All financial calculations happen server-side
- No sensitive data in frontend JavaScript

## 📞 Getting Help

### Core Business Logic
- **Service Layer**: `app/services/offer_service.py`, `app/services/customer_service.py`
- **Calculations**: `engine/basic_matcher.py`, `engine/calculator.py`
- **Payment Logic**: `engine/payment_utils.py`
- **Smart Search**: `engine/smart_search.py`

### Data Access
- **Database Queries**: `data/database.py` (NO global state!)
- **Cache Management**: `data/cache_manager.py`
- **Data Loading**: `data/loader.py` (used by database.py)

### Configuration
- **Business Rules**: `config/config.py`
- **Runtime Config**: `config/engine_config.json`
- **Cache Settings**: `config/cache_config.py`

### Architecture Documentation
- **Service Layer**: `SERVICE_LAYER_ARCHITECTURE.md`
- **Data Architecture**: `DATA_ARCHITECTURE.md`
- **Performance**: `TWO_STAGE_FILTERING.md`
- **Refactor Details**: `REFACTORING_PHASE1_REPORT.md`

When in doubt, search for the business term (e.g., "service_fee", "npv", "payment") to find where it's implemented.

## 🔄 Recent Updates (June 2025)

### Latest Critical Fixes (Just Completed)
1. **Comprehensive Configuration Management** ✅
   - ALL hardcoded values moved to configuration system
   - Multi-source configuration (DB, files, env, defaults)
   - Runtime configuration changes without restart
   - GPS fees, IVA rate, payment tiers - all configurable
   - Configuration validation and audit trail
   - See `config/facade.py`

2. **Financial Audit Trail System** ✅
   - All calculations logged for compliance
   - Structured JSON Lines format with rotation
   - Search and reporting capabilities
   - Automatic Decimal serialization
   - See `engine/financial_audit.py`

3. **Decimal Precision for Money** ✅
   - Optional Decimal type for all monetary calculations
   - Eliminates floating-point rounding errors
   - Configurable via `features.enable_decimal_precision`
   - Backwards compatible

4. **Enhanced Error Handling** ✅
   - Specific exception types (Connection, Timeout, etc.)
   - Better error messages in API responses
   - Circuit breaker for Redshift connections

### Major Architecture Refactor
1. **Eliminated Global DataFrames**
   - Replaced global state with on-demand queries
   - All data access through `data/database.py`
   - Better memory usage and scalability

2. **Service Layer Architecture**
   - Business logic moved to `app/services/`
   - Clean separation of concerns
   - Routes are now thin controllers

3. **Two-Stage Filtering Performance**
   - 85-92% reduction in data loading
   - Pre-filters at database level
   - Smart caching with configurable TTL

4. **Modern Data Architecture**
   - Always fresh data or controllably cached
   - Cache management UI and APIs
   - Support for multiple server instances

### Previous Fixes (Dec 2024)
1. **Amortization columns** - Now add up correctly
2. **Custom config values** - Properly applied in calculations
3. **Frontend/Backend sync** - Fixed endpoint mismatches

## ✅ Testing Changes

### Verify New Systems
```bash
# Run comprehensive verification script
python verify_new_systems.py
```

This script verifies:
- Configuration system is working
- Audit logging is capturing calculations
- Decimal precision is enabled
- Old hardcoded systems are removed

### Quick Verification
```bash
# Check cache status
curl http://localhost:8000/api/cache/status

# Generate offers (uses two-stage filtering)
curl -X POST http://localhost:8000/api/generate-offers-basic \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "TMCJ33A32GJ053451"}'

# Force cache refresh
curl -X POST http://localhost:8000/api/cache/refresh
```

### Verify Configuration Changes
```python
# Test runtime configuration changes
from config.facade import get, set, get_all

# View current configuration
print(get_all())

# Change a value
set("fees.gps.monthly", "400.0")

# Verify it persists
print(get("fees.gps.monthly"))  # Should show 400.0
```

### Verify Audit Logging
```python
# Check audit logs are being created
import os
print(os.listdir("logs/financial_audit/"))  # Should show .jsonl files

# View recent calculations
from engine.financial_audit import get_audit_logger
audit = get_audit_logger()
print(audit.get_recent_entries(5))
```

### Verify Architecture Changes
1. Monitor server logs - should NOT load all data on startup
2. Configuration loads from multiple sources
3. Audit logs created in `logs/financial_audit/`
4. GPS fees and IVA rate loaded from configuration
5. Decimal precision used when enabled