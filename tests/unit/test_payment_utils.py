"""
Unit tests for payment utilities
"""
import pytest
from engine.payment_utils import (
    calculate_monthly_payment_with_fees,
    calculate_loan_components
)


class TestPaymentUtils:
    """Test payment calculation utilities"""
    
    def test_calculate_monthly_payment_basic(self):
        """Test basic monthly payment calculation"""
        payment = calculate_monthly_payment_with_fees(
            principal=100000,
            annual_rate=0.20,
            term_months=12,
            fees={'service_fee': 4000, 'kavak_total': 0}
        )
        
        assert payment > 0
        assert isinstance(payment, (int, float))
    
    def test_calculate_loan_components(self):
        """Test loan component calculation"""
        components = calculate_loan_components(
            car_price=200000,
            down_payment=40000,
            equity=50000,
            fees={
                'service_fee_amount': 8000,
                'kavak_total_amount': 25000,
                'insurance_amount': 10999
            }
        )
        
        assert 'total_financed' in components
        assert 'financed_main' in components
        assert 'equity_to_finance' in components
        
        # Total financed should include all components
        assert components['total_financed'] > 0
        assert components['financed_main'] > 0
    
    def test_payment_with_all_fees(self):
        """Test payment calculation with all fees included"""
        payment = calculate_monthly_payment_with_fees(
            principal=150000,
            annual_rate=0.225,
            term_months=72,
            fees={
                'service_fee': 6000,
                'kavak_total': 25000,
                'insurance': 10999,
                'gps_monthly': 350,
                'gps_installation': 750
            }
        )
        
        assert payment > 0
        # Payment should be higher with fees
        payment_no_fees = calculate_monthly_payment_with_fees(
            principal=150000,
            annual_rate=0.225,
            term_months=72,
            fees={'service_fee': 0, 'kavak_total': 0}
        )
        
        assert payment > payment_no_fees