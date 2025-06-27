# API Response Audit Report

## Summary
This audit identifies all mismatches between backend API responses and frontend expectations in the Trade-Up Engine application.

## Critical Findings

### 1. `/api/generate-offers-basic` and `/api/generate-offers-custom`

#### Backend Returns (offer_service.py):
```python
{
    "offers": {
        "refresh": [...],      # lowercase keys
        "upgrade": [...],      
        "max_upgrade": [...]   # underscore format
    },
    "total_offers": int,
    "cars_tested": int,
    "processing_time": float,
    "fees_used": {...},
    "message": str,
    "customer": {...}
}
```

#### Backend Internally Uses (basic_matcher.py):
```python
{
    "offers": {
        "Refresh": [...],      # Title case!
        "Upgrade": [...],      
        "Max Upgrade": [...]   # Space, not underscore!
    }
}
```

#### Frontend Expects (modern_customer_detail_enhanced.html):
```javascript
// Expects lowercase with underscores:
data.offers.refresh
data.offers.upgrade  
data.offers.max_upgrade
```

**STATUS**: ✅ FIXED - The service layer correctly maps from backend title case to frontend lowercase

### 2. `/api/amortization` and `/api/amortization-table`

#### Backend Returns (offer_service.py):
```python
{
    "schedule": [...],      # List of amortization rows
    "table": [...],         # Duplicate of schedule for compatibility
    "payment_total": float,
    "principal_month1": float,
    "interest_month1": float,
    "gps_fee": float,
    "cargos": float
}
```

#### Amortization Row Structure (calculator.py):
```python
{
    # Spanish column names for Excel compatibility
    "cuota": int,              # Payment number
    "saldo_insoluto": float,   # Beginning balance
    "capital": float,          # Principal (includes GPS install in month 1)
    "interes": float,          # Interest without IVA
    "cargos": float,           # GPS fees WITHOUT IVA
    "iva": float,              # IVA on (interest + GPS)
    "exigible": float,         # Total payment
    
    # Legacy fields for backward compatibility
    "month": int,
    "beginning_balance": float,
    "payment": float,
    "principal": float,
    "interest": float,
    "ending_balance": float,
    "balance": float,
    // ... additional detail fields
}
```

#### Frontend Expects (modern_customer_detail_enhanced.html):
```javascript
// Expects 'table' field with Spanish column names:
data.table.map(r => {
    r.cuota         // Month number
    r.saldo_insoluto // Outstanding balance
    r.capital       // Principal
    r.interes       // Interest  
    r.cargos        // Charges
    r.iva           // Tax
    r.exigible      // Total payment
})
```

**STATUS**: ✅ COMPATIBLE - Backend provides Spanish field names as expected by frontend

### 3. `/api/customers` Search API

#### Backend Returns (customer_service.py):
```python
{
    "customers": [...],     # List of customer objects
    "total": int,          # Total count
    "page": int,           # Current page
    "pages": int,          # Total pages
    "has_next": bool,      # Has next page
    "has_prev": bool       # Has previous page
}
```

#### Frontend Expects (modern_dashboard.html):
```javascript
// Expects:
data.customers  // Array of customers
// Each customer should have:
customer.customer_id
customer.current_monthly_payment
customer.vehicle_equity
// etc.
```

**STATUS**: ✅ COMPATIBLE - Structure matches

### 4. `/api/config` Configuration API

#### Backend Returns (config_service.py):
```python
{
    "fees": {
        "service_fee_pct": float,       # As decimal (0.04 for 4%)
        "cxa_pct": float,              # As decimal
        "cac_min": int,
        "cac_max": int,
        "cac_bonus": int,
        "kavak_total_enabled": bool,
        "kavak_total_amount": int,
        "gps_monthly": int,
        "gps_installation": int,
        "insurance_annual": int
    },
    "tiers": {
        "refresh": {"min": float, "max": float},      # As decimals
        "upgrade": {"min": float, "max": float},
        "max_upgrade": {"min": float, "max": float}
    },
    "business_rules": {
        "min_npv": int,
        "max_payment_increase": float,
        "available_terms": [int]
    }
}
```

