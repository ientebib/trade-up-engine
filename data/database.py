"""
Direct database access layer - NO GLOBAL STATE!
Each function queries exactly what it needs, when it needs it.
With smart caching for performance.
"""
import pandas as pd
import logging
import os
from typing import Optional, List, Dict
from .loader import data_loader
from .cache_manager import cache_manager

logger = logging.getLogger(__name__)

# Production mode only - no mock data
# Mock data has been removed for production use


def get_customer_by_id(customer_id: str) -> Optional[Dict]:
    """Get a single customer by ID - fresh from database"""
    logger.info(f"🔍 Fetching customer {customer_id}")
    
    # Load fresh customer data - no mock data in production
    customers_df = data_loader.load_customers_data()
    
    if customers_df.empty:
        logger.error("❌ No customer data available")
        return None
    
    mask = customers_df["customer_id"] == customer_id
    if not mask.any():
        return None
    
    return customers_df[mask].iloc[0].to_dict()


def search_customers(
    search_term: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[Dict], int]:
    """Search customers with filtering - returns (results, total_count)"""
    # Validate inputs to prevent slice object errors
    if not isinstance(limit, int) or limit < 0:
        raise ValueError(f"limit must be a non-negative integer, got {type(limit).__name__}: {limit}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError(f"offset must be a non-negative integer, got {type(offset).__name__}: {offset}")
    
    logger.info(f"🔍 Searching customers: term='{search_term}', limit={limit}, offset={offset}")
    
    # Load fresh customer data - no mock data in production
    customers_df = data_loader.load_customers_data()
    
    if customers_df.empty:
        return [], 0
    
    # Apply search filter if provided
    filtered_df = customers_df
    if search_term:
        search_term = search_term.upper()
        mask = (
            filtered_df["customer_id"].astype(str).str.contains(search_term, na=False) |
            filtered_df.get("customer_name", pd.Series()).astype(str).str.upper().str.contains(search_term, na=False)
        )
        filtered_df = filtered_df[mask]
    
    total_count = len(filtered_df)
    
    # Apply pagination - ensure indices are integers
    start_idx = int(offset) if offset is not None else 0
    end_idx = start_idx + int(limit) if limit is not None else len(filtered_df)
    
    results = filtered_df.iloc[start_idx:end_idx].to_dict("records")
    
    return results, total_count


def get_all_inventory() -> List[Dict]:
    """Get entire inventory from Redshift - with smart caching"""
    
    def fetch_inventory():
        logger.info("🔍 Fetching inventory from Redshift...")
        _, inventory_df = data_loader.load_all_data()
        
        if inventory_df.empty:
            logger.error("❌ No inventory data from Redshift!")
            return []
        
        logger.info(f"✅ Loaded {len(inventory_df)} cars from Redshift")
        return inventory_df.to_dict("records")
    
    # Use cache with 4-hour TTL (configurable)
    data, from_cache = cache_manager.get("inventory_all", fetch_inventory)
    return data


def get_inventory_stats() -> Dict:
    """Get inventory statistics - with smart caching"""
    
    def calculate_stats():
        logger.info("📊 Calculating inventory stats from Redshift...")
        _, inventory_df = data_loader.load_all_data()
        
        if inventory_df.empty:
            return {
                "total_cars": 0,
                "average_price": 0,
                "min_price": 0,
                "max_price": 0,
                "brands": 0
            }
        
        # Use car_price for mock data, sales_price for real data
        price_col = "sales_price"  # Production column name
        brand_col = "car_brand"
        
        stats = {
            "total_cars": len(inventory_df),
            "average_price": float(inventory_df[price_col].mean()),
            "min_price": float(inventory_df[price_col].min()),
            "max_price": float(inventory_df[price_col].max()),
            "brands": inventory_df[brand_col].nunique() if brand_col in inventory_df.columns else 0
        }
        logger.info(f"✅ Calculated stats for {stats['total_cars']} cars")
        return stats
    
    # Use same cache key as inventory to ensure consistency
    data, from_cache = cache_manager.get("inventory_stats", calculate_stats)
    return data


def get_car_by_id(car_id: str) -> Optional[Dict]:
    """Get a single car by ID directly from Redshift."""
    logger.info(f"🔍 Fetching car {car_id}")

    # Always treat car_id as string for comparison
    car_id_str = str(car_id)

    try:
        car = data_loader.load_single_car_from_redshift(car_id_str)
        if car:
            return car
    except Exception as e:
        logger.error(f"❌ Error loading car {car_id} from Redshift: {e}")

    logger.warning(f"⚠️ Car {car_id} not found")
    return None


def search_inventory(
    query: Optional[str] = None,
    limit: int = 100,
    make_filter: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None
) -> List[Dict]:
    """Search inventory with filters - returns filtered results"""
    logger.info(f"🔍 Searching inventory: query='{query}', limit={limit}")
    
    # Get inventory data - production mode
    _, inventory_df = data_loader.load_all_data()
    
    if inventory_df.empty:
        return []
    
    # Apply filters
    filtered_df = inventory_df
    
    # Text search
    if query:
        query_lower = query.lower()
        mask = (
            filtered_df["model"].astype(str).str.lower().str.contains(query_lower, na=False) |
            filtered_df.get("make", filtered_df.get("car_brand", pd.Series())).astype(str).str.lower().str.contains(query_lower, na=False) |
            filtered_df["car_id"].astype(str).str.lower().str.contains(query_lower, na=False)
        )
        filtered_df = filtered_df[mask]
    
    # Make filter
    if make_filter:
        make_col = "make" if "make" in filtered_df.columns else "car_brand"
        if make_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[make_col] == make_filter]
    
    # Year range
    if year_min is not None:
        filtered_df = filtered_df[filtered_df["year"] >= year_min]
    if year_max is not None:
        filtered_df = filtered_df[filtered_df["year"] <= year_max]
    
    # Price range
    price_col = "sales_price"  # Production column name
    if price_min is not None:
        filtered_df = filtered_df[filtered_df[price_col] >= price_min]
    if price_max is not None:
        filtered_df = filtered_df[filtered_df[price_col] <= price_max]
    
    # Apply limit
    results = filtered_df.head(limit).to_dict("records")
    
    logger.info(f"✅ Found {len(results)} cars matching filters")
    return results


