import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import toast from 'react-hot-toast';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
    ArcElement
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
    ArcElement
);

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const Analytics = () => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState(30); // days
    const [selectedZone, setSelectedZone] = useState(null);

    useEffect(() => {
        fetchAnalytics();
    }, [timeRange]);

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/analytics?days=${timeRange}`);
            // Handle both old and new response formats
            const data = response.data.analytics || response.data;
            setAnalyticsData(data);
            console.log('Analytics data:', data);
        } catch (error) {
            console.error('Error fetching analytics:', error);
            toast.error('Failed to fetch analytics data');
        } finally {
            setLoading(false);
        }
    };

    // Prepare weekly crime rate chart data
    const getWeeklyChartData = () => {
        if (!analyticsData?.daily_reports) return null;

        const weeklyData = {};
        analyticsData.daily_reports.forEach(day => {
            const weekNumber = Math.floor(new Date(day._id).getDate() / 7) + 1;
            const weekKey = `Week ${weekNumber}`;
            weeklyData[weekKey] = (weeklyData[weekKey] || 0) + day.count;
        });

        return {
            labels: Object.keys(weeklyData),
            datasets: [{
                label: 'Wildlife Crimes Reported',
                data: Object.values(weeklyData),
                backgroundColor: 'rgba(59, 130, 246, 0.5)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 2,
            }]
        };
    };

    // Prepare offence type distribution data
    const getOffenceTypeData = () => {
        if (!analyticsData?.offence_stats) return null;

        return {
            labels: analyticsData.offence_stats.map(stat => stat._id || 'Unknown'),
            datasets: [{
                data: analyticsData.offence_stats.map(stat => stat.count),
                backgroundColor: [
                    '#ef4444',
                    '#f59e0b',
                    '#10b981',
                    '#3b82f6',
                    '#8b5cf6',
                    '#ec4899',
                ],
                borderWidth: 2,
                borderColor: '#ffffff',
            }]
        };
    };

    // Prepare severity distribution data
    const getSeverityData = () => {
        if (!analyticsData?.severity_stats) return null;

        return {
            labels: ['Critical', 'Medium', 'Low'],
            datasets: [{
                label: 'Severity Distribution',
                data: [
                    analyticsData.severity_rate?.High || 0,
                    analyticsData.severity_rate?.Medium || 0,
                    analyticsData.severity_rate?.Low || 0
                ],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                ],
                borderColor: [
                    'rgba(239, 68, 68, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(16, 185, 129, 1)',
                ],
                borderWidth: 2,
            }]
        };
    };

    const getMarkerColor = (count) => {
        if (count >= 10) return 'red';
        if (count >= 5) return 'orange';
        return 'yellow';
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
                            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
                            <p className="mt-2 text-gray-600">
                                Comprehensive analysis of wildlife offence data
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            <select
                                value={timeRange}
                                onChange={(e) => setTimeRange(parseInt(e.target.value))}
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

                {/* Detection Statistics Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-blue-100 rounded-lg">
                                <span className="text-blue-600 text-xl">📊</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Total Reports</p>
                                <p className="text-2xl font-bold text-gray-900">
                                    {analyticsData?.detection_statistics?.total_reports || 
                                     analyticsData?.offence_stats?.reduce((sum, stat) => sum + stat.count, 0) || 0}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-green-100 rounded-lg">
                                <span className="text-green-600 text-xl">🦁</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Species Detected</p>
                                <p className="text-2xl font-bold text-green-600">
                                    {analyticsData?.detection_statistics?.species_detected ||
                                     analyticsData?.offence_stats?.find(s => s._id === 'Species Monitoring')?.count || 0}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center">
                            <div className="p-2 bg-red-100 rounded-lg">
                                <span className="text-red-600 text-xl">🔫</span>
                            </div>
                            <div className="ml-4">
                                <p className="text-sm font-medium text-gray-600">Weapon Detections</p>
                                <p className="text-2xl font-bold text-red-600">
                                    {analyticsData?.detection_statistics?.weapon_detections ||
                                     analyticsData?.offence_stats?.find(s => s._id === 'Poaching')?.count || 0}
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
                                <p className="text-sm font-medium text-gray-600">Critical Threats</p>
                                <p className="text-2xl font-bold text-orange-600">
                                    {analyticsData?.severity_rate?.High || 0}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    {/* Weekly Crime Rate Chart */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Weekly Crime Rate</h3>
                        {getWeeklyChartData() ? (
                            <Bar
                                data={getWeeklyChartData()}
                                options={{
                                    responsive: true,
                                    plugins: {
                                        legend: {
                                            position: 'top',
                                        },
                                        title: {
                                            display: false,
                                        },
                                    },
                                    scales: {
                                        y: {
                                            beginAtZero: true,
                                            title: {
                                                display: true,
                                                text: 'Number of Incidents'
                                            }
                                        }
                                    }
                                }}
                            />
                        ) : (
                            <div className="h-64 flex items-center justify-center text-gray-500">
                                No data available for the selected period
                            </div>
                        )}
                    </div>

                    {/* Offence Type Distribution */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Offence Type Distribution</h3>
                        {getOffenceTypeData() ? (
                            <Pie
                                data={getOffenceTypeData()}
                                options={{
                                    responsive: true,
                                    plugins: {
                                        legend: {
                                            position: 'right',
                                        },
                                        title: {
                                            display: false,
                                        },
                                    }
                                }}
                            />
                        ) : (
                            <div className="h-64 flex items-center justify-center text-gray-500">
                                No offence data available
                            </div>
                        )}
                    </div>
                </div>

                {/* Severity Distribution */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Severity Distribution</h3>
                        {getSeverityData() ? (
                            <Bar
                                data={getSeverityData()}
                                options={{
                                    responsive: true,
                                    plugins: {
                                        legend: {
                                            display: false
                                        }
                                    },
                                    scales: {
                                        y: {
                                            beginAtZero: true,
                                            title: {
                                                display: true,
                                                text: 'Number of Reports'
                                            }
                                        }
                                    }
                                }}
                            />
                        ) : (
                            <div className="h-64 flex items-center justify-center text-gray-500">
                                No severity data available
                            </div>
                        )}
                    </div>

                    {/* High-Risk Zones List */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">High-Risk Zones</h3>
                        {analyticsData?.high_risk_zones?.length > 0 ? (
                            <div className="space-y-3">
                                {analyticsData.high_risk_zones.slice(0, 5).map((zone, index) => (
                                    <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                                        <div className="flex items-center space-x-3">
                                            <span className="text-lg font-bold text-red-600">#{index + 1}</span>
                                            <div>
                                                <p className="text-sm font-medium text-gray-900">
                                                    Zone {String.fromCharCode(65 + index)}
                                                </p>
                                                <p className="text-xs text-gray-600">
                                                    Lat: {zone._id.lat}, Lng: {zone._id.lng}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-lg font-bold text-red-600">{zone.count}</p>
                                            <p className="text-xs text-gray-600">incidents</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="h-64 flex items-center justify-center text-gray-500">
                                No high-risk zones identified
                            </div>
                        )}
                    </div>
                </div>

                {/* High-Risk Zones Map */}
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">High-Risk Zones Map</h3>
                    <div className="h-96 rounded-lg overflow-hidden">
                        {analyticsData?.high_risk_zones?.length > 0 ? (
                            <MapContainer
                                center={[20.5937, 78.9629]} // India center
                                zoom={6}
                                style={{ height: '100%', width: '100%', zIndex: 0 }}
                            >
                                <TileLayer
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                />
                                {analyticsData.high_risk_zones.map((zone, index) => {
                                    const markerColor = getMarkerColor(zone.count);
                                    const customIcon = new L.DivIcon({
                                        className: 'custom-div-icon',
                                        html: `<div style="background-color: ${markerColor}; width: ${15 + zone.count * 2}px; height: ${15 + zone.count * 2}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">${zone.count}</div>`,
                                        iconSize: [15 + zone.count * 2, 15 + zone.count * 2],
                                        iconAnchor: [(15 + zone.count * 2) / 2, (15 + zone.count * 2) / 2]
                                    });

                                    return (
                                        <Marker
                                            key={index}
                                            position={[zone._id.lat, zone._id.lng]}
                                            icon={customIcon}
                                            eventHandlers={{
                                                click: () => setSelectedZone(zone)
                                            }}
                                        >
                                            <Popup>
                                                <div className="p-2">
                                                    <h4 className="font-medium text-gray-900">High-Risk Zone {String.fromCharCode(65 + index)}</h4>
                                                    <p className="text-sm text-gray-600">{zone.count} incidents</p>
                                                    <p className="text-xs text-gray-500">
                                                        Lat: {zone._id.lat}, Lng: {zone._id.lng}
                                                    </p>
                                                </div>
                                            </Popup>
                                        </Marker>
                                    );
                                })}
                            </MapContainer>
                        ) : (
                            <div className="h-full flex items-center justify-center text-gray-500">
                                No location data available for mapping
                            </div>
                        )}
                    </div>
                </div>

                {/* Selected Zone Details Modal */}
                {selectedZone && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                            <div className="mt-3">
                                <h3 className="text-lg font-medium text-gray-900 mb-4">
                                    High-Risk Zone Details
                                </h3>
                                <div className="space-y-3">
                                    <div>
                                        <p className="text-sm text-gray-600">Location</p>
                                        <p className="font-medium">Lat: {selectedZone._id.lat}, Lng: {selectedZone._id.lng}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Incident Count</p>
                                        <p className="font-medium text-red-600">{selectedZone.count} critical incidents</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Risk Level</p>
                                        <p className="font-medium">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                selectedZone.count >= 10 ? 'bg-red-100 text-red-800' :
                                                selectedZone.count >= 5 ? 'bg-orange-100 text-orange-800' :
                                                'bg-yellow-100 text-yellow-800'
                                            }`}>
                                                {selectedZone.count >= 10 ? 'Critical' : selectedZone.count >= 5 ? 'High' : 'Medium'}
                                            </span>
                                        </p>
                                    </div>
                                </div>
                                <div className="flex justify-end space-x-3 mt-6">
                                    <button
                                        onClick={() => setSelectedZone(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Analytics;