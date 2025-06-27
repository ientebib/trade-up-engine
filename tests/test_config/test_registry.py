"""Tests for the configuration registry"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from config.registry import ConfigRegistry
from config.loaders.base import BaseLoader


class MockLoader(BaseLoader):
    """Mock loader for testing"""
    
    def __init__(self, priority, data):
        self.PRIORITY = priority
        self.data = data
        self.load_called = False
    
    def load(self):
        self.load_called = True
        return self.data


class TestConfigRegistry:
    """Test the configuration registry"""
    
    def test_default_loaders(self):
        """Test that default loaders are initialized correctly"""
        registry = ConfigRegistry()
        
        # Should have 4 default loaders
        assert len(registry.loaders) == 4
        
        # Check they're sorted by priority (reverse for merging)
        priorities = [loader.PRIORITY for loader in registry.loaders]
        assert priorities == [4, 3, 2, 1]  # Defaults, Env, File, Database
    
    def test_custom_loaders(self):
        """Test using custom loaders"""
        loader1 = MockLoader(1, {"key1": "value1"})
        loader2 = MockLoader(2, {"key2": "value2"})
        
        registry = ConfigRegistry([loader1, loader2])
        
        assert len(registry.loaders) == 2
        # Should be sorted by priority (reverse)
        assert registry.loaders[0] is loader2  # Priority 2 comes first
        assert registry.loaders[1] is loader1  # Priority 1 comes second
    
    def test_load_all_merging(self):
        """Test that configurations are merged correctly by priority"""
        # Lower priority (loaded first)
        loader1 = MockLoader(3, {
            "key1": "value1_low",
            "key2": "value2_low",
            "key3": "value3_low"
        })
        
        # Higher priority (loaded second, overwrites)
        loader2 = MockLoader(1, {
            "key1": "value1_high",  # Overwrites
            "key4": "value4_high"   # New key
        })
        
        registry = ConfigRegistry([loader1, loader2])
        config = registry.load_all()
        
        # Both loaders should be called
        assert loader1.load_called
        assert loader2.load_called
        
        # Higher priority should overwrite
        assert config["key1"] == "value1_high"
        # Lower priority values remain
        assert config["key2"] == "value2_low"
        assert config["key3"] == "value3_low"
        # New keys from higher priority
        assert config["key4"] == "value4_high"
    
    def test_get_value(self):
        """Test getting configuration values"""
        loader = MockLoader(1, {"test.key": "test_value"})
        registry = ConfigRegistry([loader])
        
        # First get should trigger load
        value = registry.get("test.key")
        assert value == "test_value"
        assert loader.load_called
        
        # Default value
        assert registry.get("missing.key", "default") == "default"
    
    def test_get_all(self):
        """Test getting all configuration values"""
        data = {"key1": "value1", "key2": "value2"}
        loader = MockLoader(1, data)
        registry = ConfigRegistry([loader])
        
        all_config = registry.get_all()
        assert all_config == data
        # Should be a copy
        all_config["key3"] = "value3"
        assert "key3" not in registry._config
    
    def test_get_by_prefix(self):
        """Test getting values by prefix"""
        loader = MockLoader(1, {
            "financial.iva_rate": Decimal("0.16"),
            "financial.max_loan": 1000000,
            "gps_fees.monthly": 350,
            "gps_fees.installation": 750
        })
        
        registry = ConfigRegistry([loader])
        
        financial_config = registry.get_by_prefix("financial")
        assert len(financial_config) == 2
        assert financial_config["financial.iva_rate"] == Decimal("0.16")
        assert financial_config["financial.max_loan"] == 1000000
        
        gps_config = registry.get_by_prefix("gps_fees")
        assert len(gps_config) == 2
        assert gps_config["gps_fees.monthly"] == 350
    
    def test_set_value(self):
        """Test setting configuration values"""
        loader = MockLoader(1, {"existing": "value"})
        registry = ConfigRegistry([loader])
        
        # Load initial config
        registry.load_all()
        
        # Set new value
        registry.set("new.key", "new_value", persist=False)
        assert registry.get("new.key") == "new_value"
        
        # Update existing value
        registry.set("existing", "updated", persist=False)
        assert registry.get("existing") == "updated"
    
    def test_reload(self):
        """Test reloading configuration"""
        # Use a loader that returns different data each time
        call_count = 0
        def dynamic_load():
            nonlocal call_count
            call_count += 1
            return {f"key{call_count}": f"value{call_count}"}
        
        loader = MockLoader(1, {})
        loader.load = dynamic_load
        
        registry = ConfigRegistry([loader])
        
        # First load
        config1 = registry.load_all()
        assert config1 == {"key1": "value1"}
        
        # Reload
        config2 = registry.reload()
        assert config2 == {"key2": "value2"}
        assert call_count == 2
    
    def test_validate_missing_required(self):
        """Test validation detects missing required keys"""
        loader = MockLoader(1, {
            "financial.iva_rate": Decimal("0.16"),
            # Missing other required keys
        })
        
        registry = ConfigRegistry([loader])
        errors = registry.validate()
        
        assert len(errors) > 0
        assert any("gps_fees.monthly" in error for error in errors)
        assert any("insurance.amount" in error for error in errors)
    
    def test_validate_out_of_range(self):
        """Test validation detects out of range values"""
        loader = MockLoader(1, {
            "financial.iva_rate": Decimal("1.5"),  # Too high
            "payment_tiers.refresh_min": Decimal("0.1"),  # Should be negative
            "gps_fees.monthly": Decimal("350"),
            "gps_fees.installation": Decimal("750"),
            "insurance.amount": Decimal("10999")
        })
        
        registry = ConfigRegistry([loader])
        errors = registry.validate()
        
        assert any("financial.iva_rate" in error and "outside valid range" in error for error in errors)
        assert any("payment_tiers.refresh_min" in error for error in errors)
    
    def test_get_source_info(self):
        """Test getting information about configuration sources"""
        loader1 = MockLoader(1, {})
        loader2 = MockLoader(2, {})
        
        registry = ConfigRegistry([loader1, loader2])
        info = registry.get_source_info()
        
        assert len(info) == 2
        assert info[0]["name"] == "MockLoader"
        assert info[0]["priority"] == 2
        assert info[1]["priority"] == 1
    
    def test_loader_error_handling(self):
        """Test that loader errors are handled gracefully"""
        # Create a loader that raises an exception
        bad_loader = MockLoader(1, {})
        bad_loader.load = Mock(side_effect=Exception("Load failed"))
        
        good_loader = MockLoader(2, {"key": "value"})
        
        registry = ConfigRegistry([bad_loader, good_loader])
        config = registry.load_all()
        
        # Should still get config from good loader
        assert config == {"key": "value"}
        # Bad loader should have been called
        bad_loader.load.assert_called_once()
    
    def test_lazy_loading(self):
        """Test that configuration is loaded lazily"""
        loader = MockLoader(1, {"key": "value"})
        registry = ConfigRegistry([loader])
        
        # Should not be loaded yet
        assert not loader.load_called
        assert not registry._loaded
        
        # First access triggers load
        value = registry.get("key")
        assert loader.load_called
        assert registry._loaded
        assert value == "value"