#!/usr/bin/env python3
"""
Debug script to understand the amortization calculation mismatch
"""
import json
from engine.calculator import generate_amortization_table
from config import IVA_RATE

# Test offer matching the screenshot
test_offer = {
    "loan_amount": 134332.46,
    "term": 72,
    "interest_rate": 0.18,  # 18% annual
    "service_fee_amount": 4676.10,  # Approximate from the offer
    "kavak_total_amount": 25000,
    "insurance_amount": 10999,
    "gps_install_fee": 870  # 750 * 1.16
}

print("DEBUGGING AMORTIZATION CALCULATION")
print("="*50)
print(f"IVA_RATE = {IVA_RATE}")
print(f"Loan Amount: ${test_offer['loan_amount']:,.2f}")
print(f"Interest Rate: {test_offer['interest_rate']*100:.1f}%")
print(f"Interest Rate with IVA: {test_offer['interest_rate']*(1+IVA_RATE)*100:.1f}%")
print("\n")

# Generate table
table = generate_amortization_table(test_offer)
first_month = table[0]

print("FIRST MONTH RAW DATA:")
print(json.dumps(first_month, indent=2, default=str))
print("\n")

print("COLUMN VALUES:")
print(f"1. Capital: ${first_month['capital']:,.2f}")
print(f"2. Interés (sin IVA): ${first_month['interes']:,.2f}")
print(f"3. IVA: ${first_month['iva']:,.2f}")
print(f"4. Cargos: ${first_month['cargos']:,.2f}")
print(f"   SUM: ${first_month['capital'] + first_month['interes'] + first_month['iva'] + first_month['cargos']:,.2f}")
print(f"5. Exigible: ${first_month['exigible']:,.2f}")
print(f"   DIFFERENCE: ${first_month['exigible'] - (first_month['capital'] + first_month['interes'] + first_month['iva'] + first_month['cargos']):,.2f}")
print("\n")

print("INTERNAL PAYMENT CALCULATION:")
print(f"Payment (from 'payment' field): ${first_month['payment']:,.2f}")
print(f"Principal (from 'principal' field): ${first_month['principal']:,.2f}")
print(f"Interest with IVA (from 'interest' field): ${first_month['interest']:,.2f}")
print("\n")

# Let's manually calculate what the payment should be
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

print("PAYMENT CALCULATION BREAKDOWN:")
print(f"Base loan payment: ${payment_calc['payment_base']:,.2f}")
print(f"Service fee payment: ${payment_calc['payment_service_fee']:,.2f}")
print(f"Kavak Total payment: ${payment_calc['payment_kavak_total']:,.2f}")
print(f"Insurance payment: ${payment_calc['payment_insurance']:,.2f}")
print(f"GPS monthly: ${payment_calc['gps_monthly_with_iva']:,.2f}")
print(f"TOTAL: ${payment_calc['payment_total']:,.2f}")