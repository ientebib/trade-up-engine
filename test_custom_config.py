#!/usr/bin/env python3
"""
Test that custom config actually affects calculations
"""
from engine.basic_matcher import BasicMatcher
from data.loader import DataLoader

loader = DataLoader()
customers_df, inventory_df = loader.load_all_data()

# Data already loaded above

# Get first customer
customer = customers_df.iloc[0].to_dict()
inventory = inventory_df.head(10).to_dict('records')

print(f"Testing with customer: {customer['customer_id']}")
print(f"Current payment: ${customer['current_monthly_payment']:,.0f}")
print()

# Test 1: With Kavak Total
config_with_kt = {
    'service_fee_pct': 0.04,
    'cxa_pct': 0.04,
    'cac_bonus': 0,
    'kavak_total_amount': 25000,  # Enabled
    'gps_monthly_fee': 350,
    'gps_installation_fee': 750,
    'insurance_amount': 10999
}

matcher = BasicMatcher()
result_with = matcher.find_all_viable(customer, inventory, config_with_kt)

print("WITH KAVAK TOTAL ($25,000):")
print(f"Total offers: {result_with['total_offers']}")
if result_with['total_offers'] > 0:
    # Get first offer
    for tier, offers in result_with['offers'].items():
        if offers:
            offer = offers[0]
            print(f"First {tier} offer:")
            print(f"  Car: {offer['car_model']}")
            print(f"  Price: ${offer['new_car_price']:,.0f}")
            print(f"  Loan amount: ${offer['loan_amount']:,.0f}")
            print(f"  Monthly payment: ${offer['monthly_payment']:,.0f}")
            print(f"  Kavak Total in loan: ${offer['kavak_total_amount']:,.0f}")
            break

print("\n" + "="*50 + "\n")

# Test 2: Without Kavak Total
config_no_kt = {
    'service_fee_pct': 0.04,
    'cxa_pct': 0.04,
    'cac_bonus': 0,
    'kavak_total_amount': 0,  # Disabled
    'gps_monthly_fee': 350,
    'gps_installation_fee': 750,
    'insurance_amount': 10999
}

result_without = matcher.find_all_viable(customer, inventory, config_no_kt)

print("WITHOUT KAVAK TOTAL ($0):")
print(f"Total offers: {result_without['total_offers']}")
if result_without['total_offers'] > 0:
    # Get first offer
    for tier, offers in result_without['offers'].items():
        if offers:
            offer = offers[0]
            print(f"First {tier} offer:")
            print(f"  Car: {offer['car_model']}")
            print(f"  Price: ${offer['new_car_price']:,.0f}")
            print(f"  Loan amount: ${offer['loan_amount']:,.0f}")
            print(f"  Monthly payment: ${offer['monthly_payment']:,.0f}")
            print(f"  Kavak Total in loan: ${offer['kavak_total_amount']:,.0f}")
            break

print("\n" + "="*50 + "\n")
print("DIFFERENCE:")
if result_with['total_offers'] > 0 and result_without['total_offers'] > 0:
    for tier in ['Refresh', 'Upgrade', 'Max Upgrade']:
        if result_with['offers'][tier] and result_without['offers'][tier]:
            offer_with = result_with['offers'][tier][0]
            offer_without = result_without['offers'][tier][0]
            if offer_with['car_id'] == offer_without['car_id']:
                print(f"\nSame car ({offer_with['car_model']}):")
                print(f"  Payment WITH KT: ${offer_with['monthly_payment']:,.0f}")
                print(f"  Payment WITHOUT KT: ${offer_without['monthly_payment']:,.0f}")
                print(f"  Difference: ${offer_with['monthly_payment'] - offer_without['monthly_payment']:,.0f}")
                break