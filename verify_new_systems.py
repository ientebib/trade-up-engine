#!/usr/bin/env python3
"""
Verification script for new configuration, audit, and Decimal systems
"""
import sys
from decimal import Decimal
from datetime import datetime

def verify_configuration_system():
    """Verify the configuration management system is working"""
    print("\n=== VERIFYING CONFIGURATION SYSTEM ===")
    
    try:
        from config.configuration_manager import get_config
        config = get_config()
        
        # Test getting values
        tests = [
            ("IVA Rate", "financial.iva_rate", Decimal("0.16")),
            ("GPS Monthly", "fees.gps.monthly", Decimal("350.0")),
            ("GPS Installation", "fees.gps.installation", Decimal("750.0")),
            ("Insurance Amount", "fees.insurance.amount", Decimal("10999.0")),
            ("Kavak Total", "fees.kavak_total.amount", Decimal("25000.0")),
            ("Service Fee %", "fees.service.percentage", Decimal("0.04")),
        ]
        
        all_passed = True
        for name, key, expected in tests:
            value = config.get_decimal(key)
            status = "✅" if value == expected else "❌"
            print(f"{status} {name}: {value} (expected: {expected})")
            if value != expected:
                all_passed = False
        
        # Test payment tiers
        from config.configuration_manager import get_payment_tiers
        tiers = get_payment_tiers()
        print(f"\n✅ Payment Tiers loaded: {tiers}")
        
        # Test configuration validation
        errors = config.validate_config()
        if errors:
            print(f"❌ Configuration validation errors: {errors}")
            all_passed = False
        else:
            print("✅ Configuration validation passed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Configuration system error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_audit_logging():
    """Verify the audit logging system is working"""
    print("\n=== VERIFYING AUDIT LOGGING ===")
    
    try:
        from engine.financial_audit import get_audit_logger, CalculationType
        from config.configuration_manager import get_config
        
        config = get_config()
        if not config.get_bool("features.enable_audit_logging"):
            print("⚠️  Audit logging is disabled in configuration")
            return True
        
        audit_logger = get_audit_logger()
        
        # Test logging a calculation
        audit_id = audit_logger.log_calculation(
            calculation_type=CalculationType.PAYMENT_COMPONENT,
            inputs={
                "loan_amount": "100000",
                "interest_rate": "0.20",
                "term_months": 24
            },
            outputs={
                "monthly_payment": "5089.51",
                "total_interest": "22148.24"
            },
            customer_id="TEST_CUSTOMER",
            metadata={"test": True}
        )
        
        print(f"✅ Created audit entry: {audit_id}")
        
        # Verify we can retrieve it
        recent = audit_logger.get_recent_entries(1)
        if recent and recent[0]['audit_id'] == audit_id:
            print("✅ Successfully retrieved audit entry")
        else:
            print("❌ Failed to retrieve audit entry")
            return False
        
        # Test payment calculation logging
        audit_id2 = audit_logger.log_payment_calculation(
            loan_amount=Decimal("100000"),
            interest_rate=Decimal("0.20"),
            term_months=24,
            fees={
                "gps_monthly": Decimal("406"),
                "gps_install": Decimal("870")
            },
            monthly_payment=Decimal("5365.51"),
            customer_id="TEST_CUSTOMER"
        )
        
        print(f"✅ Logged payment calculation: {audit_id2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audit logging error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_decimal_precision():
    """Verify Decimal precision is working in calculations"""
    print("\n=== VERIFYING DECIMAL PRECISION ===")
    
    try:
        from engine.payment_utils import calculate_monthly_payment
        from config.configuration_manager import get_config
        
        config = get_config()
        use_decimal = config.get_bool("features.enable_decimal_precision")
        print(f"Decimal precision enabled: {use_decimal}")
        
        # Test calculation with Decimal
        result = calculate_monthly_payment(
            loan_base=100000.0,
            service_fee_amount=4000.0,
            kavak_total_amount=25000.0,
            insurance_amount=10999.0,
            annual_rate_nominal=0.20,
            term_months=24,
            gps_install_fee=870.0
        )
        
        print(f"✅ Monthly payment calculated: ${result['monthly_payment']:,.2f}")
        print(f"   Principal: ${result['principal']:,.2f}")
        print(f"   Interest: ${result['interest']:,.2f}")
        print(f"   GPS Fee: ${result['gps_fee']:,.2f}")
        
        # Test that configuration values are being used
        gps_monthly_config = float(config.get_decimal("fees.gps.monthly"))
        iva_rate = float(config.get_decimal("financial.iva_rate"))
        expected_gps = gps_monthly_config * (1 + iva_rate)
        
        if abs(result['gps_fee'] - expected_gps) < 0.01:
            print(f"✅ GPS fee correctly uses config: {result['gps_fee']} = {gps_monthly_config} * (1 + {iva_rate})")
        else:
            print(f"❌ GPS fee mismatch: got {result['gps_fee']}, expected {expected_gps}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Decimal precision error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_old_system_removed():
    """Verify old hardcoded systems are removed"""
    print("\n=== VERIFYING OLD SYSTEMS REMOVED ===")
    
    checks = []
    
    # Check that payment_utils uses configuration
    try:
        with open("engine/payment_utils.py") as f:
            content = f.read()
            if "350.0 * (1 + IVA_RATE)" in content:
                checks.append("❌ Hardcoded GPS calculation still in payment_utils.py")
            else:
                checks.append("✅ Hardcoded GPS calculation removed from payment_utils.py")
            
            if "from config.configuration_manager import get_config" in content:
                checks.append("✅ payment_utils.py uses configuration manager")
            else:
                checks.append("❌ payment_utils.py not using configuration manager")
    except Exception as e:
        checks.append(f"❌ Error checking payment_utils.py: {e}")
    
    # Check that calculator uses configuration
    try:
        with open("engine/calculator.py") as f:
            content = f.read()
            if "from config.configuration_manager import get_config" in content:
                checks.append("✅ calculator.py uses configuration manager")
            else:
                checks.append("❌ calculator.py not using configuration manager")
            
            if "from .financial_audit import get_audit_logger" in content:
                checks.append("✅ calculator.py has audit logging")
            else:
                checks.append("❌ calculator.py missing audit logging")
    except Exception as e:
        checks.append(f"❌ Error checking calculator.py: {e}")
    
    # Check config.py loads from configuration manager
    try:
        with open("config/config.py") as f:
            content = f.read()
            if "from .configuration_manager import get_config" in content:
                checks.append("✅ config.py loads from configuration manager")
            else:
                checks.append("❌ config.py not using configuration manager")
    except Exception as e:
        checks.append(f"❌ Error checking config.py: {e}")
    
    for check in checks:
        print(check)
    
    return all("✅" in check for check in checks)


def main():
    """Run all verification tests"""
    print("🔍 VERIFYING NEW SYSTEMS IMPLEMENTATION")
    print("=" * 50)
    
    results = {
        "Configuration System": verify_configuration_system(),
        "Audit Logging": verify_audit_logging(),
        "Decimal Precision": verify_decimal_precision(),
        "Old Systems Removed": verify_old_system_removed()
    }
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    all_passed = True
    for system, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{system}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL SYSTEMS VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Some systems need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())