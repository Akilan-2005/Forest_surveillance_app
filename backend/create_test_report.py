#!/usr/bin/env python3
"""
Script to create a test report for testing the system
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def create_test_report():
    print("Creating test report...")
    
    # First, login to get a token
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return
        
        token = response.json().get('token')
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a test report
        test_report = {
            "title": "Test Wildlife Offence Report",
            "description": "This is a test report to verify the system is working properly. I observed suspicious activity in the forest area.",
            "offence_type": "Poaching",
            "location": {
                "lat": 20.5937,
                "lng": 78.9629,
                "address": "Test Location, India"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/reports", json=test_report, headers=headers)
        if response.status_code == 201:
            print("✅ Test report created successfully!")
            report_data = response.json()
            print(f"   Report ID: {report_data['report']['_id']}")
            print(f"   Severity: {report_data['report']['severity']}")
        else:
            print(f"❌ Report creation failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_test_report()


