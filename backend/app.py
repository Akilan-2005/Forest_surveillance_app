from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_mail import Mail, Message
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import re
from PIL import Image
import io
import base64
import json
from datetime import datetime, timedelta
import jwt
import bcrypt
from functools import wraps
import requests
from geopy.geocoders import Nominatim
from twilio.rest import Client as TwilioClient
# Import YOLOv3 detector with fallback
try:
    from yolo_detector import yolo_detector
    YOLO_AVAILABLE = True
    print("YOLOv3 detector loaded successfully")
except ImportError as e:
    print(f"YOLOv3 detector not available: {e}")
    print("Falling back to text-based analysis only")
    YOLO_AVAILABLE = False
    yolo_detector = None

# Import Enhanced YOLO service for dual-mode detection
try:
    from enhanced_yolo_service import get_enhanced_yolo_service, DetectionMode, ThreatLevel
    ENHANCED_YOLO_AVAILABLE = True
    print("Enhanced YOLO service available for dual-mode detection")
except ImportError as e:
    print(f"Enhanced YOLO service not available: {e}")
    ENHANCED_YOLO_AVAILABLE = False
    enhanced_yolo_service = None

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret')

# CORS configuration
CORS(app, origins=["http://localhost:3000"])

# SocketIO configuration
socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000")

# MongoDB configuration
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.wildlife_offence_db

# Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# YOLOv3 AI configuration (no API key needed)
print("Initializing YOLOv3 wildlife offence detector...")

# Initialize Enhanced YOLO service for dual-mode detection
enhanced_yolo_service = None
detection_mode = None  # Initialize detection_mode variable

if ENHANCED_YOLO_AVAILABLE:
    try:
        print("★ Attempting to initialize Enhanced YOLO service...")
        enhanced_yolo_service = get_enhanced_yolo_service()
        
        # CRITICAL: Call initialize() to load models
        if enhanced_yolo_service.initialize():
            status = enhanced_yolo_service.get_initialization_status()
            print(f"✓ Enhanced YOLO service initialized successfully")
            print(f"  - Species model loaded: {status['species_model_loaded']}")
            print(f"  - Threat model loaded: {status['threat_model_loaded']}")
            print(f"  - Fallback mode: {status['fallback_mode']}")
        else:
            status = enhanced_yolo_service.get_initialization_status()
            print(f"✗ Enhanced YOLO service failed to initialize")
            print(f"  Error: {status['error']}")
            enhanced_yolo_service = None
    except Exception as e:
        print(f"✗ Error initializing enhanced YOLO service: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        enhanced_yolo_service = None
else:
    print("✗ Enhanced YOLO service not available (ultralytics not installed)")

# Twilio configuration (optional)
twilio_client = None
if os.getenv('TWILIO_ACCOUNT_SID'):
    twilio_client = TwilioClient(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )

# Collections
users_collection = db.users
reports_collection = db.reports
officials_collection = db.officials

# Helpers
def normalize_severity(severity_value):
    if not severity_value:
        return 'Low'
    value = str(severity_value).strip().lower()
    if value in ['critical', 'high', 'severe']:
        return 'Critical'
    if value in ['medium', 'moderate']:
        return 'Medium'
    return 'Low'

def infer_severity_from_text(text):
    if not text:
        return 'Low'
    lower = text.lower()
    high_keywords = ['gun', 'weapon', 'dead', 'carcass', 'poach', 'shoot', 'blood']
    medium_keywords = ['trap', 'snare', 'vehicle', 'restricted', 'chainsaw', 'cutting']
    if any(k in lower for k in high_keywords):
        return 'Critical'
    if any(k in lower for k in medium_keywords):
        return 'Medium'
    return 'Low'

def extract_detected_objects(text):
    if not text:
        return []
    candidates = [
        'gun', 'weapon', 'rifle', 'trap', 'snare', 'chainsaw', 'vehicle', 'car', 'jeep',
        'dead animal', 'carcass', 'blood', 'injured animal', 'fire', 'axe'
    ]
    lower = text.lower()
    found = []
    for word in candidates:
        if word in lower:
            found.append(word)
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for w in found:
        if w not in seen:
            unique.append(w)
            seen.add(w)
    return unique

# JWT token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Status endpoint (no auth required - for debugging)
@app.route('/api/status', methods=['GET'])
def get_status():
    """Get backend service status and initialization details."""
    status = {
        'backend': 'running',
        'enhanced_yolo': {
            'available': enhanced_yolo_service is not None,
            'initialized': enhanced_yolo_service.is_initialized() if enhanced_yolo_service else False
        }
    }
    
    if enhanced_yolo_service:
        status['enhanced_yolo']['details'] = enhanced_yolo_service.get_initialization_status()
    
    return jsonify(status), 200

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if user already exists
    if users_collection.find_one({'email': data['email']}):
        return jsonify({'message': 'User already exists'}), 400
    
    # Hash password
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    # Create user
    user = {
        'name': data['name'],
        'email': data['email'],
        'password': hashed_password,
        'role': data.get('role', 'user'),  # 'user' or 'official'
        'phone': data.get('phone', ''),
        'created_at': datetime.utcnow()
    }
    
    result = users_collection.insert_one(user)
    user['_id'] = str(result.inserted_id)
    del user['password']
    
    return jsonify({'message': 'User created successfully', 'user': user}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = users_collection.find_one({'email': data['email']})
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': str(user['_id']),
        'role': user['role'],
        'exp': datetime.now() + timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
    
    user['_id'] = str(user['_id'])
    del user['password']
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user
    })

