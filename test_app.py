#!/usr/bin/env python3
"""Test the application without running a server"""

import sys
sys.path.append('/Users/isaacentebi/Desktop/Trade-Up-Engine')

from data import database
from app.services.offer_service import offer_service

# Test database connection
print("Testing database connection...")
status = database.test_database_connection()
print(f"Customers: {status['customers']['count']}")
print(f"Inventory: {status['inventory']['count']}")

# Test getting a customer
print("\nTesting customer retrieval...")
customers, _ = database.search_customers(limit=1)
if customers:
    customer = customers[0]
    print(f"Customer: {customer['customer_id']}")
    print(f"Monthly Payment: ${customer.get('current_monthly_payment', 0):,.0f}")
    
    # Test offer generation with two-stage filtering
    print("\nTesting offer generation with two-stage filtering...")
    try:
        offers = offer_service.generate_offers_for_customer(customer['customer_id'])
        total_offers = sum(len(tier) for tier in offers['offers'].values())
        print(f"Generated {total_offers} offers")
        print(f"Stats: {offers.get('stats', {})}")
    except Exception as e:
        print(f"Error generating offers: {e}")
else:
    print("No customers found")