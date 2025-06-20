"""
Development Data Loader Module for Trade-Up Engine
Uses CSV files and dummy data instead of Redshift for virtual agent compatibility
"""

import pandas as pd
import os
import logging
from core.logging_config import setup_logging
from pathlib import Path

# Set up logging
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

class DevelopmentDataLoader:
    def __init__(self):
        """Initialize development data loader with CSV-based data sources"""
        # Simple in-memory caches so repeated API calls do not constantly
        # re-read the CSV files.  These are populated on first use.
        self._customers_cache = None
        self._inventory_cache = None
        # Risk profile mapping to indices
        self.risk_profile_mapping = {
            'Low': 0, 'Medium': 1, 'High': 2,
            'AAA': 0, 'AA': 1, 'A': 2, 'A1': 3, 'A2': 4, 'B': 5, 
            'C1': 6, 'C2': 7, 'C3': 8, 'D1': 9, 'D2': 10, 'D3': 11,
            'E1': 12, 'E2': 13, 'E3': 14, 'E4': 15, 'E5': 16, 
            'F1': 17, 'F2': 18, 'F3': 19, 'F4': 20,
            'B_SB': 21, 'C1_SB': 22, 'C2_SB': 23, 'E5_SB': 24, 'Z': 25
        }

    def create_sample_inventory(self):
        """Create sample inventory data for development"""
        logger.info("📦 Creating sample inventory data...")
        
        sample_inventory = [
            {
                'car_id': 'INV001',
                'model': 'Tesla Model 3 2023 Standard Range',
                'sales_price': 850000,
                'region': 'CDMX',
                'kilometers': 15000,
                'color': 'White',
                'has_promotion': True,
                'price_difference': 50000,
                'hub_name': 'Kavak CDMX Centro',
                'region_growth': 0.15
            },
            {
                'car_id': 'INV002',
                'model': 'BMW X3 2022 xDrive30i',
                'sales_price': 1200000,
                'region': 'Monterrey',
                'kilometers': 25000,
                'color': 'Black',
                'has_promotion': False,
                'price_difference': 0,
                'hub_name': 'Kavak Monterrey',
                'region_growth': 0.12
            },
            {
                'car_id': 'INV003',
                'model': 'Audi A4 2021 Premium Plus',
                'sales_price': 950000,
                'region': 'Guadalajara',
                'kilometers': 30000,
                'color': 'Silver',
                'has_promotion': True,
                'price_difference': 75000,
                'hub_name': 'Kavak Guadalajara',
                'region_growth': 0.18
            },
            {
                'car_id': 'INV004',
                'model': 'Toyota Camry 2023 XSE',
                'sales_price': 750000,
                'region': 'CDMX',
                'kilometers': 12000,
                'color': 'Blue',
                'has_promotion': False,
                'price_difference': 0,
                'hub_name': 'Kavak CDMX Sur',
                'region_growth': 0.15
            },
            {
                'car_id': 'INV005',
                'model': 'Honda Accord 2022 Touring',
                'sales_price': 680000,
                'region': 'Querétaro',
                'kilometers': 18000,
                'color': 'Red',
                'has_promotion': True,
                'price_difference': 45000,
                'hub_name': 'Kavak Querétaro',
                'region_growth': 0.10
            }
        ]
        
        inventory_df = pd.DataFrame(sample_inventory)
        logger.info(f"✅ Created {len(inventory_df)} sample inventory items")
        return inventory_df

    def load_inventory_from_csv(self, csv_path='inventory_data.csv'):
        """Load inventory data from CSV file"""
        try:
            if os.path.exists(csv_path):
                logger.info(f"📦 Loading inventory from {csv_path}...")
                df = pd.read_csv(csv_path)
                logger.info(f"✅ Loaded {len(df)} inventory items from CSV")
                return df
            else:
                logger.info("📦 No inventory CSV found, creating sample data...")
                return self.create_sample_inventory()
        except Exception as e:
            logger.error(f"❌ Failed to load inventory from CSV: {str(e)}")
            logger.info("📦 Falling back to sample inventory data...")
            return self.create_sample_inventory()

    def load_customers_from_csv(self, csv_path='customer_data.csv'):
        """Load and transform customer data from CSV"""
        try:
            if os.path.exists(csv_path):
                logger.info(f"📊 Loading customer data from {csv_path}...")
                df = pd.read_csv(csv_path)
                
                # Check if this is the simple format or the full format
                if 'customer_id' in df.columns:
                    # Simple format (created by setup script)
                    customers_df = self.transform_simple_customer_data(df)
                else:
                    # Full format (original CSV)
                    customers_df = self.transform_full_customer_data(df)
                
                logger.info(f"✅ Loaded {len(customers_df)} customers from CSV")
                return customers_df
            else:
                logger.info("📊 No customer CSV found, creating sample data...")
                return self.create_sample_customers()
                
        except Exception as e:
            logger.error(f"❌ Failed to load customer data: {str(e)}")
            logger.info("📊 Falling back to sample customer data...")
            return self.create_sample_customers()

    # ------------------------------------------------------------------
    # Public helper methods used by API routes
    # ------------------------------------------------------------------

    def load_inventory(self, csv_path='inventory_data.csv'):
        """Return inventory DataFrame with basic caching."""
        if self._inventory_cache is None:
            self._inventory_cache = self.load_inventory_from_csv(csv_path)
        return self._inventory_cache

    def load_customers(self, csv_path='customer_data.csv'):
        """Return customer DataFrame with basic caching."""
        if self._customers_cache is None:
            self._customers_cache = self.load_customers_from_csv(csv_path)
        return self._customers_cache

    def transform_simple_customer_data(self, raw_df):
        """Transform simple customer CSV data (from setup script)"""
        
        # Map risk profile names to indices
        raw_df['risk_profile_index'] = raw_df['risk_profile'].map(self.risk_profile_mapping)
        
        # Handle any unmapped risk profiles
        unmapped = raw_df[raw_df['risk_profile_index'].isna()]
        if len(unmapped) > 0:
            logger.warning(f"⚠️ Found {len(unmapped)} customers with unmapped risk profiles: {unmapped['risk_profile'].unique()}")
            # Default unmapped profiles to medium risk
            raw_df.loc[raw_df['risk_profile_index'].isna(), 'risk_profile_index'] = 1
        
        # Generate stock IDs based on customer_id prefix
        raw_df['current_stock_id'] = 'STOCK_' + raw_df['customer_id'].str[:8]

        # Create the final customers DataFrame
        customers_df = pd.DataFrame({
            'customer_id': raw_df['customer_id'],
            'contract_id': raw_df['customer_id'],  # Use customer_id as contract_id
            'current_stock_id': raw_df['current_stock_id'],
            'current_monthly_payment': pd.to_numeric(raw_df['monthly_payment'], errors='coerce'),
            'vehicle_equity': pd.to_numeric(raw_df['current_balance'], errors='coerce') * 0.3,  # Estimate equity
            'outstanding_balance': pd.to_numeric(raw_df['current_balance'], errors='coerce'),
            'current_car_price': pd.to_numeric(raw_df['current_balance'], errors='coerce') * 1.2,  # Estimate car price
            'risk_profile_name': raw_df['risk_profile'],
            'risk_profile_index': raw_df['risk_profile_index'].astype(int),
            'current_car_model': raw_df['vehicle_make'] + ' ' + raw_df['vehicle_model']
        })
        
        # Clean up and validate
        customers_df = customers_df.dropna(subset=['customer_id', 'current_monthly_payment', 'vehicle_equity', 'current_car_price'])
        customers_df = customers_df[customers_df['current_monthly_payment'] > 0]
        customers_df = customers_df[customers_df['current_car_price'] > 0]
        
        return customers_df

    def transform_full_customer_data(self, raw_df):
        """Transform full customer CSV data (original format)"""
        
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
            'customer_id': raw_df['customer_id'],
            'contract_id': raw_df['CONTRATO'],
            'current_stock_id': raw_df['STOCK ID'],
            'current_monthly_payment': pd.to_numeric(raw_df['current_monthly_payment'], errors='coerce'),
            'vehicle_equity': pd.to_numeric(raw_df['vehicle_equity'], errors='coerce'),
            'outstanding_balance': pd.to_numeric(raw_df['saldo insoluto'], errors='coerce'),
            'current_car_price': pd.to_numeric(raw_df['current_car_price'], errors='coerce'),
            'risk_profile_name': raw_df['risk_profile'],
            'risk_profile_index': raw_df['risk_profile_index'].astype(int),
            'current_car_model': 'Unknown'  # Will be enriched later
        })
        
        # Clean up and validate
        customers_df = customers_df.dropna(subset=['customer_id', 'current_monthly_payment', 'vehicle_equity', 'current_car_price'])
        customers_df = customers_df[customers_df['current_monthly_payment'] > 0]
        customers_df = customers_df[customers_df['current_car_price'] > 0]
        
        return customers_df

    def create_sample_customers(self):
        """Create sample customer data for development"""
        logger.info("📊 Creating sample customer data...")
        
        sample_customers = [
            {
                'customer_id': 'TMCJ33A32GJ053451',
                'contract_id': 'TMCJ33A32GJ053451',
                'current_stock_id': 'STOCK_TMCJ33A3',
                'current_monthly_payment': 8500,
                'vehicle_equity': 45000,
                'outstanding_balance': 150000,
                'current_car_price': 200000,
                'risk_profile_name': 'A1',
                'current_car_model': 'Tesla Model 3'
            },
            {
                'customer_id': 'MEX5G2607HT063991',
                'contract_id': 'MEX5G2607HT063991',
                'current_stock_id': 'STOCK_MEX5G260',
                'current_monthly_payment': 12000,
                'vehicle_equity': 60000,
                'outstanding_balance': 200000,
                'current_car_price': 260000,
                'risk_profile_name': 'B',
                'current_car_model': 'BMW X3'
            },
            {
                'customer_id': 'WAUAYJ8V9G1017027',
                'contract_id': 'WAUAYJ8V9G1017027',
                'current_stock_id': 'STOCK_WAUAYJ8V',
                'current_monthly_payment': 15000,
                'vehicle_equity': 75000,
                'outstanding_balance': 250000,
                'current_car_price': 325000,
                'risk_profile_name': 'C1',
                'current_car_model': 'Audi A4'
            },
            {
                'customer_id': 'JTDKARFU0J1234567',
                'contract_id': 'JTDKARFU0J1234567',
                'current_stock_id': 'STOCK_JTDKARFU',
                'current_monthly_payment': 9000,
                'vehicle_equity': 48000,
                'outstanding_balance': 160000,
                'current_car_price': 208000,
                'risk_profile_name': 'A2',
                'current_car_model': 'Toyota Camry'
            },
            {
                'customer_id': '1HGBH41JXMN109186',
                'contract_id': '1HGBH41JXMN109186',
                'current_stock_id': 'STOCK_1HGBH41J',
                'current_monthly_payment': 11000,
                'vehicle_equity': 54000,
                'outstanding_balance': 180000,
                'current_car_price': 234000,
                'risk_profile_name': 'D1',
                'current_car_model': 'Honda Accord'
            }
        ]

        customers_df = pd.DataFrame(sample_customers)
        # Map profile names to indices used by financial tables
        customers_df['risk_profile_index'] = customers_df['risk_profile_name'].map(self.risk_profile_mapping).astype(int)
        
        logger.info(f"✅ Created {len(customers_df)} sample customers")
        return customers_df

    def enrich_customer_models(self, customers_df, inventory_df):
        """Enrich customer data with current car model names from inventory"""
        
        # Create a lookup dictionary from inventory
        inventory_lookup = inventory_df.set_index('car_id')['model'].to_dict()
        
        # Map current stock IDs to model names
        customers_df['current_car_model'] = customers_df['current_stock_id'].map(inventory_lookup)
        
        # Fill any missing models with existing values or "Unknown"
        customers_df['current_car_model'] = customers_df['current_car_model'].fillna(customers_df.get('current_car_model', 'Unknown'))
        
        logger.info(f"✅ Enriched customer data with car models. {customers_df['current_car_model'].notna().sum()} customers have known models")
        
        return customers_df

    def load_all_data(self):
        """Load and integrate all data sources for development"""
        
        logger.info("🚀 Starting development data loading process...")
        logger.info("🔧 Using CSV files and sample data (no Redshift connection)")
        
        # Load inventory from CSV or create sample data
        inventory_df = self.load_inventory_from_csv()
        
        # Load customers from CSV or create sample data
        customers_df = self.load_customers_from_csv()
        
        # Enrich customer data with car models
        if not customers_df.empty and not inventory_df.empty:
            customers_df = self.enrich_customer_models(customers_df, inventory_df)
        
        logger.info("✅ Development data loading complete!")
        logger.info(f"📊 Final data summary:")
        logger.info(f"   - Customers: {len(customers_df)}")
        logger.info(f"   - Inventory: {len(inventory_df)}")
        logger.info("🔧 Development mode: Using local data sources only")
        
        return customers_df, inventory_df

# Create a singleton instance
dev_data_loader = DevelopmentDataLoader() 
