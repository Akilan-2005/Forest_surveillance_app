#!/usr/bin/env python3
"""
Test script to identify any remaining issues with the Wildlife Surveillance App
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    print("✅ App imported successfully")
    
    # Test MongoDB connection
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017/')
    db = client.wildlife_offence_db
    
    # Test database connection
    try:
        test_connection = db.command('ping')
        print(f"✅ MongoDB connection successful: {test_connection}")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
    
    # Test enhanced_yolo_service import
    try:
        from enhanced_yolo_service import get_enhanced_yolo_service, DetectionMode, ThreatLevel
        print("✅ Enhanced YOLO service imported successfully")
        
        # Test service initialization
        yolo_service = get_enhanced_yolo_service()
        if yolo_service:
            print(f"✅ Enhanced YOLO service initialized: {yolo_service.is_initialized()}")
        else:
            print("❌ Enhanced YOLO service failed to initialize")
    except ImportError as e:
        print(f"❌ Enhanced YOLO service import failed: {e}")
    
    print("\n🎯 All tests completed successfully!")
    print("🔍 If no errors shown above, the app should work correctly!")
    
except Exception as e:
    print(f"💥 Critical error during testing: {e}")
    print(f"💥 Error type: {type(e).__name__}")
    print(f"💥 Error details: {str(e)}")
