# Inventory Query Documentation

## Overview
The inventory data is loaded exclusively from Redshift using the query in `inventory_query.sql`. There is no CSV fallback - if Redshift is unavailable, the system will not have inventory data.

## Query Details

### Source Tables
- `serving.inventory_history` - Main inventory data
- `dwh.dim_car_stock` - Car details (brand, model, year, version, color)
- `playground.dl_region_growth_playground` - Regional growth data

### Filters Applied
1. **Status**: Only `available` and `preloaded` vehicles
2. **Country**: Mexico only (`country_iso = 'MX'`)
3. **Published**: Only published inventory (`flag_published = TRUE`)
4. **Region**: Must have valid region (excludes São Paulo)
5. **Recency**: Only inventory from last 90 days
6. **Deduplication**: Latest record per stock_id

### Fields Retrieved
- `stock_id` - Unique vehicle identifier
- `kilometers` - Vehicle mileage
- `regular_published_price_financing` - Standard financing price
- `promotion_published_price_financing` - Promotional price (if any)
- `region_name` - Vehicle location
- `car_brand`, `model`, `year`, `version`, `color` - Vehicle details
- `region_growth`, `hub_name` - Regional metrics
- `has_promotion_discount` - Boolean flag for promotions
- `price_difference_abs` - Discount amount

## Data Transformation

After loading from Redshift, the data undergoes transformation:

1. **Model Name Cleaning**: Combines brand, model, year, and version into a clean display name
2. **Price Selection**: Uses promotional price if available and lower than regular price
3. **Column Mapping**: Maps Redshift columns to expected format:
   - `stock_id` → `car_id` (as string)
   - Selected price → `sales_price`
   - `full_model` → `model`

## Requirements

### Environment Variables
- `REDSHIFT_HOST`
- `REDSHIFT_DATABASE`
- `REDSHIFT_USER`
- `REDSHIFT_PASSWORD`
- `REDSHIFT_PORT` (default: 5439)

### Connection
- Uses `redshift-connector` Python library
- Timeout: 10 seconds (configurable via `DATA_LOADER_TIMEOUT`)
- Retry logic: 3 attempts with exponential backoff

## Error Handling
If Redshift connection fails:
- Logs detailed error with traceback
- Returns empty DataFrame
- **No CSV fallback** - system operates without inventory

## Usage
```python
from data.loader import data_loader

# Load inventory (always from Redshift)
inventory_df = data_loader.load_inventory()

if inventory_df.empty:
    logger.error("No inventory available - check Redshift connection")
```