# Enhanced Dual-Mode Detection endpoint
@app.route('/api/detect/enhanced', methods=['POST'])
@token_required
def enhanced_detect_objects(current_user):
    """
    Enhanced dual-mode object detection endpoint.
    
    Supports two detection modes:
    - species: Detect animal species only
    - threat: Detect humans, weapons, and suspicious objects
    
    Expects:
        - file: Image file (multipart/form-data) OR
        - image_data: Base64 encoded image (JSON)
        - mode: Detection mode ('species' or 'threat')
    
    Returns:
        {
            "success": true,
            "mode": "species|threat",
            "detections": [
                {
                    "label": "lion",
                    "confidence": 0.87,
                    "box": [x1, y1, x2, y2],
                    "color": "#00FF00",
                    "display_label": "lion - 87%",
                    "threat_level": "LOW|MEDIUM|CRITICAL",
                    "detection_type": "species|threat"
                }
            ],
            "message": "Detected 2 objects"
        }
    """
    try:
        # Check if enhanced YOLO service is available
        if not enhanced_yolo_service:
            error_msg = "Enhanced detection service not initialized at startup. Check backend logs for initialization errors."
            print(f"✗ ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'detections': [],
                'message': error_msg
            }), 503
        
        # If service exists but not initialized, try to diagnose and reinitialize if needed
        if not enhanced_yolo_service.is_initialized():
            status = enhanced_yolo_service.get_initialization_status()
            
            # Log detailed status for debugging
            print(f"⚠️  Detection service not initialized on request:")
            print(f"    - CV2 available: {status.get('cv2_available')}")
            print(f"    - Ultralytics available: {status.get('ultralytics_available')}")
            print(f"    - Species model loaded: {status.get('species_model_loaded')}")
            print(f"    - Threat model loaded: {status.get('threat_model_loaded')}")
            print(f"    - Error: {status.get('error')}")
            
            # Try to initialize if not already initialized
            print("Attempting to initialize YOLO service on-demand...")
            if enhanced_yolo_service.initialize():
                print("✓ Successfully initialized on-demand!")
                status = enhanced_yolo_service.get_initialization_status()
            else:
                # Still failed, return error with details
                error_msg = f"Detection service failed to initialize. Error: {status.get('error', 'Unknown error')}"
                print(f"✗ ERROR: {error_msg}")
                return jsonify({
                    'success': False,
                    'detections': [],
                    'message': error_msg,
                    'debug': {
                        'cv2_available': status.get('cv2_available'),
                        'ultralytics_available': status.get('ultralytics_available'),
                        'error_details': str(status.get('error'))
                    }
                }), 503
        
        # Get detection mode
        mode = request.form.get('mode') or request.json.get('mode', 'species').lower()
        if mode not in ['species', 'threat']:
            return jsonify({
                'success': False,
                'message': 'Invalid mode. Must be "species" or "threat"'
            }), 400
        
        detection_mode = DetectionMode.SPECIES if mode == 'species' else DetectionMode.THREAT
        
        # Get confidence threshold
        conf_threshold = float(request.form.get('conf_threshold', 0.25))
        
        image_bytes = None
        
        # Check for multipart file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not '.' in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({
                    'success': False,
                    'message': 'Invalid file type. Allowed: png, jpg, jpeg'
                }), 400
            
            image_bytes = file.read()
        
        # Check for JSON with base64 image data
        elif request.is_json:
            data = request.get_json()
            image_data = data.get('image_data')
            if image_data:
                # Handle base64 data URI format
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
        
        if not image_bytes:
            return jsonify({
                'success': False,
                'message': 'No image provided. Send file (multipart) or image_data (base64 JSON)'
            }), 400
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if len(image_bytes) > max_size:
            return jsonify({
                'success': False,
                'message': 'File too large. Maximum size: 10MB'
            }), 400
        
        # Run detection based on mode
        try:
            print(f"Running {mode} detection (threshold: {conf_threshold})...")
            if detection_mode == DetectionMode.SPECIES:
                detections = enhanced_yolo_service.detect_species(image_bytes, conf_threshold)
                mode_label = "Species Monitoring"
            else:
                detections = enhanced_yolo_service.detect_threats(image_bytes, conf_threshold)
                mode_label = "Threat Monitoring"
                
                # Check for critical threats and trigger alerts
                critical_detections = [d for d in detections if d.get('threat_level') == 'CRITICAL']
                if critical_detections:
                    print(f"🚨 ALERT: {len(critical_detections)} critical threats detected!")
                    # Trigger real-time alert to officials
                    try:
                        socketio.emit('critical_threat_alert', {
                            'user_id': str(current_user['_id']),
                            'user_name': current_user.get('name', 'Unknown'),
                            'detections': critical_detections,
                            'message': f'CRITICAL THREAT DETECTED: {len(critical_detections)} high-risk objects found'
                        }, room='officials')
                        print("✓ Critical threat alert sent to officials")
                    except Exception as e:
                        print(f"⚠ Failed to send critical threat alert: {e}")
            
            print(f"✓ {mode_label} detection complete: {len(detections)} objects detected")
            return jsonify({
                'success': True,
                'mode': mode,
                'mode_label': mode_label,
                'detections': detections,
                'message': f'Detected {len(detections)} objects using {mode_label}'
            })
        
        except Exception as detection_error:
            error_msg = f"Detection processing error: {type(detection_error).__name__}: {str(detection_error)}"
            print(f"✗ {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'detections': [],
                'message': error_msg
            }), 500
    
    except Exception as e:
        error_msg = f"Unexpected error in enhanced detection: {type(e).__name__}: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'detections': [],
            'message': error_msg
        }), 500

