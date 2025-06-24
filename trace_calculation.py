#!/usr/bin/env python3
"""
Trace the exact calculation to find the $14.68 difference
"""
import numpy_financial as npf
from config import IVA_RATE

# Test values from screenshot
loan_amount = 134332.46
term = 72
rate = 0.18
service_fee = 4676.10
kavak_total = 25000
insurance = 10999

# Calculate components
financed_main = loan_amount - service_fee - kavak_total - insurance
financed_sf = service_fee
financed_kt = kavak_total
financed_ins = insurance

print(f"LOAN COMPONENTS:")
print(f"Main: ${financed_main:,.2f}")
print(f"Service Fee: ${financed_sf:,.2f}")
print(f"Kavak Total: ${financed_kt:,.2f}")
print(f"Insurance: ${financed_ins:,.2f}")
print(f"TOTAL: ${loan_amount:,.2f}")
print()

# Calculate interest rates
monthly_rate = rate / 12
rate_with_iva = rate * (1 + IVA_RATE)
monthly_rate_with_iva = rate_with_iva / 12

print(f"INTEREST RATES:")
print(f"Annual rate: {rate*100:.1f}%")
print(f"Monthly rate: {monthly_rate*100:.4f}%")
print(f"Annual rate with IVA: {rate_with_iva*100:.1f}%")
print(f"Monthly rate with IVA: {monthly_rate_with_iva*100:.4f}%")
print()

# Calculate principal for each component (month 1)
principal_main = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -financed_main))
principal_sf = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -financed_sf))
principal_kt = abs(npf.ppmt(monthly_rate_with_iva, 1, term, -financed_kt))
principal_ins = abs(npf.ppmt(monthly_rate_with_iva, 1, 12, -financed_ins))  # 12 month term

print(f"PRINCIPAL COMPONENTS (Month 1):")
print(f"Main: ${principal_main:,.2f}")
print(f"Service Fee: ${principal_sf:,.2f}")
print(f"Kavak Total: ${principal_kt:,.2f}")
print(f"Insurance: ${principal_ins:,.2f}")
print(f"TOTAL PRINCIPAL: ${principal_main + principal_sf + principal_kt + principal_ins:,.2f}")
print()

# Calculate interest WITHOUT IVA
interest_main_base = abs(npf.ipmt(monthly_rate, 1, term, -financed_main))
interest_sf_base = abs(npf.ipmt(monthly_rate, 1, term, -financed_sf))
interest_kt_base = abs(npf.ipmt(monthly_rate, 1, term, -financed_kt))
interest_ins_base = abs(npf.ipmt(monthly_rate, 1, 12, -financed_ins))

print(f"INTEREST WITHOUT IVA (Month 1):")
print(f"Main: ${interest_main_base:,.2f}")
print(f"Service Fee: ${interest_sf_base:,.2f}")
print(f"Kavak Total: ${interest_kt_base:,.2f}")
print(f"Insurance: ${interest_ins_base:,.2f}")
print(f"TOTAL BASE INTEREST: ${interest_main_base + interest_sf_base + interest_kt_base + interest_ins_base:,.2f}")
print()

# Calculate interest WITH IVA (as used in payment)
interest_main = interest_main_base * (1 + IVA_RATE)
interest_sf = interest_sf_base * (1 + IVA_RATE)
interest_kt = interest_kt_base * (1 + IVA_RATE)
interest_ins = interest_ins_base * (1 + IVA_RATE)

print(f"INTEREST WITH IVA (Month 1):")
print(f"Main: ${interest_main:,.2f}")
print(f"Service Fee: ${interest_sf:,.2f}")
print(f"Kavak Total: ${interest_kt:,.2f}")
print(f"Insurance: ${interest_ins:,.2f}")
print(f"TOTAL INTEREST WITH IVA: ${interest_main + interest_sf + interest_kt + interest_ins:,.2f}")
print()

# GPS fees
gps_monthly = 350 * (1 + IVA_RATE)
gps_install = 750 * (1 + IVA_RATE)

print(f"GPS FEES:")
print(f"Monthly: ${gps_monthly:,.2f}")
print(f"Installation (month 1): ${gps_install:,.2f}")
print(f"Total month 1: ${gps_monthly + gps_install:,.2f}")
print()

# Calculate total payment
total_principal = principal_main + principal_sf + principal_kt + principal_ins
total_interest_with_iva = interest_main + interest_sf + interest_kt + interest_ins
total_gps = gps_monthly + gps_install

payment = total_principal + total_interest_with_iva + total_gps

print(f"PAYMENT CALCULATION:")
print(f"Principal: ${total_principal:,.2f}")
print(f"Interest (with IVA): ${total_interest_with_iva:,.2f}")
print(f"GPS fees: ${total_gps:,.2f}")
print(f"TOTAL PAYMENT: ${payment:,.2f}")
print()

# Now show what the display columns should be
total_base_interest = interest_main_base + interest_sf_base + interest_kt_base + interest_ins_base
iva_on_interest = total_base_interest * IVA_RATE

print(f"DISPLAY COLUMNS:")
print(f"Capital: ${total_principal:,.2f}")
print(f"Interés: ${total_base_interest:,.2f}")
print(f"IVA: ${iva_on_interest:,.2f}")
print(f"Cargos: ${total_gps:,.2f}")
print(f"SUM: ${total_principal + total_base_interest + iva_on_interest + total_gps:,.2f}")
print(f"Exigible: ${payment:,.2f}")
print(f"DIFFERENCE: ${payment - (total_principal + total_base_interest + iva_on_interest + total_gps):,.2f}")