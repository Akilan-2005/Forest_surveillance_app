# Integrated Wildlife Offence Detection & YOLO System Setup

This document provides complete setup and running instructions for the integrated Wildlife Offence Detection platform with YOLO object detection capabilities.

## System Overview

This integrated system combines:
- **Wildlife Offence Detection Platform**: A production-grade Flask/React application for reporting and managing wildlife offences
- **YOLO Object Detection**: Computer vision capabilities for automatic object detection in uploaded images

### Key Features
- Citizens can submit wildlife offence reports with images
- AI automatically analyzes images for:
  - Wildlife offence indicators (weapons, vehicles, injured animals) using YOLOv3
  - General object detection (exit signs, fire extinguishers, chairs, etc.) using YOLOv8
- Officials can view reports with bounding box visualizations
- Real-time notifications and analytics dashboard

---

## Prerequisites

### Required Software

1. **Node.js** (v16 or higher)
   - Download: https://nodejs.org/
   - Verify: `node --version`

2. **Python** (v3.9 or higher)
   - Download: https://python.org/downloads/
   - Verify: `python --version`

3. **MongoDB** (v5.0 or higher)
   - Download: https://www.mongodb.com/try/download/community
   - Or use MongoDB Atlas cloud service

4. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

### System Requirements
- **RAM**: 4GB minimum (8GB recommended for YOLO)
- **Storage**: 2GB free space
- **OS**: Windows 10/11, macOS, or Linux

---

## Installation Steps

### 1. MongoDB Setup

#### Option A: Local MongoDB Installation

**Windows:**
```powershell
# Install MongoDB Community Edition from the official installer
# Start MongoDB service
net start MongoDB

# Or using mongod directly
mkdir C:\data\db
mongod --dbpath C:\data\db
```

**macOS/Linux:**
```bash
# Using Homebrew (macOS)
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Or using apt (Ubuntu/Debian)
sudo apt-get install mongodb
sudo systemctl start mongodb
```

#### Option B: MongoDB Atlas (Cloud)
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a new cluster (free tier available)
3. Get your connection string
4. Use the connection string in backend `.env` file

### 2. Backend Setup

Navigate to the Wildlife Offence Detection backend:

```powershell
# Windows
cd "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend"

# macOS/Linux
cd /path/to/project/backend
```

Create a Python virtual environment:
```powershell
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Additional YOLO dependencies:
```bash
# These should already be in requirements.txt, but if needed:
pip install ultralytics opencv-python numpy scipy pyyaml
```

### 3. YOLO Model Setup

Create the YOLO model directory and copy model files:

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend\yolo_model"

# Copy model files from the YOLO project
copy "c:\Users\Blesson John\Desktop\final\yolo\backend\yolov8n.mat" "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend\yolo_model\"
copy "c:\Users\Blesson John\Desktop\final\yolo\backend\data.yaml" "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend\yolo_model\"

# Also copy the .pt file if available (for fallback)
copy "c:\Users\Blesson John\Desktop\final\yolo\backend\yolov8n.pt" "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend\yolo_model\"
```

Your `backend/yolo_model/` directory should contain:
- `yolov8n.mat` - MATLAB model file
- `data.yaml` - Class names configuration
- `yolov8n.pt` - PyTorch weights (optional fallback)

### 4. Environment Configuration

Create backend `.env` file:

```bash
cd "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend"
copy env.example .env
```

Edit `.env` with your configuration:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
# OR for Atlas: MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/wildlife_offence_db

# Flask Configuration
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Mail Configuration (optional - for email alerts)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Twilio Configuration (optional - for SMS alerts)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token

# YOLO Model Configuration (optional - uses defaults if not set)
YOLO_MODEL_PATH=./yolo_model/yolov8n.mat
YOLO_CLASSES_PATH=./yolo_model/data.yaml
```

### 5. Frontend Setup

Navigate to the frontend directory:

```powershell
cd "c:\Users\Blesson John\Desktop\final\akilan\new project\project\frontend"
```

Install Node.js dependencies:
```bash
npm install
```

Create frontend `.env` file:
```bash
echo "REACT_APP_API_URL=http://localhost:5000" > .env
```

---

## Running the System

### Terminal 1: MongoDB (if running locally)

```powershell
# Windows (if MongoDB service is not already running)
net start MongoDB

