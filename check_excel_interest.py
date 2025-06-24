#!/usr/bin/env python3
"""
Check why Excel shows different interest amount
"""
import numpy_financial as npf

# Values
b5 = 93657.36    # main loan  
b7 = 0.18        # rate
b9 = 4676.10     # service fee
b11 = 10999      # insurance
b13 = 25000      # kavak total

# Our calculation
interest_our = (
    abs(npf.ipmt(b7/12, 1, 72, -b5)) +
    abs(npf.ipmt(b7/12, 1, 72, -b9)) +
    abs(npf.ipmt(b7/12, 1, 12, -b11)) +
    abs(npf.ipmt(b7/12, 1, 72, -b13))
)

print(f"Our interest calculation: ${interest_our:,.2f}")
print(f"Excel shows: $2,348.01")
print(f"Difference: ${2348.01 - interest_our:,.2f}")

# What if the loan amounts are different?
# Work backwards from Excel's interest
excel_interest = 2348.01
rate_monthly = b7/12

# If it's a simple loan
simple_loan = excel_interest / rate_monthly
print(f"\nIf simple loan, principal would be: ${simple_loan:,.2f}")

# Check our total loan
our_total = b5 + b9 + b11 + b13
print(f"\nOur total components: ${our_total:,.2f}")

# Maybe Excel has different component values?
print("\nLet's check component interest values:")
print(f"Main ({b5:,.2f}): ${abs(npf.ipmt(b7/12, 1, 72, -b5)):,.2f}")
print(f"Service ({b9:,.2f}): ${abs(npf.ipmt(b7/12, 1, 72, -b9)):,.2f}")
print(f"Insurance ({b11:,.2f}): ${abs(npf.ipmt(b7/12, 1, 12, -b11)):,.2f}")
print(f"Kavak ({b13:,.2f}): ${abs(npf.ipmt(b7/12, 1, 72, -b13)):,.2f}")

# What if main loan is different?
# Excel total loan: 134,171.92 (from screenshot)
# Our components: service + kavak + insurance = 40,675.10
excel_main = 134171.92 - 40675.10
print(f"\nIf Excel main loan is: ${excel_main:,.2f}")
print(f"Interest would be: ${abs(npf.ipmt(b7/12, 1, 72, -excel_main)):,.2f}")

# Recalculate with this
new_interest = (
    abs(npf.ipmt(b7/12, 1, 72, -excel_main)) +
    abs(npf.ipmt(b7/12, 1, 72, -b9)) +
    abs(npf.ipmt(b7/12, 1, 12, -b11)) +
    abs(npf.ipmt(b7/12, 1, 72, -b13))
)
print(f"Total interest with adjusted main: ${new_interest:,.2f}")