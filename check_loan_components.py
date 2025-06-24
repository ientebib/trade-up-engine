#!/usr/bin/env python3
"""
Check what's included in our loan amount vs Excel
"""

# From the screenshots and previous tests
engine_loan_amount = 134332.46  # Our engine
excel_loan_amount = 134172.46   # Excel
difference = engine_loan_amount - excel_loan_amount

print("LOAN AMOUNT COMPARISON")
print("="*50)
print(f"Engine loan amount: ${engine_loan_amount:,.2f}")
print(f"Excel loan amount:  ${excel_loan_amount:,.2f}")
print(f"Difference:         ${difference:,.2f}")
print()

# Typical loan components in our engine
car_price = 340000  # Example
down_payment = 230427  # From screenshot
service_fee = car_price * 0.04  # 13,600
kavak_total = 25000
insurance = 10999

print("ENGINE LOAN COMPONENTS (typical):")
print(f"Car price:           ${car_price:,.2f}")
print(f"- Down payment:      ${down_payment:,.2f}")
print(f"= Base loan:         ${car_price - down_payment:,.2f}")
print(f"+ Service fee (4%):  ${service_fee:,.2f}")
print(f"+ Kavak Total:       ${kavak_total:,.2f}")
print(f"+ Insurance:         ${insurance:,.2f}")
print(f"= Total financed:    ${car_price - down_payment + service_fee + kavak_total + insurance:,.2f}")
print()

# The Excel appears to NOT include some components
print("EXCEL APPEARS TO:")
print("- Calculate simple loan payment")
print("- Add GPS as separate non-financed charge")
print("- Apply IVA to both interest and GPS")
print()

print("OUR ENGINE:")
print("- Finances service fee, Kavak Total, and insurance")
print("- Calculates separate principal/interest for each component")
print("- GPS is NOT financed, added to monthly payment")
print("- IVA only on interest, GPS already includes IVA")
print()

print("TO MATCH EXCEL, WE WOULD NEED TO:")
print("1. Change IVA calculation to include GPS: IVA = (Interest + GPS) * 0.16")
print("2. Show GPS without IVA in 'Cargos' column ($350 instead of $406)")
print("3. Possibly use simpler loan calculation instead of buckets")