# macOS/Linux
brew services start mongodb-community
```

### Terminal 2: Flask Backend

```powershell
cd "c:\Users\Blesson John\Desktop\final\akilan\new project\project\backend"
venv\Scripts\activate  # Windows
python app.py
```

The backend will start on `http://localhost:5000`

**Expected console output:**
```
YOLOv3 detector loaded successfully
YOLO service available for object detection
Initializing YOLOv3 wildlife offence detector...
YOLO service initialized successfully (fallback: True/False)
 * Serving Flask app 'app'
 * Debug mode: on
```

### Terminal 3: React Frontend

```powershell
cd "c:\Users\Blesson John\Desktop\final\akilan\new project\project\frontend"
npm start
```

The frontend will start on `http://localhost:3000`

### Terminal 4: YOLO Standalone Project (Optional)

To run the standalone YOLO project independently:

```powershell
# Backend
cd "c:\Users\Blesson John\Desktop\final\yolo\backend"
# Create venv if not exists
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Frontend - Open in browser directly
cd "c:\Users\Blesson John\Desktop\final\yolo\frontend"
# Open index.html in a browser or serve with any static server
python -m http.server 3001
```

---

## Folder Structure

After integration, the project structure is:

```
new project/
├── project/
│   ├── backend/                      # Flask Backend
│   │   ├── app.py                    # Main Flask application
│   │   ├── yolo_service.py           # YOLO detection service (NEW)
│   │   ├── yolo_detector.py          # Existing YOLOv3 detector
│   │   ├── yolo_model/               # YOLO model files (NEW)
│   │   │   ├── yolov8n.mat           # MATLAB model
│   │   │   ├── yolov8n.pt          # PyTorch fallback
│   │   │   └── data.yaml             # Class definitions
│   │   ├── requirements.txt
│   │   └── .env
│   └── frontend/                     # React Frontend
│       ├── src/
│       │   └── components/
│       │       └── officials/
│       │           ├── OfficialsDashboard.js    # Updated with detection viewer
│       │           └── DetectionViewer.js         # NEW: Bounding box visualization
│       ├── package.json
│       └── .env
└── yolo/                             # Standalone YOLO (unchanged)
    ├── backend/
    │   ├── api.py                    # FastAPI standalone
    │   ├── model_loader.py           # Original model loader
    │   └── yolov8n.mat
    └── frontend/
        └── index.html                # Standalone frontend
```

---

## API Documentation

### YOLO Detection Endpoint

**POST** `/api/yolo/detect`

Runs YOLO object detection on an uploaded image.

**Authentication:** Bearer Token required

**Request (multipart/form-data):**
```bash
curl -X POST http://localhost:5000/api/yolo/detect \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@/path/to/image.jpg" \
  -F "conf_threshold=0.25" \
  -F "iou_threshold=0.45"
```

**Request (JSON with base64):**
```json
{
  "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD..."
}
```

**Response:**
```json
{
  "success": true,
  "detections": [
    {
      "label": "fireextinguisher",
      "confidence": 0.87,
      "box": [120, 150, 280, 400]
    },
    {
      "label": "exit",
      "confidence": 0.92,
      "box": [50, 80, 200, 250]
    }
  ],
  "message": "Detected 2 objects"
}
```

### Report Submission with YOLO

**POST** `/api/reports`

Automatically runs YOLO detection when submitting a report with an image.

**Response includes:**
```json
{
  "report": {
    "ai_analysis": { ... },          // Existing wildlife offence analysis
    "yolo_detections": [             // NEW: YOLO object detection results
      {
        "label": "chair",
        "confidence": 0.93,
        "box": [100, 150, 300, 400]
      }
    ]
  }
}
```

---

## YOLO Classes

The integrated YOLO model detects the following classes:

| Class ID | Class Name      |
|----------|-----------------|
| 0        | exit            |
| 1        | fireextinguisher|
| 2        | chair           |
| 3        | clock           |
| 4        | trashbin        |
| 5        | screen          |
| 6        | printer         |

---

## Troubleshooting

### Common Issues

#### 1. "YOLO service not available" Error

**Problem:** The YOLO service failed to initialize.

