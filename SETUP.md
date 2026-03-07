# Wildlife Offence Detection System - Setup Guide

## Prerequisites

Before setting up the system, ensure you have the following installed:

- **Node.js** (v16 or higher)
- **Python** (v3.8 or higher)
- **MongoDB** (v4.4 or higher)
- **Git**

## Installation Steps

### 1. Clone and Install Dependencies

```bash
# Install root dependencies
npm install

# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

### 2. Environment Configuration

#### Backend Environment (.env)
Create a `.env` file in the `backend` directory:

```env
# Database Configuration
MONGODB_URI=mongodb://localhost:27017/wildlife_offence_db

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key_here

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# SMS Configuration (Optional)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Server Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_flask_secret_key
```

#### Frontend Environment (.env)
Create a `.env` file in the `frontend` directory:

```env
REACT_APP_API_URL=http://localhost:5000
```

### 3. API Keys Setup

#### Google Gemini API
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your backend `.env` file

#### Email Configuration (Optional)
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password
3. Use the App Password in your `.env` file

#### Twilio SMS (Optional)
1. Sign up for [Twilio](https://www.twilio.com/)
2. Get your Account SID and Auth Token
3. Add them to your `.env` file

### 4. Database Setup

#### MongoDB
1. Start MongoDB service:
   ```bash
   # Windows
   net start MongoDB
   
   # macOS/Linux
   sudo systemctl start mongod
   ```

2. Create the database (it will be created automatically when the app runs)

### 5. Running the Application

#### Development Mode
```bash
# From the root directory
npm run dev
```

This will start both the backend (Flask) and frontend (React) servers.

#### Manual Start
```bash
# Terminal 1 - Backend
cd backend
python app.py

# Terminal 2 - Frontend
cd frontend
npm start
```

### 6. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

## Default User Accounts

### Create Test Accounts
1. Go to http://localhost:3000/register
2. Register as a "Citizen" (user role)
3. Register as a "Forest Official" (official role)

## Features Overview

### For Citizens (Users)
- Report wildlife offences with photos/videos
- GPS location tracking
- AI-powered analysis of uploaded media
- Track report status
- View personal report history

### For Forest Officials
- Real-time dashboard with live reports
- Interactive map with report locations
- AI analysis insights
- Status management (New → Investigation → Verified → Resolved)
- Analytics dashboard with trends and patterns
- Email/SMS notifications for critical reports

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Reports
- `POST /api/reports` - Submit new report
- `GET /api/reports` - Get reports (officials only)
- `GET /api/reports/user` - Get user's reports
- `PUT /api/reports/:id/status` - Update report status

### Analytics
- `GET /api/analytics` - Get analytics data (officials only)

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Ensure MongoDB is running
   - Check the connection string in `.env`

2. **Gemini API Error**
   - Verify your API key is correct
   - Check if you have API quota remaining

3. **CORS Issues**
   - Ensure backend is running on port 5000
   - Check CORS configuration in `app.py`

4. **Location Services**
   - Ensure HTTPS for production (required for geolocation)
   - Test location access in browser

### Development Tips

1. **Hot Reload**: Both frontend and backend support hot reload
2. **Database Reset**: Delete the MongoDB database to start fresh
3. **Logs**: Check browser console and terminal for errors
4. **Network**: Ensure both servers can communicate

## Production Deployment

### Backend (Flask)
- Use a production WSGI server like Gunicorn
- Set up proper environment variables
- Configure HTTPS
- Set up database backups

### Frontend (React)
- Build the production bundle: `npm run build`
- Serve with a web server like Nginx
- Configure HTTPS
- Set up CDN for static assets

### Database (MongoDB)
- Use MongoDB Atlas for cloud hosting
- Set up authentication
- Configure backup strategies
- Monitor performance

## Support

For issues and questions:
1. Check the console logs
2. Verify all environment variables
3. Ensure all services are running
4. Check network connectivity

## Security Notes

- Change all default passwords and keys
- Use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Use environment variables for secrets
- Regular security updates
