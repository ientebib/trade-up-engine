"""
Mock data loader for development/testing environments
Used when Redshift is not accessible (e.g., GitHub Codespaces)
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_mock_inventory(num_cars=100):
    """Generate realistic mock inventory data matching the expected structure"""
    brands = ['CHEVROLET', 'NISSAN', 'MAZDA', 'VOLKSWAGEN', 'KIA', 'TOYOTA', 'HONDA']
    models = {
        'CHEVROLET': ['AVEO', 'SPARK', 'SONIC', 'CRUZE'],
        'NISSAN': ['VERSA', 'SENTRA', 'ALTIMA', 'MARCH'],
        'MAZDA': ['MAZDA2', 'MAZDA3', 'CX-3', 'CX-5'],
        'VOLKSWAGEN': ['VENTO', 'JETTA', 'GOLF', 'TIGUAN'],
        'KIA': ['RIO', 'FORTE', 'OPTIMA', 'SPORTAGE'],
        'TOYOTA': ['YARIS', 'COROLLA', 'CAMRY', 'RAV4'],
        'HONDA': ['FIT', 'CITY', 'CIVIC', 'CR-V']
    }
    regions = ['CDMX', 'GUADALAJARA', 'MONTERREY', 'PUEBLA', 'QUERETARO']
    
    data = []
    for i in range(num_cars):
        brand = np.random.choice(brands)
        model_name = np.random.choice(models[brand])
        year = np.random.randint(2015, 2024)
        price = np.random.randint(150000, 500000)
        km = np.random.randint(10000, 150000)
        
        # Build full model name like the real data
        full_model = f"{brand} {model_name} {year}"
        
        data.append({
            'car_id': f'MOCK{i:05d}',
            'model': full_model,  # Full model string
            'car_price': price,
            'sales_price': price,  # Alias for backward compatibility
            'region': np.random.choice(regions),
            'kilometers': km,
            'color': np.random.choice(['BLANCO', 'NEGRO', 'GRIS', 'ROJO', 'AZUL']),
            'has_promotion': np.random.choice([True, False], p=[0.2, 0.8]),
            'price_difference': np.random.randint(-5000, 5000),
            'hub_name': np.random.choice(['Hub Norte', 'Hub Sur', 'Hub Centro']),
            'region_growth': np.random.uniform(0.8, 1.2),
            'car_brand': brand,
            'make': brand,  # Alias for compatibility
            'brand': brand,  # Another alias
            'year': year,
            'model_short': model_name,
            # Additional fields for filtering
            'transmission': np.random.choice(['MANUAL', 'AUTOMATICO']),
            'fuel_type': 'GASOLINA',
            'doors': np.random.choice([4, 5]),
            'engine_size': np.random.choice(['1.4L', '1.6L', '2.0L', '2.5L']),
            'status': 'DISPONIBLE'
        })
    
    logger.info(f"✅ Generated {num_cars} mock inventory items")
    return pd.DataFrame(data)

def generate_mock_customers(num_customers=50):
    """Generate realistic mock customer data matching the expected structure"""
    risk_profiles = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'C3']
    first_names = ['Juan', 'Maria', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofia']
    last_names = ['Garcia', 'Rodriguez', 'Martinez', 'Lopez', 'Gonzalez', 'Perez', 'Sanchez']
    brands = ['NISSAN', 'CHEVROLET', 'MAZDA', 'VOLKSWAGEN', 'KIA']
    models = ['VERSA', 'AVEO', 'MAZDA3', 'VENTO', 'RIO']
    
    # Risk profile mapping for index
    risk_mapping = {
        'A1': 3, 'A2': 4, 'B1': 5, 'B2': 6,
        'C1': 7, 'C2': 8, 'C3': 9
    }
    
    data = []
    for i in range(num_customers):
        payment = np.random.randint(3000, 15000)
        balance = np.random.randint(50000, 400000)
        car_price = balance * 1.2
        equity = car_price - balance
        first_name = np.random.choice(first_names)
        last_name = np.random.choice(last_names)
        risk_profile = np.random.choice(risk_profiles)
        car_year = np.random.randint(2015, 2022)
        car_brand = np.random.choice(brands)
        car_model = np.random.choice(models)
        
        # Generate contract date 6-36 months ago
        months_ago = np.random.randint(6, 36)
        contract_date = datetime.now() - pd.DateOffset(months=months_ago)
        
        data.append({
            # IDs
            'customer_id': f'MOCK{i:05d}',
            'contract_id': f'MOCK{i:05d}',
            'current_stock_id': f'STOCK{i:05d}',
            
            # Personal info
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f'{first_name} {last_name}',
            'name': f'{first_name} {last_name}',
            'email': f'customer{i}@example.com',
            
            # Financial info
            'current_monthly_payment': payment,
            'vehicle_equity': equity,
            'outstanding_balance': balance,
            'current_car_price': car_price,
            'original_loan_amount': balance * 1.1,
            'original_interest_rate': np.random.uniform(0.12, 0.25),
            
            # Contract details
            'contract_date': contract_date,
            'remaining_months': np.random.randint(12, 48),
            'has_kavak_total': np.random.choice([True, False], p=[0.3, 0.7]),
            
            # Car details
            'current_car_brand': car_brand,
            'current_car_model_name': car_model,
            'current_car_year': car_year,
            'current_car_km': np.random.randint(20000, 100000),
            'current_car_model': f'{car_brand} {car_model} {car_year}',
            'aging': np.random.randint(0, 3),
            'car_age_at_purchase': np.random.randint(0, 3),
            
            # Risk profile
            'risk_profile_name': risk_profile,
            'risk_profile': risk_profile,
            'risk_profile_index': risk_mapping.get(risk_profile, 10),
            
            # Calculated fields
            'months_since_contract': months_ago
        })
    
    df = pd.DataFrame(data)
    
    logger.info(f"✅ Generated {num_customers} mock customers")
    return df

def load_mock_data():
    """Load all mock data for testing"""
    return {
        'customers': generate_mock_customers(),
        'inventory': generate_mock_inventory()
    }