#### Frontend Expects (modern_config.html):
```javascript
// GET /api/config expects:
config.fees.service_fee_pct    // As decimal, converts to % for display
config.fees.cxa_pct            // As decimal
config.fees.cac_min
config.fees.cac_max
// etc.

// Note: Frontend converts decimals to percentages for display:
// Display: (config.fees.service_fee_pct * 100).toFixed(1)
```

**STATUS**: ✅ COMPATIBLE - Frontend correctly handles decimal/percentage conversion

### 5. `/api/cache/status`

#### Backend Returns (cache_manager.py):
```python
{
    "enabled": bool,
    "default_ttl_hours": float,
    "entries": [
        {
            "key": str,
            "age": str,        # e.g., "2h 15m"
            "hits": int
        }
    ],
    "stats": {
        "hits": int,
        "misses": int,
        "hit_rate": float,     # 0-100
        "force_refreshes": int,
        "total_requests": int
    },
    "last_refresh": {...}
}
```

#### Frontend Expects (modern_dashboard.html):
```javascript
// Expects:
data.entries  // Array with .key and .age
data.stats.hit_rate  // Percentage
data.enabled  // Boolean
data.default_ttl_hours  // Number
```

**STATUS**: ✅ COMPATIBLE - Structure matches

## Other Potential Issues Found

### 1. Offer Object Field Names
Within offer objects, ensure consistency:
- `payment_delta` vs `payment_change`
- `car_id` vs `carId` 
- `new_car_price` vs `newCarPrice`
- `monthly_payment` vs `monthlyPayment`

### 2. Data Type Mismatches
- Car IDs: Backend treats as strings, ensure frontend does too
- Monetary values: Backend uses floats, frontend expects numbers (not strings)
- Percentages: Some as decimals (0.04), some as percentages (4)

### 3. Missing Error Handling
Frontend doesn't always handle these backend error responses:
- 404 Customer not found
- 503 Service unavailable
- 422 Validation errors

## Recommendations

1. **Standardize Field Naming**: Use consistent snake_case throughout
2. **Document API Contracts**: Create OpenAPI/Swagger documentation
3. **Add Response Validation**: Validate responses match expected schema
4. **Improve Error Messages**: Make backend errors more user-friendly
5. **Version APIs**: Add versioning to prevent breaking changes

### 6. `/api/save-config` Configuration Save

#### Frontend Sends (modern_config.html):
```javascript
{
    "fees": {
        "service_fee_pct": float,      // Converted from % to decimal
        "cxa_pct": float,              // Converted from % to decimal
        "cac_min": float,
        "cac_max": float
    },
    "payment_delta_tiers": {           // Note: different key name!
        "refresh": {
            "min": float,              // Converted from % to decimal
            "max": float
        },
        // etc.
    },
    "business_rules": {
        "min_npv": float,
        "available_terms": [int],
        "kavak_total_enabled": bool,
        "kavak_total_amount": float
    }
}
```

#### Backend Expects (config_service.py):
The backend's `_flatten_config` method expects a structure with `tiers` not `payment_delta_tiers`.

**STATUS**: ⚠️ MISMATCH - Frontend sends `payment_delta_tiers` but backend expects `tiers`

## Fixed Issues
1. ✅ "Refresh" vs "refresh" tier naming - Service layer now maps correctly
2. ✅ `kavak_total_enabled` boolean vs `kavak_total_amount` number
3. ✅ Amortization display using correct template file

## Files Requiring Attention
1. `/app/services/offer_service.py` - Ensure amortization Spanish field names
2. `/app/templates/modern_customer_detail_enhanced.html` - Add error handling
3. `/engine/calculator.py` - Verify amortization field names match frontend