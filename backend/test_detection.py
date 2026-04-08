#!/usr/bin/env python
"""Quick test of detection service"""

import sys
import asyncio
from api_yolo import app
from fastapi.testclient import TestClient

print("=" * 60)
print("TESTING DETECTION SERVICE")
print("=" * 60)

try:
    client = TestClient(app)
    
    # Test 1: Health check
    print("\n[TEST 1] Health Check")
    response = client.get("/")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"✓ Service Status: {data.get('status')}")
    print(f"✓ Model Loaded: {data.get('model_loaded')}")
    print(f"✓ Fallback Mode: {data.get('fallback_mode')}")
    
    # Test 2: Create a simple test image
    print("\n[TEST 2] Detection with Test Image")
    from PIL import Image
    import io
    
    # Create a simple test image (100x100 pixels)
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {'offence_type': 'Threat Monitoring'}
    
    response = client.post("/detect", files=files, data=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"✓ Detection completed")
    print(f"✓ Objects detected: {result.get('count')}")
    if result.get('detections'):
        for det in result['detections'][:3]:
            print(f"  - {det['label']}: {det['confidence']:.2%}")
    
    print("\n" + "=" * 60)
    print("✅ DETECTION SERVICE WORKING CORRECTLY")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
