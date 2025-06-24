#!/usr/bin/env python3
"""
Test payment difference with/without Kavak Total
"""
from engine.calculator import calculate_final_npv
from engine.payment_utils import calculate_monthly_payment

# Test parameters
loan_base = 90000  # After down payment
service_fee = 3600  # 4% of 90k
annual_rate = 0.18
term = 48

print("TESTING KAVAK TOTAL IMPACT ON MONTHLY PAYMENT")
print("="*50)
print(f"Base loan: ${loan_base:,.0f}")
print(f"Service fee: ${service_fee:,.0f}")
print(f"Interest rate: {annual_rate*100:.0f}%")
print(f"Term: {term} months")
print()

# With Kavak Total
payment_with_kt = calculate_monthly_payment(
    loan_base=loan_base,
    service_fee_amount=service_fee,
    kavak_total_amount=25000,
    insurance_amount=10999,
    annual_rate_nominal=annual_rate,
    term_months=term,
    gps_install_fee=870
)

print("WITH KAVAK TOTAL ($25,000):")
print(f"  Total financed: ${loan_base + service_fee + 25000 + 10999:,.0f}")
print(f"  Monthly payment: ${payment_with_kt['payment_total']:,.2f}")

# Without Kavak Total
payment_no_kt = calculate_monthly_payment(
    loan_base=loan_base,
    service_fee_amount=service_fee,
    kavak_total_amount=0,
    insurance_amount=10999,
    annual_rate_nominal=annual_rate,
    term_months=term,
    gps_install_fee=870
)

print("\nWITHOUT KAVAK TOTAL ($0):")
print(f"  Total financed: ${loan_base + service_fee + 0 + 10999:,.0f}")
print(f"  Monthly payment: ${payment_no_kt['payment_total']:,.2f}")

print(f"\nDIFFERENCE:")
print(f"  Payment increase: ${payment_with_kt['payment_total'] - payment_no_kt['payment_total']:,.2f}/month")
print(f"  Percentage increase: {((payment_with_kt['payment_total'] / payment_no_kt['payment_total']) - 1) * 100:.1f}%")