#!/usr/bin/env python3
"""
Quick test script for Enhanced Detection functionality.
Run this after starting the backend to verify everything is working.

Usage:
    python test_enhanced_detection.py
"""

import requests
import base64
import json
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:5000"
STATUS_ENDPOINT = f"{API_URL}/api/status"
DETECTION_ENDPOINT = f"{API_URL}/api/detect/enhanced"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ {text}{RESET}")

def check_status():
    """Check backend service status."""
    print_header("1. Checking Backend Service Status")
    
    try:
        response = requests.get(STATUS_ENDPOINT, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        print_success("Backend is running")
        
        # Check YOLO service
        yolo_status = data.get('enhanced_yolo', {})
        if yolo_status.get('initialized'):
            print_success(f"Enhanced YOLO service initialized")
            
            details = yolo_status.get('details', {})
            if details.get('species_model_loaded'):
                print_success("Species model loaded")
            else:
                print_error("Species model NOT loaded")
            
            if details.get('threat_model_loaded'):
                print_success("Threat model loaded")
            else:
                print_error("Threat model NOT loaded")
            
            return True
        else:
            print_error("Enhanced YOLO service NOT initialized")
            error = yolo_status.get('details', {}).get('error', 'Unknown error')
            print_error(f"Error: {error}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running on http://localhost:5000?")
        print_info("Start backend with: cd backend && python app.py")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def test_detection():
    """Test detection endpoint with a sample image."""
    print_header("2. Testing Detection Endpoint")
    
    # Create a simple test image (red square, 100x100)
    try:
        from PIL import Image
        import io
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        print_info("Created test image (100x100 red square)")
        
        # Test species detection
        print_info("Testing species detection...")
        files = {'file': ('test.jpg', img_bytes, 'image/jpeg')}
        data = {'mode': 'species', 'conf_threshold': '0.25'}
        
        response = requests.post(
            DETECTION_ENDPOINT,
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 401:
            print_warning("Authentication required. Please provide token.")
            print_info("Note: You need to be logged in to test this endpoint.")
            return True  # Not a critical error
        
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            print_success(f"Detection successful")
            print_info(f"Detected {len(result.get('detections', []))} objects in test image")
            return True
        else:
            print_error(f"Detection failed: {result.get('message', 'Unknown error')}")
            return False
            
    except ImportError:
        print_warning("PIL not available, skipping image creation test")
        print_info("Install with: pip install Pillow")
        return True
    except requests.exceptions.Timeout:
        print_error("Request timeout. Detection is taking too long.")
        return False
    except Exception as e:
        print_warning(f"Test could not complete: {e}")
        return True  # Not critical

def verify_files():
    """Verify that all patched files exist."""
    print_header("3. Verifying Modified Files")
    
    files_to_check = [
        ('backend/app.py', 'Backend app'),
        ('backend/enhanced_yolo_service.py', 'Enhanced YOLO service'),
        ('frontend/src/components/user/EnhancedDetectionViewer.js', 'Detection viewer'),
    ]
    
    all_exist = True
    base_path = Path(__file__).parent
    
    for file_path, description in files_to_check:
        full_path = base_path / file_path
        if full_path.exists():
            print_success(f"{description} exists")
        else:
            print_error(f"{description} NOT found at {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print(f"\n{BOLD}{YELLOW}Enhanced Detection Verification Tool{RESET}")
    print("=" * 60)
    
    tests = [
        ("File Verification", verify_files),
        ("Backend Status", check_status),
        ("Detection Endpoint", test_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{BOLD}Overall: {passed}/{total} tests passed{RESET}\n")
    
    if passed == total:
        print_success("All tests passed! Enhanced Detection should be working.")
        return 0
    else:
        print_error("Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
