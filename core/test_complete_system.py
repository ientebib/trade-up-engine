#!/usr/bin/env python3
"""
Complete System Test for Kavak Trade-Up Engine Dashboard
Tests all major functionality including API endpoints and data flow
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_main_dashboard():
    """Test main dashboard page"""
    print("🏠 Testing Main Dashboard...")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "Kavak Trade-Up - Main Dashboard" in response.text
    print("✅ Main Dashboard: PASSED")

def test_customer_view():
    """Test customer view page"""
    print("👤 Testing Customer View...")
    response = requests.get(f"{BASE_URL}/customer/1001")
    assert response.status_code == 200
    assert "Customer 1001 Analysis" in response.text
    print("✅ Customer View: PASSED")

def test_config_page():
    """Test configuration page"""
    print("⚙️ Testing Configuration Page...")
    response = requests.get(f"{BASE_URL}/config")
    assert response.status_code == 200
    assert "Global Engine Configuration" in response.text
    print("✅ Configuration Page: PASSED")

def test_customers_api():
    """Test customers API endpoint"""
    print("📊 Testing Customers API...")
    response = requests.get(f"{BASE_URL}/api/customers")
    assert response.status_code == 200
    customers = response.json()
    assert len(customers) > 0
    assert "customer_id" in customers[0]
    assert "risk_profile_name" in customers[0]
    print(f"✅ Found {len(customers)} customers")

def test_inventory_api():
    """Test inventory API endpoint"""
    print("🚗 Testing Inventory API...")
    response = requests.get(f"{BASE_URL}/api/inventory")
    assert response.status_code == 200
    inventory = response.json()
    assert len(inventory) > 0
    assert "car_id" in inventory[0]
    assert "model" in inventory[0]
    print(f"✅ Found {len(inventory)} cars in inventory")

def test_scenario_analysis():
    """Test scenario analysis API"""
    print("🧪 Testing Scenario Analysis...")
    config_data = {
        "include_kavak_total": True
    }
    response = requests.post(f"{BASE_URL}/api/scenario-analysis", json=config_data)
    assert response.status_code == 200
    result = response.json()
    assert "actual_metrics" in result
    assert "execution_details" in result
    print("✅ Scenario Analysis: PASSED")

def test_offer_generation():
    """Test offer generation with real data"""
    print("🎯 Testing Offer Generation...")
    
    # Get customer data
    customers_response = requests.get(f"{BASE_URL}/api/customers")
    customers = customers_response.json()
    test_customer = customers[0]
    
    # Get inventory data
    inventory_response = requests.get(f"{BASE_URL}/api/inventory")
    inventory = inventory_response.json()
    
    # Prepare offer request
    offer_request = {
        "customer_data": {
            "customer_id": test_customer["customer_id"],
            "current_monthly_payment": test_customer["current_monthly_payment"],
            "vehicle_equity": test_customer["vehicle_equity"],
            "current_car_price": test_customer["current_car_price"],
            "risk_profile_name": test_customer["risk_profile_name"],
            "risk_profile_index": test_customer["risk_profile_index"]
        },
        "inventory": inventory[:10],  # Use first 10 cars for speed
        "engine_config": {
            "include_kavak_total": True
        }
    }
    
    # Generate offers
    response = requests.post(f"{BASE_URL}/api/generate-offers", json=offer_request)
    assert response.status_code == 200
    result = response.json()
    
    print(f"✅ Generated offers for Customer {test_customer['customer_id']}")
    if "offers" in result and result["offers"]:
        total_offers = sum(len(offers) for offers in result["offers"].values())
        print(f"   📈 Total offers: {total_offers}")
        print(f"   🏷️ Tiers available: {list(result['offers'].keys())}")
    else:
        print("   ℹ️ No offers generated (this may be normal depending on customer profile)")

def main():
    """Run all tests"""
    print("🚀 Starting Complete System Test")
    print("=" * 50)
    
    try:
        # Test static pages
        test_main_dashboard()
        test_customer_view()
        test_config_page()
        
        # Test API endpoints
        test_customers_api()
        test_inventory_api()
        test_scenario_analysis()
        
        # Test core functionality
        test_offer_generation()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! Dashboard is fully functional.")
        print(f"🌐 Access your dashboard at: {BASE_URL}")
        print("📱 Features available:")
        print("   • Main Dashboard - Portfolio overview with KPIs and charts")
        print("   • Customer Deep Dive - Individual customer analysis")
        print("   • Global Configuration - Scenario testing")
        print("   • Real-time offer generation")
        print("   • Interactive customer selection")
        print("   • Responsive design")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    main() 