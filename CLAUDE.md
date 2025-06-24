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

```
app/
├── main.py              # FastAPI entry point
├── models.py            # Request/response models
├── api/                 # REST endpoints
├── routes/              # Web page routes
├── core/                # App initialization
└── utils/               # Utilities

engine/                  # Business logic
├── basic_matcher.py     # Main offer calculation
├── calculator.py        # NPV & amortization
└── payment_utils.py     # Payment calculations

config/                  # Configuration
└── config.py           # Business rules & rates

data/                   # Data management
└── loader.py          # Redshift/CSV loading
```

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

## 🔧 Common Development Tasks

### Change Interest Rates
```python
# Location: config/config.py
INTEREST_RATE_TABLE = {
    "A1": {"12": 0.1949, "24": 0.1949, ...},
    # Modify rates here
}
```

### Change Fee Structure
```python
# Location: config/config.py
DEFAULT_FEES = {
    'service_fee_pct': 0.04,  # 4% of car price
    'cxa_pct': 0.04,          # 4% marketing fee
    # Modify fees here
}
```

### Change Payment Tiers
```python
# Location: config/config.py
PAYMENT_DELTA_TIERS = {
    'refresh': (-0.05, 0.05),     # ±5%
    'upgrade': (0.05, 0.25),      # +5% to +25%
    'max_upgrade': (0.25, 1.0),   # +25% to +100%
}
```

### Add New Risk Profile
1. Add to `INTEREST_RATE_TABLE` in `config/config.py`
2. Add to `RISK_PROFILE_INDICES` mapping
3. Update down payment table if needed

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

- Offer generation uses parallel processing (14 threads)
- Each customer × inventory combination is evaluated
- Cache is currently disabled (always recalculates)
- Typical response time: 1-2 seconds for ~4000 cars

## 🔐 Security Notes

- Never commit Redshift credentials
- Use `.env` file for local development
- All financial calculations happen server-side
- No sensitive data in frontend JavaScript

## 📞 Getting Help

- Main business logic: `engine/basic_matcher.py`
- Payment calculations: `engine/payment_utils.py`
- Configuration: `config/config.py`
- API endpoints: `app/api/offers.py`

When in doubt, search for the business term (e.g., "service_fee", "npv", "payment") to find where it's implemented.

## 🔄 Recent Fixes (Dec 2024)

1. **Amortization columns now add up correctly**
   - Fixed by calculating display interest from same values used in payment
   - File: `engine/calculator.py` lines 125-135

2. **Custom config values now work**
   - Fixed Kavak Total being ignored: `engine/basic_matcher.py` line 146
   - Fixed GPS fees being ignored: `engine/basic_matcher.py` lines 152-155
   - Fixed display showing $25k when OFF: `modern_customer_detail_enhanced.html` line 1213

3. **Frontend/Backend sync**
   - Fixed non-existent endpoints: `main.js` 
   - Fixed request parameter mismatches
   - Disabled broken features with user feedback

## ✅ Verification Script

ALWAYS run this after making changes:
```bash
python VERIFY_EVERYTHING.py
```

This verifies:
- Kavak Total toggle works
- Amortization columns add up
- Custom fees are applied
- CAC bonus affects equity