**Solutions:**
```bash
# Check if model files exist
ls backend/yolo_model/

# Reinstall ultralytics
pip uninstall ultralytics
pip install ultralytics

# Check Python version (must be 3.8+)
python --version
```

#### 2. OpenCV Import Error

**Problem:** `ImportError: DLL load failed while importing cv2`

**Solution (Windows):**
```bash
pip uninstall opencv-python
pip install opencv-python-headless
# OR reinstall
pip install --force-reinstall opencv-python
```

#### 3. MongoDB Connection Error

**Problem:** `pymongo.errors.ServerSelectionTimeoutError`

**Solutions:**
- Ensure MongoDB service is running: `net start MongoDB` (Windows)
- Check connection string in `.env` file
- Verify MongoDB port (default: 27017) is not blocked

#### 4. Model Loading Takes Too Long

**Problem:** First detection request is very slow.

**Explanation:** This is normal. The model loads on first use. Subsequent detections will be fast.

**To pre-load at startup:** The YOLO service now loads automatically when the Flask app starts.

#### 5. CORS Errors in Browser

**Problem:** `Access-Control-Allow-Origin` errors in browser console.

**Solution:**
- Check that `CORS(app, origins=["http://localhost:3000"])` is in `app.py`
- Verify frontend `.env` has correct `REACT_APP_API_URL`

#### 6. "No module named 'ultralytics'"

**Solution:**
```bash
pip install ultralytics
# If using conda:
conda install -c conda-forge ultralytics
```

#### 7. YOLO Model File Not Found

**Problem:** `FileNotFoundError: Model file not found`

**Solution:**
```powershell
# Verify paths in .env or use absolute paths
YOLO_MODEL_PATH=c:/Users/.../backend/yolo_model/yolov8n.mat
YOLO_CLASSES_PATH=c:/Users/.../backend/yolo_model/data.yaml
```

### Debug Mode

Enable detailed logging by setting in your `.env`:
```env
FLASK_DEBUG=True
FLASK_ENV=development
```

Check console output for:
- `YOLO service initialized successfully`
- Model loading messages
- Detection result counts

---

## Production Deployment

### Backend Deployment Checklist

1. **Environment Variables:**
   - Use strong random strings for `SECRET_KEY` and `JWT_SECRET_KEY`
   - Use MongoDB Atlas for production database
   - Configure production mail server
   - Set `FLASK_ENV=production`

2. **Security:**
   ```python
   # In app.py, update for production:
   CORS(app, origins=["https://yourdomain.com"])  # Restrict origins
   ```

3. **Process Manager:**
   ```bash
   # Install gunicorn
   pip install gunicorn
   
   # Run with gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

4. **Model Files:**
   - Ensure `yolo_model/` directory is included in deployment
   - Set proper file permissions

### Frontend Deployment

```bash
cd frontend
npm run build

# Deploy build/ folder to your web server
```

---

## Maintenance

### Updating Dependencies

```bash
# Backend
pip list --outdated
pip install --upgrade flask pymongo

# Frontend
npm outdated
npm update
```

### Backing Up MongoDB

```bash
mongodump --db wildlife_offence_db --out backup/
```

### Model Retraining

To update the YOLO model with new training:
1. Replace `yolov8n.mat` and `yolov8n.pt` in `backend/yolo_model/`
2. Update `data.yaml` if class names changed
3. Restart Flask backend

---

## Support

For issues related to:
- **Wildlife Detection System**: Check existing documentation in `README.md`
- **YOLO Integration**: Review this document and check console logs
- **Standalone YOLO Project**: Refer to `yolo/README.md`

---

## Summary

This integration provides:
1. ✅ **Backend Integration**: `POST /api/yolo/detect` endpoint in Flask
2. ✅ **Automatic Detection**: YOLO runs on every report submission with images
3. ✅ **Detection Storage**: Results stored in `yolo_detections` field in MongoDB
4. ✅ **Frontend Visualization**: `DetectionViewer` component with bounding boxes
5. ✅ **Official Dashboard**: Enhanced report view with detection details
6. ✅ **Standalone Preservation**: Original YOLO project unchanged and functional

**Quick Start:**
1. Start MongoDB
2. Run `python app.py` in backend
3. Run `npm start` in frontend
4. Access at http://localhost:3000
