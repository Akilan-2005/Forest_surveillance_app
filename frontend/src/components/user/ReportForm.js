import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import toast from 'react-hot-toast';

const ReportForm = () => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        offence_type: '',
        media_type: '',
        media_data: ''
    });
    const [location, setLocation] = useState(null);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const navigate = useNavigate();

    // Geolocation availability and fetch via browser API
    const [isGeolocationAvailable, setIsGeolocationAvailable] = useState(false);
    const [isLocating, setIsLocating] = useState(false);
    const [locationError, setLocationError] = useState(null);
    const [locationAccuracy, setLocationAccuracy] = useState(null);

    useEffect(() => {
        const hasGeo = typeof navigator !== 'undefined' && 'geolocation' in navigator;
        setIsGeolocationAvailable(hasGeo);
        if (!hasGeo) {
            setLocationError('Geolocation is not supported by your browser');
            return;
        }

        // Get high-accuracy location
        setIsLocating(true);
        setLocationError(null);
        
        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const locationData = {
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                    altitude: pos.coords.altitude,
                    altitudeAccuracy: pos.coords.altitudeAccuracy,
                    heading: pos.coords.heading,
                    speed: pos.coords.speed,
                    timestamp: pos.timestamp
                };
                
                setLocation(locationData);
                setLocationAccuracy(pos.coords.accuracy);
                setIsLocating(false);
                console.log('Location captured:', locationData);
            },
            (error) => {
                console.error('Geolocation error:', error);
                setIsLocating(false);
                
                let errorMessage = 'Unable to get your location';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = 'Location permission denied. Please enable location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = 'Location information is unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage = 'Location request timed out.';
                        break;
                    default:
                        errorMessage = 'An unknown error occurred.';
                        break;
                }
                setLocationError(errorMessage);
            },
            options
        );
    }, []);

    const offenceTypes = [
        'Species Monitoring',
        'Poaching',
        'Illegal Hunting',
        'Tree Cutting',
        'Injured Animal',
        'Animal Accident',
        'Diseased Wildlife',
        'Illegal Forest Entry',
        'Other'
    ];

    const detectionModeInfo = {
        'Species Monitoring': {
            description: 'Detect wildlife species only (lion, tiger, elephant, rhino, bear, deer, zebra, cow, cat, dog, horse, birds)',
            icon: '🦁',
            color: 'green'
        },
        'Poaching': {
            description: 'Detect poachers, weapons, and suspicious activities',
            icon: '🚨',
            color: 'red'
        },
        'Illegal Hunting': {
            description: 'Detect hunters, weapons, and illegal hunting equipment',
            icon: '🔫',
            color: 'orange'
        },
        'Illegal Forest Entry': {
            description: 'Detect unauthorized persons and vehicles in protected areas',
            icon: '🚷',
            color: 'red'
        },
        'Tree Cutting': {
            description: 'Detect illegal logging and deforestation activities',
            icon: '🪓',
            color: 'orange'
        },
        'Injured Animal': {
            description: 'Document injured wildlife for rescue operations',
            icon: '🏥',
            color: 'yellow'
        },
        'Animal Accident': {
            description: 'Report wildlife accidents and roadkill incidents',
            icon: '🚗',
            color: 'yellow'
        },
        'Diseased Wildlife': {
            description: 'Report sick or diseased animals for medical intervention',
            icon: '🦠',
            color: 'yellow'
        },
        'Other': {
            description: 'Other wildlife-related incidents',
            icon: '📋',
            color: 'gray'
        }
    };

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const onDrop = async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return;

        const file = acceptedFiles[0];
        setUploading(true);

        try {
            const reader = new FileReader();
            reader.onload = (e) => {
                const result = e.target.result;
                setFormData({
                    ...formData,
                    media_type: file.type.startsWith('image/') ? 'image' : 'video',
                    media_data: result
                });
                setUploading(false);
                toast.success('Media uploaded successfully!', { id: 'media-upload-success' });
            };
            reader.readAsDataURL(file);
        } catch (error) {
            setUploading(false);
            toast.error('Failed to upload media', { id: 'media-upload-error' });
        }
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png', '.gif'],
            'video/*': ['.mp4', '.mov', '.avi', '.mkv']
        },
        maxFiles: 1,
        maxSize: 10 * 1024 * 1024 // 10MB
    });

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate required fields
        if (!formData.title || !formData.description || !formData.offence_type) {
            toast.error('Please fill in all required fields', { id: 'validation-error' });
            return;
        }

        // Check location (optional but warn user)
        if (!location && !isGeolocationAvailable) {
            const proceed = window.confirm('Location access is not available. Do you want to proceed without location data?');
            if (!proceed) {
                return;
            }
        }

        setLoading(true);

        try {
            const reportData = {
                ...formData,
                location: location || { 
                    lat: 0, 
                    lng: 0, 
                    address: 'Location not available',
                    accuracy: null,
                    timestamp: null
                }
            };

            console.log('Submitting report with enhanced location:', reportData);
            const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:5000';
            const token = localStorage.getItem('token');
            const response = await axios.post(`${apiBase}/api/reports`, reportData, {
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                timeout: 30000 // 30 second timeout
            });

            if (response.status === 200 || response.status === 201) {
                toast.success('Report submitted successfully!', { id: 'report-submit-success' });
                console.log('Report submitted:', response.data);
                navigate('/');
            } else {
                throw new Error('Unexpected response status');
            }
        } catch (error) {
            console.error('Report submission error:', error);

            if (error.code === 'ECONNABORTED') {
                toast.error('Request timeout. Please check your connection and try again.', { id: 'report-submit-timeout' });
            } else if (error.response) {
                // Server responded with error status
                const errorMessage = error.response.data?.message || 'Failed to submit report';
                toast.error(errorMessage, { id: 'report-submit-error' });
                console.error('Server error:', error.response.data);
            } else if (error.request) {
                // Request was made but no response received
                toast.error('Unable to connect to server. Please check your internet connection.', { id: 'report-submit-network-error' });
                console.error('Network error:', error.request);
            } else {
                // Something else happened
                toast.error('An unexpected error occurred. Please try again.', { id: 'report-submit-unexpected-error' });
                console.error('Unexpected error:', error.message);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white shadow rounded-lg">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h1 className="text-2xl font-bold text-gray-900">Report Wildlife Offence</h1>
                        <p className="mt-1 text-sm text-gray-600">
                            Help protect wildlife by reporting offences and violations
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="p-6 space-y-6">
                        {/* Title */}
                        <div>
                            <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                                Report Title *
                            </label>
                            <input
                                type="text"
                                name="title"
                                id="title"
                                required
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                                placeholder="Brief description of the offence"
                                value={formData.title}
                                onChange={handleChange}
                            />
                        </div>

                        {/* Offence Type */}
                        <div>
                            <label htmlFor="offence_type" className="block text-sm font-medium text-gray-700">
                                Monitoring Mode *
                            </label>
                            <select
                                name="offence_type"
                                id="offence_type"
                                required
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                                value={formData.offence_type}
                                onChange={handleChange}
                            >
                                <option value="">Select monitoring mode</option>
                                {offenceTypes.map(type => (
                                    <option key={type} value={type}>
                                        {detectionModeInfo[type]?.icon || '📋'} {type}
                                    </option>
                                ))}
                            </select>
                            {formData.offence_type && detectionModeInfo[formData.offence_type] && (
                                <div className={`mt-2 p-3 rounded-lg border ${
                                    formData.offence_type === 'Species Monitoring' 
                                        ? 'bg-green-50 border-green-200' 
                                        : 'bg-red-50 border-red-200'
                                }`}>
                                    <div className="flex items-start">
                                        <span className="text-2xl mr-3">
                                            {detectionModeInfo[formData.offence_type].icon}
                                        </span>
                                        <div>
                                            <h4 className="text-sm font-medium text-gray-900 mb-1">
                                                {formData.offence_type}
                                            </h4>
                                            <p className="text-xs text-gray-600">
                                                {detectionModeInfo[formData.offence_type].description}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Description */}
                        <div>
                            <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                                Detailed Description *
                            </label>
                            <textarea
                                name="description"
                                id="description"
                                rows={4}
                                required
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                                placeholder="Provide detailed information about what you observed, when, and any other relevant details"
                                value={formData.description}
                                onChange={handleChange}
                            />
                        </div>

                        {/* Media Upload */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Upload Photo or Video (Optional)
                            </label>
                            <div
                                {...getRootProps()}
                                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${isDragActive
                                    ? 'border-primary-500 bg-primary-50'
                                    : 'border-gray-300 hover:border-gray-400'
                                    } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                <input {...getInputProps()} disabled={uploading} />
                                {uploading ? (
                                    <div className="space-y-2">
                                        <div className="loading-spinner mx-auto"></div>
                                        <p className="text-sm text-gray-600">Uploading...</p>
                                    </div>
                                ) : formData.media_data ? (
                                    <div className="space-y-2">
                                        <div className="text-green-600 text-2xl">✅</div>
                                        <p className="text-sm text-green-600">Media uploaded successfully</p>
                                        <p className="text-xs text-gray-500">
                                            {formData.media_type === 'image' ? 'Image' : 'Video'} ready for analysis
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="text-gray-400 text-4xl">📷</div>
                                        <p className="text-sm text-gray-600">
                                            {isDragActive
                                                ? 'Drop the file here...'
                                                : 'Drag & drop a photo or video here, or click to select'}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Supports: JPG, PNG, GIF, MP4, MOV (Max 10MB)
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Location Info */}
                        <div className={`border rounded-lg p-4 ${
                            locationError ? 'bg-red-50 border-red-200' : 'bg-blue-50 border-blue-200'
                        }`}>
                            <div className="flex items-start">
                                <div className="flex-shrink-0">
                                    <span className={locationError ? 'text-red-600' : 'text-blue-600'} style={{ fontSize: '1.125rem' }}>📍</span>
                                </div>
                                <div className="ml-3 flex-1">
                                    <h3 className={`text-sm font-medium ${locationError ? 'text-red-900' : 'text-blue-900'}`}>
                                        GPS Location Tracking
                                    </h3>
                                    <div className="mt-2 text-sm">
                                        {location ? (
                                            <div>
                                                <div className="flex items-center text-green-700 mb-1">
                                                    <span className="mr-2">✅</span>
                                                    <span className="font-medium">Location captured successfully</span>
                                                </div>
                                                <div className="space-y-1 text-xs text-green-600">
                                                    <p>Latitude: {location.lat.toFixed(6)}°</p>
                                                    <p>Longitude: {location.lng.toFixed(6)}°</p>
                                                    {location.accuracy && (
                                                        <p>Accuracy: ±{location.accuracy.toFixed(0)} meters</p>
                                                    )}
                                                    {location.altitude && (
                                                        <p>Altitude: {location.altitude.toFixed(1)}m</p>
                                                    )}
                                                </div>
                                            </div>
                                        ) : locationError ? (
                                            <div className="text-red-700">
                                                <div className="flex items-center mb-1">
                                                    <span className="mr-2">❌</span>
                                                    <span className="font-medium">Location Error</span>
                                                </div>
                                                <p className="text-xs">{locationError}</p>
                                                <button
                                                    type="button"
                                                    onClick={() => window.location.reload()}
                                                    className="mt-2 text-xs bg-red-100 hover:bg-red-200 text-red-800 px-2 py-1 rounded"
                                                >
                                                    Retry Location
                                                </button>
                                            </div>
                                        ) : isGeolocationAvailable ? (
                                            <div className="text-blue-700">
                                                <div className="flex items-center">
                                                    <span className="mr-2">⏳</span>
                                                    <span>{isLocating ? 'Getting precise GPS location...' : 'Waiting for location permission...'}</span>
                                                </div>
                                                <p className="text-xs mt-1">This may take a few seconds for high accuracy</p>
                                            </div>
                                        ) : (
                                            <div className="text-red-700">
                                                <div className="flex items-center mb-1">
                                                    <span className="mr-2">❌</span>
                                                    <span className="font-medium">Location Not Available</span>
                                                </div>
                                                <p className="text-xs">Your browser doesn't support geolocation or location services are disabled.</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* AI Analysis Notice */}
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                            <div className="flex items-start">
                                <div className="flex-shrink-0">
                                    <span className="text-yellow-600 text-lg">🤖</span>
                                </div>
                                <div className="ml-3">
                                    <h3 className="text-sm font-medium text-yellow-900">AI Analysis</h3>
                                    <p className="mt-1 text-sm text-yellow-700">
                                        Your uploaded media will be automatically analyzed by our AI system to detect
                                        wildlife offences and classify the severity level.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <div className="flex justify-end space-x-3">
                            <button
                                type="button"
                                onClick={() => navigate('/')}
                                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={loading || uploading}
                                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Submitting...' : 'Submit Report'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default ReportForm;
