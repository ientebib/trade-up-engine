#!/usr/bin/env python3
"""
Simple Test for Trade-Up Engine
Quick connectivity and basic endpoint test for virtual agent environment
"""

import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def test_connection():
    """Test basic server connection"""
    print("🔌 Testing server connection...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is responding!")
            health_data = response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Environment: {health_data.get('environment', 'unknown')}")
            return True
        else:
            print(f"❌ Server responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_basic_endpoints():
    """Test basic endpoints"""
    endpoints = [
        ("/", "Main Dashboard"),
        ("/dev-info", "Development Info"),
        ("/api/customers", "Customers API"),
        ("/api/inventory", "Inventory API"),
        ("/api/config", "Configuration API")
    ]
    
    passed = 0
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
                passed += 1
            else:
                print(f"❌ {name}: Status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: Failed - {e}")
    
    return passed, len(endpoints)

def main():
    print("🚀 Simple Trade-Up Engine Test")
    print("=" * 40)
    
    # Test connection first
    if not test_connection():
        print("\n💡 To start the server:")
        print("   ./agent_setup.sh")
        print("   OR")
        print("   uvicorn main_dev:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    print("\n🧪 Testing endpoints...")
    passed, total = test_basic_endpoints()
    
    print("=" * 40)
    print(f"📊 Results: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print(f"🌐 Access your app at: {BASE_URL}")
        return True
    else:
        print(f"⚠️ {total - passed} endpoints failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
