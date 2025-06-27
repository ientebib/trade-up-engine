# CLAUDE.md - AI Assistant Guide for Trade-Up Engine

## 🎯 What This Codebase Does

**Trade-Up Engine** calculates vehicle trade-up offers for Kavak customers in Mexico. It finds cars customers can upgrade to with similar monthly payments.

**Core Flow**: Customer → Find Better Cars → Calculate Payments → Generate Offers → Categorize by Payment Change

## ⚡ Quick Start for AI Assistants

### Understanding the Code
```bash
# Main entry point
app/main.py                 # FastAPI application

# Where business logic lives
app/services/               # All business logic here
engine/basic_matcher.py     # Core offer calculation
engine/calculator.py        # Payment calculations

# Data access
data/database.py           # Get customers/inventory
config/facade.py           # All configuration
```

### Making Changes
1. **ALWAYS** test financial calculations - they affect real money
2. **NEVER** modify `generate_amortization_table` in calculator.py
3. **USE** config facade for all values - no hardcoding
4. **CHECK** if your changes actually show up (common frontend/backend mismatch)

## 🏗️ Architecture (Simple Version)

```
User Request → API Route → Service → Database/Engine → Response
                ↓            ↓          ↓
             (thin)    (business)   (queries)
                         (logic)     (no global state)
```

### Key Points:
- **No Global State** - Everything queries on-demand
- **Services** - All business logic in `app/services/`
- **Config** - Single source of truth in `config/schema.py`
- **Domain Models** - Use typed models in `app/domain/` (new!)

## 💰 Critical Business Logic

### 1. Payment Calculation (DO NOT CHANGE)
```python
# Mexican loans have IVA (16% tax) on interest only
monthly_payment = principal + interest + (interest * 0.16) + gps_fee + insurance

# GPS has two parts:
# - Installation: $750 + IVA = $870 (first month only)
# - Monthly: $350 + IVA = $406 (every month)
```

### 2. Offer Categories
- **Refresh**: -5% to +5% payment change (same payment)
- **Upgrade**: +5% to +25% payment change (bit more)
- **Max Upgrade**: +25% to +100% payment change (much more)

### 3. Interest Rates
- Based on risk profile (A1=21%, B2=25%, C3=30%, etc.)
- +1% for 60-month terms
- +1.5% for 72-month terms

## 🚨 Common Pitfalls & Fixes

### 1. IVA Calculation Error
```python
# ❌ WRONG (common bug)
gps_with_iva = GPS_FEE * IVA_RATE  # 350 * 0.16 = 56

# ✅ CORRECT
gps_with_iva = GPS_FEE * (1 + IVA_RATE)  # 350 * 1.16 = 406
```

### 2. Car ID Type Mismatch
```python
# ❌ WRONG - Causes 422 errors
car_id = 12345  # Integer

# ✅ CORRECT - Always string
car_id = "12345"
```

### 3. Frontend/Backend Mismatch
```python
# Common issue: Frontend expects different endpoint
# Backend: /api/generate-offers-basic
# Frontend might call: /api/generate-offers
# Always verify both sides match!
```

### 4. Config Not Applied
```javascript
// ❌ WRONG - Treats 0 as falsy
const kavakTotal = customConfig.kavak_total || 25000;  // 0 becomes 25000!

// ✅ CORRECT
const kavakTotal = customConfig.kavak_total !== undefined ? customConfig.kavak_total : 25000;
```

## 📁 Where Things Live

### Business Logic
- `app/services/offer_service.py` - Offer generation orchestration
- `app/services/customer_service.py` - Customer operations
- `engine/basic_matcher.py` - Core matching algorithm
- `engine/calculator.py` - Financial calculations

### Configuration
- `config/schema.py` - ALL default values (source of truth)
- `config/facade.py` - How to access config
- `config/engine_config.json` - Runtime overrides

### Data Access
- `data/database.py` - All data queries
- `data/cache_manager.py` - Caching logic
- **NO GLOBAL DATAFRAMES** - Always query fresh

### New Domain Models
- `app/domain/customer.py` - Customer type
- `app/domain/vehicle.py` - Vehicle type
- `app/domain/offer.py` - Offer type
- Use these instead of dictionaries!

## 🔧 Common Tasks

### Change a Fee/Rate
```python
# Use config facade
from config.facade import set

# Change GPS monthly fee
set("fees.gps.monthly", "400")  # Now $400 instead of $350

# Change interest rate for A1
set("rates.A1", "0.23")  # Now 23% instead of 21%
```

