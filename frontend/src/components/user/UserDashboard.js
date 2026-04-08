import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import io from 'socket.io-client';
import toast from 'react-hot-toast';

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const UserDashboard = () => {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const [socket, setSocket] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [stats, setStats] = useState({
        total: 0,
        critical: 0,
        medium: 0,
        low: 0
    });
    const [lastUpdated, setLastUpdated] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        fetchUserReports();

        const newSocket = io(process.env.REACT_APP_API_URL || 'http://localhost:5000');

        newSocket.on('connect', () => {
            console.log('Connected to server');
            setConnectionStatus('connected');
            // Join user room for status updates
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (user._id) {
                newSocket.emit('join_user', { user_id: user._id });
            }
        });

        newSocket.on('disconnect', () => {
            console.log('Disconnected from server');
            setConnectionStatus('disconnected');
        });

        newSocket.on('status_update', (data) => {
            console.log('Status update received:', data);
            toast.success(`Your report status has been updated to: ${data.status}`, { id: data.report_id || 'status_update' });
            fetchUserReports(); // Refresh reports
        });

        setSocket(newSocket);

        // Auto-refresh every 30 seconds if enabled
        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchUserReports(false); // Silent refresh
            }, 30000);
            return () => clearInterval(interval);
        }

        return () => {
            newSocket.disconnect();
        };
    }, [autoRefresh]);

    const fetchUserReports = async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            
            // Add cache busting timestamp
            const timestamp = Date.now();
            const response = await axios.get(`/api/reports/user?t=${timestamp}`);
            
            console.log('User reports response:', response.data);
            console.log('Response data:', response.data);
            console.log('Reports array:', response.data.reports);
            console.log('Reports count:', response.data.reports?.length || 0);
            
            setReports(response.data.reports || []);
            setLastUpdated(new Date());

            // Calculate stats efficiently
            const reports = response.data.reports || [];
            const stats = reports.reduce((acc, report) => {
                acc.total++;
                if (report.severity === 'Critical') acc.critical++;
                else if (report.severity === 'Medium') acc.medium++;
                else if (report.severity === 'Low') acc.low++;
                return acc;
            }, { total: 0, critical: 0, medium: 0, low: 0 });

            setStats(stats);
            
            // Debug logging
            console.log(`Fetched ${reports.length} reports for user`);
            reports.forEach((report, index) => {
                console.log(`Report ${index + 1}: ${report.title} - ${report.status}`);
            });
            
        } catch (error) {
            console.error('Error fetching reports:', error);
            if (error.response?.status !== 304) { // Not modified
                toast.error('Failed to fetch reports');
            }
        } finally {
            if (showLoading) setLoading(false);
        }
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

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="loading-spinner"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Your Wildlife</h1>
                            <p className="mt-2 text-gray-600">
                                Track your submitted reports and their current status
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <div className={`flex items-center px-3 py-2 rounded-full text-sm font-medium ${connectionStatus === 'connected'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                <div className={`w-2 h-2 rounded-full mr-2 ${connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'
                                    }`}></div>
                                {connectionStatus === 'connected' ? 'Live Updates' : 'Disconnected'}
                            </div>
                            <button
                                onClick={() => setAutoRefresh(!autoRefresh)}
                                className={`px-3 py-2 rounded-full text-sm font-medium ${
                                    autoRefresh 
                                        ? 'bg-blue-100 text-blue-800' 
                                        : 'bg-gray-100 text-gray-800'
                                }`}
                                title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
                            >
                                {autoRefresh ? '🔄 Auto' : '⏸️ Auto'}
                            </button>
                            {lastUpdated && (
                                <span className="text-xs text-gray-500">
                                    Last: {lastUpdated.toLocaleTimeString()}
                                </span>
                            )}
                            <button
                                onClick={() => fetchUserReports()}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                            >
                                🔄 Refresh
                            </button>
                        </div>
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
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
                            <div className="p-2 bg-red-100 rounded-lg">
                                <span className="text-red-600 text-xl">🚨</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Critical</p>
                                <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-yellow-100 rounded-lg">
                                <span className="text-yellow-600 text-xl">⚠️</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Medium</p>
                                <p className="text-2xl font-bold text-yellow-600">{stats.medium}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-green-100 rounded-lg">
                                <span className="text-green-600 text-xl">✅</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Low</p>
                                <p className="text-2xl font-bold text-green-600">{stats.low}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="mb-8">
                    <Link
                        to="/report"
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    >
                        <span className="mr-2">➕</span>
                        Report New Offence
                    </Link>
                </div>

                {/* Map Visualization */}
                {reports.length > 0 && (
                    <div className="bg-white shadow rounded-lg mb-8">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h3 className="text-lg font-medium text-gray-900">Your Report Locations</h3>
                            <p className="text-sm text-gray-600">Geographic distribution of your submitted reports</p>
                        </div>
                        <div className="p-6">
                            <div className="h-96 rounded-lg overflow-hidden">
                                <MapContainer
                                    center={reports.length > 0 && reports[0].location?.lat && reports[0].location?.lng 
                                        ? [reports[0].location.lat, reports[0].location.lng] 
                                        : [20.5937, 78.9629]}
                                    zoom={reports.length > 0 ? 10 : 6}
                                    style={{ height: '100%', width: '100%', zIndex: 0 }}
                                >
                                    <TileLayer
                                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                    />
                                    {reports.map((report) => {
                                        if (!report.location?.lat || !report.location?.lng || 
                                            report.location.lat === 0 || report.location.lng === 0) return null;

                                        const markerColor = report.severity === 'Critical' ? 'red' : 
                                                         report.severity === 'Medium' ? 'orange' : 'green';
                                        const customIcon = new L.DivIcon({
                                            className: 'custom-div-icon',
                                            html: `<div style="background-color: ${markerColor}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                                            iconSize: [20, 20],
                                            iconAnchor: [10, 10]
                                        });

                                        return (
                                            <Marker
                                                key={report._id}
                                                position={[report.location.lat, report.location.lng]}
                                                icon={customIcon}
                                            >
                                                <Popup>
                                                    <div className="p-2 max-w-xs">
                                                        <h4 className="font-medium text-gray-900 mb-1">{report.title}</h4>
                                                        <p className="text-sm text-gray-600 mb-2">{report.offence_type}</p>
                                                        <div className="text-xs text-gray-500 space-y-1">
                                                            <p><strong>Location:</strong> {report.location.address}</p>
                                                            <p><strong>Coordinates:</strong> {report.location.lat.toFixed(6)}, {report.location.lng.toFixed(6)}</p>
                                                            {report.location.accuracy && (
                                                                <p><strong>Accuracy:</strong> ±{report.location.accuracy.toFixed(0)}m</p>
                                                            )}
                                                            <p><strong>Date:</strong> {new Date(report.created_at).toLocaleDateString()}</p>
                                                            <p><strong>Status:</strong> {report.status}</p>
                                                        </div>
                                                    </div>
                                                </Popup>
                                            </Marker>
                                        );
                                    })}
                                </MapContainer>
                            </div>
                        </div>
                    </div>
                )}
                <div className="bg-white shadow rounded-lg">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h3 className="text-lg font-medium text-gray-900">Your Reports</h3>
                    </div>

                    {reports.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="text-gray-400 text-6xl mb-4">📝</div>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">No reports yet</h3>
                            <p className="text-gray-600 mb-4">Start by reporting a wildlife offence</p>
                            <Link
                                to="/report"
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                            >
                                Create First Report
                            </Link>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200">
                            {reports.map((report) => (
                                <div key={report._id} className="p-6">
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

                                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                                                <span>📍 {report.location?.address || 'Location not available'}</span>
                                                <span>📅 {new Date(report.created_at).toLocaleDateString()}</span>
                                                <span>🕒 {new Date(report.created_at).toLocaleTimeString()}</span>
                                            </div>

                                            {report.ai_analysis && (
                                                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                                                    <h5 className="text-sm font-medium text-gray-900 mb-1">AI Analysis</h5>
                                                    <p className="text-sm text-gray-600">{report.ai_analysis.description}</p>
                                                    {report.ai_analysis.detected_objects && report.ai_analysis.detected_objects.length > 0 && (
                                                        <div className="mt-2">
                                                            <span className="text-xs font-medium text-gray-700">Detected: </span>
                                                            <span className="text-xs text-gray-600">
                                                                {report.ai_analysis.detected_objects.join(', ')}
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default UserDashboard;