@app.route('/api/yolo/detect', methods=['POST'])
@token_required
def detect_objects(current_user):
    """
    Run YOLO object detection on an uploaded image.
    
    Expects:
        - file: Image file (multipart/form-data) OR
        - image_data: Base64 encoded image (JSON)
    
    Returns:
        {
            "success": true,
            "detections": [
                {
                    "label": "fireextinguisher",
                    "confidence": 0.87,
                    "box": [x1, y1, x2, y2]
                }
            ],
            "message": "Detected 2 objects"
        }
    """
    try:
        # Check if YOLO service is available
        if not yolo_service or not yolo_service.is_initialized():
            return jsonify({
                'success': False,
                'detections': [],
                'message': 'YOLO service not available'
            }), 503
        
        image_bytes = None
        
        # Check for multipart file upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not '.' in file.filename or \
               file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({
                    'success': False,
                    'message': 'Invalid file type. Allowed: png, jpg, jpeg'
                }), 400
            
            image_bytes = file.read()
        
        # Check for JSON with base64 image data
        elif request.is_json:
            data = request.get_json()
            image_data = data.get('image_data')
            if image_data:
                # Handle base64 data URI format
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
        
        if not image_bytes:
            return jsonify({
                'success': False,
                'message': 'No image provided. Send file (multipart) or image_data (base64 JSON)'
            }), 400
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if len(image_bytes) > max_size:
            return jsonify({
                'success': False,
                'message': 'File too large. Maximum size: 10MB'
            }), 400
        
        # Get optional parameters
        conf_threshold = request.args.get('conf_threshold', 0.25)
        iou_threshold = request.args.get('iou_threshold', 0.45)
        try:
            conf_threshold = float(conf_threshold)
            iou_threshold = float(iou_threshold)
        except (ValueError, TypeError):
            conf_threshold = 0.25
            iou_threshold = 0.45
        
        # Run detection
        detections = yolo_service.detect_from_bytes(
            image_bytes,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold
        )
        
        return jsonify({
            'success': True,
            'detections': detections,
            'message': f'Detected {len(detections)} objects'
        })
    
    except Exception as e:
        print(f"YOLO detection error: {e}")
        return jsonify({
            'success': False,
            'detections': [],
            'message': f'Error processing image: {str(e)}'
        }), 500

