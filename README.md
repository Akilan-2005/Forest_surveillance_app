# Wildlife Offence Detection and Reporting System

An AI-powered web application for detecting and reporting wildlife offences using React.js, Flask, MongoDB, and YOLOv3 computer vision.

## 🚀 New Features & Improvements

### 🤖 Enhanced AI Analysis
- **YOLOv3 Integration**: Replaced Gemini AI with YOLOv3 for better wildlife offence detection
- **Computer Vision**: Detects weapons, vehicles, wildlife, and suspicious activities
- **Fallback Analysis**: Text-based analysis when YOLOv3 is unavailable
- **Severity Classification**: Automatic severity assessment (Critical/Medium/Low)

### 🔔 Interactive Features
- **Real-time Notifications**: Live updates for new reports and status changes
- **Notification Center**: Centralized notification management for officials
- **Auto-refresh**: Automatic data refresh with manual controls
- **Connection Status**: Live connection indicators
- **Enhanced Analytics**: Interactive charts with real-time updates

### 🎨 UI/UX Improvements
- **Modern Design**: Enhanced visual design with better animations
- **Responsive Layout**: Improved mobile and desktop experience
- **Interactive Elements**: Better user interactions and feedback
- **Status Indicators**: Visual connection and update status
- **Loading States**: Enhanced loading animations and feedback

## Tech Stack

### Frontend
- React.js with React Router
- Tailwind CSS for styling
- Axios for API communication
- Leaflet.js for maps
- Chart.js for analytics

### Backend
- Flask (Python)
- MongoDB for database
- Flask-SocketIO for real-time communication
- Flask-Mail for notifications
- YOLOv3 for AI analysis (OpenCV + computer vision)
- OpenCV for image processing

## Run Instructions (Windows - PowerShell)

### 1) Prerequisites
- Node.js 16+
- Python 3.8+
- MongoDB (local or Atlas)
- OpenCV 4.8+ (for YOLOv3)
- YOLOv3 weights and config files (optional - fallback available)

### 2) Clone and install
```powershell
# From your desired folder
git clone <your-repo-url> wildlife-offence
cd wildlife-offence

# Install root tools (concurrently)
npm install

# Frontend deps
cd frontend
npm install

# Backend deps
cd ..\backend
pip install -r requirements.txt
```

### 3) Configure environment
Create `backend/.env` with values like:
```bash
MONGODB_URI=mongodb://localhost:27017/wildlife_offence_db
JWT_SECRET_KEY=change_this_secret
SECRET_KEY=change_this_secret

# Email (optional but required for critical alerts)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# Twilio SMS (optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

**Note**: No API keys required for YOLOv3! The system works with or without YOLOv3 weights.

Optionally add `frontend/.env`:
```bash
REACT_APP_API_URL=http://localhost:5000
```

### 4) Start MongoDB
- If running locally, ensure the MongoDB service is started.
```powershell
# Windows Service (if installed as a service)
net start MongoDB
```

### 5) Run the app (dev)
From the project root:
```powershell
npm run dev
```
This starts:
- Backend Flask API on `http://localhost:5000`
- Frontend React app on `http://localhost:3000`

Alternatively, start manually in two terminals:
```powershell
# Terminal 1
cd backend
python app.py

# Terminal 2
cd frontend
npm start
```

### 6) Create test accounts
1. Open `http://localhost:3000/register`
2. Create a Citizen (user role) account
3. Create a Forest Official (official role) account

### 4) YOLOv3 Setup (Optional)
For enhanced AI detection, download YOLOv3 files:
```powershell
# Download YOLOv3 weights (237MB)
curl -L -o backend/yolov3.weights https://pjreddie.com/media/files/yolov3.weights

# Download YOLOv3 config
curl -L -o backend/yolov3.cfg https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg

# Download COCO names
curl -L -o backend/coco.names https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names
```

**Note**: The system works without YOLOv3 files using fallback text analysis.

