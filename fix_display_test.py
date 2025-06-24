#!/usr/bin/env python3
"""
Test fix for display columns
"""
from engine.calculator import generate_amortization_table

# Test offer
test_offer = {
    "loan_amount": 134332.46,
    "term": 72,
    "interest_rate": 0.18,
    "service_fee_amount": 4676.10,
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870
}

# Generate table
table = generate_amortization_table(test_offer)
first = table[0]

print("CHECKING FIRST MONTH:")
print(f"Capital: ${first['capital']:,.2f}")
print(f"Interés: ${first['interes']:,.2f}")  
print(f"IVA: ${first['iva']:,.2f}")
print(f"Cargos: ${first['cargos']:,.2f}")
print(f"---")
print(f"Sum: ${first['capital'] + first['interes'] + first['iva'] + first['cargos']:,.2f}")
print(f"Exigible: ${first['exigible']:,.2f}")
print(f"Difference: ${abs(first['exigible'] - (first['capital'] + first['interes'] + first['iva'] + first['cargos'])):,.2f}")

# Check internal fields
print("\nINTERNAL FIELDS:")
print(f"payment: ${first['payment']:,.2f}")
print(f"principal: ${first['principal']:,.2f}")
print(f"interest (with IVA): ${first['interest']:,.2f}")

# Let's see what the exact issue is
print("\nDEBUG VALUES:")
print(f"end_balance_main: ${first['end_balance_main']:,.2f}")
print(f"end_balance_service_fee: ${first['end_balance_service_fee']:,.2f}")
print(f"end_balance_kavak_total: ${first['end_balance_kavak_total']:,.2f}")
print(f"end_balance_insurance: ${first['end_balance_insurance']:,.2f}")