# YOLOv3 AI analysis function (existing)
def analyze_media_with_yolo(image_data, description):
    try:
        # Validate input
        if not image_data:
            return {
                "offence_detected": False,
                "offence_type": "unknown",
                "severity": "Low",
                "confidence": 0.0,
                "detected_objects": [],
                "description": "No image provided for analysis"
            }
        
        # Check if YOLOv3 is available
        if not YOLO_AVAILABLE or yolo_detector is None:
            print("YOLOv3 not available, using text-based analysis")
            inferred = infer_severity_from_text(description or "")
            return {
                "offence_detected": inferred in ['Critical', 'Medium'],
                "offence_type": "text_analysis",
                "severity": inferred,
                "confidence": 0.3,
                "detected_objects": extract_detected_objects(description or ""),
                "description": "YOLOv3 not available, using text analysis"
            }
        
        print("Starting YOLOv3 analysis...")
        
        # Use YOLOv3 detector
        analysis_result = yolo_detector.analyze_wildlife_offence(image_data, description or "")
        
        print(f"YOLOv3 analysis completed: {analysis_result}")
        
        return analysis_result
            
    except Exception as e:
        print(f"YOLOv3 analysis error: {str(e)}")
        # Fallback to text-based analysis
        inferred = infer_severity_from_text(description or "")
        return {
            "offence_detected": inferred in ['Critical', 'Medium'],
            "offence_type": "unknown",
            "severity": inferred,
            "confidence": 0.3,
            "detected_objects": extract_detected_objects(description or ""),
            "description": f"YOLOv3 analysis failed, using text analysis: {str(e)}"
        }