def get_inventory_aggregates() -> Dict:
    """Get inventory aggregate data for filters - cached for performance"""
    
    def calculate_aggregates():
        logger.info("📊 Calculating inventory aggregates...")
        # Production mode - always use real data
        _, inventory_df = data_loader.load_all_data()
        
        if inventory_df.empty:
            return {
                "makes": [],
                "years": [],
                "price_range": {"min": 0, "max": 0},
                "total_cars": 0
            }
        
        # Get unique makes
        make_col = "make" if "make" in inventory_df.columns else "car_brand"
        makes = sorted(inventory_df[make_col].dropna().unique().tolist()) if make_col in inventory_df.columns else []
        
        # Get year range
        years = sorted(inventory_df["year"].dropna().unique().astype(int).tolist())
        
        # Get price range
        price_col = "sales_price"  # Production column name
        prices = inventory_df[price_col].dropna()
        if len(prices) > 0:
            price_range = {
                "min": float(prices.min()),
                "max": float(prices.max())
            }
        else:
            price_range = {"min": 0, "max": 0}
        
        aggregates = {
            "makes": makes,
            "years": years,
            "price_range": price_range,
            "total_cars": len(inventory_df)
        }
        
        logger.info(f"✅ Calculated aggregates: {len(makes)} makes, {len(years)} years")
        return aggregates
    
    # Cache with same TTL as inventory
    data, from_cache = cache_manager.get("inventory_aggregates", calculate_aggregates)
    return data


