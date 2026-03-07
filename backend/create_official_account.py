#!/usr/bin/env python3
"""
Script to create an official account for testing
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def create_official_account():
    print("Creating official account...")
    
    # Create official account
    official_data = {
        "name": "Forest Official",
        "email": "official@forest.gov",
        "password": "official123",
        "role": "official"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=official_data)
        if response.status_code == 201:
            print("✅ Official account created successfully!")
        elif response.status_code == 400 and "already exists" in response.text:
            print("✅ Official account already exists")
        else:
            print(f"⚠️ Official account creation issue: {response.status_code} - {response.text}")
            
        # Test login as official
        login_data = {
            "email": "official@forest.gov",
            "password": "official123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            print("✅ Official login working")
            token = response.json().get('token')
            
            # Test officials reports endpoint
            headers = {"Authorization": f"Bearer {token}"}
            reports_response = requests.get(f"{BASE_URL}/api/reports", headers=headers)
            if reports_response.status_code == 200:
                print("✅ Officials reports endpoint working")
                reports = reports_response.json().get('reports', [])
                print(f"   Found {len(reports)} reports for officials")
            else:
                print(f"⚠️ Officials reports endpoint issue: {reports_response.status_code} - {reports_response.text}")
                
        else:
            print(f"❌ Official login failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_official_account()


