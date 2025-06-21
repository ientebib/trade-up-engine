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
from core.logging_config import setup_logging
from core import cache_utils  # local import to avoid circular
from core.risk_profiles import RISK_PROFILE_MAPPING

# Load environment variables
load_dotenv()

# Set up logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self):
        """Initialize data loader with database connection parameters"""
        self.redshift_config = {
            "host": os.getenv("REDSHIFT_HOST"),
            "port": os.getenv("REDSHIFT_PORT", 5439),
            "database": os.getenv("REDSHIFT_DATABASE"),  # Fixed: was REDSHIFT_DB
            "user": os.getenv("REDSHIFT_USER"),
            "password": os.getenv("REDSHIFT_PASSWORD"),
        }

        # Use shared risk profile mapping
        self.risk_profile_mapping = RISK_PROFILE_MAPPING

        # Caches for repeated access
        self._customers_cache = None
        self._inventory_cache = None

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3)
    )
    def load_inventory_from_redshift(self):
        """Load inventory data from Redshift using the redshift-connector."""
        logger.info("🔌 Connecting to Redshift using 'redshift-connector'...")

        if not all(self.redshift_config.values()):
            logger.error("❌ Redshift configuration is incomplete.")
            return pd.DataFrame()

        try:
            with open("redshift.sql", "r") as file:
                query = file.read()
        except FileNotFoundError:
            logger.error("❌ redshift.sql file not found.")
            return pd.DataFrame()

        chaos = os.getenv("CHAOS_MODE")
        if chaos:
            if chaos == "network" and random.random() < 0.3:
                logger.warning("💥 Chaos mode: simulating network drop")
                raise ConnectionError("simulated network drop")
            if chaos == "stall" and random.random() < 0.3:
                delay = random.uniform(5, 10)
                logger.warning(f"💥 Chaos mode: stalling for {delay:.1f}s")
                time.sleep(delay)

        conn = None
        try:
            conn = redshift_connector.connect(
                host=self.redshift_config["host"],
                database=self.redshift_config["database"],
                user=self.redshift_config["user"],
                password=self.redshift_config["password"],
                port=int(self.redshift_config["port"]),
                timeout=int(os.getenv("DATA_LOADER_TIMEOUT", 10)),
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

            logger.error(
                f"❌ Failed to load inventory from Redshift: {type(e).__name__}"
            )
            logger.error(f"Full Traceback:\n{traceback.format_exc()}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
                logger.info("🔌 Redshift connection closed.")

    def transform_inventory_data(self, raw_df):
        """Transform raw Redshift inventory data to expected format"""

        # Create the model name by combining brand, model, year, version
        raw_df["full_model"] = raw_df.apply(
            lambda row: f"{row['car_brand']} {row['model']} {row['year']}"
            + (
                f" {row['version']}"
                if pd.notna(row["version"]) and row["version"].strip()
                else ""
            ),
            axis=1,
        )

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
            }
        )

        # Clean up and validate
        inventory_df = inventory_df.dropna(subset=["car_id", "model", "sales_price"])
        inventory_df["sales_price"] = pd.to_numeric(
            inventory_df["sales_price"], errors="coerce"
        )
        inventory_df = inventory_df[inventory_df["sales_price"] > 0]

        return inventory_df

    def load_customers_from_csv(self, csv_path="customer_data.csv"):
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

    def load_inventory(self, csv_path="inventory_data.csv", force_refresh=False):
        """Return inventory data with TTL-based caching."""
        if force_refresh:
            self._inventory_cache = None

        if self._inventory_cache is not None:
            return self._inventory_cache

        cached = cache_utils.get_cached_inventory()
        if cached is not None and not force_refresh:
            logger.info("✅ Loaded inventory from cache (%d rows).", len(cached))
            self._inventory_cache = cached
            return cached

        if os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true":
            logger.info(
                "🚫 External calls disabled via ENV. Loading inventory from CSV only …"
            )
            if os.path.exists(csv_path):
                try:
                    inv_df = pd.read_csv(csv_path)
                    logger.info(
                        f"✅ Loaded {len(inv_df)} inventory items from {csv_path}."
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to read {csv_path}: {e}")
                    inv_df = pd.DataFrame()
            else:
                logger.warning(f"⚠️ {csv_path} not found. Inventory will be empty.")
                inv_df = pd.DataFrame()
        else:
            inv_df = self.load_inventory_from_redshift()
            if inv_df.empty:
                inv_df = (
                    pd.read_csv(csv_path)
                    if os.path.exists(csv_path)
                    else pd.DataFrame()
                )

        if not inv_df.empty:
            cache_utils.set_cached_inventory(inv_df)

        self._inventory_cache = inv_df
        return self._inventory_cache

    def load_customers(self, csv_path="customer_data.csv", force_refresh=False):
        """Return customer data with TTL-based caching."""
        if force_refresh:
            self._customers_cache = None

        if self._customers_cache is not None:
            return self._customers_cache

        cached = cache_utils.get_cached_customers()
        if cached is not None and not force_refresh:
            logger.info("✅ Loaded customers from cache (%d rows).", len(cached))
            self._customers_cache = cached
            return cached

        customers_df = self.load_customers_from_csv(csv_path)
        if not customers_df.empty:
            cache_utils.set_cached_customers(customers_df)
        self._customers_cache = customers_df
        return self._customers_cache

    def transform_customer_data(self, raw_df):
        """Transform raw customer CSV data to expected format"""

        # Map risk profile names to indices
        raw_df["risk_profile_index"] = raw_df["risk_profile"].map(
            self.risk_profile_mapping
        )

        # Handle any unmapped risk profiles
        unmapped = raw_df[raw_df["risk_profile_index"].isna()]
        if len(unmapped) > 0:
            logger.warning(
                f"⚠️ Found {len(unmapped)} customers with unmapped risk profiles: {unmapped['risk_profile'].unique()}"
            )
            # Default unmapped profiles to highest risk index
            raw_df.loc[raw_df["risk_profile_index"].isna(), "risk_profile_index"] = 25

        # Use CONTRATO as the customer_id directly (it's already unique)
        raw_df["customer_id"] = raw_df["CONTRATO"]

        # Create the final customers DataFrame
        customers_df = pd.DataFrame(
            {
                "customer_id": raw_df["customer_id"],  # Now using CONTRATO as ID
                "contract_id": raw_df["CONTRATO"],
                "current_stock_id": raw_df["STOCK ID"],
                "current_monthly_payment": pd.to_numeric(
                    raw_df["current_monthly_payment"], errors="coerce"
                ),
                "vehicle_equity": pd.to_numeric(
                    raw_df["vehicle_equity"], errors="coerce"
                ),
                "outstanding_balance": pd.to_numeric(
                    raw_df["saldo insoluto"], errors="coerce"
                ),
                "current_car_price": pd.to_numeric(
                    raw_df["current_car_price"], errors="coerce"
                ),
                "risk_profile_name": raw_df["risk_profile"],
                "risk_profile_index": raw_df["risk_profile_index"].astype(int),
            }
        )

        # Add current car model by looking up stock ID (this would require inventory data)
        customers_df["current_car_model"] = (
            "Unknown"  # Placeholder - can be enriched later
        )

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

    def enrich_customer_models(self, customers_df, inventory_df):
        """Enrich customer data with current car model names from inventory"""

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
        """Load and integrate all data sources"""

        logger.info("🚀 Starting comprehensive data loading process...")

        # Load inventory from Redshift
        inventory_df = self.load_inventory_from_redshift()

        # Load customers from CSV
        customers_df = self.load_customers_from_csv()

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
