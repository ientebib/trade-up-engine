# Configuration Migration Guide

## Overview

We have consolidated all configuration values into a single source of truth: `config/schema.py`. This eliminates duplication and confusion about which values to use.

## Migration Summary

### Old Way (Multiple Sources)
```python
# From app/constants.py
from app.constants import DEFAULT_SERVICE_FEE_PCT, REFRESH_TIER_MIN

# From config/config.py  
from config.config import IVA_RATE, GPS_MONTHLY_FEE, DEFAULT_FEES

# Direct access to hardcoded values
service_fee = 0.04  # Was this 0.03 or 0.04?
```

### New Way (Single Source)
```python
# All configuration through the facade
from config.facade import get, get_decimal

# Access any configuration value
service_fee = get_decimal('fees.service.percentage')
refresh_min = get_decimal('tiers.refresh.min')
iva_rate = get_decimal('financial.iva_rate')
```

## What Changed

### 1. `app/constants.py`
- Financial constants now loaded from config system
- Backward compatibility maintained through dynamic loading
- Non-financial constants (validation limits, etc.) remain

### 2. `config/config.py`
- Now loads values from centralized config
- Provides backward compatibility layer
- Will be deprecated in future versions

### 3. `config/schema.py`
- **Single source of truth** for all business configuration
- Type-safe with Pydantic validation
- Default values defined in one place

## Configuration Paths

### Financial Configuration
```python
# Fees
get_decimal('fees.service.percentage')     # Service fee (default: 0.04)
get_decimal('fees.cxa.percentage')         # CXA fee (default: 0.04)
get_decimal('fees.gps.monthly')            # GPS monthly (default: 350)
get_decimal('fees.gps.installation')       # GPS install (default: 750)
get_decimal('fees.kavak_total.amount')     # Kavak Total (default: 25000)
get_decimal('fees.insurance.amount')       # Insurance (default: 10999)

# CAC Bonus
get_decimal('fees.cac_bonus.min')          # Min bonus (default: 0)
get_decimal('fees.cac_bonus.max')          # Max bonus (default: 5000)
get_decimal('fees.cac_bonus.default')      # Default (default: 0)

# IVA
get_decimal('financial.iva_rate')          # IVA rate (default: 0.16)
```

### Payment Tiers
```python
# Refresh Tier
get_decimal('tiers.refresh.min')           # -0.05
get_decimal('tiers.refresh.max')           # 0.05

# Upgrade Tier  
get_decimal('tiers.upgrade.min')           # 0.05
get_decimal('tiers.upgrade.max')           # 0.25

# Max Upgrade Tier
get_decimal('tiers.max_upgrade.min')       # 0.25
get_decimal('tiers.max_upgrade.max')       # 1.0
```

### Interest Rates
```python
# By risk profile
get('rates.A1')                            # "0.1949"
get('rates.B2')                            # "0.2349"
get('rates.C3')                            # "0.2749"

# Term adjustments
get_decimal('terms.rate_adjustment_60')    # 0.01
get_decimal('terms.rate_adjustment_72')    # 0.015
```

### Database & Cache
```python
# Connection Pool
get('database.pool.min_connections')       # 2
get('database.pool.max_connections')       # 10
get('database.pool.connection_timeout')    # 30

# Cache TTL
get('cache.default_ttl_hours')            # 4.0
get('cache.inventory_ttl_hours')          # 4.0
```

## Migration Steps

### For New Code
Always use the config facade:
```python
from config.facade import get, get_decimal

# Good
service_fee = get_decimal('fees.service.percentage')

# Bad - Don't hardcode
service_fee = 0.04
```

### For Existing Code
1. Replace imports gradually:
```python
# Old
from app.constants import DEFAULT_SERVICE_FEE_PCT
fee = DEFAULT_SERVICE_FEE_PCT

# New  
from config.facade import get_decimal
fee = get_decimal('fees.service.percentage')
```

2. Use backward compatibility during transition:
```python
# app/constants.py still works but now loads from config
from app.constants import DEFAULT_SERVICE_FEE_PCT  # Still works
```

## Testing Configuration

### In Unit Tests
```python
from unittest.mock import patch

# Mock specific config values
with patch('config.facade.get_decimal') as mock_get:
    mock_get.side_effect = lambda key, default=None: {
        'fees.service.percentage': 0.05,  # Test with 5%
        'fees.cxa.percentage': 0.03       # Test with 3%
    }.get(key, default)
    
    # Your test code here
```

### In Integration Tests
```python
# Temporarily override config
from config.facade import set

# Override for test
set('fees.service.percentage', '0.05')

# Run test
result = generate_offer(...)

# Config auto-resets after test (if using pytest fixture)
```

## Benefits

1. **Single Source of Truth**: No more confusion about which value is correct
2. **Type Safety**: Pydantic validation ensures correct types
3. **Runtime Updates**: Change config without restarting
4. **Better Testing**: Easy to mock/override for tests
5. **Audit Trail**: All config changes can be logged

## Future Deprecations

The following will be deprecated in v3.0:
- Direct imports from `config.config` (use facade instead)
- Hardcoded values in `app/constants.py` (financial constants)
- `DEFAULT_FEES` dictionary (use individual config values)

## Common Pitfalls

1. **Don't Mix Sources**
```python
# Bad - mixing sources
from app.constants import DEFAULT_SERVICE_FEE_PCT
from config.facade import get_decimal
fee1 = DEFAULT_SERVICE_FEE_PCT
fee2 = get_decimal('fees.service.percentage')
# These might have different values!
```

2. **Use Correct Types**
```python
# get() returns strings
rate_str = get('rates.A1')  # "0.1949"

# get_decimal() returns Decimal
rate_dec = get_decimal('rates.A1')  # Decimal('0.1949')
```

3. **Check Key Paths**
```python
# Wrong path
get('service_fee')  # ❌ No such key

# Correct path  
get('fees.service.percentage')  # ✓
```

## Questions?

- Check `config/schema.py` for all available configuration keys
- Use `config.facade.get_all()` to see current configuration
- Run validation with `config.facade.validate()`