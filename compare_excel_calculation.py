#!/usr/bin/env python3
"""
Compare our calculation with Excel's approach
"""
import numpy_financial as npf
from config import IVA_RATE

# Loan parameters (matching the screenshot)
loan_amount = 134172.46  # From Excel
term = 72
annual_rate = 0.18
monthly_rate = annual_rate / 12
monthly_rate_with_iva = (annual_rate * (1 + IVA_RATE)) / 12

print("COMPARING EXCEL VS ENGINE CALCULATIONS")
print("="*50)
print(f"Loan amount: ${loan_amount:,.2f}")
print(f"Term: {term} months")
print(f"Annual rate: {annual_rate*100:.0f}%")
print(f"Monthly rate: {monthly_rate*100:.4f}%")
print(f"Monthly rate with IVA: {monthly_rate_with_iva*100:.4f}%")
print()

# Calculate PMT the way Excel does
pmt_excel = abs(npf.pmt(monthly_rate_with_iva, term, -loan_amount))
print(f"Excel PMT calculation: ${pmt_excel:,.2f}")

# Calculate principal and interest for month 1
principal_excel = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -loan_amount))
interest_excel = abs(npf.ipmt(monthly_rate, 1, term, -loan_amount))  # Without IVA

print(f"\nMONTH 1 - EXCEL METHOD:")
print(f"Principal: ${principal_excel:,.2f}")
print(f"Interest (without IVA): ${interest_excel:,.2f}")
print(f"GPS (cargos): $350.00")
print(f"IVA on (Interest + GPS): ${(interest_excel + 350) * IVA_RATE:,.2f}")
print(f"Total: ${principal_excel + interest_excel + 350 + (interest_excel + 350) * IVA_RATE:,.2f}")

# Now show what our engine does
print(f"\nMONTH 1 - OUR ENGINE:")
print(f"Principal: $1,588.45 (from screenshot)")
print(f"Interest (without IVA): $2,346.90")
print(f"GPS with IVA: $1,276.00 (includes install fee)")
print(f"IVA on interest only: $375.50")
print(f"Total: $5,586.85")

# The key difference: Excel appears to calculate a simple PMT payment
# and split it into principal/interest, while we calculate separate
# payments for each component (main loan, service fee, kavak total, insurance)

print("\nKEY DIFFERENCES:")
print("1. Excel: Simple loan calculation, GPS added separately")
print("2. Engine: Bucketized calculation with multiple loan components")
print("3. Excel: IVA on (Interest + GPS)")
print("4. Engine: IVA on Interest only, GPS already includes IVA")
print("5. Excel: Single principal calculation")
print("6. Engine: Principal split across main/service fee/kavak total/insurance")