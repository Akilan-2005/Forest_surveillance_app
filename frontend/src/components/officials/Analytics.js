import React, { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import toast from 'react-hot-toast';
import io from 'socket.io-client';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement
);

const Analytics = () => {
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [dateRange, setDateRange] = useState(30);
    const [socket, setSocket] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [autoRefresh, setAutoRefresh] = useState(false);

    useEffect(() => {
        fetchAnalytics();
        initializeSocket();

        return () => {
            if (socket) {
                socket.disconnect();
            }
        };
    }, [dateRange]);

    const initializeSocket = () => {
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

        newSocket.on('new_report', (data) => {
            console.log('New report received:', data);
            if (autoRefresh) {
                fetchAnalytics();
                toast.success('Analytics updated with new report');
            }
        });

        setSocket(newSocket);
    };

    // Auto-refresh effect
    useEffect(() => {
        let interval;
        if (autoRefresh) {
            interval = setInterval(() => {
                fetchAnalytics();
            }, 30000); // Refresh every 30 seconds
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [autoRefresh]);

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/analytics', {
                params: { days: dateRange }
            });
            setAnalytics(response.data);
        } catch (error) {
            console.error('Error fetching analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="loading-spinner"></div>
            </div>
        );
    }

    if (!analytics) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="text-gray-400 text-6xl mb-4">📊</div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No analytics data</h3>
                    <p className="text-gray-600">Analytics data is not available</p>
                </div>
            </div>
        );
    }

    // Prepare chart data
    const offenceData = {
        labels: analytics.offence_stats.map(item => item._id),
        datasets: [
            {
                label: 'Number of Reports',
                data: analytics.offence_stats.map(item => item.count),
                backgroundColor: [
                    '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'
                ],
                borderColor: [
                    '#dc2626', '#ea580c', '#ca8a04', '#16a34a', '#0891b2', '#2563eb', '#7c3aed', '#db2777'
                ],
                borderWidth: 1,
            },
        ],
    };

    const severityData = {
        labels: analytics.severity_stats.map(item => item._id),
        datasets: [
            {
                data: analytics.severity_stats.map(item => item.count),
                backgroundColor: ['#ef4444', '#f97316', '#22c55e'],
                borderColor: ['#dc2626', '#ea580c', '#16a34a'],
                borderWidth: 1,
            },
        ],
    };

    const dailyData = {
        labels: analytics.daily_reports.map(item => item._id),
        datasets: [
            {
                label: 'Daily Reports',
                data: analytics.daily_reports.map(item => item.count),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.1,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
            },
            title: {
                display: true,
                text: 'Wildlife Offence Analytics',
            },
        },
    };

    const getMarkerColor = (count) => {
        if (count >= 5) return '#ef4444'; // Red for high risk
        if (count >= 3) return '#f97316'; // Orange for medium risk
        return '#22c55e'; // Green for low risk
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
                            <p className="mt-2 text-gray-600">
                                Comprehensive insights into wildlife offence patterns and trends
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <div className={`flex items-center px-3 py-2 rounded-full text-sm font-medium ${connectionStatus === 'connected'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                <div className={`w-2 h-2 rounded-full mr-2 ${connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'
                                    }`}></div>
                                {connectionStatus === 'connected' ? 'Live' : 'Offline'}
                            </div>
                            <button
                                onClick={() => setAutoRefresh(!autoRefresh)}
                                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${autoRefresh
                                        ? 'bg-green-600 text-white hover:bg-green-700'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                            >
                                {autoRefresh ? '🔄 Auto Refresh ON' : '⏸️ Auto Refresh OFF'}
                            </button>
                            <label className="text-sm font-medium text-gray-700">Date Range:</label>
                            <select
                                value={dateRange}
                                onChange={(e) => setDateRange(Number(e.target.value))}
                                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                            >
                                <option value={7}>Last 7 days</option>
                                <option value={30}>Last 30 days</option>
                                <option value={90}>Last 90 days</option>
                                <option value={365}>Last year</option>
                            </select>
                            <button
                                onClick={fetchAnalytics}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                            >
                                🔄 Refresh
                            </button>
                        </div>
                    </div>
                </div>

                {/* Charts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                    {/* Offence Types Chart */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Offence Types Distribution</h3>
                        <div className="h-80">
                            <Bar data={offenceData} options={chartOptions} />
                        </div>
                    </div>

                    {/* Severity Distribution */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Severity Distribution</h3>
                        <div className="h-80">
                            <Doughnut
                                data={severityData}
                                options={{
                                    ...chartOptions,
                                    plugins: {
                                        ...chartOptions.plugins,
                                        title: {
                                            display: false,
                                        },
                                    },
                                }}
                            />
                        </div>
                    </div>
                </div>

                {/* Daily Trends */}
                <div className="bg-white rounded-lg shadow p-6 mb-8">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">Daily Report Trends</h3>
                    <div className="h-80">
                        <Line
                            data={dailyData}
                            options={{
                                ...chartOptions,
                                plugins: {
                                    ...chartOptions.plugins,
                                    title: {
                                        display: false,
                                    },
                                },
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        ticks: {
                                            stepSize: 1,
                                        },
                                    },
                                },
                            }}
                        />
                    </div>
                </div>

                {/* High Risk Zones Map */}
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">High Risk Zones</h3>
                    <div className="h-96 rounded-lg overflow-hidden">
                        <MapContainer
                            center={[20.5937, 78.9629]} // India center
                            zoom={6}
                            style={{ height: '100%', width: '100%', zIndex: 0 }}
                        >
                            <TileLayer
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                            />
                            {analytics.high_risk_zones.map((zone, index) => (
                                <CircleMarker
                                    key={index}
                                    center={[zone._id.lat, zone._id.lng]}
                                    radius={Math.min(zone.count * 2, 20)}
                                    pathOptions={{
                                        color: getMarkerColor(zone.count),
                                        fillColor: getMarkerColor(zone.count),
                                        fillOpacity: 0.6,
                                        weight: 2,
                                    }}
                                >
                                    <Popup>
                                        <div className="p-2">
                                            <h3 className="font-medium text-gray-900">High Risk Zone</h3>
                                            <p className="text-sm text-gray-600">
                                                <strong>Reports:</strong> {zone.count}
                                            </p>
                                            <p className="text-xs text-gray-500">
                                                Lat: {zone._id.lat}, Lng: {zone._id.lng}
                                            </p>
                                        </div>
                                    </Popup>
                                </CircleMarker>
                            ))}
                        </MapContainer>
                    </div>
                </div>

                {/* Summary Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-red-100 rounded-lg">
                                <span className="text-red-600 text-xl">🚨</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Critical Reports</p>
                                <p className="text-2xl font-bold text-red-600">
                                    {analytics.severity_stats.find(s => s._id === 'Critical')?.count || 0}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-orange-100 rounded-lg">
                                <span className="text-orange-600 text-xl">⚠️</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Medium Reports</p>
                                <p className="text-2xl font-bold text-orange-600">
                                    {analytics.severity_stats.find(s => s._id === 'Medium')?.count || 0}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-green-100 rounded-lg">
                                <span className="text-green-600 text-xl">✅</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Low Reports</p>
                                <p className="text-2xl font-bold text-green-600">
                                    {analytics.severity_stats.find(s => s._id === 'Low')?.count || 0}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Analytics;
