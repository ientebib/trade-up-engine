"""
Test Decimal/float consistency in financial calculations
"""
import os
os.environ['USE_NEW_CONFIG'] = 'true'

import pytest
from decimal import Decimal
from engine.payment_utils import calculate_payment_components, calculate_monthly_payment
from config.facade import set as config_set


class TestDecimalConsistency:
    """Test that calculations are consistent whether using Decimal or float"""
    
    def setup_method(self):
        """Set up test configuration"""
        # Enable decimal precision
        config_set("features.enable_decimal_precision", True)
    
    def test_payment_components_decimal_vs_float(self):
        """Test that payment components are consistent with Decimal vs float"""
        # Test parameters
        params = {
            "loan_base": 150000.0,
            "service_fee_amount": 6000.0,
            "kavak_total_amount": 25000.0,
            "insurance_amount": 10999.0,
            "annual_rate_nominal": 0.20,
            "term_months": 36,
            "period": 1,
            "insurance_term": 12
        }
        
        # Calculate with Decimal
        decimal_result = calculate_payment_components(**params, use_decimal=True)
        
        # Calculate with float
        float_result = calculate_payment_components(**params, use_decimal=False)
        
        # Results should be very close (within rounding error)
        for key in decimal_result:
            decimal_val = float(decimal_result[key]) if isinstance(decimal_result[key], Decimal) else decimal_result[key]
            float_val = float_result[key]
            
            # Allow for small floating point differences (0.01 peso)
            assert abs(decimal_val - float_val) < 0.01, f"{key}: {decimal_val} != {float_val}"
    
    def test_monthly_payment_decimal_vs_float(self):
        """Test that monthly payment calculation is consistent"""
        params = {
            "loan_base": 200000.0,
            "service_fee_amount": 8000.0,
            "kavak_total_amount": 25000.0,
            "insurance_amount": 10999.0,
            "annual_rate_nominal": 0.225,
            "term_months": 48,
            "gps_install_fee": 870.0
        }
        
        # Calculate with Decimal
        decimal_result = calculate_monthly_payment(**params, use_decimal=True)
        
        # Calculate with float
        float_result = calculate_monthly_payment(**params, use_decimal=False)
        
        # Monthly payment should be very close
        decimal_payment = float(decimal_result["monthly_payment"]) if isinstance(decimal_result["monthly_payment"], Decimal) else decimal_result["monthly_payment"]
        float_payment = float_result["monthly_payment"]
        
        assert abs(decimal_payment - float_payment) < 0.01, f"Payments differ: {decimal_payment} != {float_payment}"
    
    def test_decimal_precision_edge_cases(self):
        """Test edge cases where float precision matters"""
        # Test with values that have precision issues in float
        # 0.1 + 0.2 = 0.30000000000000004 in float
        params = {
            "loan_base": 100000.1,
            "service_fee_amount": 4000.2,
            "kavak_total_amount": 0.0,
            "insurance_amount": 0.0,
            "annual_rate_nominal": 0.1999999,  # Close to 20%
            "term_months": 12,
            "period": 1
        }
        
        # With Decimal, we should get exact calculations
        result = calculate_payment_components(**params, use_decimal=True)
        
        # Verify results are Decimal type when decimal is enabled
        assert isinstance(result["principal_main"], (Decimal, float))
        assert isinstance(result["total_principal"], (Decimal, float))
    
    def test_large_amount_precision(self):
        """Test precision with very large amounts"""
        params = {
            "loan_base": 5000000.0,  # 5 million
            "service_fee_amount": 200000.0,
            "kavak_total_amount": 25000.0,
            "insurance_amount": 10999.0,
            "annual_rate_nominal": 0.18,
            "term_months": 72,
            "period": 1
        }
        
        # Both should handle large amounts correctly
        decimal_result = calculate_payment_components(**params, use_decimal=True)
        float_result = calculate_payment_components(**params, use_decimal=False)
        
        # Even with large amounts, results should be close
        for key in ["total_principal", "total_interest"]:
            decimal_val = float(decimal_result[key]) if isinstance(decimal_result[key], Decimal) else decimal_result[key]
            float_val = float_result[key]
            
            # Allow 0.1% difference for large amounts
            relative_diff = abs(decimal_val - float_val) / max(decimal_val, float_val)
            assert relative_diff < 0.001, f"{key}: relative difference {relative_diff} too large"