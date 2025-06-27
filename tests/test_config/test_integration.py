"""Integration tests for the complete configuration system"""
import os
import json
import pytest
from decimal import Decimal
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

from config import facade
from config.registry import ConfigRegistry
from config.loaders.defaults import DefaultsLoader
from config.loaders.env import EnvLoader
from config.loaders.file import FileLoader


class TestConfigurationIntegration:
    """Test the integrated configuration system"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture(autouse=True)
    def reset_facade(self):
        """Reset facade state before each test"""
        facade._registry = None
        yield
        facade._registry = None
    
    def test_priority_override_chain(self, temp_config_dir):
        """Test that configuration sources override in correct priority order"""
        # Create base config file
        base_config = {
            "financial": {
                "iva_rate": "0.15"  # Will be overridden
            },
            "gps_fees": {
                "monthly": "300"  # Will be overridden
            },
            "insurance": {
                "amount": "10000"  # Will remain
            }
        }
        
        base_file = temp_config_dir / "base_config.json"
        with open(base_file, 'w') as f:
            json.dump(base_config, f)
        
        # Create override file (higher priority than base)
        override_config = {
            "financial": {
                "iva_rate": "0.17"  # Overrides base
            }
        }
        
        override_file = temp_config_dir / "engine_config.json"
        with open(override_file, 'w') as f:
            json.dump(override_config, f)
        
        # Set environment variable (higher priority than files)
        env_vars = {
            "GPS_FEES_MONTHLY": "400"  # Overrides base
        }
        
        with patch.dict(os.environ, env_vars):
            # Create custom registry with our loaders
            registry = ConfigRegistry([
                DefaultsLoader(),
                EnvLoader(),
                FileLoader(temp_config_dir)
            ])
            
            config = registry.load_all()
            
            # Check final values
            assert config["financial.iva_rate"] == Decimal("0.17")  # From override file
            assert config["gps_fees.monthly"] == Decimal("400")  # From env var
            assert config["insurance.amount"] == Decimal("10000")  # From base file
    
    def test_facade_with_real_loaders(self, temp_config_dir):
        """Test facade API with real configuration sources"""
        # Create test config
        config_data = {
            "system": {
                "max_concurrent_requests": 5,
                "cache_ttl_hours": 6.5
            },
            "features": {
                "enable_caching": True
            }
        }
        
        config_file = temp_config_dir / "base_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Mock the config directory
        with patch('config.loaders.file.Path') as mock_path:
            mock_path.return_value = temp_config_dir
            
            # Use facade
            assert facade.get_int("system.max_concurrent_requests") == 5
            assert facade.get_float("system.cache_ttl_hours") == 6.5
            assert facade.get_bool("features.enable_caching") is True
            
            # Test defaults from schema
            assert facade.get_decimal("financial.iva_rate") == Decimal("0.16")
            assert facade.get_list("terms.search_order") == [60, 72, 48, 36, 24, 12]
    
    def test_runtime_updates(self, temp_config_dir):
        """Test runtime configuration updates"""
        with patch('config.loaders.file.Path') as mock_path:
            mock_path.return_value = temp_config_dir
            
            # Initial value from defaults
            assert facade.get_decimal("gps_fees.monthly") == Decimal("350")
            
            # Update at runtime
            facade.set("gps_fees.monthly", Decimal("400"))
            
            # Should be updated
            assert facade.get_decimal("gps_fees.monthly") == Decimal("400")
            
            # Should be persisted to override file
            override_file = temp_config_dir / "engine_config.json"
            assert override_file.exists()
            
            with open(override_file) as f:
                saved_data = json.load(f)
            
            assert saved_data["gps_fees"]["monthly"] == "400"
    
    def test_configuration_shim_compatibility(self):
        """Test that ConfigurationManagerShim provides compatible API"""
        shim = ConfigurationManagerShim()
        
        # Test basic get methods
        iva_rate = shim.get("financial.iva_rate")
        assert isinstance(iva_rate, Decimal)
        
        # Test typed getters
        assert isinstance(shim.get_decimal("gps_fees.monthly"), Decimal)
        assert isinstance(shim.get_int("system.max_concurrent_requests"), int)
        assert isinstance(shim.get_bool("features.enable_caching"), bool)
        assert isinstance(shim.get_list("terms.search_order"), list)
        
        # Test other methods
        all_config = shim.get_all()
        assert isinstance(all_config, dict)
        assert len(all_config) > 0
        
        prefix_config = shim.get_by_prefix("financial")
        assert all(k.startswith("financial") for k in prefix_config.keys())
        
        # Test validation
        errors = shim.validate_config()
        assert isinstance(errors, list)
    
    def test_complete_workflow(self, temp_config_dir):
        """Test a complete configuration workflow"""
        # 1. Start with defaults
        with patch('config.loaders.file.Path') as mock_path:
            mock_path.return_value = temp_config_dir
            
            # Get default value
            default_iva = facade.get_decimal("financial.iva_rate")
            assert default_iva == Decimal("0.16")
            
            # 2. Override via environment
            with patch.dict(os.environ, {"FINANCIAL_IVA_RATE": "0.18"}):
                # Need to reload to pick up env change
                facade.reload()
                env_iva = facade.get_decimal("financial.iva_rate")
                assert env_iva == Decimal("0.18")
            
            # 3. Override via file
            override_config = {"financial": {"iva_rate": "0.20"}}
            override_file = temp_config_dir / "engine_config.json"
            with open(override_file, 'w') as f:
                json.dump(override_config, f)
            
            facade.reload()
            file_iva = facade.get_decimal("financial.iva_rate")
            assert file_iva == Decimal("0.20")
            
            # 4. Runtime update
            facade.set("financial.iva_rate", Decimal("0.22"))
            runtime_iva = facade.get_decimal("financial.iva_rate")
            assert runtime_iva == Decimal("0.22")
            
            # 5. Validate
            errors = facade.validate()
            # IVA rate of 0.22 should be valid (between 0 and 1)
            assert not any("financial.iva_rate" in error for error in errors)
    
    def test_backward_compatibility_imports(self):
        """Test that old import patterns still work"""
        # Old way
        from config.configuration_manager import get_config_value, get_gps_fees
        
        # Should work without errors
        iva = get_config_value("financial.iva_rate")
        assert isinstance(iva, Decimal)
        
        gps = get_gps_fees()
        assert "monthly" in gps
        assert "installation" in gps
    
    def test_performance_metrics(self):
        """Test that configuration loads within performance requirements"""
        import time
        
        # Reset to force fresh load
        facade._registry = None
        
        start_time = time.time()
        
        # First access triggers load
        facade.get("financial.iva_rate")
        
        load_time = time.time() - start_time
        
        # Should load in under 150ms
        assert load_time < 0.15, f"Configuration load took {load_time:.3f}s"
        
        # Subsequent access should be instant
        start_time = time.time()
        facade.get("gps_fees.monthly")
        access_time = time.time() - start_time
        
        assert access_time < 0.001, f"Configuration access took {access_time:.3f}s"