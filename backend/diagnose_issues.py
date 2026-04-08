#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Wildlife Surveillance App
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_all_components():
    """Check all major components of the application"""
    print("🔍 COMPREHENSIVE SYSTEM DIAGNOSTIC")
    print("=" * 60)
    
    # 1. Check Python imports
    print("1. 🐍 PYTHON IMPORTS CHECK")
    try:
        import app
        print("   ✅ app.py - OK")
    except ImportError as e:
        print(f"   ❌ app.py - FAILED: {e}")
    
    try:
        from pymongo import MongoClient
        print("   ✅ pymongo - OK")
    except ImportError as e:
        print(f"   ❌ pymongo - FAILED: {e}")
    
    try:
        from bson import ObjectId
        print("   ✅ bson - OK")
    except ImportError as e:
        print(f"   ❌ bson - FAILED: {e}")
    
    try:
        from flask import Flask, request, jsonify
        print("   ✅ flask - OK")
    except ImportError as e:
        print(f"   ❌ flask - FAILED: {e}")
    
    try:
        from flask_cors import CORS
        print("   ✅ flask_cors - OK")
    except ImportError as e:
        print(f"   ❌ flask_cors - FAILED: {e}")
    
    try:
        from flask_socketio import SocketIO, emit
        print("   ✅ flask_socketio - OK")
    except ImportError as e:
        print(f"   ❌ flask_socketio - FAILED: {e}")
    
    try:
        from flask_mail import Mail, Message
        print("   ✅ flask_mail - OK")
    except ImportError as e:
        print(f"   ❌ flask_mail - FAILED: {e}")
    
    try:
        from dotenv import load_dotenv
        print("   ✅ python-dotenv - OK")
    except ImportError as e:
        print(f"   ❌ python-dotenv - FAILED: {e}")
    
    # 2. Check enhanced_yolo_service
    print("\n2. 🔍 ENHANCED YOLO SERVICE CHECK")
    try:
        from enhanced_yolo_service import get_enhanced_yolo_service, DetectionMode, ThreatLevel
        print("   ✅ enhanced_yolo_service - OK")
        
        # Test service initialization
        yolo_service = get_enhanced_yolo_service()
        if yolo_service:
            print(f"   ✅ YOLO service initialized: {yolo_service.is_initialized()}")
        else:
            print("   ❌ YOLO service failed to initialize")
    except ImportError as e:
        print(f"   ❌ enhanced_yolo_service import FAILED: {e}")
    
    # 3. Check MongoDB connection
    print("\n3. 🗄️ MONGODB CONNECTION CHECK")
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client.wildlife_offence_db
        
        # Test database connection
        test_connection = db.command('ping')
        print(f"   ✅ MongoDB connection: {test_connection}")
        
        # Test collections
        reports_count = db.reports.count_documents({})
        print(f"   ✅ Reports collection accessible: {reports_count} documents")
        
        client.close()
    except Exception as e:
        print(f"   ❌ MongoDB connection FAILED: {e}")
    
    # 4. Check Flask app configuration
    print("\n4. 🌐 FLASK APP CONFIGURATION CHECK")
    try:
        from app import app
        print(f"   ✅ Flask app created: {app}")
        print(f"   ✅ Routes configured: {len(app.url_map)} routes")
    except Exception as e:
        print(f"   ❌ Flask app configuration FAILED: {e}")
    
    # 5. Check environment variables
    print("\n5. 📋 ENVIRONMENT VARIABLES CHECK")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("   ✅ Environment variables loaded")
        
        # Check critical environment variables
        required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY', 'MONGODB_URI']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"   ✅ {var}: {'*' * 10}{value[-4:]}")
            else:
                print(f"   ⚠️ {var}: NOT SET")
    except Exception as e:
        print(f"   ❌ Environment variables check FAILED: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSTIC COMPLETE")
    print("\n📝 NEXT STEPS:")
    print("1. If all checks show ✅, try running the app:")
    print("   python app.py")
    print("2. If any ❌ appear, install missing dependencies:")
    print("   pip install flask flask-cors flask-socketio pymongo python-dotenv flask-mail")
    print("3. If MongoDB connection fails, check:")
    print("   - MongoDB service is running")
    print("   - Connection string is correct")
    print("   - Database exists and is accessible")
    print("4. If enhanced_yolo_service fails, check:")
    print("   - enhanced_yolo_service.py file exists")
    print("   - YOLO model files are in yolo_model/ directory")
    print("   - Required dependencies are installed")
    print("\n🚀 The application should be ready to run!")

if __name__ == '__main__':
    check_all_components()
