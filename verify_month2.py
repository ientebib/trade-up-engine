#!/usr/bin/env python3
"""
Verify month 2 matches Excel
"""
from engine.calculator import generate_amortization_table

# Test with exact Excel values
test_offer = {
    "loan_amount": 134332,
    "term": 72,
    "interest_rate": 0.21,  # 21%
    "service_fee_amount": 12680,
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870
}

table = generate_amortization_table(test_offer)

print("EXCEL VS OUR CALCULATION - FIRST 3 MONTHS")
print("="*90)
print(f"{'Month':>5} {'Capital':>12} {'Interés':>12} {'Cargos':>10} {'IVA':>10} {'Exigible':>12} {'Sum':>12} {'Match':>6}")
print("-"*90)

# Excel values for comparison
excel_values = [
    {"capital": 2459.01, "interes": 2350.81, "cargos": 350, "iva": 432.13, "exigible": 5591.95},
    {"capital": 1621.27, "interes": 2321.07, "cargos": 350, "iva": 427.37, "exigible": 4719.71},
    {"capital": 1654.18, "interes": 2290.81, "cargos": 350, "iva": 422.53, "exigible": 4717.52},
]

for i in range(3):
    row = table[i]
    excel = excel_values[i]
    
    # Calculate sum
    calc_sum = row['capital'] + row['interes'] + row['cargos'] + row['iva']
    
    # Check if values match Excel
    cap_match = abs(row['capital'] - excel['capital']) < 0.02
    int_match = abs(row['interes'] - excel['interes']) < 0.02
    iva_match = abs(row['iva'] - excel['iva']) < 0.02
    pay_match = abs(row['exigible'] - excel['exigible']) < 0.02
    sum_match = abs(calc_sum - row['exigible']) < 0.02
    
    print(f"{i+1:>5} ${row['capital']:>11,.2f} ${row['interes']:>11,.2f} ${row['cargos']:>9,.2f} ${row['iva']:>9,.2f} ${row['exigible']:>11,.2f} ${calc_sum:>11,.2f} {'✓' if all([cap_match, int_match, iva_match, pay_match, sum_match]) else '✗'}")
    
    # Show Excel values for comparison
    print(f"Excel: ${excel['capital']:>11,.2f} ${excel['interes']:>11,.2f} ${excel['cargos']:>9,.2f} ${excel['iva']:>9,.2f} ${excel['exigible']:>11,.2f}")
    if not all([cap_match, int_match, iva_match, pay_match]):
        print("       DIFFERENCES:")
        if not cap_match: print(f"       Capital: {row['capital'] - excel['capital']:+.2f}")
        if not int_match: print(f"       Interés: {row['interes'] - excel['interes']:+.2f}")
        if not iva_match: print(f"       IVA: {row['iva'] - excel['iva']:+.2f}")
        if not pay_match: print(f"       Payment: {row['exigible'] - excel['exigible']:+.2f}")
    print()