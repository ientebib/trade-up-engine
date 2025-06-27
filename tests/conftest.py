"""
Global pytest configuration and fixtures
"""
import sys
import os

# Add the project root to Python path before any imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import MagicMock, Mock
from typing import Dict, List
from decimal import Decimal
import pandas as pd
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_registry():
    """Mock config registry for testing"""
    from config.registry import ConfigRegistry
    registry = MagicMock(spec=ConfigRegistry)
    registry.get.return_value = "test_value"
    registry.get_all.return_value = {"test.key": "test_value"}
    registry.validate.return_value = []
    return registry


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing"""
    config_file = tmp_path / "test_config.json"
    config_file.write_text('{"test": {"key": "value"}}')
    return config_file


@pytest.fixture
def mock_cache_manager():
    """Mock the cache manager"""
    mock_cache = Mock()
    mock_cache.get = Mock(return_value=None)
    mock_cache.set = Mock()
    mock_cache.delete = Mock()
    mock_cache.clear = Mock()
    mock_cache.is_enabled = Mock(return_value=True)
    return mock_cache


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances before each test"""
    # Reset connection pool
    try:
        from data import connection_pool
        connection_pool._pool_instance = None
    except:
        pass
    
    # Reset circuit breakers
    try:
        from data.circuit_breaker_factory import CircuitBreakerFactory
        CircuitBreakerFactory._instances = {}
    except:
        pass
    
    # Reset config registry
    try:
        from config.registry import ConfigRegistry
        ConfigRegistry._instance = None
    except:
        pass
    
    yield


@pytest.fixture
def mock_customer():
    """Create a complete mock customer for testing"""
    return {
        "customer_id": "TEST123",
        "current_monthly_payment": 15000.0,
        "vehicle_equity": 100000.0,
        "current_car_price": 250000.0,
        "outstanding_balance": 150000.0,
        "risk_profile_name": "A1",
        "risk_profile_index": 3,
        "region": "CDMX",
        "current_brand": "Toyota",
        "current_model": "Corolla",
        "current_year": 2020
    }


@pytest.fixture
def mock_vehicle():
    """Create a mock vehicle for testing"""
    return {
        "car_id": "VEH456",
        "model": "Camry",
        "brand": "Toyota",
        "year": 2022,
        "car_price": 350000.0,
        "sales_price": 350000.0,
        "km": 15000,
        "region": "CDMX",
        "color": "Silver",
        "vehicle_class": "Sedan"
    }


@pytest.fixture
def mock_inventory():
    """Create mock inventory dataframe"""
    return pd.DataFrame([
        {
            "car_id": f"VEH{i:03d}",
            "model": f"Model{i}",
            "brand": "Toyota" if i % 2 == 0 else "Honda",
            "year": 2020 + (i % 3),
            "car_price": 200000 + (i * 50000),
            "sales_price": 200000 + (i * 50000),
            "km": 10000 + (i * 5000),
            "region": "CDMX",
            "color": ["Silver", "Black", "White"][i % 3],
            "vehicle_class": "Sedan"
        }
        for i in range(10)
    ])


@pytest.fixture
def mock_database(mock_customer, mock_inventory):
    """Mock database for testing with complete functionality"""
    mock_db = MagicMock()
    
    # Customer operations
    mock_db.get_customer_by_id.return_value = mock_customer
    mock_db.search_customers.return_value = pd.DataFrame([mock_customer])
    mock_db.get_all_customers.return_value = pd.DataFrame([mock_customer])
    
    # Inventory operations
    mock_db.get_tradeup_inventory_for_customer.return_value = mock_inventory
    mock_db.get_all_inventory.return_value = mock_inventory
    
    return mock_db