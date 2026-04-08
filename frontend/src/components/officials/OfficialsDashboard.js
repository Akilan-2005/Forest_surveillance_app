import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import toast from 'react-hot-toast';
import io from 'socket.io-client';
import NotificationCenter from '../common/NotificationCenter';
import EnhancedDetectionViewer from '../user/EnhancedDetectionViewer';

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const OfficialsDashboard = () => {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedStatus, setSelectedStatus] = useState('all');
    const [selectedReport, setSelectedReport] = useState(null);
    const [viewingReport, setViewingReport] = useState(null);  // For detection viewer modal
    const [detectionMode, setDetectionMode] = useState('threat'); // 'species' or 'threat'
    const [showAnnotations, setShowAnnotations] = useState(true);
    const [showDetectionModal, setShowDetectionModal] = useState(false);
    const [selectedReportForDetection, setSelectedReportForDetection] = useState(null);
    const [detectionLoading, setDetectionLoading] = useState(false);
    const [socket, setSocket] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [stats, setStats] = useState({
        total: 0,
        new: 0,
        investigation: 0,
        verified: 0,
        resolved: 0
    });

    useEffect(() => {
        fetchReports();

        const newSocket = io(process.env.REACT_APP_API_URL || 'http://localhost:5000');

        newSocket.on('connect', () => {
            console.log('Connected to server');
            setConnectionStatus('connected');
            newSocket.emit('join_officials');
        });

        newSocket.on('disconnect', () => {
            console.log('Disconnected from server');
            setConnectionStatus('disconnected');
        });

        newSocket.on('critical_threat_alert', (data) => {
            console.log('Critical threat alert received:', data);
            toast.error(`🚨 CRITICAL THREAT ALERT: ${data.message}`, {
                duration: 10000,
                icon: '🚨'
            });
            fetchReports(); // Refresh reports
        });

        newSocket.on('new_report', (data) => {
            console.log('New report received:', data);
            toast.success(`New ${data.report?.severity || 'New'} severity report: ${data.report?.title || ''}`, { id: data.report?._id || 'new_report' });
            fetchReports(); // Refresh reports
        });

        newSocket.on('status_update', (data) => {
            console.log('Status update received:', data);
            toast(`Report status updated to: ${data.status}`, { icon: 'ℹ️', id: data.report_id ? `status-${data.report_id}` : 'status_update' });
            fetchReports(); // Refresh reports
        });

        setSocket(newSocket);

        return () => {
            newSocket.disconnect();
        };
    }, [selectedStatus]);

    const fetchReports = async () => {
        try {
            setLoading(true);
            const params = selectedStatus !== 'all' ? { status: selectedStatus } : {};
            const response = await axios.get('/api/reports', { params });
            setReports(response.data.reports);

            // Calculate stats
            const total = response.data.reports.length;
            const newCount = response.data.reports.filter(r => r.status === 'New').length;
            const investigationCount = response.data.reports.filter(r => r.status === 'Under Investigation').length;
            const verifiedCount = response.data.reports.filter(r => r.status === 'Verified').length;
            const resolvedCount = response.data.reports.filter(r => r.status === 'Resolved').length;

            setStats({ total, new: newCount, investigation: investigationCount, verified: verifiedCount, resolved: resolvedCount });
        } catch (error) {
            toast.error('Failed to fetch reports', { id: 'fetch-reports-error' });
        } finally {
            setLoading(false);
        }
    };

    const updateReportStatus = async (reportId, newStatus, notes = '') => {
        try {
            await axios.put(`/api/reports/${reportId}/status`, {
                status: newStatus,
                notes
            });

            toast.success('Status updated successfully', { id: 'status-update-success' });
            fetchReports();
            setSelectedReport(null);
        } catch (error) {
            console.error('Status update error:', error);
            toast.error('Failed to update status', { id: 'status-update-error' });
        }
    };

    const runDetection = async (report, forceMode = null) => {
        if (!report.media_data) {
            toast.error('No image available for detection', { id: 'detection-error-no-image' });
            return;
        }

        const modeToUse = forceMode || report.offence_type || 'Threat Monitoring';
        setDetectionMode(modeToUse === 'Species Monitoring' ? 'Species Monitoring' : 'Threat Monitoring');

        setDetectionLoading(true);
        toast.loading(`Running ${modeToUse === 'Species Monitoring' ? 'Species' : 'Threat'} detection...`, { id: 'detection' });

        try {
            // Convert base64 to blob for multipart upload
            const base64Data = report.media_data.split(',')[1] || report.media_data;
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/jpeg' });
            
            // Create form data
            const formData = new FormData();
            formData.append('file', blob, 'image.jpg');
            // Pass the selected detection mode back to the backend
            formData.append('offence_type', modeToUse);

            // Call the FastAPI YOLO detection endpoint with timeout
            const response = await axios.post('http://localhost:8000/detect', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                timeout: 60000 // 60 second timeout for detection
            });

            // Trigger alerts for high-threat detections
            const detections = response.data.detections || [];
            const criticalThreats = detections.filter(d => d.threat_level === 'CRITICAL');
            if (criticalThreats.length > 0) {
                toast.error(`ALERT: ${criticalThreats.length} CRITICAL threat(s) detected!`, { duration: 5000, icon: '🚨' });
            }

            // Update the report with new detections from FastAPI
            const updatedReport = {
                ...report,
                yolo_detections: detections
            };
            setViewingReport(updatedReport);
            toast.success(`Detected ${detections.length} objects`, { id: 'detection' });
        } catch (error) {
            console.error('Detection error:', error);
            
            let errorMessage = 'Failed to run detection';
            
            if (error.code === 'ECONNABORTED') {
                errorMessage = 'Detection timeout - model is processing. Please try again.';
            } else if (error.response?.status === 503) {
                errorMessage = 'Detection model not initialized. Backend may still be starting up. Please wait a moment and try again.';
            } else if (error.response?.status === 500) {
                errorMessage = `Detection error: ${error.response.data?.detail || 'Internal server error'}`;
            } else if (error.response?.status === 400) {
                errorMessage = `Invalid request: ${error.response.data?.detail || 'Bad request'}`;
            } else if (error.code === 'ERR_NETWORK' || !error.response) {
                errorMessage = 'Cannot connect to detection service. Is the FastAPI backend running on port 8000? Run: uvicorn api_yolo:app --reload --host 0.0.0.0 --port 8000';
            }
            
            toast.error(errorMessage, { id: 'detection', duration: 4000 });
            // Still show the report even if detection fails
            setViewingReport(report);
        } finally {
            setDetectionLoading(false);
        }
    };

    const handleDetectionAnalysis = (report) => {
        setSelectedReportForDetection(report);
        setShowDetectionModal(true);
        // Set detection mode based on report's stored detection mode or offence type
        if (report.detection_mode) {
            setDetectionMode(report.detection_mode);
        } else if (report.offence_type === 'Species Monitoring') {
            setDetectionMode('species');
        } else {
            setDetectionMode('threat');
        }
    };

    const handleDetectionModeChange = (mode, detections) => {
        setDetectionMode(mode);
        console.log(`Detection mode changed to: ${mode}, found ${detections.length} objects`);
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'Critical': return 'bg-red-100 text-red-800 border-red-200';
            case 'Medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'Low': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'New': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'Under Investigation': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'Verified': return 'bg-purple-100 text-purple-800 border-purple-200';
            case 'Resolved': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getMarkerColor = (severity) => {
        switch (severity) {
            case 'Critical': return 'red';
            case 'Medium': return 'orange';
            case 'Low': return 'green';
            default: return 'blue';
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="loading-spinner"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Forest Officials Dashboard</h1>
                            <p className="mt-2 text-gray-600">
                                Monitor and manage wildlife offence reports in real-time
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <NotificationCenter />
                            <div className={`flex items-center px-3 py-2 rounded-full text-sm font-medium ${connectionStatus === 'connected'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                                }`}>
                                <div className={`w-2 h-2 rounded-full mr-2 ${connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'
                                    }`}></div>
                                {connectionStatus === 'connected' ? 'Live Updates' : 'Disconnected'}
                            </div>
                            <button
                                onClick={fetchReports}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                            >
                                🔄 Refresh
                            </button>
                        </div>
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-primary-100 rounded-lg">
                                <span className="text-primary-600 text-xl">📊</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Total Reports</p>
                                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-blue-100 rounded-lg">
                                <span className="text-blue-600 text-xl">🆕</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">New</p>
                                <p className="text-2xl font-bold text-blue-600">{stats.new}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-orange-100 rounded-lg">
                                <span className="text-orange-600 text-xl">🔍</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Under Investigation</p>
                                <p className="text-2xl font-bold text-orange-600">{stats.investigation}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-purple-100 rounded-lg">
                                <span className="text-purple-600 text-xl">✅</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Verified</p>
                                <p className="text-2xl font-bold text-purple-600">{stats.verified}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-green-100 rounded-lg">
                                <span className="text-green-600 text-xl">🎯</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Resolved</p>
                                <p className="text-2xl font-bold text-green-600">{stats.resolved}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white rounded-lg shadow mb-6">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-medium text-gray-900">Reports</h3>
                            <div className="flex space-x-2">
                                <select
                                    value={selectedStatus}
                                    onChange={(e) => setSelectedStatus(e.target.value)}
                                    className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                                >
                                    <option value="all">All Status</option>
                                    <option value="New">New</option>
                                    <option value="Under Investigation">Under Investigation</option>
                                    <option value="Verified">Verified</option>
                                    <option value="Resolved">Resolved</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Map */}
                    <div className="p-6">
                        <h4 className="text-lg font-medium text-gray-900 mb-4">Report Locations Map</h4>
                        <div className="h-96 rounded-lg overflow-hidden">
                            <MapContainer
                                center={reports.length > 0 && reports[0].location?.lat && reports[0].location?.lng 
                                    ? [reports[0].location.lat, reports[0].location.lng] 
                                    : [20.5937, 78.9629]}
                                zoom={reports.length > 0 ? 8 : 6}
                                style={{ height: '100%', width: '100%', zIndex: 0 }}
                            >
                                <TileLayer
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                />
                                {reports.map((report) => {
                                    if (!report.location?.lat || !report.location?.lng || 
                                        report.location.lat === 0 || report.location.lng === 0) return null;

                                    const markerColor = getMarkerColor(report.severity);
                                    const iconSize = report.severity === 'Critical' ? 25 : 
                                                   report.severity === 'Medium' ? 20 : 15;
                                    
                                    const customIcon = new L.DivIcon({
                                        className: 'custom-div-icon',
                                        html: `<div style="background-color: ${markerColor}; width: ${iconSize}px; height: ${iconSize}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 8px;">${report.severity[0]}</div>`,
                                        iconSize: [iconSize, iconSize],
                                        iconAnchor: [iconSize/2, iconSize/2]
                                    });

                                    return (
                                        <Marker
                                            key={report._id}
                                            position={[report.location.lat, report.location.lng]}
                                            icon={customIcon}
                                            eventHandlers={{
                                                click: () => setSelectedReport(report)
                                            }}
                                        >
                                            <Popup maxWidth={300}>
                                                <div className="p-3">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <h4 className="font-medium text-gray-900">{report.title}</h4>
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(report.severity)}`}>
                                                            {report.severity}
                                                        </span>
                                                    </div>
                                                    <div className="space-y-2 text-sm">
                                                        <p><strong>Offence Type:</strong> {report.offence_type}</p>
                                                        <p><strong>Reported by:</strong> {report.user_name}</p>
                                                        <p><strong>Location:</strong> {report.location.address}</p>
                                                        <p><strong>Coordinates:</strong> {report.location.lat.toFixed(6)}, {report.location.lng.toFixed(6)}</p>
                                                        {report.location.accuracy && (
                                                            <p><strong>GPS Accuracy:</strong> ±{report.location.accuracy.toFixed(0)}m</p>
                                                        )}
                                                        <p><strong>Date:</strong> {new Date(report.created_at).toLocaleDateString()}</p>
                                                        <p><strong>Time:</strong> {new Date(report.created_at).toLocaleTimeString()}</p>
                                                        <div className="flex items-center space-x-2">
                                                            <span className="text-xs font-medium text-gray-700">Status:</span>
                                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(report.status)}`}>
                                                                {report.status}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => setSelectedReport(report)}
                                                        className="mt-3 w-full px-3 py-1 text-sm font-medium text-blue-600 hover:text-blue-700 border border-blue-300 rounded-md hover:bg-blue-50"
                                                    >
                                                        View Details & Update Status
                                                    </button>
                                                </div>
                                            </Popup>
                                        </Marker>
                                    );
                                })}
                            </MapContainer>
                        </div>
                        <div className="mt-4 flex items-center justify-center space-x-6 text-xs text-gray-600">
                            <div className="flex items-center">
                                <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
                                <span>Critical</span>
                            </div>
                            <div className="flex items-center">
                                <div className="w-3 h-3 bg-orange-500 rounded-full mr-2"></div>
                                <span>Medium</span>
                            </div>
                            <div className="flex items-center">
                                <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                                <span>Low</span>
                            </div>
                        </div>
                    </div>

                    {/* Reports List */}
                    <div className="divide-y divide-gray-200">
                        {reports.length === 0 ? (
                            <div className="text-center py-12">
                                <div className="text-gray-400 text-6xl mb-4">📋</div>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">No reports found</h3>
                                <p className="text-gray-600">No reports match the current filter</p>
                            </div>
                        ) : (
                            reports.map((report) => (
                                <div key={report._id} className="p-6 hover:bg-gray-50">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-2">
                                                <h4 className="text-lg font-medium text-gray-900">
                                                    {report.title}
                                                </h4>
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(report.severity)}`}>
                                                    {report.severity}
                                                </span>
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(report.status)}`}>
                                                    {report.status}
                                                </span>
                                            </div>

                                            <p className="text-gray-600 mb-3">{report.description}</p>

                                            <div className="flex items-center space-x-4 text-sm text-gray-500 mb-3">
                                                <span>👤 {report.user_name}</span>
                                                <span>📍 {report.location?.address || 'Location not available'}</span>
                                                <span>📅 {new Date(report.created_at).toLocaleDateString()}</span>
                                                <span>🕒 {new Date(report.created_at).toLocaleTimeString()}</span>
                                            </div>

                                            {report.ai_analysis && (
                                                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                                                    <h5 className="text-sm font-medium text-gray-900 mb-1">AI Analysis (Wildlife Offence Detection)</h5>
                                                    <p className="text-sm text-gray-600">{report.ai_analysis.description}</p>
                                                    {report.ai_analysis.detected_objects && report.ai_analysis.detected_objects.length > 0 && (
                                                        <div className="mt-2">
                                                            <span className="text-xs font-medium text-gray-700">Detected: </span>
                                                            <span className="text-xs text-gray-600">
                                                                {report.ai_analysis.detected_objects.join(', ')}
                                                            </span>
                                                        </div>
                                                    )}
                                                    <div className="mt-2 flex items-center space-x-2">
                                                        <span className="text-xs font-medium text-gray-700">Severity:</span>
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                                            report.ai_analysis.severity === 'Critical' ? 'bg-red-100 text-red-800' :
                                                            report.ai_analysis.severity === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                                                            'bg-green-100 text-green-800'
                                                        }`}>
                                                            {report.ai_analysis.severity}
                                                        </span>
                                                        <span className="text-xs text-gray-500">
                                                            Confidence: {(report.ai_analysis.confidence * 100).toFixed(0)}%
                                                        </span>
                                                    </div>
                                                </div>
                                            )}

                                            {/* YOLO Object Detection Results */}
                                            {report.yolo_detections && report.yolo_detections.length > 0 && (
                                                <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <h5 className="text-sm font-medium text-blue-900">
                                                            AI Object Detection (YOLO)
                                                        </h5>
                                                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                                                            {report.yolo_detections.length} objects
                                                        </span>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        {report.yolo_detections.slice(0, 5).map((det, idx) => (
                                                            <span 
                                                                key={idx}
                                                                className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-white text-blue-700 border border-blue-200"
                                                            >
                                                                {det.label} ({(det.confidence * 100).toFixed(0)}%)
                                                            </span>
                                                        ))}
                                                        {report.yolo_detections.length > 5 && (
                                                            <span className="text-xs text-blue-600">
                                                                +{report.yolo_detections.length - 5} more
                                                            </span>
                                                        )}
                                                    </div>
                                                    <button
                                                        onClick={() => setViewingReport(report)}
                                                        className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                                                    >
                                                        View Detection Details & Bounding Boxes →
                                                    </button>
                                                    <div className="mt-4">
                                                        <div className="flex items-center justify-between mb-4">
                                                            <h3 className="text-lg font-medium text-gray-900">Detection Results</h3>
                                                            <div className="flex items-center space-x-2">
                                                                <div className="text-sm text-gray-600">
                                                                    Mode: <span className={`font-medium ${
                                                                        mode === 'species' ? 'text-green-600' : 'text-red-600'
                                                                    }`}>
                                                                        {mode === 'species' ? '🦁 Species Monitoring' : '🚨 Threat Monitoring'}
                                                                    </span>
                                                                </div>
                                                                <button
                                                                    onClick={() => setShowAnnotations(!showAnnotations)}
                                                                    className={`px-3 py-1 rounded-md text-sm font-medium ${
                                                                        showAnnotations
                                                                            ? 'bg-blue-100 text-blue-700'
                                                                            : 'bg-gray-100 text-gray-700'
                                                                    }`}
                                                                >
                                                                    {showAnnotations ? 'Hide Boxes' : 'Show Boxes'}
                                                                </button>
                                                                <button
                                                                    onClick={runDetection}
                                                                    disabled={loading}
                                                                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                                                                >
                                                                    {loading ? 'Detecting...' : 'Re-run Detection'}
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>

                                        <div className="ml-4 flex space-x-2">
                                            <button
                                                onClick={() => runDetection(report)}
                                                className="px-3 py-1 text-sm font-medium text-blue-600 hover:text-blue-700 border border-blue-300 rounded-md hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                                disabled={!report.media_data || detectionLoading}
                                            >
                                                {detectionLoading ? 'Detecting...' : (report.media_data ? 'View Image & Detect' : 'No Image')}
                                            </button>
                                            <button
                                                onClick={() => setSelectedReport(report)}
                                                className="px-3 py-1 text-sm font-medium text-primary-600 hover:text-primary-700 border border-primary-300 rounded-md hover:bg-primary-50"
                                            >
                                                Update Status
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Status Update Modal */}
                {selectedReport && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                            <div className="mt-3">
                                <h3 className="text-lg font-medium text-gray-900 mb-4">
                                    Update Report Status
                                </h3>
                                <div className="mb-4">
                                    <p className="text-sm text-gray-600 mb-2">
                                        <strong>Report:</strong> {selectedReport.title}
                                    </p>
                                    <p className="text-sm text-gray-600">
                                        <strong>Current Status:</strong> {selectedReport.status}
                                    </p>
                                </div>

                                <div className="space-y-3">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            New Status
                                        </label>
                                        <select
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                                            onChange={(e) => {
                                                const newStatus = e.target.value;
                                                const notes = prompt('Add notes (optional):') || '';
                                                updateReportStatus(selectedReport._id, newStatus, notes);
                                            }}
                                        >
                                            <option value="">Select new status</option>
                                            <option value="Under Investigation">Under Investigation</option>
                                            <option value="Verified">Verified</option>
                                            <option value="Resolved">Resolved</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="flex justify-end space-x-3 mt-6">
                                    <button
                                        onClick={() => setSelectedReport(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Detection Details Modal */}
                {viewingReport && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-75 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
                            <div className="mt-3">
                                {/* Header */}
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h3 className="text-2xl font-bold text-gray-900">
                                            AI Detection Results
                                        </h3>
                                        <p className="text-gray-600 mt-1">
                                            Report: {viewingReport.title}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => setViewingReport(null)}
                                        className="text-gray-400 hover:text-gray-600 text-2xl"
                                    >
                                        ×
                                    </button>
                                </div>

                                {/* Detection Mode Switcher */}
                                <div className="flex items-center space-x-4 mb-4 bg-gray-50 p-3 rounded-lg border border-gray-200">
                                    <label className="text-sm font-medium text-gray-700">Detection Mode:</label>
                                    <select
                                        value={detectionMode}
                                        onChange={(e) => setDetectionMode(e.target.value)}
                                        className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-primary-500 font-medium"
                                    >
                                        <option value="Species Monitoring">Species Monitoring (Animals Only)</option>
                                        <option value="Threat Monitoring">Threat Monitoring (Weapons/Poachers)</option>
                                    </select>
                                    <button
                                        onClick={() => runDetection(viewingReport, detectionMode)}
                                        disabled={detectionLoading}
                                        className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
                                    >
                                        {detectionLoading ? 'Detecting...' : 'Re-run Detection'}
                                    </button>
                                </div>

                                {/* Detection Viewer */}
                                {viewingReport.media_data && (
                                    <EnhancedDetectionViewer
                                        imageUrl={viewingReport.media_data}
                                        report={viewingReport}
                                        onModeChange={handleDetectionModeChange}
                                    />
                                )}

                                {/* Detection Summary */}
                                {viewingReport.yolo_detections && viewingReport.yolo_detections.length > 0 && (
                                    <div className="mt-6 bg-gray-50 rounded-lg p-4">
                                        <h4 className="font-semibold text-gray-900 mb-2">Detection Summary</h4>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="bg-white rounded p-3 text-center">
                                                <p className="text-2xl font-bold text-blue-600">
                                                    {viewingReport.yolo_detections.length}
                                                </p>
                                                <p className="text-xs text-gray-500">Total Detections</p>
                                            </div>
                                            <div className="bg-white rounded p-3 text-center">
                                                <p className="text-2xl font-bold text-green-600">
                                                    {new Set(viewingReport.yolo_detections.map(d => d.label)).size}
                                                </p>
                                                <p className="text-xs text-gray-500">Unique Classes</p>
                                            </div>
                                            <div className="bg-white rounded p-3 text-center">
                                                <p className="text-2xl font-bold text-purple-600">
                                                    {(Math.max(...viewingReport.yolo_detections.map(d => d.confidence)) * 100).toFixed(0)}%
                                                </p>
                                                <p className="text-xs text-gray-500">Highest Confidence</p>
                                            </div>
                                            <div className="bg-white rounded p-3 text-center">
                                                <p className="text-2xl font-bold text-orange-600">
                                                    {(viewingReport.yolo_detections.reduce((acc, d) => acc + d.confidence, 0) / viewingReport.yolo_detections.length * 100).toFixed(0)}%
                                                </p>
                                                <p className="text-xs text-gray-500">Average Confidence</p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Close button */}
                                <div className="flex justify-end mt-6">
                                    <button
                                        onClick={() => setViewingReport(null)}
                                        className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Enhanced Detection Modal */}
                {showDetectionModal && selectedReportForDetection && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-20 mx-auto p-5 border w-11/12 shadow-lg rounded-md bg-white max-h-screen overflow-y-auto">
                            <div className="mt-3 text-center">
                                <h3 className="text-lg font-medium text-gray-900 mb-2">
                                    Enhanced Detection Analysis
                                </h3>
                                <p className="text-sm text-gray-600 mb-4">
                                    Report: {selectedReportForDetection.title}
                                </p>
                            </div>

                            <div className="mt-4">
                                <EnhancedDetectionViewer
                                    imageUrl={selectedReportForDetection.media_data}
                                    report={selectedReportForDetection}
                                    onModeChange={handleDetectionModeChange}
                                />
                            </div>

                            <div className="flex justify-end space-x-3 mt-6">
                                <button
                                    onClick={() => {
                                        setShowDetectionModal(false);
                                        setSelectedReportForDetection(null);
                                    }}
                                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default OfficialsDashboard;
