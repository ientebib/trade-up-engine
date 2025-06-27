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
from unittest.mock import MagicMock


@pytest.fixture
def mock_registry():
    """Mock config registry for testing"""
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
def mock_database():
    """Mock database for testing"""
    mock_db = MagicMock()
    mock_db.get_customer_by_id.return_value = {
        "customer_id": "TEST123",
        "current_monthly_payment": 5000,
        "vehicle_equity": 100000,
        "outstanding_balance": 150000,
        "risk_profile": "A1"
    }
    return mock_db