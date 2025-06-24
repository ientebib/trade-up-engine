#!/usr/bin/env python3
"""
Test the Excel-compatible format
"""
from engine.calculator import generate_amortization_table

# Test offer matching Excel
test_offer = {
    "loan_amount": 134332.46,
    "term": 72,
    "interest_rate": 0.18,
    "service_fee_amount": 4676.10,
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870  # 750 * 1.16
}

table = generate_amortization_table(test_offer)

print("EXCEL-COMPATIBLE AMORTIZATION FORMAT")
print("="*80)
print(f"{'Cuota':>6} {'Saldo Insoluto':>15} {'Capital':>12} {'Interés':>12} {'Cargos':>10} {'IVA':>10} {'Exigible':>12}")
print("-"*80)

# Show first 3 months
for i in range(3):
    row = table[i]
    print(f"{row['cuota']:>6} ${row['saldo_insoluto']:>14,.2f} ${row['capital']:>11,.2f} ${row['interes']:>11,.2f} ${row['cargos']:>9,.2f} ${row['iva']:>9,.2f} ${row['exigible']:>11,.2f}")
    
    # Verify columns add up
    calculated = row['capital'] + row['interes'] + row['cargos'] + row['iva']
    diff = abs(row['exigible'] - calculated)
    if diff > 0.01:
        print(f"  WARNING: Columns don't add up! Diff: ${diff:.2f}")

print("\nVERIFICATION:")
first = table[0]
print(f"Capital + Interés + Cargos + IVA = ${first['capital']:,.2f} + ${first['interes']:,.2f} + ${first['cargos']:,.2f} + ${first['iva']:,.2f}")
print(f"                                  = ${first['capital'] + first['interes'] + first['cargos'] + first['iva']:,.2f}")
print(f"Exigible                          = ${first['exigible']:,.2f}")
print(f"Difference                        = ${abs(first['exigible'] - (first['capital'] + first['interes'] + first['cargos'] + first['iva'])):,.2f}")

print("\nCOMPARE TO EXCEL:")
print(f"Month 1 Cargos: ${first['cargos']:,.2f} (should be $1,100 = $350 + $750)")
print(f"Month 2 Cargos: ${table[1]['cargos']:,.2f} (should be $350)")
print(f"IVA formula: (Interés + Cargos) * 16% = (${first['interes']:,.2f} + ${first['cargos']:,.2f}) * 0.16 = ${first['iva']:,.2f}")