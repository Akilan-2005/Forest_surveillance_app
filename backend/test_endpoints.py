#!/usr/bin/env python3
"""
Simple test script to verify backend endpoints are working
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoints():
    print("Testing Wildlife Offence Detection System Endpoints...")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/auth/me")
        print(f"✅ Server is running (Status: {response.status_code})")
        if response.status_code == 401:
            print("   (Expected: Token required)")
    except Exception as e:
        print(f"❌ Server not running: {e}")
        return
    
    # Test 2: Test registration
    test_user = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpass123",
        "role": "user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=test_user)
        if response.status_code == 201:
            print("✅ User registration working")
        elif response.status_code == 400 and "already exists" in response.text:
            print("✅ User registration working (user already exists)")
        else:
            print(f"⚠️ Registration issue: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Registration failed: {e}")
    
    # Test 3: Test login
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            print("✅ User login working")
            token = response.json().get('token')
            
            # Test 4: Test reports endpoint with token
            headers = {"Authorization": f"Bearer {token}"}
            reports_response = requests.get(f"{BASE_URL}/api/reports/user", headers=headers)
            if reports_response.status_code == 200:
                print("✅ User reports endpoint working")
                reports = reports_response.json().get('reports', [])
                print(f"   Found {len(reports)} reports")
            else:
                print(f"⚠️ Reports endpoint issue: {reports_response.status_code} - {reports_response.text}")
                
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Login test failed: {e}")
    
    print("\n" + "=" * 50)
    print("Backend endpoint testing completed!")

if __name__ == "__main__":
    test_endpoints()