### Notes
- **No API keys required**: YOLOv3 works locally without external API calls
- Email/SMS alerts require valid credentials; otherwise, critical alerts will log errors but the app will continue running
- If geolocation fails in the browser, ensure location permissions are granted
- Real-time features require WebSocket support

### Common issues
- MongoDB connection error: verify `MONGODB_URI` and that MongoDB is running
- CORS/Network error: the frontend proxies to `http://localhost:5000` by default (see `frontend/package.json`). Ensure the backend is up
- YOLOv3 errors: system falls back to text analysis if YOLOv3 files are missing
- Socket connection issues: check firewall settings and ensure ports 3000 and 5000 are accessible

## Project Structure

```
├── frontend/          # React.js frontend
├── backend/           # Flask backend
├── package.json       # Root package.json for scripts
└── README.md
```

## 🤖 YOLOv3 AI Detection

### How It Works
1. **Image Analysis**: YOLOv3 processes uploaded images to detect objects
2. **Object Classification**: Identifies weapons, vehicles, wildlife, and suspicious activities
3. **Severity Assessment**: Automatically classifies reports as Critical/Medium/Low
4. **Fallback System**: Uses text analysis when YOLOv3 is unavailable

### Detection Capabilities
- **Weapons**: Guns, rifles, knives, hunting equipment
- **Vehicles**: Cars, trucks, motorcycles in restricted areas
- **Wildlife**: Animals, birds, fish for context analysis
- **Suspicious Activities**: Person detection in restricted zones

### Performance
- **Local Processing**: No external API calls required
- **Fast Analysis**: Real-time image processing
- **High Accuracy**: YOLOv3 provides reliable object detection
- **Fallback Support**: Text analysis ensures system always works

## 🔔 Real-time Features

### Live Updates
- **Socket.IO Integration**: Real-time communication between frontend and backend
- **Instant Notifications**: Officials receive immediate alerts for new reports
- **Status Updates**: Users get notified when their reports are updated
- **Connection Monitoring**: Visual indicators for connection status

### Notification System
- **Notification Center**: Centralized notification management
- **Severity-based Alerts**: Different notification types for different severity levels
- **Email Integration**: Critical alerts sent via email
- **Toast Notifications**: In-app notification system

## 📊 Enhanced Analytics

### Interactive Dashboards
- **Real-time Charts**: Live updating analytics with Chart.js
- **Geographic Visualization**: Interactive maps showing report locations
- **Trend Analysis**: Historical data and pattern recognition
- **Auto-refresh**: Automatic data updates with manual controls

### Data Insights
- **Offence Patterns**: Identify common violation types
- **Geographic Hotspots**: High-risk zone identification
- **Temporal Analysis**: Peak times and seasonal trends
- **Severity Distribution**: Risk level assessment

## API Endpoints

- `/api/auth` - Authentication endpoints
- `/api/reports` - Report management
- `/api/analytics` - Analytics data
- `/api/upload` - File upload handling
- **WebSocket Events**: Real-time communication

## 🚀 Deployment

### Production Setup
1. **Environment Variables**: Configure production settings
2. **Database**: Use MongoDB Atlas for cloud hosting
3. **YOLOv3 Files**: Download and configure YOLOv3 weights
4. **Email Service**: Configure SMTP for notifications
5. **SSL Certificate**: Enable HTTPS for security

### Performance Optimization
- **Image Compression**: Optimize uploaded images
- **Caching**: Implement Redis for session management
- **Load Balancing**: Use Nginx for production deployment
- **Monitoring**: Set up application monitoring

## Contributing

Please read the contributing guidelines before submitting pull requests.

## 📝 Changelog

### v2.0.0 - Major Update
- ✅ Fixed status update issues
- ✅ Implemented YOLOv3 AI detection
- ✅ Added real-time notifications
- ✅ Enhanced UI/UX with animations
- ✅ Improved analytics dashboard
- ✅ Added notification center
- ✅ Enhanced error handling
- ✅ Better mobile responsiveness