# Report submission
@app.route('/api/reports', methods=['POST'])
@token_required
def submit_report(current_user):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'description', 'offence_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400
        
        # Get GPS location if available
        location = data.get('location', {})
        if location and location.get('lat') and location.get('lng'):
            try:
                # Enhanced location processing with accuracy validation
                lat = float(location['lat'])
                lng = float(location['lng'])
                accuracy = location.get('accuracy')
                
                # Validate coordinates
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    location = {
                        'lat': lat,
                        'lng': lng,
                        'address': location.get('address', 'Unknown location'),
                        'accuracy': accuracy,
                        'error': None
                    }
                print(f"📍 Location processed: lat={lat}, lng={lng}, accuracy={accuracy}")
            except Exception as loc_error:
                print(f"⚠️ Location processing error: {loc_error}")
                location = {
                    'lat': 0, 
                    'lng': 0, 
                    'address': 'Location not available',
                    'accuracy': None,
                    'error': 'Invalid coordinates provided'
                }
        else:
            location = {
                'lat': 0, 
                'lng': 0, 
                'address': 'Location not available',
                'accuracy': None,
                'error': 'No coordinates provided'
            }
            print(f"📍 Using default location: {location['address']}")
        
        # Analyze media with Enhanced YOLO dual-mode detection
        enhanced_detections = []  # Store enhanced detection results
        detection_mode = None  # Initialize detection_mode
        
        if data.get('media_type') == 'image' and data.get('media_data'):
            print(f"🖼️ Processing image media type")
            # Determine detection mode based on offence type
            offence_type = data.get('offence_type', '')
            print(f"🎯 Offence type: {offence_type}")
            
            if ENHANCED_YOLO_AVAILABLE and enhanced_yolo_service:
                if offence_type == 'Species Monitoring':
                    detection_mode = DetectionMode.SPECIES
                    print("🦁 Running Species Monitoring detection...")
                else:
                    detection_mode = DetectionMode.THREAT
                    print("🚨 Running Threat Monitoring detection...")
            else:
                print("⚠️ Enhanced YOLO service not available, skipping detection")
                enhanced_detections = []
            
            # Run enhanced detection
            if enhanced_yolo_service and enhanced_yolo_service.is_initialized():
                try:
                    print("🔍 Starting enhanced detection process...")
                    # Decode base64 image for enhanced detection
                    image_data = data['media_data']
                    if ',' in image_data:
                        image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    print(f"📸 Image decoded successfully, size: {len(image_bytes)} bytes")
                    
                    # Run detection based on mode
                    if detection_mode == DetectionMode.SPECIES:
                        enhanced_detections = enhanced_yolo_service.detect_species(image_bytes)
                        print(f"🦁 Species detection completed: {len(enhanced_detections)} animals found")
                    else:
                        enhanced_detections = enhanced_yolo_service.detect_threats(image_bytes)
                        print(f"🚨 Threat detection completed: {len(enhanced_detections)} threats found")
                        
                        # Check for critical threats
                        critical_threats = [d for d in enhanced_detections if d.get('threat_level') == 'CRITICAL']
                        if critical_threats:
                            print(f"🚨 ALERT: {len(critical_threats)} CRITICAL threats detected in report submission!")
                
                except Exception as e:
                    print(f"❌ Enhanced detection failed: {e}")
                    enhanced_detections = []
                    
                    # Show detection error toast
                    try:
                        import toast
                        toast.error('Detection analysis failed', {
                            id: 'detection-error',
                            duration: 3000,
                            icon: '🔍'
                        })
                        print("✅ Detection error toast sent")
                    except ImportError:
                        print("⚠️ Toast notification not available (toast library not installed)")
            else:
                print("⚠️ Enhanced YOLO service not initialized, skipping detection")
                enhanced_detections = []
        else:
            print("📝 No image media provided, skipping detection")
        
        print(f"🔍 Enhanced detections: {len(enhanced_detections)} found")
        for i, det in enumerate(enhanced_detections):
            print(f"  Detection {i+1}: {det.get('label', 'Unknown')} ({det.get('confidence', 0):.2f})")
        
        # Create report
        report = {
            'user_id': current_user['_id'],
            'user_name': current_user['name'],
            'user_email': current_user['email'],
            'title': data['title'],
            'description': data['description'],
            'offence_type': data['offence_type'],
            'media_type': data.get('media_type'),
            'media_data': data.get('media_data'),
            'location': location,
            'enhanced_detections': enhanced_detections,  # New field for enhanced detections
            'detection_mode': detection_mode.value if detection_mode else None,
            'status': 'New',
            'severity': normalize_severity(
                max([d.get('threat_level', 'LOW') for d in enhanced_detections]) if enhanced_detections else 'Low'
            ),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        print(f"📋 Report created with keys: {list(report.keys())}")
        
        # Override severity based on enhanced detections if available
        if enhanced_detections:
            max_conf = max([d.get('confidence', 0.0) for d in enhanced_detections])
            if max_conf >= 0.8:
                report['severity'] = "Critical"
            elif max_conf >= 0.5:
                report['severity'] = "Medium"
            elif max_conf > 0:
                report['severity'] = "Low"
            print(f"🎯 Severity set to: {report['severity']} (max confidence: {max_conf:.2f})")
        
        # Insert report into database
        try:
            print(f"💾 Attempting to insert report: {report.get('title', 'Unknown')}")
            print(f"👤 User ID: {current_user['_id']}")
            print(f"📊 Report data keys: {list(report.keys())}")
            print(f"🔗 MongoDB connection status: {client is not None}")
            print(f"🗄️ Database accessible: {db is not None}")
            
            # Test database connection
            try:
                test_connection = db.command('ping')
                print(f"✅ MongoDB ping successful: {test_connection}")
            except Exception as db_error:
                print(f"❌ MongoDB connection failed: {db_error}")
                return jsonify({'message': 'Database connection failed', 'error': str(db_error)}), 500
            
            result = reports_collection.insert_one(report)
            report['_id'] = str(result.inserted_id)
            
            print(f"✅ Report inserted successfully with ID: {report['_id']}")
            print(f"💾 MongoDB insert result: {result}")
            
            # Verify the report was actually inserted
            verification = reports_collection.find_one({'_id': result.inserted_id})
            if verification:
                print(f"✅ Report verified in database: {verification.get('title', 'Unknown')}")
            else:
                print(f"❌ Report verification failed - not found in database!")
            
        except Exception as e:
            print(f"❌ Database insertion failed: {e}")
            print(f"🔥 Error type: {type(e).__name__}")
            print(f"🔥 Error details: {str(e)}")
            
            # Check if it's a MongoDB specific error
            if "duplicate key" in str(e).lower():
                return jsonify({'message': 'Duplicate report - already exists', 'error': str(e)}), 409
            elif "connection" in str(e).lower():
                return jsonify({'message': 'Database connection lost', 'error': str(e)}), 503
            else:
                return jsonify({'message': 'Failed to save report to database', 'error': str(e)}), 500
        
        # Emit real-time alert to officials
        try:
            socketio.emit('new_report', {
                'report': report,
                'message': f'New {report["severity"]} severity report: {report["title"]}'
            }, room='officials')
            print("📡 Real-time alert sent to officials")
        except Exception as e:
            print(f"❌ Failed to send real-time alert: {e}")
        
        print(f"🎉 Report submission completed successfully!")
        
        # Show success toast notification
        try:
            import toast
            toast.success('Report submitted successfully!', { 
                'id': 'report-success',
                'duration': 5000,
                'icon': '🎉'
            })
            print("✅ Success toast notification sent")
        except ImportError:
            print("⚠️ Toast notification not available (toast library not installed)")
        
        return jsonify({
            'success': True,
            'message': 'Report submitted successfully',
            'report_id': report['_id'],
            'detections_count': len(enhanced_detections),
            'severity': report['severity'],
            'detection_summary': {
                'total_detections': len(enhanced_detections),
                'threat_level': max([d.get('threat_level', 'LOW') for d in enhanced_detections]) if enhanced_detections else 'LOW',
                'detection_mode': detection_mode,
                'critical_threats': len([d for d in enhanced_detections if d.get('threat_level') == 'CRITICAL'])
            }
        }), 201
        
    except Exception as outer_error:
        print(f"💥 CRITICAL ERROR in submit_report: {outer_error}")
        print(f"💥 Error type: {type(outer_error).__name__}")
        print(f"💥 Error details: {str(outer_error)}")
        
        # Show error toast notification
        try:
            import toast
            toast.error('Report submission failed!', {
                'id': 'report-error',
                'duration': 5000,
                'icon': '❌'
            })
            print("✅ Error toast notification sent")
        except ImportError:
            print("⚠️ Toast notification not available (toast library not installed)")
        
        return jsonify({
            'success': False,
            'message': 'Report submission failed',
            'error': str(outer_error),
            'error_type': type(outer_error).__name__
        })

def send_critical_alert(report):
    try:
        # Get all officials
        officials = list(officials_collection.find({}))
        
        for official in officials:
            msg = Message(
                subject=f"CRITICAL ALERT: {report['title']}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[official['email']]
            )
            msg.body = f"""
            CRITICAL WILDLIFE OFFENCE DETECTED
            
            Report ID: {report['_id']}
            Title: {report['title']}
            Description: {report['description']}
            Location: {report['location'].get('address', 'Unknown')}
            Severity: {report['severity']}
            AI Analysis: {report['ai_analysis'].get('description', 'No analysis available')}
            
            Please take immediate action.
            """
            mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")

def send_status_update_email(report, new_status, notes, updated_by):
    try:
        msg = Message(
            subject=f"Report Status Updated: {report['title']}",
            sender=app.config['MAIL_USERNAME'],
            recipients=[report['user_email']]
        )
        msg.body = f"""
        Your wildlife offence report status has been updated.
        
        Report ID: {report['_id']}
        Title: {report['title']}
        New Status: {new_status}
        Updated by: {updated_by}
        Notes: {notes}
        
        You can view the updated status in your dashboard.
        """
        mail.send(msg)
    except Exception as e:
        print(f"Status update email sending failed: {e}")

# Get reports for officials
@app.route('/api/reports', methods=['GET'])
@token_required
def get_reports(current_user):
    try:
        # Ensure only officials can access all reports
        if current_user['role'] != 'official':
            return jsonify({'message': 'Unauthorized - This endpoint is for officials only'}), 403
        
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        query = {}
        if status != 'all':
            query['status'] = status
        
        print(f"Official {current_user['name']} fetching reports with query: {query}, page: {page}, limit: {limit}")
        
        reports = list(reports_collection.find(query)
                       .sort('created_at', -1)
                       .skip((page - 1) * limit)
                       .limit(limit))
        
        print(f"Found {len(reports)} reports for official {current_user['name']}")
        
        # Convert ObjectId to string and format dates
        for report in reports:
            report['_id'] = str(report['_id'])
            report['user_id'] = str(report['user_id'])
            if isinstance(report.get('created_at'), datetime):
                report['created_at'] = report['created_at'].isoformat()
            if isinstance(report.get('updated_at'), datetime):
                report['updated_at'] = report['updated_at'].isoformat()
            # Convert any remaining ObjectId fields
            for key, value in report.items():
                if isinstance(value, ObjectId):
                    report[key] = str(value)
        
        total = reports_collection.count_documents(query)
        print(f"Total reports: {total}")
        
        return jsonify({
            'reports': reports,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit,
            'message': f'Successfully fetched {len(reports)} reports for official {current_user["name"]}'
        })
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return jsonify({'message': 'Failed to fetch reports', 'error': str(e)}), 500

# Get reports for users
@app.route('/api/reports/user', methods=['GET'])
@token_required
def get_user_reports(current_user):
    try:
        # Ensure only users can access their own reports
        if current_user['role'] != 'user':
            return jsonify({'message': 'Unauthorized - This endpoint is for users only'}), 403
        
        print(f"Fetching reports for user: {current_user['_id']} ({current_user['name']})")
        
        # Query reports where user_id matches the logged-in user's ID
        query = {'user_id': current_user['_id']}
        reports = list(reports_collection.find(query)
                       .sort('created_at', -1))
        
        print(f"Found {len(reports)} reports for user {current_user['name']}")
        
        # Convert ObjectId to string and format dates
        for report in reports:
            report['_id'] = str(report['_id'])
            report['user_id'] = str(report['user_id'])
            if isinstance(report.get('created_at'), datetime):
                report['created_at'] = report['created_at'].isoformat()
            if isinstance(report.get('updated_at'), datetime):
                report['updated_at'] = report['updated_at'].isoformat()
            # Convert any remaining ObjectId fields
            for key, value in report.items():
                if isinstance(value, ObjectId):
                    report[key] = str(value)
        
        return jsonify({
            'reports': reports,
            'message': f'Successfully fetched {len(reports)} reports for user {current_user["name"]}'
        })
    except Exception as e:
        print(f"Error fetching user reports: {e}")
        return jsonify({'message': 'Failed to fetch reports', 'error': str(e)}), 500

# Get current user info
@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    current_user['_id'] = str(current_user['_id'])
    del current_user['password']
    return jsonify({'user': current_user})

# Update report status
@app.route('/api/reports/<report_id>/status', methods=['PUT'])
@token_required
def update_report_status(current_user, report_id):
    try:
        if current_user['role'] != 'official':
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        # Validate status
        valid_statuses = ['New', 'Under Investigation', 'Verified', 'Resolved']
        if new_status not in valid_statuses:
            return jsonify({'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Check if report exists
        try:
            report = reports_collection.find_one({'_id': ObjectId(report_id)})
            if not report:
                return jsonify({'message': 'Report not found'}), 404
        except Exception as e:
            print(f"Error finding report: {e}")
            return jsonify({'message': 'Invalid report ID'}), 400
        
        # Update report status
        try:
            result = reports_collection.update_one(
                {'_id': ObjectId(report_id)},
                {
                    '$set': {
                        'status': new_status,
                        'notes': notes,
                        'updated_at': datetime.utcnow(),
                        'updated_by': current_user['_id']
                    }
                }
            )
            
            if result.modified_count:
                print(f"Report {report_id} status updated to {new_status}")
                
                # Emit status update to all connected clients
                try:
                    socketio.emit('status_update', {
                        'report_id': report_id,
                        'status': new_status,
                        'notes': notes,
                        'updated_by': current_user['name']
                    }, room='officials')
                    
                    # Also emit to user who submitted the report
                    socketio.emit('status_update', {
                        'report_id': report_id,
                        'status': new_status,
                        'notes': notes,
                        'updated_by': current_user['name']
                    }, room=f'user_{report["user_id"]}')
                    
                    print("Status update notification sent")
                except Exception as e:
                    print(f"Failed to send status update notification: {e}")
                
                # Send email notification to user about status change
                try:
                    send_status_update_email(report, new_status, notes, current_user['name'])
                except Exception as e:
                    print(f"Failed to send status update email: {e}")
                
                return jsonify({'message': 'Status updated successfully'})
            else:
                return jsonify({'message': 'Failed to update status'}), 500
                
        except Exception as e:
            print(f"Database update error: {e}")
            return jsonify({'message': 'Failed to update report status'}), 500
            
    except Exception as e:
        print(f"Status update error: {e}")
        return jsonify({'message': 'Failed to update status. Please try again.'}), 500

# Analytics endpoint
@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    if current_user['role'] != 'official':
        return jsonify({'message': 'Unauthorized - Analytics endpoint is for officials only'}), 403
    
    try:
        # Get date range
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        print(f"Official {current_user['name']} requesting analytics for last {days} days")
        
        # Offence frequency
        offence_stats = list(reports_collection.aggregate([
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {'_id': '$offence_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Severity distribution (stored Critical/Medium/Low)
        severity_stats = list(reports_collection.aggregate([
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {'_id': '$severity', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        
        # Daily reports (grouped by date)
        daily_reports = list(reports_collection.aggregate([
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]))
        
        # Weekly reports (grouped by week)
        weekly_reports = list(reports_collection.aggregate([
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': {
                    'year': {'$year': '$created_at'},
                    'week': {'$week': '$created_at'}
                },
                'count': {'$sum': 1},
                'start_date': {'$min': '$created_at'}
            }},
            {'$sort': {'_id.year': 1, '_id.week': 1}}
        ]))
        
        # High-risk zones (areas with most critical incidents)
        high_risk_zones = list(reports_collection.aggregate([
            {'$match': {
                'created_at': {'$gte': start_date},
                'severity': 'Critical',
                'location.lat': {'$exists': True, '$ne': 0},
                'location.lng': {'$exists': True, '$ne': 0}
            }},
            {'$group': {
                '_id': {
                    'lat': {'$round': [{'$toDouble': '$location.lat'}, 2]},
                    'lng': {'$round': [{'$toDouble': '$location.lng'}, 2]}
                },
                'count': {'$sum': 1},
                'reports': {'$push': {
                    'title': '$title',
                    'offence_type': '$offence_type',
                    'created_at': '$created_at'
                }}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 20}
        ]))
        
        # Detection statistics
        total_reports = reports_collection.count_documents({'created_at': {'$gte': start_date}})
        species_detected = reports_collection.count_documents({
            'created_at': {'$gte': start_date},
            'offence_type': 'Species Monitoring'
        })
        weapon_detections = reports_collection.count_documents({
            'created_at': {'$gte': start_date},
            'offence_type': {'$in': ['Poaching', 'Illegal Hunting']}
        })
        poacher_detections = reports_collection.count_documents({
            'created_at': {'$gte': start_date},
            'offence_type': {'$in': ['Poaching', 'Illegal Hunting', 'Illegal Forest Entry']}
        })
        
        # Calculate severity rates
        severity_counts = {stat['_id']: stat['count'] for stat in severity_stats}
        severity_rate = {
            'High': severity_counts.get('Critical', 0),
            'Medium': severity_counts.get('Medium', 0),
            'Low': severity_counts.get('Low', 0),
        }
        
        # Monthly trend analysis
        monthly_trend = list(reports_collection.aggregate([
            {'$match': {'created_at': {'$gte': start_date}}},
            {'$group': {
                '_id': {
                    'year': {'$year': '$created_at'},
                    'month': {'$month': '$created_at'}
                },
                'total': {'$sum': 1},
                'critical': {
                    '$sum': {'$cond': [{'$eq': ['$severity', 'Critical']}, 1, 0]}
                },
                'medium': {
                    '$sum': {'$cond': [{'$eq': ['$severity', 'Medium']}, 1, 0]}
                },
                'low': {
                    '$sum': {'$cond': [{'$eq': ['$severity', 'Low']}, 1, 0]}
                }
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]))
        
        analytics_data = {
            'offence_stats': offence_stats,
            'severity_stats': severity_stats,
            'daily_reports': daily_reports,
            'weekly_reports': weekly_reports,
            'monthly_trend': monthly_trend,
            'high_risk_zones': high_risk_zones,
            'severity_rate': severity_rate,
            'detection_statistics': {
                'total_reports': total_reports,
                'species_detected': species_detected,
                'weapon_detections': weapon_detections,
                'poacher_detections': poacher_detections
            },
            'time_range': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat()
            }
        }
        
        print(f"Analytics generated for {current_user['name']}: {total_reports} reports, {len(high_risk_zones)} risk zones")
        
        return jsonify({
            'analytics': analytics_data,
            'message': f'Successfully generated analytics for the last {days} days'
        })
        
    except Exception as e:
        print(f"Error generating analytics: {e}")
        return jsonify({'message': 'Failed to generate analytics', 'error': str(e)}), 500

# SocketIO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_officials')
def handle_join_officials():
    join_room('officials')
    emit('status', {'message': 'Joined officials room'})

@socketio.on('leave_officials')
def handle_leave_officials():
    leave_room('officials')
    emit('status', {'message': 'Left officials room'})

@socketio.on('join_user')
def handle_join_user(data):
    user_id = data.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        emit('status', {'message': f'Joined user room for {user_id}'})

@socketio.on('leave_user')
def handle_leave_user(data):
    user_id = data.get('user_id')
    if user_id:
        leave_room(f'user_{user_id}')
        emit('status', {'message': f'Left user room for {user_id}'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
