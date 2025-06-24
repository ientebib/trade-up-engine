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
from utils.logging import setup_logging
# Caching disabled
# Risk profile mapping moved inline
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
    def __init__(self):
        """Initialize data loader with database connection parameters"""
        # Don't store password in instance variable for security
        self._host = os.getenv("REDSHIFT_HOST")
        self._port = os.getenv("REDSHIFT_PORT", 5439)
        self._database = os.getenv("REDSHIFT_DATABASE")  # Fixed: was REDSHIFT_DB
        self._user = os.getenv("REDSHIFT_USER")

        # Use shared risk profile mapping
        self.risk_profile_mapping = RISK_PROFILE_MAPPING

        # Caches for repeated access
        # Caching disabled

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3)
    )
    def load_inventory_from_redshift(self):
        """Load inventory data from Redshift using the redshift-connector."""
        logger.info("🔌 Connecting to Redshift using 'redshift-connector'...")

        # Get password only when needed
        password = os.getenv("REDSHIFT_PASSWORD")
        
        if not all([self._host, self._port, self._database, self._user, password]):
            logger.error("❌ Redshift configuration is incomplete.")
            return pd.DataFrame()

        try:
            with open("data/inventory_query.sql", "r") as file:
                query = file.read()
        except FileNotFoundError:
            logger.error("❌ inventory_query.sql file not found in data/ folder.")
            return pd.DataFrame()

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

        conn = None
        try:
            conn = redshift_connector.connect(
                host=self._host,
                database=self._database,
                user=self._user,
                password=password,
                port=int(self._port),
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
            }
        )

        # Clean up and validate
        inventory_df = inventory_df.dropna(subset=["car_id", "model", "sales_price"])
        inventory_df["sales_price"] = pd.to_numeric(
            inventory_df["sales_price"], errors="coerce"
        )
        inventory_df = inventory_df[inventory_df["sales_price"] > 0]

        return inventory_df

    def load_customers_from_csv(self, csv_path="data/customer_data.csv"):
        """Load and transform customer data from CSV"""

        try:
            # Check for enriched data file first
            enriched_csv = "data/customers_data_tradeup.csv"
            if os.path.exists(enriched_csv):
                csv_path = enriched_csv
                logger.info(f"📊 Loading ENRICHED customer data from {csv_path}...")
            elif os.path.exists("data/customer_data_tradeup.csv"):
                # Fallback to old name
                csv_path = "data/customer_data_tradeup.csv"
                logger.info(f"📊 Loading customer data from {csv_path}...")
            else:
                logger.info(f"📊 Loading customer data from {csv_path}...")
            
            # Read with encoding to handle special characters
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

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

    def load_inventory(self, force_refresh=False):
        """Return inventory data - always from Redshift."""
        inv_df = self.load_inventory_from_redshift()
        
        if inv_df.empty:
            logger.error("❌ Failed to load inventory from Redshift.")
            logger.error("💡 Check your Redshift connection settings and ensure inventory_query.sql exists in data/ folder.")
        
        return inv_df

    def load_customers(self, csv_path="data/customer_data.csv", force_refresh=False):
        """Return customer data - always fresh from source."""
        # Caching disabled - always load fresh data

        customers_df = self.load_customers_from_csv(csv_path)
        # Caching disabled - return fresh data
        return customers_df

    def transform_customer_data(self, raw_df):
        """Transform raw customer CSV data to expected format"""
        
        # First, normalize column names to handle variations
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
            
            # Risk profile
            "risk_profile": "risk_profile_name"
        }
        
        # Rename columns using the mapping
        for old_col, new_col in column_mapping.items():
            if old_col in raw_df.columns:
                raw_df[new_col] = raw_df[old_col]
        
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

        # Use CONTRATO as the customer_id directly (it's already unique)
        raw_df["customer_id"] = raw_df["contract_id"]
        
        # Parse contract date
        raw_df["contract_date"] = pd.to_datetime(raw_df["contract_date"], errors="coerce")
        
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

        # Create the final customers DataFrame with all fields
        customers_df = pd.DataFrame({
            # IDs
            "customer_id": raw_df["customer_id"],
            "contract_id": raw_df["contract_id"],
            "current_stock_id": raw_df["current_stock_id"],
            
            # Personal info
            "first_name": raw_df["first_name"],
            "last_name": raw_df["last_name"],
            "full_name": raw_df["first_name"] + " " + raw_df["last_name"],
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
            
            # Risk profile
            "risk_profile_name": raw_df["risk_profile_name"],
            "risk_profile_index": raw_df["risk_profile_index"].astype(int),
        })

        # Calculate derived fields
        customers_df["months_since_contract"] = (
            (pd.Timestamp.now() - customers_df["contract_date"]).dt.days / 30
        ).fillna(0).astype(int)
        
        customers_df["car_age_at_purchase"] = (
            customers_df["contract_date"].dt.year - customers_df["current_car_year"]
        ).fillna(0).astype(int)

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
        
        logger.info(f"📊 Transformed customer data with {len(customers_df.columns)} fields")

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

        logger.info("✅ Data loading and enrichment complete!")
        logger.info("📊 Final data summary:")
        logger.info("   - Customers: %d", len(customers_df))
        logger.info("   - Inventory: %d", len(inventory_df))

        return customers_df, inventory_df


# Create global data loader instance
data_loader = DataLoader()