### Add a New Risk Profile
```python
# 1. Add rate to config
set("rates.NEW_PROFILE", "0.35")  # 35% interest

# 2. Update validation in app/utils/data_validator.py
# 3. Add to RiskProfile enum in app/domain/customer.py
```

### Debug Offer Generation
```python
# 1. Check customer exists
curl http://localhost:8000/api/customers/CUSTOMER_ID

# 2. Generate offers with debug
curl -X POST http://localhost:8000/api/generate-offers-basic \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "CUSTOMER_ID"}'

# 3. Check logs for "🔍", "✅", "❌" emojis
```

## 🧪 Testing Your Changes

### Quick Validation
```bash
# 1. Run the app
./run_local.sh

# 2. Test calculation
python -m pytest tests/unit/engine/test_calculator.py -v

# 3. Check a real customer
# Go to http://localhost:8000/customers
# Click any customer → Generate Offers
# Verify payment calculations make sense
```

### Verify Config Changes
```python
# See current config
from config.facade import get_all
print(get_all())

# Test your change
set("fees.service.percentage", "0.05")  # 5% instead of 4%
# Generate offer and verify service fee = car_price * 0.05
```

## 📊 Data Flow

1. **Customer Request** → Has current car loan, wants upgrade
2. **Get Inventory** → Query cars more expensive than current
3. **Pre-filter** → Database filters 4000+ cars → ~500 eligible
4. **Calculate Offers** → For each car, try all terms (12-72 months)
5. **Categorize** → Sort into Refresh/Upgrade/Max tiers
6. **Return Best** → Highest NPV offers per tier

## ⚠️ DO NOT CHANGE

### 1. Amortization Table Format
The `generate_amortization_table` in `calculator.py` matches Excel exactly:
- Capital = Principal + GPS installation (month 1)
- Interest = Interest amount only
- IVA = Tax on interest only
- Charges = GPS monthly only
- **VERIFIED** with accounting team - DO NOT MODIFY

### 2. Payment Calculation Formula
The audited payment calculation in `payment_utils.py`:
- Uses specific amortization method
- Validated by risk team
- Changes require executive approval

## 🐛 Debugging Tips

### Check Logs
```bash
# Look for these emojis in logs:
🚀 - Server start
🔍 - Search/calculation start  
✅ - Success
❌ - Error
💰 - Financial calculation
⚡ - Performance metric
```

### Common Errors
- **422 Unprocessable Entity** - Check data types (especially car_id)
- **404 Customer not found** - Customer ID doesn't exist
- **500 Internal Error** - Check logs for actual error
- **NaN in calculations** - Division by zero or missing data

### Performance Issues
- First request slow? - Cache warming up
- All requests slow? - Check database connection
- Memory growing? - Check for dataframe leaks

## 🚀 Recent Major Changes

### 2025-06-27 (Today!)
1. **Fixed IVA bug** in smart_search.py
2. **Added comprehensive tests** - Run with `./run_tests.py`
3. **Consolidated config** - Use config/schema.py only
4. **Added domain models** - Replace dictionaries with types

### Architecture Improvements
- Removed global DataFrames
- Added service layer
- Two-stage filtering for performance
- Smart caching with TTL

## 💡 Pro Tips

1. **Use Domain Models**
```python
# Instead of dict
customer = Customer.from_dict(customer_data)
if customer.is_eligible_for_tradeup:
    # Type-safe, validated, clear
```

2. **Check Cache Status**
```bash
curl http://localhost:8000/api/cache/status
# Force refresh if needed
curl -X POST http://localhost:8000/api/cache/refresh
```

3. **Parallel Testing**
```python
# Test multiple scenarios quickly
./run_tests.py unit  # Just unit tests
./run_tests.py integration  # Just integration
./run_tests.py coverage  # With coverage report
```

## 🤝 Working with This Codebase

### For New Features
1. Check if similar feature exists
2. Add config values to schema.py first
3. Write tests BEFORE implementation
4. Use domain models, not dicts
5. Put logic in services, not routes

### For Bug Fixes
1. Write failing test that reproduces bug
2. Fix the bug
3. Verify test passes
4. Check for similar bugs elsewhere

### For Performance
1. Profile first - don't guess
2. Check cache hit rates
3. Look at SQL query counts
4. Use two-stage filtering pattern

---

**Remember**: This system handles real money for real customers. Test thoroughly, especially financial calculations. When in doubt, ask!