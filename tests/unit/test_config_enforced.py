"""
Test to ensure new configuration system is always used
"""
import os
import pytest


def test_new_config_is_enforced():
    """Ensure USE_NEW_CONFIG is not set to false"""
    use_new_config = os.getenv("USE_NEW_CONFIG", "true")
    assert use_new_config.lower() not in ("false", "0", "no"), \
        "Legacy configuration system detected! USE_NEW_CONFIG must be true or unset."


def test_legacy_files_removed():
    """Ensure legacy configuration files are removed"""
    legacy_files = [
        "config/configuration_manager.py",
        "config/legacy/configuration_manager.py",
        "config/legacy/configuration_shim.py"
    ]
    
    for file_path in legacy_files:
        assert not os.path.exists(file_path), \
            f"Legacy file {file_path} still exists! Remove all legacy configuration files."


def test_config_imports_work():
    """Test that configuration imports work correctly"""
    # These imports should all work without error
    from config import (
        get_config_value,
        get_decimal,
        get_int,
        get_bool,
        get_list,
        get_gps_fees,
        get_payment_tiers,
        get_interest_rate,
        get_down_payment,
        set_config_value,
        reload_config,
        validate_config
    )
    
    # Test basic functionality
    assert callable(get_decimal)
    assert callable(get_int)
    assert callable(get_bool)
    
    # Test getting some values
    iva_rate = get_decimal("financial.iva_rate")
    assert iva_rate is not None
    assert float(iva_rate) == 0.16
    
    gps_fees = get_gps_fees()
    assert isinstance(gps_fees, dict)
    assert "monthly" in gps_fees
    assert "installation" in gps_fees


def test_facade_direct_imports():
    """Test direct imports from facade work"""
    from config.facade import (
        get,
        get_decimal,
        get_int,
        get_bool,
        get_by_prefix,
        get_payment_tiers,
        get_interest_rate
    )
    
    # Test getting configuration by prefix
    financial_config = get_by_prefix("financial")
    assert isinstance(financial_config, dict)
    assert len(financial_config) > 0
    
    # Test payment tiers
    tiers = get_payment_tiers()
    assert isinstance(tiers, dict)
    assert "refresh" in tiers
    assert "upgrade" in tiers
    assert "max_upgrade" in tiers
    
    # Test interest rate
    rate = get_interest_rate("A1")
    assert rate is not None
    assert float(rate) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])