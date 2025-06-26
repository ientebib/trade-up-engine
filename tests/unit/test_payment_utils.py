"""
Unit tests for payment utilities
"""
import os
os.environ['USE_NEW_CONFIG'] = 'true'  # Force new configuration system
import pytest
from engine.payment_utils import (
    calculate_monthly_payment,
    calculate_payment_components,
    calculate_final_npv
)


class TestPaymentUtils:
    """Test payment calculation utilities"""
    
    def test_calculate_monthly_payment_basic(self):
        """Test basic monthly payment calculation"""
        payment = calculate_monthly_payment(
            loan_base=100000,
            service_fee_amount=4000,
            kavak_total_amount=0,
            insurance_amount=10999,
            annual_rate_nominal=0.20,
            term_months=12,
            gps_install_fee=870
        )
        
        assert payment > 0
        assert isinstance(payment, dict)
        assert 'payment_total' in payment
        assert payment['payment_total'] > 0
    
    def test_calculate_payment_components(self):
        """Test payment component calculation"""
        components = calculate_payment_components(
            loan_amount=150000,
            rate=0.20,
            term=12,
            service_fee_amount=6000,
            kavak_total_amount=25000,
            insurance_amount=10999,
            gps_install_fee=870,
            is_first_month=True
        )
        
        assert 'capital' in components
        assert 'interest' in components
        assert 'iva_on_interest' in components
        assert 'gps_fee' in components
        assert 'total' in components
        
        # First month should include GPS installation
        assert components['gps_fee'] > 350  # More than just monthly fee
    
    def test_payment_with_all_fees(self):
        """Test payment calculation with all fees included"""
        payment = calculate_monthly_payment(
            loan_base=150000,
            service_fee_amount=6000,
            kavak_total_amount=25000,
            insurance_amount=10999,
            annual_rate_nominal=0.225,
            term_months=72,
            gps_install_fee=870
        )
        
        assert payment['payment_total'] > 0
        assert payment['iva_on_interest'] > 0
        
    def test_calculate_final_npv(self):
        """Test NPV calculation"""
        npv = calculate_final_npv(
            loan_amount=200000,
            interest_rate=0.20,
            term_months=36
        )
        
        # NPV should be a reasonable value
        assert isinstance(npv, (int, float))
        assert npv != 0
    
    def test_payment_increases_with_rate(self):
        """Test that payment increases with interest rate"""
        payment_low = calculate_monthly_payment(
            loan_base=100000,
            service_fee_amount=4000,
            kavak_total_amount=0,
            insurance_amount=10999,
            annual_rate_nominal=0.15,
            term_months=36,
            gps_install_fee=870
        )
        
        payment_high = calculate_monthly_payment(
            loan_base=100000,
            service_fee_amount=4000,
            kavak_total_amount=0,
            insurance_amount=10999,
            annual_rate_nominal=0.25,
            term_months=36,
            gps_install_fee=870
        )
        
        assert payment_high['payment_total'] > payment_low['payment_total']
    
    def test_payment_decreases_with_term(self):
        """Test that payment decreases with longer term"""
        payment_short = calculate_monthly_payment(
            loan_base=100000,
            service_fee_amount=4000,
            kavak_total_amount=0,
            insurance_amount=10999,
            annual_rate_nominal=0.20,
            term_months=12,
            gps_install_fee=870
        )
        
        payment_long = calculate_monthly_payment(
            loan_base=100000,
            service_fee_amount=4000,
            kavak_total_amount=0,
            insurance_amount=10999,
            annual_rate_nominal=0.20,
            term_months=60,
            gps_install_fee=870
        )
        
        assert payment_long['payment_total'] < payment_short['payment_total']