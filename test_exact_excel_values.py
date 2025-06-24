#!/usr/bin/env python3
"""
Test with exact Excel values
"""
from engine.calculator import generate_amortization_table
from engine.payment_utils import calculate_monthly_payment

# Exact values from Excel screenshot
car_price = 316999
equity = 244896
down_payment = 231346  # After CXA and GPS deducted
base_loan = 85653  # Monto a financiar
interest_rate = 0.21  # 21%
service_fee = 12680
insurance = 10999
kavak_total = 25000
final_loan = 134332  # Monto a financiar final

print("EXACT EXCEL VALUES TEST")
print("="*60)
print(f"Car price: ${car_price:,}")
print(f"Interest rate: {interest_rate*100}% ({interest_rate*1.16*100:.2f}% with IVA)")
print(f"Base loan: ${base_loan:,}")
print(f"Service fee: ${service_fee:,}")
print(f"Kavak Total: ${kavak_total:,}")
print(f"Insurance: ${insurance:,}")
print(f"Final loan: ${final_loan:,}")
print()

# Create test offer
test_offer = {
    "loan_amount": final_loan,
    "term": 72,
    "interest_rate": interest_rate,  # 21%
    "service_fee_amount": service_fee,
    "kavak_total_amount": kavak_total,
    "insurance_amount": insurance,
    "gps_install_fee": 870
}

# Calculate payment
payment_calc = calculate_monthly_payment(
    loan_base=base_loan,
    service_fee_amount=service_fee,
    kavak_total_amount=kavak_total,
    insurance_amount=insurance,
    annual_rate_nominal=interest_rate,
    term_months=72,
    gps_install_fee=870
)

print(f"PAYMENT CALCULATION:")
print(f"Our calculation: ${payment_calc['payment_total']:,.2f}")
print(f"Excel shows: $5,592")
print(f"Match? {'YES ✓' if abs(payment_calc['payment_total'] - 5592) < 1 else 'NO ✗'}")
print()

# Generate amortization table
table = generate_amortization_table(test_offer)
first = table[0]

print("AMORTIZATION FIRST MONTH:")
print(f"Capital:   ${first['capital']:,.2f}")
print(f"Interés:   ${first['interes']:,.2f}")
print(f"Cargos:    ${first['cargos']:,.2f}")
print(f"IVA:       ${first['iva']:,.2f}")
print(f"---")
print(f"Sum:       ${first['capital'] + first['interes'] + first['cargos'] + first['iva']:,.2f}")
print(f"Exigible:  ${first['exigible']:,.2f}")
print(f"Columns add up? {'YES ✓' if abs(first['exigible'] - (first['capital'] + first['interes'] + first['cargos'] + first['iva'])) < 0.01 else 'NO ✗'}")