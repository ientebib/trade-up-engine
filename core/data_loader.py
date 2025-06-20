"""
Data Loader Module for Kavak Trade-Up Engine
Handles loading data from Redshift and CSV files with proper transformations
"""

import pandas as pd
import os
from dotenv import load_dotenv
import redshift_connector
import logging
from core import cache_utils  # local import to avoid circular
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self):
        """Initialize data loader with database connection parameters"""
        self.redshift_config = {
            'host': os.getenv('REDSHIFT_HOST'),
            'port': os.getenv('REDSHIFT_PORT', 5439),
            'database': os.getenv('REDSHIFT_DATABASE'),  # Fixed: was REDSHIFT_DB
            'user': os.getenv('REDSHIFT_USER'),
            'password': os.getenv('REDSHIFT_PASSWORD')
        }
        
        # Risk profile mapping to indices
        self.risk_profile_mapping = {
            'AAA': 0, 'AA': 1, 'A': 2, 'A1': 3, 'A2': 4, 'B': 5, 
            'C1': 6, 'C2': 7, 'C3': 8, 'D1': 9, 'D2': 10, 'D3': 11,
            'E1': 12, 'E2': 13, 'E3': 14, 'E4': 15, 'E5': 16, 
            'F1': 17, 'F2': 18, 'F3': 19, 'F4': 20,
            'B_SB': 21, 'C1_SB': 22, 'C2_SB': 23, 'E5_SB': 24, 'Z': 25
        }

        # Caches for repeated access
        self._customers_cache = None
        self._inventory_cache = None
        self._customers_cache_time = None
        self._inventory_cache_time = None
        self.customers_cache_ttl = cache_utils.CUSTOMER_CACHE_TTL
        self.inventory_cache_ttl = cache_utils.INVENTORY_CACHE_TTL

    def _cache_valid(self, cache_time: datetime, ttl: int) -> bool:
        if cache_time is None:
            return False
        return (datetime.utcnow() - cache_time).total_seconds() < ttl

    def load_inventory_from_redshift(self):
        """Load inventory data from Redshift using the redshift-connector."""
        logger.info("🔌 Connecting to Redshift using 'redshift-connector'...")
        
        if not all(self.redshift_config.values()):
            logger.error("❌ Redshift configuration is incomplete.")
            return pd.DataFrame()

        try:
            with open('redshift.sql', 'r') as file:
                query = file.read()
        except FileNotFoundError:
            logger.error("❌ redshift.sql file not found.")
            return pd.DataFrame()

        conn = None
        try:
            conn = redshift_connector.connect(
                host=self.redshift_config['host'],
                database=self.redshift_config['database'],
                user=self.redshift_config['user'],
                password=self.redshift_config['password'],
                port=int(self.redshift_config['port'])
            )
            logger.info("✅ Successfully connected to Redshift.")
            
            logger.info("🔍 Executing Redshift query to load inventory...")
            with conn.cursor() as cursor:
                cursor.execute(query)
                df = cursor.fetch_dataframe()

            inventory_df = self.transform_inventory_data(df)
            logger.info(f"✅ Loaded {len(inventory_df)} inventory items from Redshift.")
            return inventory_df

        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to load inventory from Redshift: {type(e).__name__}")
            logger.error(f"Full Traceback:\n{traceback.format_exc()}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
                logger.info("🔌 Redshift connection closed.")

    def transform_inventory_data(self, raw_df):
        """Transform raw Redshift inventory data to expected format"""
        
        # Create the model name by combining brand, model, year, version
        raw_df['full_model'] = raw_df.apply(
            lambda row: f"{row['car_brand']} {row['model']} {row['year']}" + 
                       (f" {row['version']}" if pd.notna(row['version']) and row['version'].strip() else ""),
            axis=1
        )
        
        # Decide between regular and promotional price
        # Use promotional price if available and lower than regular price
        raw_df['final_price'] = raw_df.apply(
            lambda row: row['promotion_published_price_financing'] 
            if (pd.notna(row['promotion_published_price_financing']) and 
                row['promotion_published_price_financing'] < row['regular_published_price_financing'])
            else row['regular_published_price_financing'],
            axis=1
        )
        
        # Create the final inventory DataFrame
        inventory_df = pd.DataFrame({
            'car_id': raw_df['stock_id'],
            'model': raw_df['full_model'],
            'sales_price': raw_df['final_price'],
            'region': raw_df['region_name'],
            'kilometers': raw_df['kilometers'],
            'color': raw_df['color'],
            'has_promotion': raw_df['has_promotion_discount'],
            'price_difference': raw_df['price_difference_abs'],
            'hub_name': raw_df['hub_name'],
            'region_growth': raw_df['region_growth']
        })
        
        # Clean up and validate
        inventory_df = inventory_df.dropna(subset=['car_id', 'model', 'sales_price'])
        inventory_df['sales_price'] = pd.to_numeric(inventory_df['sales_price'], errors='coerce')
        inventory_df = inventory_df[inventory_df['sales_price'] > 0]
        
        return inventory_df

    def load_customers_from_csv(self, csv_path='customer_data.csv'):
        """Load and transform customer data from CSV"""
        
        try:
            logger.info(f"📊 Loading customer data from {csv_path}...")
            df = pd.read_csv(csv_path)
            
            # Transform data to match expected structure
            customers_df = self.transform_customer_data(df)
            
            logger.info(f"✅ Loaded {len(customers_df)} customers from CSV")
            return customers_df
            
        except Exception as e:
            logger.error(f"❌ Failed to load customer data: {str(e)}")
            return pd.DataFrame()

    # ------------------------------------------------------------------
    # Public helper methods
    # ------------------------------------------------------------------

    def load_inventory(self, csv_path='inventory_data.csv', force_refresh: bool = False):
        """Return inventory data using TTL-based cache."""
        if force_refresh:
            self._inventory_cache = None
            self._inventory_cache_time = None
            cache_utils.invalidate_cache('inventory_data')

        if self._inventory_cache is not None and self._cache_valid(self._inventory_cache_time, self.inventory_cache_ttl):
            return self._inventory_cache

        cached_df = cache_utils.get_cache('inventory_data')
        if isinstance(cached_df, pd.DataFrame):
            self._inventory_cache = cached_df
            self._inventory_cache_time = datetime.utcnow()
            return self._inventory_cache

        if os.getenv('DISABLE_EXTERNAL_CALLS', 'false').lower() == 'true':
            logger.info("🚫 External calls disabled via ENV. Loading inventory from CSV only …")
            if os.path.exists(csv_path):
                try:
                    inv_df = pd.read_csv(csv_path)
                    logger.info(f"✅ Loaded {len(inv_df)} inventory items from {csv_path}.")
                except Exception as e:
                    logger.error(f"❌ Failed to read {csv_path}: {e}")
                    inv_df = pd.DataFrame()
            else:
                logger.warning(f"⚠️ {csv_path} not found. Inventory will be empty.")
                inv_df = pd.DataFrame()
        else:
            inv_df = self.load_inventory_from_redshift()
            if inv_df.empty:
                inv_df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()

        self._inventory_cache = inv_df
        self._inventory_cache_time = datetime.utcnow()
        if not inv_df.empty:
            cache_utils.set_cache('inventory_data', inv_df, self.inventory_cache_ttl)
        return self._inventory_cache

    def load_customers(self, csv_path='customer_data.csv', force_refresh: bool = False):
        """Return customer data using TTL-based cache."""
        if force_refresh:
            self._customers_cache = None
            self._customers_cache_time = None
            cache_utils.invalidate_cache('customer_data')

        if self._customers_cache is not None and self._cache_valid(self._customers_cache_time, self.customers_cache_ttl):
            return self._customers_cache

        cached_df = cache_utils.get_cache('customer_data')
        if isinstance(cached_df, pd.DataFrame):
            self._customers_cache = cached_df
            self._customers_cache_time = datetime.utcnow()
            return self._customers_cache

        self._customers_cache = self.load_customers_from_csv(csv_path)
        self._customers_cache_time = datetime.utcnow()
        if not self._customers_cache.empty:
            cache_utils.set_cache('customer_data', self._customers_cache, self.customers_cache_ttl)
        return self._customers_cache

    def refresh_inventory_cache(self, csv_path='inventory_data.csv'):
        """Force refresh the inventory data cache."""
        return self.load_inventory(csv_path, force_refresh=True)

    def refresh_customer_cache(self, csv_path='customer_data.csv'):
        """Force refresh the customer data cache."""
        return self.load_customers(csv_path, force_refresh=True)

    def transform_customer_data(self, raw_df):
        """Transform raw customer CSV data to expected format"""
        
        # Map risk profile names to indices
        raw_df['risk_profile_index'] = raw_df['risk_profile'].map(self.risk_profile_mapping)
        
        # Handle any unmapped risk profiles
        unmapped = raw_df[raw_df['risk_profile_index'].isna()]
        if len(unmapped) > 0:
            logger.warning(f"⚠️ Found {len(unmapped)} customers with unmapped risk profiles: {unmapped['risk_profile'].unique()}")
            # Default unmapped profiles to highest risk index
            raw_df.loc[raw_df['risk_profile_index'].isna(), 'risk_profile_index'] = 25
        
        # Use CONTRATO as the customer_id directly (it's already unique)
        raw_df['customer_id'] = raw_df['CONTRATO']
        
        # Create the final customers DataFrame
        customers_df = pd.DataFrame({
            'customer_id': raw_df['customer_id'],  # Now using CONTRATO as ID
            'contract_id': raw_df['CONTRATO'],
            'current_stock_id': raw_df['STOCK ID'],
            'current_monthly_payment': pd.to_numeric(raw_df['current_monthly_payment'], errors='coerce'),
            'vehicle_equity': pd.to_numeric(raw_df['vehicle_equity'], errors='coerce'),
            'outstanding_balance': pd.to_numeric(raw_df['saldo insoluto'], errors='coerce'),
            'current_car_price': pd.to_numeric(raw_df['current_car_price'], errors='coerce'),
            'risk_profile_name': raw_df['risk_profile'],
            'risk_profile_index': raw_df['risk_profile_index'].astype(int)
        })
        
        # Add current car model by looking up stock ID (this would require inventory data)
        customers_df['current_car_model'] = 'Unknown'  # Placeholder - can be enriched later
        
        # Clean up and validate
        customers_df = customers_df.dropna(subset=['customer_id', 'current_monthly_payment', 'vehicle_equity', 'current_car_price'])
        customers_df = customers_df[customers_df['current_monthly_payment'] > 0]
        customers_df = customers_df[customers_df['current_car_price'] > 0]
        
        return customers_df

    def enrich_customer_models(self, customers_df, inventory_df):
        """Enrich customer data with current car model names from inventory"""
        
        # Create a lookup dictionary from inventory
        inventory_lookup = inventory_df.set_index('car_id')['model'].to_dict()
        
        # Map current stock IDs to model names
        customers_df['current_car_model'] = customers_df['current_stock_id'].map(inventory_lookup)
        
        # Fill any missing models with "Unknown"
        customers_df['current_car_model'] = customers_df['current_car_model'].fillna('Unknown')
        
        logger.info(f"✅ Enriched customer data with car models. {customers_df['current_car_model'].notna().sum()} customers have known models")
        
        return customers_df

    def load_all_data(self, force_refresh: bool = False):
        """Load and integrate all data sources"""
        
        logger.info("🚀 Starting comprehensive data loading process...")
        
        # Load inventory and customers using caching rules
        inventory_df = self.load_inventory(force_refresh=force_refresh)
        customers_df = self.load_customers(force_refresh=force_refresh)
        
        # Enrich customer data with car models
        if not customers_df.empty and not inventory_df.empty:
            customers_df = self.enrich_customer_models(customers_df, inventory_df)
        
        logger.info("✅ Data loading complete!")
        logger.info(f"📊 Final data summary:")
        logger.info(f"   - Customers: {len(customers_df)}")
        logger.info(f"   - Inventory: {len(inventory_df)}")
        
        return customers_df, inventory_df

# Create global data loader instance
data_loader = DataLoader() 
