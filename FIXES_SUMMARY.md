# Summary of Frontend/Backend Fixes

## Core Calculation Logic
**NOT CHANGED** - Per user request, the validated calculation logic remains untouched

## Fixed API Mismatches

### 1. main.js fixes:
- Line 112: Customer limit 5000 → 100 (backend max)
- Line 154: Removed inventory fetch (backend loads internally)
- Line 165: `/api/generate-offers` → `/api/generate-offers-basic`
- Line 160: Fixed request payload to send only `customer_id` and `max_offers`
- Line 500: Disabled `/api/scenario-summary` call (endpoint doesn't exist)
- Line 639: Disabled `/api/scenario-analysis` call (endpoint doesn't exist)
- Line 734: `/api/config-status` → `/api/config` (using existing endpoint)

### 2. Backend fixes:
- app/api/offers.py:138-139: Now converts `kavak_total_enabled` boolean to amount
- engine/basic_matcher.py:146: Now uses custom `kavak_total_amount` from config
- engine/basic_matcher.py:152-155: Now uses custom GPS fees from config

## Remaining Known Issues

### 1. Amortization Table Display
- The columns don't add up because payment includes interest WITH IVA
- Display shows interest and IVA separately
- Located in modern_customer_detail_enhanced.html lines 1168-1197
- **NOT FIXED** per user request to preserve calculations

### 2. Templates in modern_dashboard.html
- Still references non-existent endpoints
- Need to update or remove scenario functionality

### 3. manual_simulation.html
- Still calls `/api/manual-simulation` which returns 501
- Either implement endpoint or remove feature

## Validation Steps

To verify all fixes work:
1. Load customer list page - should load without errors
2. Generate offers for a customer - should work with basic API
3. Use custom config - Kavak Total toggle should affect calculations
4. View amortization table - should display (columns won't add up per known issue)
5. Save configuration - should work without errors