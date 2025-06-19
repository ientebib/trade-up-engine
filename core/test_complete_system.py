#!/usr/bin/env python3
"""
Complete System Test for Trade-Up Engine
Tests all major functionality including API endpoints and data flow
Compatible with both pytest and standalone execution
"""

import requests
import json
import time
import sys
import pytest

BASE_URL = "http://localhost:8000"

def wait_for_server(max_attempts=10, delay=2):
    """Wait for the server to be ready"""
    print("🔄 Waiting for server to be ready...")
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            if attempt < max_attempts - 1:
                print(f"⏳ Attempt {attempt + 1}/{max_attempts} - Server not ready, waiting {delay}s...")
                time.sleep(delay)
            else:
                print("❌ Server is not responding after maximum attempts")
                return False
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_server_running():
    """Ensure server is running before any tests"""
    if not wait_for_server():
        pytest.skip("Server is not responding. Make sure it's running.")

@pytest.fixture(scope="session")
def test_customer():
    """Get a test customer for offer generation tests"""
    try:
        response = requests.get(f"{BASE_URL}/api/customers", timeout=10)
        if response.status_code == 200:
            data = response.json()
            customers = data.get("customers", [])
            if customers:
                return customers[0]
    except Exception:
        pass
    return None

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    print("✅ Health Check: PASSED")
    print(f"   Environment: {health_data.get('environment', 'unknown')}")
    print(f"   External calls: {health_data.get('external_calls', 'unknown')}")

def test_main_dashboard():
    """Test main dashboard page"""
    print("🏠 Testing Main Dashboard...")
    response = requests.get(f"{BASE_URL}/", timeout=10)
    assert response.status_code == 200
    print("✅ Main Dashboard: PASSED")

def test_dev_info():
    """Test development info endpoint"""
    print("🔧 Testing Development Info...")
    response = requests.get(f"{BASE_URL}/dev-info", timeout=10)
    assert response.status_code == 200
    dev_info = response.json()
    print("✅ Development Info: PASSED")
    print(f"   Virtual agent compatible: {dev_info.get('virtual_agent_compatible', 'unknown')}")
    print(f"   Data sources: {dev_info.get('data_sources', [])}")

def test_customers_api():
    """Test customers API endpoint"""
    print("👥 Testing Customers API...")
    response = requests.get(f"{BASE_URL}/api/customers", timeout=10)
    assert response.status_code == 200
    data = response.json()
    customers = data.get("customers", [])
    assert len(customers) > 0
    assert "customer_id" in customers[0]
    assert "risk_profile_name" in customers[0]
    print(f"✅ Found {len(customers)} customers")

def test_inventory_api():
    """Test inventory API endpoint"""
    print("🚗 Testing Inventory API...")
    response = requests.get(f"{BASE_URL}/api/inventory", timeout=10)
    assert response.status_code == 200
    data = response.json()
    inventory = data.get("inventory", [])
    assert len(inventory) > 0
    assert "car_id" in inventory[0]
    assert "model" in inventory[0]
    print(f"✅ Found {len(inventory)} cars in inventory")

def test_config_api():
    """Test configuration API endpoint"""
    print("⚙️ Testing Configuration API...")
    response = requests.get(f"{BASE_URL}/api/config", timeout=10)
    assert response.status_code == 200
    data = response.json()
    config = data.get("config", {})
    assert "min_npv_threshold" in config
    print("✅ Configuration API: PASSED")
    print(f"   NPV Threshold: {config.get('min_npv_threshold', 'unknown')}")

def test_offer_generation(test_customer):
    """Test offer generation with real data"""
    if not test_customer:
        pytest.skip("No test customer available")
        
    print("🎯 Testing Offer Generation...")
    customer_id = test_customer["customer_id"]
    response = requests.post(f"{BASE_URL}/api/generate-offers?customer_id={customer_id}", timeout=30)
    
    assert response.status_code == 200
    result = response.json()
    offers = result.get("offers", [])
    print(f"✅ Generated {len(offers)} offers for Customer {customer_id}")
    if offers:
        print(f"   First offer: {offers[0].get('car_id', 'unknown')} - NPV: {offers[0].get('final_npv', 'unknown')}")
    else:
        print("   ℹ️ No offers generated (this may be normal depending on customer profile)")

def main():
    """Run all tests when executed as standalone script"""
    print("🚀 Starting Complete System Test")
    print("=" * 50)
    
    # First, wait for server to be ready
    if not wait_for_server():
        print("❌ Server is not responding. Make sure it's running:")
        print("   • Run: uvicorn main_dev:app --host 0.0.0.0 --port 8000")
        print("   • Or use: ./agent_setup.sh")
        sys.exit(1)
    
    tests_passed = 0
    total_tests = 0
    test_customer = None
    
    # Get test customer
    try:
        response = requests.get(f"{BASE_URL}/api/customers", timeout=10)
        if response.status_code == 200:
            data = response.json()
            customers = data.get("customers", [])
            if customers:
                test_customer = customers[0]
    except Exception:
        pass
    
    # Run all tests
    test_functions = [
        ("Health Check", test_health_check),
        ("Main Dashboard", test_main_dashboard),
        ("Development Info", test_dev_info),
        ("Customers API", test_customers_api),
        ("Inventory API", test_inventory_api),
        ("Configuration API", test_config_api),
    ]
    
    for test_name, test_func in test_functions:
        total_tests += 1
        try:
            test_func()
            tests_passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
    
    # Test offer generation
    total_tests += 1
    try:
        if test_customer:
            test_offer_generation(test_customer)
            tests_passed += 1
        else:
            print("⚠️ Skipping offer generation - no test customer available")
    except Exception as e:
        print(f"❌ Offer generation failed: {e}")
    
    print("=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Trade-Up Engine is fully functional.")
        print(f"🌐 Access your application at: {BASE_URL}")
        print("📱 Available endpoints:")
        print("   • Main Dashboard: /")
        print("   • Health Check: /health")
        print("   • Development Info: /dev-info")
        print("   • Customers API: /api/customers")
        print("   • Inventory API: /api/inventory")
        print("   • Configuration API: /api/config")
        return True
    else:
        print(f"⚠️ {total_tests - tests_passed} tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
