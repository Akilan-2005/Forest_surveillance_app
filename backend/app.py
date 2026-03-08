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

# Import YOLO service for object detection
try:
    from yolo_service import get_yolo_service
    YOLO_SERVICE_AVAILABLE = True
    print("YOLO service available for object detection")
except ImportError as e:
    print(f"YOLO service not available: {e}")
    YOLO_SERVICE_AVAILABLE = False
    yolo_service = None

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

# Initialize YOLO service for object detection
yolo_service = None
if YOLO_SERVICE_AVAILABLE:
    try:
        yolo_service = get_yolo_service()
        if yolo_service.is_initialized():
            print(f"YOLO service initialized successfully (fallback: {yolo_service.fallback_mode})")
        else:
            print("YOLO service failed to initialize")
            yolo_service = None
    except Exception as e:
        print(f"Error initializing YOLO service: {e}")
        yolo_service = None

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

# YOLO Object Detection endpoint
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
                geolocator = Nominatim(user_agent="wildlife_offence_system")
                location_data = geolocator.reverse(f"{location['lat']}, {location['lng']}")
                location['address'] = location_data.address if location_data else "Unknown location"
            except Exception as e:
                print(f"Location reverse geocoding failed: {e}")
                location['address'] = "Location not available"
        else:
            location = {'lat': 0, 'lng': 0, 'address': 'Location not available'}
        
        # Analyze media with YOLOv3 AI
        ai_analysis = None
        yolo_detections = []  # Store YOLO detection results with bounding boxes
        
        if data.get('media_type') == 'image' and data.get('media_data'):
            # Run existing YOLOv3 analysis for wildlife offences
            try:
                ai_analysis = analyze_media_with_yolo(data['media_data'], data.get('description', ''))
                print(f"YOLOv3 Analysis completed: {ai_analysis}")
            except Exception as e:
                print(f"YOLOv3 analysis failed: {e}")
                ai_analysis = {
                    "offence_detected": False,
                    "offence_type": "unknown",
                    "severity": "Low",
                    "confidence": 0.0,
                    "detected_objects": [],
                    "description": f"YOLOv3 analysis failed: {str(e)}"
                }
            
            # Run new YOLO service for object detection with bounding boxes
            if yolo_service and yolo_service.is_initialized():
                try:
                    # Decode base64 image for YOLO service
                    image_data = data['media_data']
                    if ',' in image_data:
                        image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    
                    # Run YOLO detection
                    yolo_detections = yolo_service.detect_from_bytes(
                        image_bytes,
                        conf_threshold=0.25,
                        iou_threshold=0.45
                    )
                    print(f"YOLO service detection completed: {len(yolo_detections)} objects detected")
                except Exception as e:
                    print(f"YOLO service detection failed: {e}")
                    yolo_detections = []
        
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
            'ai_analysis': ai_analysis,
            'yolo_detections': yolo_detections,  # New field for YOLO detections
            'status': 'New',
            'severity': normalize_severity(
                ai_analysis.get('severity') if ai_analysis else infer_severity_from_text(data.get('description', ''))
            ),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert report into database
        try:
            result = reports_collection.insert_one(report)
            report['_id'] = str(result.inserted_id)
            # Convert non-serializable fields for response only
            if isinstance(report.get('user_id'), ObjectId):
                report['user_id'] = str(report['user_id'])
            if isinstance(report.get('created_at'), datetime):
                report['created_at'] = report['created_at'].isoformat()
            if isinstance(report.get('updated_at'), datetime):
                report['updated_at'] = report['updated_at'].isoformat()
            print(f"Report inserted successfully with ID: {report['_id']}")
        except Exception as e:
            print(f"Database insertion failed: {e}")
            return jsonify({'message': 'Failed to save report to database'}), 500
        
        # Emit real-time alert to officials
        try:
            socketio.emit('new_report', {
                'report': report,
                'message': f'New {report["severity"]} severity report: {report["title"]}'
            }, room='officials')
            print("Real-time alert sent to officials")
        except Exception as e:
            print(f"Failed to send real-time alert: {e}")
        
        # Send email notification for critical reports
        if report['severity'] == 'Critical':
            try:
                send_critical_alert(report)
                print("Critical alert email sent")
            except Exception as e:
                print(f"Failed to send critical alert email: {e}")
        
        # Provide a simple severity summary mapping for client displays
        severity_band = {
            'band': 'High' if report['severity'] == 'Critical' else ('Medium' if report['severity'] == 'Medium' else 'Low')
        }
        return jsonify({'message': 'Report submitted successfully', 'report': report, 'severity_summary': severity_band}), 201
        
    except Exception as e:
        print(f"Report submission error: {e}")
        return jsonify({'message': 'Failed to submit report. Please try again.'}), 500

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
        if current_user['role'] != 'official':
            return jsonify({'message': 'Unauthorized'}), 403
        
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        query = {}
        if status != 'all':
            query['status'] = status
        
        print(f"Fetching reports with query: {query}, page: {page}, limit: {limit}")
        
        reports = list(reports_collection.find(query)
                       .sort('created_at', -1)
                       .skip((page - 1) * limit)
                       .limit(limit))
        
        print(f"Found {len(reports)} reports")
        
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
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return jsonify({'message': 'Failed to fetch reports', 'error': str(e)}), 500

# Get reports for users
@app.route('/api/reports/user', methods=['GET'])
@token_required
def get_user_reports(current_user):
    try:
        if current_user['role'] != 'user':
            return jsonify({'message': 'Unauthorized'}), 403
        
        print(f"Fetching reports for user: {current_user['_id']}")
        
        reports = list(reports_collection.find({'user_id': current_user['_id']})
                       .sort('created_at', -1))
        
        print(f"Found {len(reports)} reports for user")
        
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
        
        return jsonify({'reports': reports})
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
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Get date range
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)
    
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
    
    # Daily reports
    daily_reports = list(reports_collection.aggregate([
        {'$match': {'created_at': {'$gte': start_date}}},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]))
    
    # High-risk zones
    high_risk_zones = list(reports_collection.aggregate([
        {'$match': {'created_at': {'$gte': start_date}, 'severity': 'Critical'}},
        {'$group': {
            '_id': {
                'lat': {'$round': [{'$toDouble': '$location.lat'}, 2]},
                'lng': {'$round': [{'$toDouble': '$location.lng'}, 2]}
            },
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]))
    
    return jsonify({
        'offence_stats': offence_stats,
        'severity_stats': severity_stats,
        'daily_reports': daily_reports,
        'high_risk_zones': high_risk_zones,
        'severity_rate': {
            'High': next((s['count'] for s in severity_stats if (s.get('_id') or '').lower() == 'critical'), 0),
            'Medium': next((s['count'] for s in severity_stats if (s.get('_id') or '').lower() == 'medium'), 0),
            'Low': next((s['count'] for s in severity_stats if (s.get('_id') or '').lower() == 'low'), 0),
        }
    })

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
