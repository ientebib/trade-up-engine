# Dashboard Fix Instructions for Senior Developer

## Current Status
- ✅ Offer generation is working (generates 2578 offers from 1000 cars)
- ✅ Customer details page is functional
- ✅ Inventory page is working
- ❌ Dashboard page shows KeyError: 'sales_price'

## The Problem

### Error Details
```
KeyError: 'sales_price'
Location: Dashboard route (/) after get_dashboard_stats() is called
Request ID: 38a7d19a-c5a9-47a3-be95-498e000886d0
```

### Root Cause Analysis
1. The data loader (data/loader.py:259) correctly renames 'sales_price' to 'car_price':
   ```python
   inventory_df = inventory_df.rename(columns={"sales_price": "car_price"})
   ```

2. Other pages (inventory, customer details) work fine with 'car_price'

3. Dashboard still tries to access 'sales_price' somewhere in the data pipeline

## Where to Look

### 1. Check get_dashboard_stats() in customer_service.py
The error happens after this method is called. Look for any direct DataFrame access using 'sales_price'.

### 2. Check get_inventory_stats() in database.py
Dashboard stats likely aggregate inventory data. This method might be accessing 'sales_price' directly.

### 3. Search for 'sales_price' references
```bash
# Find all occurrences
grep -r "sales_price" --include="*.py" .
grep -r "sales_price" --include="*.html" app/templates/
```

### 4. Check load_all_data() method
The comprehensive data loading in data/loader.py might create inconsistent data structures where some code paths have 'sales_price' and others have 'car_price'.

## Quick Fix Options

### Option 1: Add Backward Compatibility (Temporary)
In `data/loader.py` after line 259, add:
```python
# Keep sales_price as alias for backward compatibility
inventory_df["sales_price"] = inventory_df["car_price"]
```

### Option 2: Fix the Root Cause
Find where 'sales_price' is being accessed and change it to 'car_price'.

### Option 3: Add Error Handling
In the dashboard route, wrap the stats calculation with better error handling to identify the exact line:
```python
try:
    stats = customer_service.get_dashboard_stats()
except KeyError as e:
    logger.error(f"KeyError in dashboard stats: {e}")
    logger.error(f"Available columns: {inventory_df.columns.tolist()}")
    raise
```

## Debugging Steps

1. **Enable detailed logging** in app/routes/pages.py (already added):
   ```python
   import traceback
   logger.error(f"Full traceback: {traceback.format_exc()}")
   ```

2. **Check the actual data** being loaded:
   ```python
   # In get_dashboard_stats or get_inventory_stats
   logger.info(f"Inventory columns: {inventory_df.columns.tolist()}")
   ```

3. **Test the fix**:
   ```bash
   # Restart server
   ./run_local.sh
   
   # Open dashboard
   curl http://localhost:8000/
   ```

## Most Likely Culprits

Based on the error pattern:
1. `get_inventory_stats()` calculating average price using 'sales_price'
2. Any aggregation functions in dashboard stats
3. Template trying to access car.sales_price (though template errors show differently)

## Files Already Fixed
- ✅ app/templates/modern_inventory.html (changed to car_price)
- ✅ engine/basic_matcher.py (added customer_id to offers)
- ✅ data/loader.py (added name and risk_profile fields)
- ✅ data/transaction_manager.py (fixed commit/rollback)

## Contact Info
If you need the original error logs, check:
- `dashboard_debug.log` - Shows the KeyError happening
- `server_fresh.log` - Shows successful offer generation

The issue is definitely in the backend Python code, not the templates, since the error occurs before template rendering.