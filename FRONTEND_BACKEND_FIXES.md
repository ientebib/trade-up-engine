# Frontend/Backend Fixes - Complete List

## COMPLETED FIXES

### 1. Customer List API Limit
- **File**: app/static/js/main.js line 112
- **Issue**: Frontend requested 5000 limit, backend max is 100
- **Fixed**: Changed to `/api/customers?limit=100`

### 2. Generate Offers Endpoint
- **File**: app/static/js/main.js line 165
- **Issue**: Frontend called non-existent `/api/generate-offers`
- **Fixed**: Changed to `/api/generate-offers-basic`
- **Also Fixed**: Request payload now sends only `customer_id` and `max_offers`

### 3. Custom Config Kavak Total
- **File**: app/api/offers.py lines 138-139
- **Issue**: Frontend sends `kavak_total_enabled` boolean, backend expected `kavak_total_amount` number
- **Fixed**: Backend now converts boolean to amount (25000 if enabled, 0 if disabled)

### 4. BasicMatcher Custom Config
- **File**: engine/basic_matcher.py
- **Issue**: Custom config values were ignored
- **Fixed**: 
  - Line 146: Now uses custom `kavak_total_amount`
  - Lines 152-155: Now uses custom GPS fees

## REMAINING ISSUES TO FIX

### 1. Non-existent Endpoints Still Called
These need to be removed or backend implementations added:
- `/api/inventory` - main.js line 150
- `/api/scenario-summary` - main.js line 500, modern_dashboard.html line 295
- `/api/scenario-analysis` - main.js line 637, modern_dashboard.html line 389
- `/api/config-status` - main.js line 735
- `/api/manual-simulation` - manual_simulation.html line 475 (endpoint returns 501)

### 2. Amortization Display Mismatch
- **Issue**: Columns don't add up because payment uses interest WITH IVA but display shows them separately
- **Location**: modern_customer_detail_enhanced.html lines 1168-1197
- **NOT FIXED**: Keeping calculation as-is per user request

### 3. Unused Backend Endpoints
These exist but have no frontend:
- `/api/generate-offers-bulk`
- `/api/search`
- `/api/smart-search`
- `/api/inventory/filters`
- `/api/metrics`

## VALIDATION CHECKLIST

- [ ] All frontend API calls match backend endpoints
- [ ] All request parameters match expected types
- [ ] All response structures are handled correctly
- [ ] No 404 or 500 errors from mismatched APIs
- [ ] Custom configuration values are actually used