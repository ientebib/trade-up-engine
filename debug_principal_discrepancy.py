#!/usr/bin/env python3
"""
Debug why principal amounts are so different with similar loan amounts
"""
import numpy_financial as npf
from config import IVA_RATE

# Loan parameters
excel_loan = 134172.46
engine_loan = 134332.46
term = 72
annual_rate = 0.18
monthly_rate = annual_rate / 12
monthly_rate_with_iva = (annual_rate * (1 + IVA_RATE)) / 12

print("INVESTIGATING PRINCIPAL DISCREPANCY")
print("="*60)
print(f"Excel loan amount:  ${excel_loan:,.2f}")
print(f"Engine loan amount: ${engine_loan:,.2f}")
print(f"Difference:         ${engine_loan - excel_loan:,.2f}")
print(f"\nTerm: {term} months")
print(f"Annual rate: {annual_rate*100}%")
print(f"Monthly rate with IVA: {monthly_rate_with_iva*100:.4f}%")
print()

# Calculate using simple PMT (like Excel)
print("SIMPLE PMT CALCULATION (Excel method):")
pmt_excel = abs(npf.pmt(monthly_rate_with_iva, term, -excel_loan))
principal_month1_excel = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -excel_loan))
interest_month1_excel = abs(npf.ipmt(monthly_rate, 1, term, -excel_loan))

print(f"PMT: ${pmt_excel:,.2f}")
print(f"Month 1 Principal: ${principal_month1_excel:,.2f}")
print(f"Month 1 Interest (no IVA): ${interest_month1_excel:,.2f}")
print(f"Month 1 Total: ${principal_month1_excel + interest_month1_excel * (1 + IVA_RATE):,.2f}")
print()

# Now let's check what our engine is doing
# From the test data, we have these components:
service_fee = 4676.10
kavak_total = 25000
insurance = 10999

# Calculate main loan amount
main_loan = engine_loan - service_fee - kavak_total - insurance
print(f"ENGINE LOAN BREAKDOWN:")
print(f"Total loan:     ${engine_loan:,.2f}")
print(f"- Service fee:  ${service_fee:,.2f}")
print(f"- Kavak Total:  ${kavak_total:,.2f}")
print(f"- Insurance:    ${insurance:,.2f}")
print(f"= Main loan:    ${main_loan:,.2f}")
print()

# Calculate principal for each component
print("MONTH 1 PRINCIPAL BY COMPONENT:")
principal_main = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -main_loan))
principal_sf = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -service_fee))
principal_kt = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -kavak_total))
principal_ins = abs(npf.ppmt(monthly_rate_with_iva, 1, 12, -insurance))  # 12 month term!

print(f"Main loan ({term} mo):    ${principal_main:,.2f}")
print(f"Service fee ({term} mo):  ${principal_sf:,.2f}")
print(f"Kavak Total ({term} mo):  ${principal_kt:,.2f}")
print(f"Insurance (12 mo):    ${principal_ins:,.2f}")
print(f"TOTAL:                ${principal_main + principal_sf + principal_kt + principal_ins:,.2f}")
print()

# The issue might be the insurance term!
print("KEY INSIGHT: Insurance uses 12-month term, not 72!")
print(f"Insurance principal with 72-month term would be: ${abs(npf.ppmt(monthly_rate_with_iva, 1, 72, -insurance)):,.2f}")
print(f"But we use 12-month term: ${principal_ins:,.2f}")
print(f"Difference: ${principal_ins - abs(npf.ppmt(monthly_rate_with_iva, 1, 72, -insurance)):,.2f}")

# Let's also check if Excel might not include some components
print(f"\nPOSSIBLE EXCEL LOAN COMPOSITION:")
possible_main = excel_loan - service_fee
print(f"If Excel excludes service fee: ${possible_main:,.2f}")
print(f"Principal would be: ${abs(npf.ppmt(monthly_rate_with_iva, 1, term, -possible_main)):,.2f}")

possible_main2 = excel_loan - kavak_total
print(f"\nIf Excel excludes Kavak Total: ${possible_main2:,.2f}")
print(f"Principal would be: ${abs(npf.ppmt(monthly_rate_with_iva, 1, term, -possible_main2)):,.2f}")

# What if Excel includes everything?
print(f"\nIf Excel includes everything at 72 months:")
principal_all_72 = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -excel_loan))
print(f"Principal would be: ${principal_all_72:,.2f}")
print(f"Excel shows: $2,458.01")
print(f"Our engine shows: $1,703.57")

# The smoking gun: What interest rate gives Excel's principal?
# Work backwards from Excel's principal
excel_principal = 2458.01
for test_rate in [0.12, 0.15, 0.18, 0.21, 0.24, 0.27, 0.30]:
    test_monthly = test_rate / 12
    test_principal = abs(npf.ppmt(test_monthly, 1, term, -excel_loan))
    if abs(test_principal - excel_principal) < 10:
        print(f"\nFOUND IT! Rate {test_rate*100}% gives principal ${test_principal:,.2f}")