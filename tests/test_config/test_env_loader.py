"""Tests for the environment variable configuration loader"""
import os
import pytest
from decimal import Decimal
from unittest.mock import patch

from config.loaders.env import EnvLoader


class TestEnvLoader:
    """Test the environment variable loader"""
    
    def test_loader_priority(self):
        """Test that env loader has correct priority"""
        loader = EnvLoader()
        assert loader.PRIORITY == 3
        assert loader.name == "EnvLoader"
    
    def test_legacy_env_vars(self):
        """Test loading legacy KAVAK_* environment variables"""
        env_vars = {
            "KAVAK_IVA_RATE": "0.20",
            "KAVAK_GPS_MONTHLY": "400",
            "KAVAK_GPS_INSTALLATION": "800",
            "KAVAK_INSURANCE_AMOUNT": "12000",
            "KAVAK_SERVICE_FEE_PCT": "0.05",
            "KAVAK_ENABLE_CACHING": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            loader = EnvLoader()
            config = loader.load()
            
            assert config["financial.iva_rate"] == Decimal("0.20")
            assert config["gps_fees.monthly"] == Decimal("400")
            assert config["gps_fees.installation"] == Decimal("800")
            assert config["insurance.amount"] == Decimal("12000")
            assert config["service_fees.service_percentage"] == Decimal("0.05")
            assert config["features.enable_caching"] is True
    
    def test_structured_env_vars(self):
        """Test loading structured environment variables"""
        env_vars = {
            "FINANCIAL_IVA_RATE": "0.18",
            "GPS_FEES_MONTHLY": "375",
            "INSURANCE_AMOUNT": "11500",
            "SYSTEM_MAX_CONCURRENT_REQUESTS": "5",
            "FEATURES_ENABLE_DECIMAL_PRECISION": "false",
            "RATES_A1": "0.21",
            "DOWNPAYMENT_0_12": "0.35"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            loader = EnvLoader()
            config = loader.load()
            
            assert config["financial.iva_rate"] == Decimal("0.18")
            assert config["gps_fees.monthly"] == Decimal("375")
            assert config["insurance.amount"] == Decimal("11500")
            assert config["system.max_concurrent_requests"] == 5
            assert config["features.enable_decimal_precision"] is False
            assert config["rates.a1"] == Decimal("0.21")
            assert config["downpayment.0.12"] == Decimal("0.35")
    
    def test_type_parsing(self):
        """Test correct type parsing for different value types"""
        env_vars = {
            "FINANCIAL_MAX_INTEREST_RATE": "0.99",  # Decimal
            "SYSTEM_REQUEST_TIMEOUT_SECONDS": "600",  # Integer
            "SYSTEM_CACHE_TTL_HOURS": "6.5",  # Float
            "FEATURES_ENABLE_AUDIT_LOGGING": "yes",  # Boolean true
            "FEATURES_ENABLE_CACHING": "0",  # Boolean false
            "TERMS_SEARCH_ORDER": "[72, 60, 48, 36, 24, 12]"  # List
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            loader = EnvLoader()
            config = loader.load()
            
            assert config["financial.max_interest_rate"] == Decimal("0.99")
            assert config["system.request_timeout_seconds"] == 600
            assert isinstance(config["system.request_timeout_seconds"], int)
            assert config["system.cache_ttl_hours"] == 6.5
            assert isinstance(config["system.cache_ttl_hours"], float)
            assert config["features.enable_audit_logging"] is True
            assert config["features.enable_caching"] is False
            assert config["terms.search_order"] == [72, 60, 48, 36, 24, 12]
    
    def test_boolean_parsing(self):
        """Test various boolean string representations"""
        true_values = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]
        false_values = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF", "anything"]
        
        for val in true_values:
            with patch.dict(os.environ, {"FEATURES_ENABLE_CACHING": val}, clear=True):
                loader = EnvLoader()
                config = loader.load()
                assert config.get("features.enable_caching") is True, f"Failed for {val}"
        
        for val in false_values:
            with patch.dict(os.environ, {"FEATURES_ENABLE_CACHING": val}, clear=True):
                loader = EnvLoader()
                config = loader.load()
                assert config.get("features.enable_caching") is False, f"Failed for {val}"
    
    def test_invalid_values_logged(self):
        """Test that invalid values are handled gracefully"""
        env_vars = {
            "FINANCIAL_IVA_RATE": "not-a-number",
            "SYSTEM_MAX_CONCURRENT_REQUESTS": "abc",
            "TERMS_SEARCH_ORDER": "invalid-json"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            loader = EnvLoader()
            # Should not raise exception
            config = loader.load()
            # Invalid values should not be in config
            assert len(config) == 0
    
    def test_empty_environment(self):
        """Test loading with no environment variables set"""
        with patch.dict(os.environ, {}, clear=True):
            loader = EnvLoader()
            config = loader.load()
            assert config == {}
    
    def test_mixed_legacy_and_structured(self):
        """Test that both legacy and structured vars can coexist"""
        env_vars = {
            # Legacy
            "KAVAK_IVA_RATE": "0.16",
            "KAVAK_GPS_MONTHLY": "350",
            # Structured
            "INSURANCE_TERM_MONTHS": "18",
            "FEATURES_ENABLE_PAYMENT_VALIDATION": "true"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            loader = EnvLoader()
            config = loader.load()
            
            # Both should be loaded
            assert config["financial.iva_rate"] == Decimal("0.16")
            assert config["gps_fees.monthly"] == Decimal("350")
            assert config["insurance.term_months"] == 18
            assert config["features.enable_payment_validation"] is True