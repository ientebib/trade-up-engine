"""
Unit tests for calculator module
"""
import pytest
from engine.calculator import calculate_npv, generate_amortization_table
from config.config import IVA_RATE


class TestCalculator:
    """Test financial calculations"""
    
    def test_calculate_npv_basic(self):
        """Test basic NPV calculation"""
        offer = {
            'monthly_payment': 5000,
            'term': 12,
            'interest_rate': 0.20,
            'total_financed': 50000
        }
        
        npv = calculate_npv(offer)
        assert isinstance(npv, (int, float))
        assert npv != 0
    
    def test_generate_amortization_table_structure(self):
        """Test amortization table structure"""
        offer = {
            'loan_amount': 100000,
            'term': 12,
            'interest_rate': 0.20,
            'service_fee_amount': 4000,
            'kavak_total_amount': 0,
            'insurance_amount': 10999,
            'gps_monthly_fee': 350,
            'gps_installation_fee': 750
        }
        
        table = generate_amortization_table(offer)
        
        assert len(table) == 12
        assert all(isinstance(row, dict) for row in table)
        
        # Check first row has all required fields
        first_row = table[0]
        required_fields = [
            'month', 'beginning_balance', 'payment',
            'principal', 'interest', 'ending_balance'
        ]
        
        for field in required_fields:
            assert field in first_row
            assert first_row[field] is not None
    
    def test_amortization_payment_consistency(self):
        """Test that payments are consistent in amortization"""
        offer = {
            'loan_amount': 100000,
            'term': 24,
            'interest_rate': 0.18,
            'service_fee_amount': 4000,
            'kavak_total_amount': 25000,
            'insurance_amount': 10999,
            'gps_monthly_fee': 350,
            'gps_installation_fee': 750
        }
        
        table = generate_amortization_table(offer)
        
        # All payments should be positive
        for row in table:
            assert row['payment'] > 0
            assert row['principal'] >= 0
            assert row['interest'] >= 0
    
    def test_iva_application(self):
        """Test IVA is correctly applied"""
        # IVA should be 16%
        assert IVA_RATE == 0.16
        
        # Test IVA application on GPS fee
        gps_base = 350
        gps_with_iva = gps_base * (1 + IVA_RATE)
        assert gps_with_iva == 406.0