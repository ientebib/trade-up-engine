#!/usr/bin/env python3
"""
Find what values give the user's expected results
"""
import numpy_financial as npf

# User's displayed values
user_interest = 2349.70  # From screenshot
user_payment = 5591.10
user_capital = 2339.45

# Work backwards to find the loan components
# Interest = sum of interest on all components
# If monthly rate = 1.5%, then total loan * 0.015 = interest

total_loan_implied = user_interest / 0.015
print(f"IMPLIED TOTAL LOAN from interest: ${total_loan_implied:,.2f}")

# Check what interest rate gives this payment
from engine.payment_utils import calculate_monthly_payment

# Try different scenarios
print("\nTESTING DIFFERENT SCENARIOS:")

# Scenario 1: Higher loan amount
test_loan = 150000  # Higher than our 134k
payment1 = calculate_monthly_payment(
    loan_base=test_loan - 4676 - 25000 - 10999,
    service_fee_amount=4676,
    kavak_total_amount=25000,
    insurance_amount=10999,
    annual_rate_nominal=0.18,
    term_months=72,
    gps_install_fee=870
)
print(f"\nWith loan ${test_loan:,.0f}: Payment = ${payment1['payment_total']:,.2f}")

# Scenario 2: Higher interest rate
test_rate = 0.24  # 24% instead of 18%
payment2 = calculate_monthly_payment(
    loan_base=134332 - 4676 - 25000 - 10999,
    service_fee_amount=4676,
    kavak_total_amount=25000,
    insurance_amount=10999,
    annual_rate_nominal=test_rate,
    term_months=72,
    gps_install_fee=870
)
print(f"\nWith rate {test_rate*100:.0f}%: Payment = ${payment2['payment_total']:,.2f}")

# Scenario 3: No Kavak Total (user might have it off)
payment3 = calculate_monthly_payment(
    loan_base=134332 - 4676 - 0 - 10999,  # No Kavak Total
    service_fee_amount=4676,
    kavak_total_amount=0,
    insurance_amount=10999,
    annual_rate_nominal=0.18,
    term_months=72,
    gps_install_fee=870
)
print(f"\nWithout Kavak Total: Payment = ${payment3['payment_total']:,.2f}")

# The user's interest suggests a larger loan
# Let's calculate components that would give that interest
print("\n\nBACKCALCULATING FROM USER'S VALUES:")
# Total interest without IVA = 2349.70
# This is sum of IPMT for all components

# If we assume same ratios as our loan:
# Main: 93657 / 134332 = 69.7%
# Service: 4676 / 134332 = 3.5%
# Kavak: 25000 / 134332 = 18.6%
# Insurance: 10999 / 134332 = 8.2%

implied_main = total_loan_implied * 0.697
implied_sf = total_loan_implied * 0.035
implied_kt = total_loan_implied * 0.186
implied_ins = total_loan_implied * 0.082

print(f"Implied main loan: ${implied_main:,.2f}")
print(f"Implied service fee: ${implied_sf:,.2f}")
print(f"Implied Kavak Total: ${implied_kt:,.2f}")
print(f"Implied insurance: ${implied_ins:,.2f}")
print(f"Total: ${implied_main + implied_sf + implied_kt + implied_ins:,.2f}")