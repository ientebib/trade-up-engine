#!/usr/bin/env python3
"""
Debug script to verify amortization calculations
"""
import json
from engine.calculator import generate_amortization_table

# Test offer
test_offer = {
    "loan_amount": 134332.46,
    "term": 72,
    "interest_rate": 0.18,  # 18% annual
    "service_fee_amount": 5000,
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870  # 750 * 1.16
}

print("Testing amortization with offer:")
print(json.dumps(test_offer, indent=2))
print("\n" + "="*50 + "\n")

# Generate table
table = generate_amortization_table(test_offer)

# Check first month
first_month = table[0]
print("FIRST MONTH BREAKDOWN:")
print(f"Capital: ${first_month['capital']:,.2f}")
print(f"Interés: ${first_month['interes']:,.2f}")
print(f"Cargos: ${first_month['cargos']:,.2f}")
print(f"IVA: ${first_month['iva']:,.2f}")
print(f"---")
print(f"SUM: ${first_month['capital'] + first_month['interes'] + first_month['cargos'] + first_month['iva']:,.2f}")
print(f"Exigible: ${first_month['exigible']:,.2f}")
print(f"DIFFERENCE: ${first_month['exigible'] - (first_month['capital'] + first_month['interes'] + first_month['cargos'] + first_month['iva']):,.2f}")

print("\n" + "="*50 + "\n")

# Show what the payment calculation actually uses
print("INTERNAL CALCULATION:")
print(f"Payment field: ${first_month['payment']:,.2f}")
print(f"Principal field: ${first_month['principal']:,.2f}")
print(f"Interest field (with IVA): ${first_month['interest']:,.2f}")