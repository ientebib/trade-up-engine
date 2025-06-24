#!/usr/bin/env python3
"""
Test with user's exact values
"""
from engine.calculator import generate_amortization_table

# Create test offer that should give ~$5,591 payment
test_offer = {
    "loan_amount": 134332.46,
    "term": 72,
    "interest_rate": 0.18,
    "service_fee_amount": 4676.10,
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870,  # 750 * 1.16
    "monthly_payment": 5591.10  # User's expected payment
}

table = generate_amortization_table(test_offer)
first = table[0]

print("USER'S SCENARIO TEST")
print("="*60)
print(f"Expected payment: ${test_offer['monthly_payment']:,.2f}")
print(f"Calculated payment: ${first['payment']:,.2f}")
print()

print("COLUMN BREAKDOWN:")
print(f"Capital:   ${first['capital']:,.2f}")
print(f"Interés:   ${first['interes']:,.2f}")
print(f"Cargos:    ${first['cargos']:,.2f}")
print(f"IVA:       ${first['iva']:,.2f}")
print(f"---")
print(f"Sum:       ${first['capital'] + first['interes'] + first['cargos'] + first['iva']:,.2f}")
print(f"Exigible:  ${first['exigible']:,.2f}")
print(f"Matches?   {'YES ✓' if abs(first['exigible'] - (first['capital'] + first['interes'] + first['cargos'] + first['iva'])) < 0.01 else 'NO ✗'}")

# Also check what the actual monthly payment should be
from engine.payment_utils import calculate_monthly_payment

payment_calc = calculate_monthly_payment(
    loan_base=test_offer['loan_amount'] - test_offer['service_fee_amount'] - test_offer['kavak_total_amount'] - test_offer['insurance_amount'],
    service_fee_amount=test_offer['service_fee_amount'],
    kavak_total_amount=test_offer['kavak_total_amount'],
    insurance_amount=test_offer['insurance_amount'],
    annual_rate_nominal=test_offer['interest_rate'],
    term_months=test_offer['term'],
    gps_install_fee=test_offer['gps_install_fee']
)

print(f"\nPAYMENT CALCULATION CHECK:")
print(f"Calculated monthly payment: ${payment_calc['payment_total']:,.2f}")
print(f"User expects: ${test_offer['monthly_payment']:,.2f}")
print(f"Difference: ${abs(payment_calc['payment_total'] - test_offer['monthly_payment']):,.2f}")