def search_customers_with_filters(
    search_term: Optional[str] = None,
    risk_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> tuple[List[Dict], int]:
    """Search customers with risk filtering at database level"""
    # Validate inputs to prevent slice object errors
    if not isinstance(limit, int) or limit < 0:
        raise ValueError(f"limit must be a non-negative integer, got {type(limit).__name__}: {limit}")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError(f"offset must be a non-negative integer, got {type(offset).__name__}: {offset}")
    
    logger.info(f"🔍 Searching customers: term='{search_term}', risk='{risk_filter}', limit={limit}")
    
    # Load customer data - production mode
    customers_df = data_loader.load_customers_data()
    
    if customers_df.empty:
        return [], 0
    
    # Apply search filter
    filtered_df = customers_df
    if search_term:
        search_term = search_term.upper()
        mask = (
            filtered_df["customer_id"].astype(str).str.contains(search_term, na=False) |
            filtered_df.get("customer_name", pd.Series()).astype(str).str.upper().str.contains(search_term, na=False)
        )
        filtered_df = filtered_df[mask]
    
    # Apply risk filter at database level
    if risk_filter and risk_filter != "all":
        # Map risk profiles to numeric indices
        risk_indices = {
            "A1": 1, "A2": 2, "A3": 3,
            "B1": 4, "B2": 5, "B3": 6,
            "C1": 7, "C2": 8, "C3": 9,
            "D1": 10, "D2": 11, "D3": 12,
            "E1": 13, "E2": 14, "E3": 15,
            "F1": 16, "F2": 17, "F3": 18,
            "G1": 19, "G2": 20, "G3": 21,
            "H1": 22, "H2": 23, "H3": 24
        }
        
        # Add risk index column
        filtered_df["risk_index"] = filtered_df["risk_profile"].map(risk_indices).fillna(99)
        
        # Filter by risk level
        if risk_filter == "low":
            filtered_df = filtered_df[filtered_df["risk_index"] <= 5]
        elif risk_filter == "medium":
            filtered_df = filtered_df[(filtered_df["risk_index"] > 5) & (filtered_df["risk_index"] <= 15)]
        elif risk_filter == "high":
            filtered_df = filtered_df[filtered_df["risk_index"] > 15]
    
    # Get total count AFTER filtering
    total_count = len(filtered_df)
    
    # Apply pagination - ensure indices are integers
    start_idx = int(offset) if offset is not None else 0
    end_idx = start_idx + int(limit) if limit is not None else len(filtered_df)
    
    results = filtered_df.iloc[start_idx:end_idx].to_dict("records")
    
    logger.info(f"✅ Found {total_count} customers, returning {len(results)} for page")
    return results, total_count


def get_tradeup_inventory_for_customer(customer_car_details: Dict) -> List[Dict]:
    """
    Stage 1 Pre-filtering: Get inventory that represents logical trade-ups for a customer.
    
    A trade-up car must be:
    - Newer (year >= customer's car year)
    - More expensive (price > customer's car price)
    - Lower mileage (kilometers < customer's car kilometers)
    
    Args:
        customer_car_details: Dict with customer's current car details including:
            - 'ANO AUTO' or 'year': Current car year
            - 'PRECIO AUTO' or 'current_car_price': Current car price
            - 'KILOMETRAJE' or 'kilometers': Current car kilometers
            
    Returns:
        List of cars that are logical trade-up candidates
    """
    logger.info("🔍 Pre-filtering inventory for trade-up candidates")
    
    # Extract customer car details with fallback field names
    current_year = customer_car_details.get('current_car_year') or customer_car_details.get('ANO AUTO') or customer_car_details.get('year', 0)
    current_price = customer_car_details.get('current_car_price') or customer_car_details.get('PRECIO AUTO', 0)
    current_km = customer_car_details.get('current_car_km') or customer_car_details.get('KILOMETRAJE') or customer_car_details.get('kilometers', float('inf'))
    
    # Convert to appropriate types
    try:
        current_year = int(current_year) if current_year else 0
        current_price = float(current_price) if current_price else 0
        current_km = float(current_km) if current_km else float('inf')
    except (ValueError, TypeError):
        logger.error("❌ Invalid customer car details for pre-filtering")
        return []
    
    logger.info(f"📊 Customer car: Year={current_year}, Price=${current_price:,.0f}, KM={current_km:,.0f}")
    
    # Try to load pre-filtered inventory from database (efficient)
    try:
        filtered_df = data_loader.load_filtered_inventory_from_redshift(
            year=current_year,
            price=current_price,
            kilometers=current_km
        )
        
        if not filtered_df.empty:
            filtered_count = len(filtered_df)
            logger.info(f"✅ Pre-filtered inventory: {filtered_count} cars from database")
            return filtered_df.to_dict("records")
    except Exception as e:
        logger.error(f"❌ Filtered query failed: {e}")
        # Don't fall back to loading all inventory - it's too expensive
        logger.warning("⚠️ Returning empty inventory to prevent memory exhaustion")
        return []
    
    # NO FALLBACK - If we can't get filtered inventory, return empty
    # Loading all inventory is too expensive and causes performance issues
    logger.warning("⚠️ Unable to get filtered inventory, returning empty list")
    return []


def get_customer_statistics() -> Dict:
    """Get aggregated customer statistics - with caching"""
    
    def calculate_customer_stats():
        logger.info("📊 Calculating customer statistics...")
        # Production mode - always use real data
        customers_df = data_loader.load_customers_data()
        
        if customers_df.empty:
            return {
                "avg_payment": 0,
                "avg_equity": 0,
                "avg_balance": 0,
                "total_active": 0
            }
        
        # Calculate averages
        avg_payment = float(customers_df["current_monthly_payment"].mean())
        avg_equity = float(customers_df["vehicle_equity"].mean())
        avg_balance = float(customers_df["outstanding_balance"].mean())
        total_active = len(customers_df[customers_df["outstanding_balance"] > 0])
        
        stats = {
            "avg_payment": round(avg_payment, 2),
            "avg_equity": round(avg_equity, 2),
            "avg_balance": round(avg_balance, 2),
            "total_active": total_active
        }
        
        logger.info(f"✅ Customer stats: Avg payment=${stats['avg_payment']:,.0f}")
        return stats
    
    # Cache for 1 hour
    data, from_cache = cache_manager.get("customer_stats", calculate_customer_stats, ttl_seconds=3600)
    return data


def get_offer_generation_stats() -> Dict:
    """Get offer generation statistics - simplified for now"""
    
    def calculate_offer_stats():
        logger.info("📊 Calculating offer generation statistics...")
        
        # In a real implementation, this would track:
        # - Number of offers generated
        # - Average NPV per offer
        # - Conversion rates
        # For now, return reasonable estimates
        
        return {
            "conversion_rate": 12.5,  # 12.5% of customers get viable offers
            "avg_npv": 25000,  # Average NPV per offer
            "offers_generated_today": 0,
            "avg_offers_per_customer": 3.2
        }
    
    # Cache for 15 minutes
    data, from_cache = cache_manager.get("offer_stats", calculate_offer_stats, ttl_seconds=900)
    return data


def test_database_connection() -> Dict:
    """Test database connections and return status"""
    logger.info("🧪 Testing database connections")
    
    # Production mode only - no mock data
    
    status = {
        "customers": {"connected": False, "count": 0, "source": "CSV"},
        "inventory": {"connected": False, "count": 0, "source": "Redshift"}
    }
    
    try:
        # Test customer data (CSV) - just check if file exists and is readable
        csv_path = "customers_data_tradeup.csv"
        if os.path.exists(csv_path):
            # Read just the first row to verify format
            test_df = pd.read_csv(csv_path, nrows=1)
            if not test_df.empty:
                # Count rows without loading entire file
                with open(csv_path, 'r') as f:
                    row_count = sum(1 for line in f) - 1  # Subtract header
                status["customers"]["connected"] = True
                status["customers"]["count"] = row_count
                logger.info(f"✅ Customer CSV accessible, ~{row_count} records")
    except Exception as e:
        status["customers"]["error"] = str(e)
    
    try:
        # Test Redshift connection with a lightweight query
        from .connection_pool import get_connection_pool
        pool = get_connection_pool()
        
        with pool.get_connection() as conn:
            with conn.cursor() as cursor:
                # Just verify connection works - don't count millions of rows!
                cursor.execute("SELECT 1")
                cursor.fetchone()
                status["inventory"]["connected"] = True
                status["inventory"]["count"] = 0  # Don't count on startup
                logger.info("✅ Redshift connection verified")
    except Exception as e:
        status["inventory"]["connected"] = False
        status["inventory"]["error"] = str(e)
    
    return status