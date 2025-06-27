"""Tests for the configuration facade"""
import sys
import os
# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from decimal import Decimal
from unittest.mock import patch, Mock

import config.facade as facade
from config.registry import ConfigRegistry


class TestConfigFacade:
    """Test the configuration facade"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset the global registry before each test"""
        facade._registry = None
        yield
        facade._registry = None
    
    def test_get_value(self):
        """Test getting configuration values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            mock_get.return_value = "test_value"
            
            value = facade.get("test.key")
            assert value == "test_value"
            mock_get.assert_called_once_with("test.key", None)
            
            # With default
            facade.get("test.key2", "default")
            mock_get.assert_called_with("test.key2", "default")
    
    def test_get_decimal(self):
        """Test getting decimal values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            # Already a Decimal
            mock_get.return_value = Decimal("123.45")
            value = facade.get_decimal("test.decimal")
            assert value == Decimal("123.45")
            assert isinstance(value, Decimal)
            
            # String that needs conversion
            mock_get.return_value = "67.89"
            value = facade.get_decimal("test.string")
            assert value == Decimal("67.89")
            
            # With default
            mock_get.return_value = None
            value = facade.get_decimal("missing", Decimal("10"))
            assert value == Decimal("10")
    
    def test_get_int(self):
        """Test getting integer values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            mock_get.return_value = 42
            value = facade.get_int("test.int")
            assert value == 42
            assert isinstance(value, int)
            
            # String conversion
            mock_get.return_value = "123"
            value = facade.get_int("test.string")
            assert value == 123
    
    def test_get_float(self):
        """Test getting float values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            # From Decimal
            mock_get.return_value = Decimal("123.45")
            value = facade.get_float("test.decimal")
            assert value == 123.45
            assert isinstance(value, float)
            
            # Already float
            mock_get.return_value = 67.89
            value = facade.get_float("test.float")
            assert value == 67.89
    
    def test_get_bool(self):
        """Test getting boolean values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            mock_get.return_value = True
            assert facade.get_bool("test.true") is True
            
            mock_get.return_value = False
            assert facade.get_bool("test.false") is False
            
            # Truthy/falsy conversion
            mock_get.return_value = 1
            assert facade.get_bool("test.one") is True
            
            mock_get.return_value = ""
            assert facade.get_bool("test.empty") is False
    
    def test_get_list(self):
        """Test getting list values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            # Already a list
            mock_get.return_value = [1, 2, 3]
            value = facade.get_list("test.list")
            assert value == [1, 2, 3]
            
            # Tuple conversion
            mock_get.return_value = (4, 5, 6)
            value = facade.get_list("test.tuple")
            assert value == [4, 5, 6]
            
            # Default
            mock_get.return_value = None
            value = facade.get_list("missing", [7, 8, 9])
            assert value == [7, 8, 9]
    
    def test_get_dict(self):
        """Test getting dict values"""
        with patch.object(ConfigRegistry, 'get') as mock_get:
            test_dict = {"key": "value"}
            mock_get.return_value = test_dict
            value = facade.get_dict("test.dict")
            assert value == test_dict
    
    def test_set_value(self):
        """Test setting configuration values"""
        with patch.object(ConfigRegistry, 'set') as mock_set:
            mock_set.return_value = True
            
            result = facade.set("test.key", "value")
            assert result is True
            mock_set.assert_called_once_with("test.key", "value", True)
            
            # Without persistence
            facade.set("test.key2", "value2", persist=False)
            mock_set.assert_called_with("test.key2", "value2", False)
    
    def test_get_all(self):
        """Test getting all configuration"""
        with patch.object(ConfigRegistry, 'get_all') as mock_get_all:
            mock_get_all.return_value = {"key1": "value1", "key2": "value2"}
            
            all_config = facade.get_all()
            assert all_config == {"key1": "value1", "key2": "value2"}
    
    def test_get_by_prefix(self):
        """Test getting by prefix"""
        with patch.object(ConfigRegistry, 'get_by_prefix') as mock_get_prefix:
            mock_get_prefix.return_value = {"financial.iva": 0.16}
            
            financial_config = facade.get_by_prefix("financial")
            assert financial_config == {"financial.iva": 0.16}
            mock_get_prefix.assert_called_once_with("financial")
    
    def test_reload(self):
        """Test reloading configuration"""
        with patch.object(ConfigRegistry, 'reload') as mock_reload:
            mock_reload.return_value = {"reloaded": True}
            
            result = facade.reload()
            assert result == {"reloaded": True}
    
    def test_validate(self):
        """Test validation"""
        with patch.object(ConfigRegistry, 'validate') as mock_validate:
            mock_validate.return_value = ["Error 1", "Error 2"]
            
            errors = facade.validate()
            assert errors == ["Error 1", "Error 2"]
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # Mock the registry get method
        test_data = {
            "gps_fees.monthly": Decimal("350"),
            "gps_fees.installation": Decimal("750"),
            "gps_fees.apply_iva": True,
            "payment_tiers.refresh_min": Decimal("-0.05"),
            "payment_tiers.refresh_max": Decimal("0.05"),
            "payment_tiers.upgrade_min": Decimal("0.05"),
            "payment_tiers.upgrade_max": Decimal("0.25"),
            "payment_tiers.max_upgrade_min": Decimal("0.25"),
            "payment_tiers.max_upgrade_max": Decimal("1.0"),
            "rates.A1": Decimal("0.1949"),
            "downpayment.0.12": Decimal("0.3"),
            "terms.search_order": [60, 72, 48, 36, 24, 12],
            "financial.iva_rate": Decimal("0.16"),
            "service_fees.service_percentage": Decimal("0.04"),
            "service_fees.cxa_percentage": Decimal("0.04"),
            "cac_bonus.default": Decimal("0"),
            "kavak_total.amount": Decimal("25000")
        }
        
        with patch.object(ConfigRegistry, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: test_data.get(key, default)
            
            # Test GPS fees
            gps_fees = facade.get_gps_fees()
            assert gps_fees["monthly"] == Decimal("350")
            assert gps_fees["installation"] == Decimal("750")
            assert gps_fees["apply_iva"] is True
            
            # Test payment tiers
            tiers = facade.get_payment_tiers()
            assert tiers["refresh"] == (-0.05, 0.05)
            assert tiers["upgrade"] == (0.05, 0.25)
            assert tiers["max_upgrade"] == (0.25, 1.0)
            
            # Test interest rate
            rate = facade.get_interest_rate("A1")
            assert rate == Decimal("0.1949")
            
            # Test down payment
            down = facade.get_down_payment(0, 12)
            assert down == Decimal("0.3")
            
            # Test term search order
            terms = facade.get_term_search_order()
            assert terms == [60, 72, 48, 36, 24, 12]
            
            # Test IVA rate
            iva = facade.get_iva_rate()
            assert iva == Decimal("0.16")
            
            # Test service fees
            fees = facade.get_service_fees()
            assert fees["service_fee_pct"] == Decimal("0.04")
            assert fees["cxa_pct"] == Decimal("0.04")
            assert fees["cac_bonus"] == Decimal("0")
            assert fees["kavak_total_amount"] == Decimal("25000")
    
    def test_get_config_value_alias(self):
        """Test backward compatibility alias"""
        assert facade.get_config_value is facade.get
    
    def test_singleton_registry(self):
        """Test that registry is a singleton"""
        # First call creates registry
        facade.get("test.key")
        registry1 = facade._registry
        
        # Second call reuses same registry
        facade.get("test.key2")
        registry2 = facade._registry
        
        assert registry1 is registry2
        assert registry1 is not None