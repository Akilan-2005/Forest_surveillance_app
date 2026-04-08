import requests
import json
import base64
from io import BytesIO
from PIL import Image
import sys

# Create a test image
print("📸 Creating test image...")
img = Image.new('RGB', (100, 100), color='red')
img_bytes = BytesIO()
img.save(img_bytes, format='PNG')
img_bytes.seek(0)
img_data = base64.b64encode(img_bytes.read()).decode('utf-8')

# Test report submission with threat detection mode
test_report = {
    "title": "Test Threat Detection Report",
    "description": "Testing enum serialization fix for threat detection",
    "offence_type": "Threat Monitoring",
    "media_type": "image",
    "media_data": f"data:image/png;base64,{img_data}",
    "location": {
        "lat": 6.5244,
        "lng": 3.3792,
        "address": "Lagos, Nigeria",
        "accuracy": 100
    }
}

# First, need to login to get token
login_data = {
    "email": "testuser@example.com",
    "password": "password123"
}

try:
    # Try to login
    print("🔐 Attempting login...")
    login_response = requests.post('http://localhost:5000/api/auth/login', json=login_data, timeout=5)
    print(f"Login response status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        token = login_response.json().get('token')
        print(f"✓ Login successful, token obtained")
        
        # Submit report with token
        print("📝 Submitting report with threat detection mode...")
        headers = {'Authorization': f'Bearer {token}'}
        report_response = requests.post('http://localhost:5000/api/reports', json=test_report, headers=headers, timeout=10)
        
        print(f"\nReport submission status: {report_response.status_code}")
        
        if report_response.status_code == 201:
            print("✅ SUCCESS! Report submitted successfully with threat detection mode!")
            print(f"Response: {json.dumps(report_response.json(), indent=2)}")
        else:
            print(f"❌ Report submission failed")
            print(f"Status: {report_response.status_code}")
            print(f"Response: {report_response.text}")
    else:
        print(f"❌ Login failed")
        print(f"Status: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
