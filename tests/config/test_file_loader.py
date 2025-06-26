"""Tests for the file configuration loader"""
import json
import pytest
from decimal import Decimal
from pathlib import Path
import tempfile
import shutil

from config.loaders.file import FileLoader


class TestFileLoader:
    """Test the file configuration loader"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_loader_priority(self):
        """Test that file loader has correct priority"""
        loader = FileLoader()
        assert loader.PRIORITY == 2
        assert loader.name == "FileLoader"
    
    def test_load_base_config(self, temp_config_dir):
        """Test loading base configuration file"""
        base_config = {
            "financial": {
                "iva_rate": "0.17",
                "max_loan_amount": "5000000"
            },
            "gps_fees": {
                "monthly": "360",
                "installation": "760"
            }
        }
        
        base_file = temp_config_dir / "base_config.json"
        with open(base_file, 'w') as f:
            json.dump(base_config, f)
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        assert config["financial.iva_rate"] == Decimal("0.17")
        assert config["financial.max_loan_amount"] == Decimal("5000000")
        assert config["gps_fees.monthly"] == Decimal("360")
        assert config["gps_fees.installation"] == Decimal("760")
    
    def test_load_override_config(self, temp_config_dir):
        """Test loading override configuration file"""
        override_config = {
            "financial": {
                "iva_rate": "0.18"
            },
            "features": {
                "enable_caching": False
            }
        }
        
        override_file = temp_config_dir / "engine_config.json"
        with open(override_file, 'w') as f:
            json.dump(override_config, f)
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        assert config["financial.iva_rate"] == Decimal("0.18")
        assert config["features.enable_caching"] is False
    
    def test_override_precedence(self, temp_config_dir):
        """Test that override file takes precedence over base"""
        base_config = {
            "financial": {
                "iva_rate": "0.16",
                "max_loan_amount": "1000000"
            }
        }
        
        override_config = {
            "financial": {
                "iva_rate": "0.20"  # Override this value
            }
        }
        
        base_file = temp_config_dir / "base_config.json"
        override_file = temp_config_dir / "engine_config.json"
        
        with open(base_file, 'w') as f:
            json.dump(base_config, f)
        
        with open(override_file, 'w') as f:
            json.dump(override_config, f)
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        # Override should win
        assert config["financial.iva_rate"] == Decimal("0.20")
        # Base value should remain
        assert config["financial.max_loan_amount"] == Decimal("1000000")
    
    def test_save_override(self, temp_config_dir):
        """Test saving a configuration override"""
        loader = FileLoader(temp_config_dir)
        
        # Save some overrides
        assert loader.save_override("gps_fees.monthly", Decimal("400"))
        assert loader.save_override("features.enable_caching", False)
        assert loader.save_override("system.max_concurrent_requests", 5)
        
        # Verify file was created
        override_file = temp_config_dir / "engine_config.json"
        assert override_file.exists()
        
        # Verify content
        with open(override_file) as f:
            saved_data = json.load(f)
        
        assert saved_data["gps_fees"]["monthly"] == "400"  # Decimal saved as string
        assert saved_data["features"]["enable_caching"] is False
        assert saved_data["system"]["max_concurrent_requests"] == 5
    
    def test_save_override_preserves_existing(self, temp_config_dir):
        """Test that saving overrides preserves existing values"""
        # Create initial override file
        initial_data = {
            "financial": {
                "iva_rate": "0.18"
            }
        }
        
        override_file = temp_config_dir / "engine_config.json"
        with open(override_file, 'w') as f:
            json.dump(initial_data, f)
        
        loader = FileLoader(temp_config_dir)
        
        # Add new override
        loader.save_override("gps_fees.monthly", Decimal("380"))
        
        # Verify both values exist
        with open(override_file) as f:
            saved_data = json.load(f)
        
        assert saved_data["financial"]["iva_rate"] == "0.18"  # Preserved
        assert saved_data["gps_fees"]["monthly"] == "380"  # New
    
    def test_nested_config_flattening(self, temp_config_dir):
        """Test that nested configurations are properly flattened"""
        nested_config = {
            "financial": {
                "rates": {
                    "default": "0.25",
                    "special": {
                        "vip": "0.15"
                    }
                }
            },
            "payment_tiers": {
                "refresh": {
                    "min": "-0.10",
                    "max": "0.10"
                }
            }
        }
        
        base_file = temp_config_dir / "base_config.json"
        with open(base_file, 'w') as f:
            json.dump(nested_config, f)
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        assert config["financial.rates.default"] == Decimal("0.25")
        assert config["financial.rates.special.vip"] == Decimal("0.15")
        assert config["payment_tiers.refresh.min"] == Decimal("-0.10")
        assert config["payment_tiers.refresh.max"] == Decimal("0.10")
    
    def test_decimal_string_conversion(self, temp_config_dir):
        """Test that decimal strings are converted to Decimal objects"""
        config_data = {
            "values": {
                "decimal_with_dot": "123.45",
                "decimal_scientific": "1.23e-4",
                "integer_string": "123",
                "regular_string": "hello",
                "boolean": True,
                "list": [1, 2, 3]
            }
        }
        
        base_file = temp_config_dir / "base_config.json"
        with open(base_file, 'w') as f:
            json.dump(config_data, f)
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        assert config["values.decimal_with_dot"] == Decimal("123.45")
        assert config["values.decimal_scientific"] == Decimal("1.23e-4")
        assert config["values.integer_string"] == "123"  # Not converted (no decimal point)
        assert config["values.regular_string"] == "hello"
        assert config["values.boolean"] is True
        assert config["values.list"] == [1, 2, 3]
    
    def test_missing_files(self, temp_config_dir):
        """Test that missing files don't cause errors"""
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        # Should return empty dict
        assert config == {}
    
    def test_invalid_json(self, temp_config_dir):
        """Test handling of invalid JSON files"""
        base_file = temp_config_dir / "base_config.json"
        with open(base_file, 'w') as f:
            f.write("{ invalid json }")
        
        loader = FileLoader(temp_config_dir)
        config = loader.load()
        
        # Should handle gracefully and return empty
        assert config == {}