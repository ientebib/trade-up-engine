#!/usr/bin/env python3
"""
Comprehensive verification that EVERYTHING works correctly
"""
import json
from engine.calculator import generate_amortization_table
from engine.basic_matcher import BasicMatcher
from data.loader import DataLoader

print("COMPREHENSIVE SYSTEM VERIFICATION")
print("="*60)

# Load data
loader = DataLoader()
customers_df, inventory_df = loader.load_all_data()
customer = customers_df.iloc[0].to_dict()
inventory = inventory_df.head(5).to_dict('records')

print(f"Testing with customer: {customer['customer_id']}")
print(f"Current payment: ${customer['current_monthly_payment']:,.0f}")
print()

# TEST 1: Kavak Total ON vs OFF
print("TEST 1: KAVAK TOTAL TOGGLE")
print("-"*40)

matcher = BasicMatcher()

# With KT
config_kt_on = {
    'service_fee_pct': 0.04,
    'cxa_pct': 0.04,
    'cac_bonus': 0,
    'kavak_total_amount': 25000,  # ON
    'gps_monthly_fee': 350,
    'gps_installation_fee': 750,
    'insurance_amount': 10999
}

result_on = matcher.find_all_viable(customer, inventory, config_kt_on)

# Without KT
config_kt_off = {
    'service_fee_pct': 0.04,
    'cxa_pct': 0.04,
    'cac_bonus': 0,
    'kavak_total_amount': 0,  # OFF
    'gps_monthly_fee': 350,
    'gps_installation_fee': 750,
    'insurance_amount': 10999
}

result_off = matcher.find_all_viable(customer, inventory, config_kt_off)

# Compare same car
for tier in ['Refresh', 'Upgrade', 'Max Upgrade']:
    if result_on['offers'][tier] and result_off['offers'][tier]:
        offer_on = result_on['offers'][tier][0]
        offer_off = result_off['offers'][tier][0]
        if offer_on['car_id'] == offer_off['car_id']:
            print(f"\n{tier} tier - {offer_on['car_model']}:")
            print(f"  WITH KT: Payment=${offer_on['monthly_payment']:,.0f}, KT Amount=${offer_on['kavak_total_amount']:,.0f}")
            print(f"  NO KT:   Payment=${offer_off['monthly_payment']:,.0f}, KT Amount=${offer_off['kavak_total_amount']:,.0f}")
            print(f"  Difference: ${offer_on['monthly_payment'] - offer_off['monthly_payment']:,.0f}/month")
            
            # Verify KT amount is correct
            assert offer_on['kavak_total_amount'] == 25000, f"KT ON should be 25000, got {offer_on['kavak_total_amount']}"
            assert offer_off['kavak_total_amount'] == 0, f"KT OFF should be 0, got {offer_off['kavak_total_amount']}"
            break

# TEST 2: Amortization Table Columns Add Up
print("\n\nTEST 2: AMORTIZATION TABLE COLUMNS")
print("-"*40)

if result_on['offers']['Refresh']:
    test_offer = result_on['offers']['Refresh'][0]
    table = generate_amortization_table(test_offer)
    
    # Check first 3 months
    for i in range(min(3, len(table))):
        row = table[i]
        calculated_sum = row['capital'] + row['interes'] + row['iva'] + row['cargos']
        difference = abs(row['exigible'] - calculated_sum)
        
        print(f"\nMonth {row['month']}:")
        print(f"  Capital:   ${row['capital']:,.2f}")
        print(f"  Interés:   ${row['interes']:,.2f}")
        print(f"  IVA:       ${row['iva']:,.2f}")
        print(f"  Cargos:    ${row['cargos']:,.2f}")
        print(f"  Sum:       ${calculated_sum:,.2f}")
        print(f"  Exigible:  ${row['exigible']:,.2f}")
        print(f"  Diff:      ${difference:,.2f} {'✓' if difference < 0.01 else '✗'}")
        
        assert difference < 0.01, f"Columns don't add up! Difference: ${difference:.2f}"

# TEST 3: Custom Service Fee
print("\n\nTEST 3: CUSTOM SERVICE FEE")
print("-"*40)

config_custom_fee = config_kt_on.copy()
config_custom_fee['service_fee_pct'] = 0.06  # 6% instead of 4%

result_custom = matcher.find_all_viable(customer, inventory[:2], config_custom_fee)

if result_custom['offers']['Refresh'] and result_on['offers']['Refresh']:
    # Find matching car
    for offer_custom in result_custom['offers']['Refresh']:
        for offer_normal in result_on['offers']['Refresh']:
            if offer_custom['car_id'] == offer_normal['car_id']:
                print(f"\nCar: {offer_custom['car_model']} (${offer_custom['new_car_price']:,.0f})")
                print(f"  4% fee: ${offer_normal['service_fee_amount']:,.0f}")
                print(f"  6% fee: ${offer_custom['service_fee_amount']:,.0f}")
                
                expected_4pct = offer_custom['new_car_price'] * 0.04
                expected_6pct = offer_custom['new_car_price'] * 0.06
                
                assert abs(offer_normal['service_fee_amount'] - expected_4pct) < 1, "4% fee calculation wrong"
                assert abs(offer_custom['service_fee_amount'] - expected_6pct) < 1, "6% fee calculation wrong"
                break

# TEST 4: CAC Bonus
print("\n\nTEST 4: CAC BONUS")
print("-"*40)

config_cac = config_kt_on.copy()
config_cac['cac_bonus'] = 10000  # $10k bonus

result_cac = matcher.find_all_viable(customer, inventory[:2], config_cac)

if result_cac['offers']['Refresh'] and result_on['offers']['Refresh']:
    for offer_cac in result_cac['offers']['Refresh']:
        for offer_normal in result_on['offers']['Refresh']:
            if offer_cac['car_id'] == offer_normal['car_id']:
                print(f"\nCar: {offer_cac['car_model']}")
                print(f"  Equity NO bonus: ${offer_normal['effective_equity']:,.0f}")
                print(f"  Equity WITH $10k bonus: ${offer_cac['effective_equity']:,.0f}")
                print(f"  Difference: ${offer_cac['effective_equity'] - offer_normal['effective_equity']:,.0f}")
                
                assert abs((offer_cac['effective_equity'] - offer_normal['effective_equity']) - 10000) < 1, "CAC bonus not applied correctly"
                break

print("\n\n" + "="*60)
print("ALL TESTS PASSED! ✓")
print("- Kavak Total toggle works correctly")
print("- Amortization columns add up exactly")
print("- Custom service fee is applied")
print("- CAC bonus increases equity")
print("="*60)