"""Tests for the defaults configuration loader"""
import pytest
from decimal import Decimal

from config.loaders.defaults import DefaultsLoader


class TestDefaultsLoader:
    """Test the defaults loader"""
    
    def test_loader_priority(self):
        """Test that defaults loader has lowest priority"""
        loader = DefaultsLoader()
        assert loader.PRIORITY == 4
        assert loader.name == "DefaultsLoader"
    
    def test_load_defaults(self):
        """Test loading default values"""
        loader = DefaultsLoader()
        config = loader.load()
        
        # Check some key defaults are present
        assert "financial.iva_rate" in config
        assert config["financial.iva_rate"] == Decimal("0.16")
        
        assert "gps_fees.monthly" in config
        assert config["gps_fees.monthly"] == Decimal("350.0")
        
        assert "features.enable_caching" in config
        assert config["features.enable_caching"] is True
    
    def test_downpayment_matrix(self):
        """Test that downpayment matrix is loaded correctly"""
        loader = DefaultsLoader()
        config = loader.load()
        
        # Check specific downpayment values
        assert config["downpayment.0.12"] == Decimal("0.3")
        assert config["downpayment.1.24"] == Decimal("0.25")
        assert config["downpayment.25.72"] == Decimal("0.9999")
        
        # Check all profiles and terms are present
        for profile in range(26):
            for term in [12, 24, 36, 48, 60, 72]:
                key = f"downpayment.{profile}.{term}"
                assert key in config
                assert isinstance(config[key], Decimal)
    
    def test_all_rates_present(self):
        """Test that all risk profile rates are loaded"""
        loader = DefaultsLoader()
        config = loader.load()
        
        expected_profiles = [
            "AAA", "AA", "A", "A1", "A2", "B", "C1", "C2", "C3",
            "D1", "D2", "D3", "E1", "E2", "E3", "E4", "E5",
            "F1", "F2", "F3", "F4", "B_SB", "C1_SB", "C2_SB", "E5_SB", "Z"
        ]
        
        for profile in expected_profiles:
            key = f"rates.{profile}"
            assert key in config
            assert isinstance(config[key], Decimal)
            assert Decimal("0") < config[key] <= Decimal("1")
    
    def test_payment_tiers(self):
        """Test payment tier defaults"""
        loader = DefaultsLoader()
        config = loader.load()
        
        # Refresh tier
        assert config["payment_tiers.refresh_min"] == Decimal("-0.05")
        assert config["payment_tiers.refresh_max"] == Decimal("0.05")
        
        # Upgrade tier
        assert config["payment_tiers.upgrade_min"] == Decimal("0.05")
        assert config["payment_tiers.upgrade_max"] == Decimal("0.25")
        
        # Max upgrade tier
        assert config["payment_tiers.max_upgrade_min"] == Decimal("0.25")
        assert config["payment_tiers.max_upgrade_max"] == Decimal("1.0")
    
    def test_system_defaults(self):
        """Test system configuration defaults"""
        loader = DefaultsLoader()
        config = loader.load()
        
        assert config["system.max_concurrent_requests"] == 3
        assert config["system.request_timeout_seconds"] == 300
        assert config["system.cache_ttl_hours"] == 4.0
        assert config["system.max_customers_per_bulk"] == 50
    
    def test_all_values_have_correct_types(self):
        """Test that all values have appropriate types"""
        loader = DefaultsLoader()
        config = loader.load()
        
        for key, value in config.items():
            # Decimal fields
            if any(k in key for k in ["rate", "percentage", "amount", "fee", "bonus", "min", "max", "downpayment"]):
                assert isinstance(value, Decimal), f"{key} should be Decimal, got {type(value)}"
            
            # Integer fields
            elif any(k in key for k in ["months", "seconds", "requests", "customers"]) and "hours" not in key:
                assert isinstance(value, int), f"{key} should be int, got {type(value)}"
            
            # Float fields (only cache_ttl_hours)
            elif "hours" in key:
                assert isinstance(value, float), f"{key} should be float, got {type(value)}"
            
            # Boolean fields
            elif any(k in key for k in ["enable", "apply"]):
                assert isinstance(value, bool), f"{key} should be bool, got {type(value)}"
            
            # List fields
            elif "search_order" in key:
                assert isinstance(value, list), f"{key} should be list, got {type(value)}"