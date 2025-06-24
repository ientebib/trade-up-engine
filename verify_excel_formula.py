#!/usr/bin/env python3
"""
Verify we understand the Excel formula correctly
"""
import numpy_financial as npf

# Excel values from formula
b5 = 93657.36    # monto a financiar (main loan)
b6 = 72          # term
b7 = 0.18        # interest rate (annual)
b9 = 4676.10     # service fee
b11 = 10999      # insurance
b13 = 25000      # kavak total
b17 = 750        # GPS installation fee (no IVA)

# Calculate month 1
h3 = 1  # cuota

# Principal calculation (with 1.16 for IVA)
principal_main = abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b5))
principal_sf = abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b9))
principal_ins = abs(npf.ppmt(b7 * 1.16 / 12, h3, 12, -b11))  # 12 month term!
principal_kt = abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b13))
gps_install = b17  # Only for month 1

total_principal = principal_main + principal_sf + principal_ins + principal_kt + gps_install

print("EXCEL FORMULA VERIFICATION")
print("="*50)
print(f"Main loan principal:    ${principal_main:,.2f}")
print(f"Service fee principal:  ${principal_sf:,.2f}")
print(f"Insurance principal:    ${principal_ins:,.2f}")
print(f"Kavak Total principal:  ${principal_kt:,.2f}")
print(f"GPS installation:       ${gps_install:,.2f}")
print(f"TOTAL CAPITAL:          ${total_principal:,.2f}")
print(f"Excel shows:            $2,458.01")
print()

# Interest calculation (without IVA)
interest_main = abs(npf.ipmt(b7 / 12, h3, b6, -b5))
interest_sf = abs(npf.ipmt(b7 / 12, h3, b6, -b9))
interest_ins = abs(npf.ipmt(b7 / 12, h3, 12, -b11))
interest_kt = abs(npf.ipmt(b7 / 12, h3, b6, -b13))

total_interest = interest_main + interest_sf + interest_ins + interest_kt

print(f"Main loan interest:     ${interest_main:,.2f}")
print(f"Service fee interest:   ${interest_sf:,.2f}")
print(f"Insurance interest:     ${interest_ins:,.2f}")
print(f"Kavak Total interest:   ${interest_kt:,.2f}")
print(f"TOTAL INTEREST:         ${total_interest:,.2f}")
print(f"Excel shows:            $2,348.01")

# Check month 2 (no GPS installation)
print("\nMONTH 2 CHECK:")
h3 = 2
principal_month2 = (abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b5)) +
                   abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b9)) +
                   abs(npf.ppmt(b7 * 1.16 / 12, h3, 12, -b11)) +
                   abs(npf.ppmt(b7 * 1.16 / 12, h3, b6, -b13)))
print(f"Total principal (no GPS): ${principal_month2:,.2f}")