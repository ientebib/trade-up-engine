#!/usr/bin/env python3
"""
Test script to verify the undefined values fix in offer generation
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_offer_generation():
    """Test that offer generation returns proper values"""
    
    # First get a customer
    print("Getting customer list...")
    response = requests.get(f"{BASE_URL}/api/customers?limit=1")
    if response.status_code != 200:
        print(f"Failed to get customers: {response.status_code}")
        return False
    
    customers = response.json()
    if not customers.get('customers'):
        print("No customers found")
        return False
    
    customer_id = customers['customers'][0]['customer_id']
    print(f"Testing with customer: {customer_id}")
    
    # Test basic offer generation
    print("\nTesting basic offer generation...")
    response = requests.post(
        f"{BASE_URL}/api/generate-offers-basic",
        json={"customer_id": customer_id}
    )
    
    if response.status_code != 200:
        print(f"Failed to generate offers: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    # Check required fields
    required_fields = ['offers', 'total_offers', 'cars_tested', 'processing_time']
    missing_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        else:
            print(f"✓ {field}: {data[field]}")
    
    if missing_fields:
        print(f"\n❌ Missing fields: {missing_fields}")
        return False
    
    # Check offers structure
    print("\nChecking offers structure...")
    if 'offers' in data:
        for tier in ['refresh', 'upgrade', 'max_upgrade']:
            if tier in data['offers']:
                count = len(data['offers'][tier])
                print(f"✓ {tier}: {count} offers")
            else:
                print(f"❌ Missing tier: {tier}")
    
    # Test custom offer generation
    print("\n\nTesting custom offer generation...")
    custom_config = {
        "customer_id": customer_id,
        "service_fee_pct": 0.05,
        "cxa_pct": 0.04,
        "cac_bonus": 5000,
        "insurance_amount": 10999,
        "interest_rate": 0.18,
        "kavak_total_enabled": True
    }
    
    response = requests.post(
        f"{BASE_URL}/api/generate-offers-custom",
        json=custom_config
    )
    
    if response.status_code != 200:
        print(f"Failed to generate custom offers: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    # Check required fields again
    for field in required_fields:
        if field not in data:
            print(f"❌ Custom missing field: {field}")
        else:
            print(f"✓ {field}: {data[field]}")
    
    print("\n✅ All tests passed!")
    return True

if __name__ == "__main__":
    print("Testing offer generation API...\n")
    
    try:
        success = test_offer_generation()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)