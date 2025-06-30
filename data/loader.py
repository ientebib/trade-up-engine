"""
Data Loader Module for Kavak Trade-Up Engine
Handles loading data from Redshift and CSV files with proper transformations
"""

import pandas as pd
import os
from dotenv import load_dotenv
import redshift_connector
import logging
import random
import time
from tenacity import retry, wait_exponential, stop_after_attempt
from app.utils.logging import setup_logging
from .connection_pool import get_connection_pool
from app.utils.validation import UnifiedValidator as DataValidator, DataIntegrityError
from data.cache_manager import cache_manager
RISK_PROFILE_MAPPING = {
    'AAA': 0, 'AA': 1, 'A': 2, 'A1': 3, 'A2': 4,
    'B': 5, 'C1': 6, 'C2': 7, 'C3': 8,
    'D1': 9, 'D2': 10, 'D3': 11,
    'E1': 12, 'E2': 13, 'E3': 14, 'E4': 15, 'E5': 16,
    'F1': 17, 'F2': 18, 'F3': 19, 'F4': 20,
    'B_SB': 21, 'C1_SB': 22, 'C2_SB': 23, 'E5_SB': 24, 'Z': 25
}

# Load environment variables
load_dotenv()

# Set up logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """
    Centralized data loading and transformation service for the Trade-Up Engine.
    
    The DataLoader handles all data ingestion from external sources (Redshift, CSV),
    performing necessary transformations, validations, and enrichments to provide
    clean, consistent data to the application.
    
    Key Features:
        - Redshift inventory loading with connection pooling
        - CSV customer data processing with Spanish->English mapping
        - Data validation and integrity checking
        - Cross-reference enrichment between datasets
        - Retry logic and error handling
        - Comprehensive logging and monitoring
    
    Data Sources:
        - Inventory: Redshift database (live vehicle data)
        - Customers: CSV files (customer loan and vehicle data)
    
    Performance Considerations:
        - Uses connection pooling for Redshift
        - Implements retry logic with exponential backoff
        - Handles large datasets efficiently with pandas
        - Provides both full and filtered loading options
    """
    
    def __init__(self):
        """
        Initialize data loader with database connection parameters.
        
        Sets up Redshift connection configuration and risk profile mappings.
        Connection credentials are loaded from environment variables for security.
        """
        # Don't store password in instance variable for security
        self._host = os.getenv("REDSHIFT_HOST")
        self._port = os.getenv("REDSHIFT_PORT", 5439)
        self._database = os.getenv("REDSHIFT_DATABASE")  # Fixed: was REDSHIFT_DB
        self._user = os.getenv("REDSHIFT_USER")

        # Use shared risk profile mapping for consistent customer categorization
        self.risk_profile_mapping = RISK_PROFILE_MAPPING
        
        logger.info(f"📊 DataLoader initialized with {len(self.risk_profile_mapping)} risk profiles")


    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3)
    )
    def load_inventory_from_redshift(self):
        """Load inventory data from Redshift using connection pool."""
        logger.info("🔌 Getting connection from pool...")

        try:
            # Always use the single canonical query file.
            with open("data/inventory_query.sql", "r") as file:
                query = file.read()
            logger.info("📊 Using main inventory query from data/inventory_query.sql")
        except FileNotFoundError:
            from app.utils.exceptions import DataLoadError
            logger.error("❌ inventory_query.sql file not found in data/ folder.")
            raise DataLoadError(
                source="inventory_query.sql",
                reason="Query file not found in data/ folder"
            )

        # Chaos testing mode (only runs in non-production environments)
        if os.getenv("ENV") != "production":
            chaos = os.getenv("CHAOS_MODE")
            if chaos:
                if chaos == "network" and random.random() < 0.3:
                    logger.warning("💥 Chaos mode: simulating network drop")
                    raise redshift_connector.OperationalError("Simulated network error")
                if chaos == "stall" and random.random() < 0.3:
                    delay = random.uniform(2, 5)
                    logger.warning(f"💥 Chaos mode: stalling for {delay:.1f}s")
                    time.sleep(delay)

        def _fetch_inventory():
            pool = get_connection_pool()
            with pool.get_connection() as conn:
                logger.info("✅ Got connection from pool")
                
                logger.info("🔍 Executing Redshift query to load inventory...")
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    df = cursor.fetch_dataframe()

            return self.transform_inventory_data(df)

        # Use cache manager to avoid repeating heavy query within TTL
        inventory_df, from_cache = cache_manager.get("inventory_df", _fetch_inventory)
        if not from_cache:
            logger.info(f"✅ Loaded {len(inventory_df)} inventory items from Redshift and cached the result")
        else:
            logger.info(f"✅ Reused cached inventory ({len(inventory_df)} rows)")

        return inventory_df

    def transform_inventory_data(self, raw_df):
        """
        Transform raw Redshift inventory data to standardized application format.
        
        This method processes raw vehicle inventory data from Redshift, performing
        data cleaning, standardization, and validation to ensure consistency
        across the application.
        
        Args:
            raw_df (pd.DataFrame): Raw inventory data from Redshift containing:
                - stock_id: Unique vehicle identifier
                - car_brand: Vehicle manufacturer
                - model: Vehicle model name
                - year: Manufacturing year
                - version: Vehicle version/trim (optional)
                - regular_published_price_financing: Standard financing price
                - promotion_published_price_financing: Promotional price (if available)
                - region_name: Geographic region
                - kilometers: Vehicle mileage
                - color: Vehicle color
                - has_promotion_discount: Boolean promotion flag
                - price_difference_abs: Price difference from market
                - hub_name: Sales hub location
                - region_growth: Regional market growth indicator
        
        Returns:
            pd.DataFrame: Standardized inventory data with columns:
                - car_id: String identifier (consistent type)
                - model: Cleaned full model name (brand + model + year)
                - car_price: Final price (promotional if lower, else regular)
                - region: Geographic region
                - kilometers: Vehicle mileage
                - color: Vehicle color
                - has_promotion: Boolean promotion indicator
                - price_difference: Market price difference
                - hub_name: Sales hub
                - region_growth: Market growth metric
                - car_brand: Manufacturer name
                - make: Manufacturer alias for compatibility
                - brand: Manufacturer name (standardized)
                - year: Manufacturing year
                - model_short: Short model name
        
        Data Cleaning Operations:
            1. Clean model names by removing redundant brand information
            2. Build standardized full model names (Brand Model Year Version)
            3. Select optimal pricing (promotional vs regular)
            4. Validate and convert data types
            5. Remove invalid records (missing IDs, zero prices)
            6. Add required fields for backward compatibility
            7. Rename columns for consistency (sales_price -> car_price)
        
        Note:
            - Promotional prices are used only if lower than regular prices
            - Version information is cleaned and truncated for readability
            - All invalid or incomplete records are filtered out
            - Field aliases ensure compatibility with existing code
        """

        # Clean up model names - remove redundant info
        def clean_model_name(row):
            brand = row['car_brand']
            model = row['model']
            year = row['year']
            version = row.get('version', '')
            
            # Remove redundant info from model if it contains brand
            if pd.notna(model) and brand.lower() in model.lower():
                model = model.replace(brand, '').strip()
            
            # Build clean name
            parts = [brand, model, str(year)]
            
            # Only add version if it's meaningful and not too long
            if pd.notna(version) and version.strip():
                version_clean = version.strip()
                # Remove common redundant suffixes
                for suffix in ['CVT', 'MT', 'AT', '| 2.0L', '| 1.6L', '| 1.8L', ', Sedán', ', SUV', ', Hatchback']:
                    version_clean = version_clean.replace(suffix, '')
                version_clean = version_clean.strip(' ,|')
                
                if version_clean and len(version_clean) < 20:
                    parts.append(version_clean)
            
            return ' '.join(parts)
        
        raw_df["full_model"] = raw_df.apply(clean_model_name, axis=1)

        # Decide between regular and promotional price
        # Use promotional price if available and lower than regular price
        raw_df["final_price"] = raw_df.apply(
            lambda row: (
                row["promotion_published_price_financing"]
                if (
                    pd.notna(row["promotion_published_price_financing"])
                    and row["promotion_published_price_financing"]
                    < row["regular_published_price_financing"]
                )
                else row["regular_published_price_financing"]
            ),
            axis=1,
        )

        # Create the final inventory DataFrame
        inventory_df = pd.DataFrame(
            {
                "car_id": raw_df["stock_id"],
                "model": raw_df["full_model"],
                "sales_price": raw_df["final_price"],
                "region": raw_df["region_name"],
                "kilometers": raw_df["kilometers"],
                "color": raw_df["color"],
                "has_promotion": raw_df["has_promotion_discount"],
                "price_difference": raw_df["price_difference_abs"],
                "hub_name": raw_df["hub_name"],
                "region_growth": raw_df["region_growth"],
                "car_brand": raw_df["car_brand"],
                "make": raw_df["car_brand"],  # Alias for compatibility
                "year": raw_df["year"],
            }
        )

        # Ensure correct numeric types before any downstream filtering
        inventory_df["year"] = pd.to_numeric(inventory_df["year"], errors="coerce").fillna(0).astype(int)
        inventory_df["kilometers"] = pd.to_numeric(inventory_df["kilometers"], errors="coerce")

        # Clean up and validate
        inventory_df = inventory_df.dropna(subset=["car_id", "model", "sales_price"])
        inventory_df["sales_price"] = pd.to_numeric(
            inventory_df["sales_price"], errors="coerce"
        )
        inventory_df = inventory_df[inventory_df["sales_price"] > 0]
        
        # Rename sales_price to car_price for consistency
        inventory_df = inventory_df.rename(columns={"sales_price": "car_price"})
        
        # ------------------------------------------------------------------
        # Backward compatibility: Keep 'sales_price' as an alias to 'car_price'
        # Many legacy modules (e.g., smart_search, database stats) still
        # reference the old column name. Once those modules are refactored to
        # use 'car_price' directly, this alias can be removed.
        # ------------------------------------------------------------------
        inventory_df["sales_price"] = inventory_df["car_price"]
        
        # Add missing required fields
        inventory_df["brand"] = inventory_df["car_brand"]
        inventory_df["model_short"] = inventory_df["model"]
        
        # Validate the dataframe
        try:
            inventory_df = DataValidator.validate_dataframe(inventory_df, 'inventory')
            logger.info(f"✅ Validated inventory: {len(inventory_df)} cars")
        except DataIntegrityError as e:
            logger.error(f"❌ Inventory validation failed: {e}")
            raise

        return inventory_df

    def load_customers_from_csv(self, csv_path="data/customer_data.csv"):
        """Load and transform customer data from CSV (cached)."""

        def _read_and_transform() -> pd.DataFrame:
            """Inner helper that actually hits the disk — used by the cache."""
            try:
                # Check for enriched data file first
                enriched_csv = "data/customers_data_tradeup.csv"
                if os.path.exists(enriched_csv):
                    _path = enriched_csv
                    logger.info(f"📊 Loading ENRICHED customer data from {_path}...")
                elif os.path.exists("data/customer_data_tradeup.csv"):
                    _path = "data/customer_data_tradeup.csv"
                    logger.info(f"📊 Loading customer data from {_path}...")
                else:
                    _path = csv_path
                    logger.info(f"📊 Loading customer data from {_path}...")

                # Read with encoding to handle special characters
                df_local = pd.read_csv(_path, encoding="utf-8-sig")

                # Transform data to match expected structure
                customers_local = self.transform_customer_data(df_local)

                # Validate the dataframe once
                try:
                    customers_local = DataValidator.validate_dataframe(
                        customers_local, "customers"
                    )
                    logger.info(
                        f"✅ Validated customers: {len(customers_local)} records"
                    )
                except DataIntegrityError as e:
                    logger.error(f"❌ Customer data validation failed: {e}")
                    raise

                logger.info(
                    f"✅ Loaded {len(customers_local)} customers from CSV (disk read)"
                )
                return customers_local

            except Exception as e:
                from app.utils.exceptions import DataLoadError
                logger.error(f"❌ Failed to load customer data: {str(e)}")
                raise DataLoadError(
                    source="customers_data_tradeup.csv", reason=str(e)
                )

        # Retrieve from cache or read if missing/expired
        customers_df, from_cache = cache_manager.get("customers_df", _read_and_transform)

        if from_cache:
            logger.info(
                f"✅ Reused cached customers dataframe ({len(customers_df)} rows)"
            )

        return customers_df

    # ------------------------------------------------------------------
    # Public helper methods
    # ------------------------------------------------------------------

    def load_inventory(self, force_refresh=False):
        """Return inventory data - always from Redshift."""
        inv_df = self.load_inventory_from_redshift()
        
        if inv_df.empty:
            logger.error("❌ Failed to load inventory from Redshift.")
            logger.error("💡 Check your Redshift connection settings and ensure inventory_query.sql exists in data/ folder.")
        
        return inv_df

    def load_customers(self, csv_path="data/customer_data.csv", force_refresh=False):
        """Return customer data - always fresh from source."""
        customers_df = self.load_customers_from_csv(csv_path)
        return customers_df

    def _map_column_names(self, raw_df):
        """Map Spanish column names to English equivalents."""
        column_mapping = {
            # Contract and IDs
            "CONTRATO": "contract_id",
            "STOCK ID": "current_stock_id",
            
            # Personal info
            "NOMBRE": "first_name",
            "APELLIDO": "last_name", 
            "MAIL": "email",
            
            # Financial info
            "MONTO DE LA MENSUALIDAD": "current_monthly_payment",
            "SALDO INSOLUTO": "outstanding_balance",
            "PRECIO AUTO": "current_car_price",
            "TASA": "original_interest_rate",
            "MONTO A FINANCIAR": "original_loan_amount",
            
            # Contract details
            "FECHA DE CONTRATO": "contract_date",
            "PLAZO REMANENTE": "remaining_months",
            "TIENE KT": "has_kavak_total",
            
            # Car details
            "MARCA": "current_car_brand",
            "MODELO": "current_car_model_name",
            "ANO AUTO": "current_car_year",
            "KILOMETRAJE": "current_car_km",
            "AGING": "aging",
            
            # Risk profile
            "risk_profile": "risk_profile_name"
        }
        
        # Rename columns using the mapping
        for old_col, new_col in column_mapping.items():
            if old_col in raw_df.columns:
                raw_df[new_col] = raw_df[old_col]
        
        return raw_df

    def _process_risk_profiles(self, raw_df):
        """Map risk profile names to indices and handle unmapped profiles."""
        # Map risk profile names to indices
        raw_df["risk_profile_index"] = raw_df["risk_profile_name"].map(
            self.risk_profile_mapping
        )

        # Handle any unmapped risk profiles
        unmapped = raw_df[raw_df["risk_profile_index"].isna()]
        if len(unmapped) > 0:
            logger.warning(
                f"⚠️ Found {len(unmapped)} customers with unmapped risk profiles: {unmapped['risk_profile_name'].unique()}"
            )
            # Default unmapped profiles to highest risk index
            raw_df.loc[raw_df["risk_profile_index"].isna(), "risk_profile_index"] = 25
        
        return raw_df

    def _process_dates(self, raw_df):
        """Parse and process date fields with error handling."""
        # Parse contract date with explicit format to avoid warning
        # The CSV uses M/D/YY format
        try:
            raw_df["contract_date"] = pd.to_datetime(raw_df["contract_date"], format="%m/%d/%y", errors="coerce")
        except:
            # Fallback to automatic parsing if format doesn't match
            raw_df["contract_date"] = pd.to_datetime(raw_df["contract_date"], errors="coerce")
        
        return raw_df

    def _calculate_derived_fields(self, raw_df):
        """Calculate derived fields like equity and full model string."""
        # Use CONTRATO as the customer_id directly (it's already unique)
        raw_df["customer_id"] = raw_df["contract_id"]
        
        # Calculate vehicle equity (if not provided in data)
        if "vehicle_equity" not in raw_df.columns:
            # Simple calculation: current car price - outstanding balance
            raw_df["vehicle_equity"] = (
                pd.to_numeric(raw_df["current_car_price"], errors="coerce") - 
                pd.to_numeric(raw_df["outstanding_balance"], errors="coerce")
            )
        
        # Create full car model string
        raw_df["current_car_model"] = raw_df.apply(
            lambda row: f"{row.get('current_car_brand', '')} {row.get('current_car_model_name', '')} {row.get('current_car_year', '')}".strip(),
            axis=1
        )
        
        return raw_df

    def _clean_data_types(self, customers_df):
        """Convert columns to proper data types with error handling."""
        # Calculate derived fields
        customers_df["months_since_contract"] = (
            (pd.Timestamp.now() - customers_df["contract_date"]).dt.days / 30
        ).fillna(0).astype(int)
        
        # The aging field from CSV tells us how old the car was when purchased
        customers_df["car_age_at_purchase"] = pd.to_numeric(
            customers_df["aging"], errors="coerce"
        ).fillna(0).astype(int)
        
        return customers_df

    def _build_final_dataframe(self, raw_df):
        """Assemble the final dataframe with all required fields."""
        customers_df = pd.DataFrame({
            # IDs
            "customer_id": raw_df["customer_id"],
            "contract_id": raw_df["contract_id"],
            "current_stock_id": raw_df["current_stock_id"],
            
            # Personal info
            "first_name": raw_df["first_name"],
            "last_name": raw_df["last_name"],
            "full_name": raw_df["first_name"] + " " + raw_df["last_name"],
            "name": raw_df["first_name"] + " " + raw_df["last_name"],  # Add 'name' for validator
            "email": raw_df["email"],
            
            # Financial info
            "current_monthly_payment": pd.to_numeric(
                raw_df["current_monthly_payment"], errors="coerce"
            ),
            "vehicle_equity": pd.to_numeric(
                raw_df["vehicle_equity"], errors="coerce"
            ),
            "outstanding_balance": pd.to_numeric(
                raw_df["outstanding_balance"], errors="coerce"
            ),
            "current_car_price": pd.to_numeric(
                raw_df["current_car_price"], errors="coerce"
            ),
            "original_loan_amount": pd.to_numeric(
                raw_df["original_loan_amount"], errors="coerce"
            ),
            "original_interest_rate": pd.to_numeric(
                raw_df["original_interest_rate"], errors="coerce"
            ),
            
            # Contract details
            "contract_date": raw_df["contract_date"],
            "remaining_months": pd.to_numeric(
                raw_df["remaining_months"], errors="coerce"
            ).fillna(0).astype(int),
            "has_kavak_total": raw_df["has_kavak_total"].astype(bool),
            
            # Car details
            "current_car_brand": raw_df["current_car_brand"],
            "current_car_model_name": raw_df["current_car_model_name"],
            "current_car_year": pd.to_numeric(
                raw_df["current_car_year"], errors="coerce"
            ).fillna(0).astype(int),
            "current_car_km": pd.to_numeric(
                raw_df["current_car_km"], errors="coerce"
            ).fillna(0).astype(int),
            "current_car_model": raw_df["current_car_model"],
            "aging": raw_df["aging"],  # How old the car was when purchased
            
            # Risk profile
            "risk_profile_name": raw_df["risk_profile_name"],
            "risk_profile": raw_df["risk_profile_name"],  # Add 'risk_profile' for validator
            "risk_profile_index": raw_df["risk_profile_index"].astype(int),
        })
        
        return customers_df

    def _validate_and_filter(self, customers_df):
        """Validate data and filter out invalid records."""
        # Clean up and validate
        customers_df = customers_df.dropna(
            subset=[
                "customer_id",
                "current_monthly_payment", 
                "vehicle_equity",
                "current_car_price",
            ]
        )
        customers_df = customers_df[customers_df["current_monthly_payment"] > 0]
        customers_df = customers_df[customers_df["current_car_price"] > 0]
        
        return customers_df

    def transform_customer_data(self, raw_df):
        """
        Transform raw customer CSV data to standardized application format.
        
        This method processes customer data from CSV files, handling data type
        conversions, field mapping, validation, and enrichment to create a
        consistent customer dataset for the trade-up engine.
        
        Args:
            raw_df (pd.DataFrame): Raw customer data from CSV with Spanish column names:
                - CONTRATO: Contract ID (becomes customer_id)
                - NOMBRE/APELLIDO: Customer name components
                - MAIL: Email address
                - MONTO DE LA MENSUALIDAD: Current monthly payment
                - SALDO INSOLUTO: Outstanding loan balance
                - PRECIO AUTO: Current car price
                - TASA: Original interest rate
                - MONTO A FINANCIAR: Original loan amount
                - FECHA DE CONTRATO: Contract date
                - PLAZO REMANENTE: Remaining loan months
                - TIENE KT: Kavak Total flag
                - MARCA/MODELO/ANO AUTO: Current car details
                - KILOMETRAJE: Current car mileage
                - AGING: Car age at purchase
                - risk_profile: Risk profile code
        
        Returns:
            pd.DataFrame: Standardized customer data with columns:
                - customer_id: Unique identifier (from CONTRATO)
                - contract_id: Contract identifier
                - current_stock_id: Current vehicle stock ID
                - first_name/last_name/full_name: Name components
                - email: Contact email
                - current_monthly_payment: Current loan payment (numeric)
                - vehicle_equity: Calculated vehicle equity
                - outstanding_balance: Remaining loan balance
                - current_car_price: Current vehicle value
                - original_loan_amount: Initial loan amount
                - original_interest_rate: Original rate
                - contract_date: Parsed contract date
                - remaining_months: Months left on loan
                - has_kavak_total: Boolean Kavak Total flag
                - current_car_brand/model/year: Vehicle details
                - current_car_km: Vehicle mileage
                - current_car_model: Full model string
                - aging/car_age_at_purchase: Vehicle age metrics
                - risk_profile_name: Risk profile code
                - risk_profile_index: Numeric risk index
                - months_since_contract: Calculated contract age
        
        Data Processing Operations:
            1. Map Spanish column names to English equivalents
            2. Convert all numeric fields with error handling
            3. Parse dates with format detection
            4. Map risk profiles to numeric indices
            5. Calculate derived fields (equity, contract age, etc.)
            6. Validate data integrity and remove invalid records
            7. Build composite fields (full names, model strings)
        
        Business Logic:
            - Vehicle equity = current car price - outstanding balance
            - Unmapped risk profiles default to highest risk index (25)
            - Contract age calculated from current date
            - All financial fields validated for positive values
        
        Data Quality:
            - Removes customers with missing critical financial data
            - Validates positive car prices and monthly payments
            - Handles missing or malformed dates gracefully
            - Provides fallback values for optional fields
        """
        # Step 1: Map column names from Spanish to English
        raw_df = self._map_column_names(raw_df)
        
        # Step 2: Process risk profiles
        raw_df = self._process_risk_profiles(raw_df)
        
        # Step 3: Process dates
        raw_df = self._process_dates(raw_df)
        
        # Step 4: Calculate derived fields
        raw_df = self._calculate_derived_fields(raw_df)
        
        # Step 5: Build final dataframe
        customers_df = self._build_final_dataframe(raw_df)
        
        # Step 6: Clean data types
        customers_df = self._clean_data_types(customers_df)
        
        # Step 7: Validate and filter
        customers_df = self._validate_and_filter(customers_df)
        
        logger.info(f"📊 Transformed customer data with {len(customers_df.columns)} fields")

        return customers_df

    def enrich_customer_models(self, customers_df, inventory_df):
        """
        Enrich customer data with current car model names from inventory.
        
        This method cross-references customer current_stock_id values with
        the inventory database to provide accurate, up-to-date vehicle model
        names for display and analysis purposes.
        
        Args:
            customers_df (pd.DataFrame): Customer data with current_stock_id
            inventory_df (pd.DataFrame): Inventory data with car_id and model
        
        Returns:
            pd.DataFrame: Enhanced customer data with current_car_model field
        
        Process:
            1. Create lookup dictionary from inventory (car_id -> model)
            2. Map customer stock IDs to model names
            3. Fill missing models with "Unknown" placeholder
            4. Log enrichment statistics
        
        Note:
            - Non-matching stock IDs result in "Unknown" model names
            - Preserves all original customer data
            - Logs count of successfully enriched records
        """

        # Create a lookup dictionary from inventory
        inventory_lookup = inventory_df.set_index("car_id")["model"].to_dict()

        # Map current stock IDs to model names
        customers_df["current_car_model"] = customers_df["current_stock_id"].map(
            inventory_lookup
        )

        # Fill any missing models with "Unknown"
        customers_df["current_car_model"] = customers_df["current_car_model"].fillna(
            "Unknown"
        )

        logger.info(
            f"✅ Enriched customer data with car models. {customers_df['current_car_model'].notna().sum()} customers have known models"
        )

        return customers_df

    def load_all_data(self):
        """
        Load and integrate all data sources for the Trade-Up Engine.
        
        This method orchestrates the complete data loading process, fetching
        inventory from Redshift and customer data from CSV files, then enriching
        customer records with current vehicle model information.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (customers_df, inventory_df)
                - customers_df: Enriched customer data with vehicle models
                - inventory_df: Processed inventory data
        
        Process:
            1. Load inventory data from Redshift (with retries)
            2. Load customer data from CSV files
            3. Cross-reference to enrich customer vehicle models
            4. Validate data integrity
            5. Log comprehensive data summary
        
        Note:
            - Uses connection pooling for Redshift access
            - Handles missing data gracefully
            - Provides detailed logging for monitoring
        """

        logger.info("🚀 Starting comprehensive data loading process...")

        # Load inventory from Redshift
        inventory_df = self.load_inventory_from_redshift()

        # Load customers from CSV
        customers_df = self.load_customers_from_csv()

        # Enrich customer data with car models
        if not customers_df.empty and not inventory_df.empty:
            customers_df = self.enrich_customer_models(customers_df, inventory_df)

        logger.info("✅ Data loading and enrichment complete!")
        logger.info("📊 Final data summary:")
        logger.info("   - Customers: %d", len(customers_df))
        logger.info("   - Inventory: %d", len(inventory_df))

        return customers_df, inventory_df


    def load_customers_data(self):
        """Load only customer data (for API use)"""
        return self.load_customers_from_csv()
    
    def load_filtered_inventory_from_redshift(self, year: int, price: float, kilometers: float):
        """Load pre-filtered inventory from Redshift for trade-up candidates.

        If an optimized SQL file (data/filtered_inventory_query.sql) is present, it
        will be executed server-side for efficiency. If the file is missing, we
        transparently fall back to loading the full inventory and applying the
        filter in memory so the feature continues to work without the extra
        query file.
        """
        logger.info(
            f"🔍 Loading filtered inventory: year>={year}, price>${price:,.0f}, km<{kilometers:,.0f}"
        )

        sql_available = False
        try:
            with open("data/filtered_inventory_query.sql", "r") as file:
                query = file.read()
                sql_available = True
        except FileNotFoundError:
            logger.warning(
                "⚠️ filtered_inventory_query.sql not found – falling back to in-memory filtering"
            )

        if sql_available:
            try:
                pool = get_connection_pool()
                with pool.get_connection() as conn:
                    logger.info("✅ Got connection from pool for filtered query")
                    with conn.cursor() as cursor:
                        cursor.execute(query, (year, price, kilometers))
                        df = cursor.fetch_dataframe()

                if df.empty:
                    logger.info("📊 No inventory matches the filter criteria (SQL)")
                    return pd.DataFrame()

                inventory_df = self.transform_inventory_data(df)
                logger.info(
                    f"✅ Loaded {len(inventory_df)} pre-filtered items from Redshift"
                )
                return inventory_df

            except Exception as e:
                from app.utils.exceptions import DataLoadError
                logger.error(
                    f"❌ Failed SQL-based filtered inventory load: {type(e).__name__}: {e}"
                )
                raise DataLoadError(
                    source="Redshift (filtered)",
                    reason=f"{type(e).__name__}: {str(e)}",
                )
        else:
            # Fallback: load full inventory then filter locally
            full_df = self.load_inventory_from_redshift()
            if full_df.empty:
                logger.warning("⚠️ Full inventory load returned 0 rows – cannot apply filter")
                return pd.DataFrame()

            filtered_df = full_df[
                (full_df["year"] >= year)
                & (full_df["car_price"] > price)
                & (full_df["kilometers"] < kilometers)
            ]
            logger.info(
                f"✅ In-memory fallback filter produced {len(filtered_df)} candidate cars"
            )
            return filtered_df

    def load_single_car_from_redshift(self, car_id: str):
        """Load a single car from Redshift using WHERE clause - TRUE optimization."""
        logger.info(f"🔍 Loading single car {car_id} from Redshift...")
        
        # Build query with WHERE clause
        query = """
        SELECT 
            stock_id,
            full_model,
            region_name,
            kilometers,
            color,
            regular_published_price_financing,
            promotion_published_price_financing,
            has_promotion_discount,
            price_difference_abs,
            hub_name,
            region_growth,
            year
        FROM public.mx_inventory_with_data
        WHERE is_available = true
          AND financing_enabled = true
          AND has_financing_price = true
          AND stock_id = %s
        LIMIT 1
        """
        
        try:
            pool = get_connection_pool()
            with pool.get_connection(timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (car_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        logger.warning(f"⚠️ Car {car_id} not found in Redshift")
                        return None
                    
                    columns = [desc[0] for desc in cursor.description]
                    df = pd.DataFrame([result], columns=columns)
                
                # Transform to match expected format
                inventory_df = self.transform_inventory_data(df)
                
                if inventory_df.empty:
                    return None
                    
                logger.info(f"✅ Successfully loaded car {car_id} from Redshift")
                return inventory_df.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"❌ Error loading car from Redshift: {e}")
            return None


# Create global data loader instance
data_loader = DataLoader()
