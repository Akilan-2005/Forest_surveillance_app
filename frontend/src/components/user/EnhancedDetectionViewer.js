import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

const EnhancedDetectionViewer = ({ imageUrl, report, onModeChange }) => {
    const [detections, setDetections] = useState([]);
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState('species'); // 'species' or 'threat'
    const [annotatedImage, setAnnotatedImage] = useState(null);
    const [showAnnotations, setShowAnnotations] = useState(true);
    const [backendStatus, setBackendStatus] = useState(null);

    // Check backend status on mount
    useEffect(() => {
        checkBackendStatus();
    }, []);

    // Run detection when image or mode changes
    useEffect(() => {
        if (imageUrl) {
            runDetection();
        }
    }, [imageUrl, mode]);

    const checkBackendStatus = async () => {
        try {
            const response = await axios.get('/api/status');
            setBackendStatus(response.data);
            
            // Log status for debugging
            console.log('Backend Status:', response.data);
            
            if (!response.data.enhanced_yolo.initialized) {
                console.warn('⚠️ Enhanced YOLO service not initialized:', response.data.enhanced_yolo.details);
            }
        } catch (error) {
            console.error('Failed to check backend status:', error);
        }
    };

    const runDetection = async (retryCount = 0, maxRetries = 3) => {
        if (!imageUrl) return;

        setLoading(true);
        try {
            console.log(`Starting ${mode} detection${retryCount > 0 ? ` (retry ${retryCount}/${maxRetries})` : ''}...`);
            
            // Convert base64 to blob for upload
            const base64Data = imageUrl.split(',')[1] || imageUrl;
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/jpeg' });

            console.log(`Image blob size: ${blob.size} bytes`);

            // Create form data
            const formData = new FormData();
            formData.append('file', blob, 'image.jpg');
            formData.append('mode', mode);
            formData.append('conf_threshold', '0.25');

            // Call enhanced detection endpoint
            console.log('Sending detection request to /api/detect/enhanced');
            const response = await axios.post('/api/detect/enhanced', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                timeout: 60000  // 60 second timeout
            });

            console.log('Detection response received:', response.data);

            if (response.data.success) {
                setDetections(response.data.detections);
                
                // Notify parent component about mode change
                if (onModeChange) {
                    onModeChange(mode, response.data.detections);
                }

                // Trigger alerts for critical threats
                const criticalThreats = response.data.detections.filter(d => d.threat_level === 'CRITICAL');
                if (criticalThreats.length > 0) {
                    toast.error(`🚨 ${criticalThreats.length} CRITICAL threat(s) detected!`, {
                        duration: 5000,
                        icon: '🚨'
                    });
                }

                const detectionCount = response.data.detections.length;
                const successMessage = `${response.data.mode_label} completed: ${detectionCount} object${detectionCount !== 1 ? 's' : ''} detected`;
                console.log(`✓ ${successMessage}`);
                toast.success(successMessage);
                
                // Generate annotated image
                generateAnnotatedImage(response.data.detections);
            } else {
                const errorMessage = response.data.message || 'Detection failed - no error message provided';
                console.error(`✗ Detection failed: ${errorMessage}`);
                toast.error(errorMessage, { duration: 6000 });
            }
        } catch (error) {
            console.error('Detection error:', error);
            
            let errorMessage = 'Failed to run enhanced detection';
            const shouldRetry = error.response?.status === 503 && retryCount < maxRetries;
            
            if (error.response) {
                // Server responded with error status
                const status = error.response.status;
                const data = error.response.data;
                
                if (status === 503) {
                    if (shouldRetry) {
                        console.warn(`⚠️ Service unavailable, retrying in 3 seconds... (${retryCount + 1}/${maxRetries})`);
                        toast.loading(`Still loading models... Retrying (${retryCount + 1}/${maxRetries})`, { id: 'detection-retry' });
                        
                        // Wait and retry
                        await new Promise(resolve => setTimeout(resolve, 3000));
                        setLoading(false);
                        const result = await runDetection(retryCount + 1, maxRetries);
                        return result;
                    } else {
                        errorMessage = 'Detection service still loading. Please try again in a few seconds.';
                        console.error('SERVICE_UNAVAILABLE (max retries reached):', data.message);
                    }
                } else if (status === 401) {
                    errorMessage = 'Authentication failed. Please log in again.';
                    console.error('UNAUTHORIZED:', data.message);
                } else if (status === 400) {
                    errorMessage = data.message || 'Invalid request parameters.';
                    console.error('BAD_REQUEST:', data.message);
                } else if (status === 500) {
                    errorMessage = data.message || 'Server error. Check backend logs.';
                    console.error('SERVER_ERROR:', data.message);
                } else {
                    errorMessage = data.message || `Server error (${status}): ${error.message}`;
                    console.error(`ERROR_${status}:`, data.message);
                }
            } else if (error.request) {
                // Request made but no response
                errorMessage = 'No response from server. Check if backend is running.';
                console.error('NO_RESPONSE:', error.message);
            } else if (error.code === 'ECONNABORTED') {
                errorMessage = 'Detection timeout. Try again with a smaller image or wait a moment.';
                console.error('TIMEOUT:', error.message);
            } else {
                // Error in request setup
                errorMessage = error.message || 'Failed to send detection request.';
                console.error('REQUEST_ERROR:', error.message);
            }
            
            toast.error(errorMessage, { duration: 6000 });
        } finally {
            setLoading(false);
        }
    };

    const generateAnnotatedImage = (detections) => {
        if (!imageUrl || !showAnnotations || !detections || !Array.isArray(detections)) {
            setAnnotatedImage(null);
            return;
        }

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            // Draw bounding boxes and labels
            detections.forEach(detection => {
                const [x1, y1, x2, y2] = detection.box;
                const color = detection.color || '#FF0000';

                // Draw bounding box
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

                // Draw label background
                ctx.fillStyle = color;
                const label = detection.display_label || `${detection.label} - ${(detection.confidence * 100).toFixed(0)}%`;
                const metrics = ctx.measureText(label);
                const labelHeight = 20;

                ctx.fillRect(x1, y1 - labelHeight - 5, metrics.width + 10, labelHeight);

                // Draw label text
                ctx.fillStyle = 'white';
                ctx.font = '12px Arial';
                ctx.fillText(label, x1 + 5, y1 - 8);
            });

            setAnnotatedImage(canvas.toDataURL());
        };

        img.src = imageUrl;
    };

    const getDetectionTypeIcon = (detection) => {
        if (detection.detection_type === 'species') {
            return '🦁'; // Wildlife icon
        } else if (detection.threat_level === 'CRITICAL') {
            return '🚨'; // Critical threat icon
        } else if (detection.threat_level === 'MEDIUM') {
            return '⚠️'; // Medium threat icon
        } else {
            return '⚡'; // Low threat icon
        }
    };

    const getThreatLevelColor = (level) => {
        switch (level) {
            case 'CRITICAL': return 'text-red-600 bg-red-100 border-red-200';
            case 'MEDIUM': return 'text-orange-600 bg-orange-100 border-orange-200';
            case 'LOW': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
            default: return 'text-gray-600 bg-gray-100 border-gray-200';
        }
    };

    return (
        <div className="space-y-4">
            {/* Detection Mode Selection */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Detection Mode</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                        onClick={() => setMode('species')}
                        className={`p-4 rounded-lg border-2 transition-all ${
                            mode === 'species'
                                ? 'bg-green-500 text-white border-green-500'
                                : 'bg-white text-gray-700 border-gray-300 hover:border-green-300'
                        }`}
                    >
                        <div className="text-center">
                            <div className="text-2xl mb-2">🦁</div>
                            <h4 className="font-medium">Species Monitoring</h4>
                            <p className="text-sm opacity-75">Detect animals only</p>
                        </div>
                    </button>
                    <button
                        onClick={() => setMode('threat')}
                        className={`p-4 rounded-lg border-2 transition-all ${
                            mode === 'threat'
                                ? 'bg-red-500 text-white border-red-500'
                                : 'bg-white text-gray-700 border-gray-300 hover:border-red-300'
                        }`}
                    >
                        <div className="text-center">
                            <div className="text-2xl mb-2">🚨</div>
                            <h4 className="font-medium">Threat Monitoring</h4>
                            <p className="text-sm opacity-75">Detect poachers & weapons</p>
                        </div>
                    </button>
                </div>
            </div>

            {/* Detection Results */}
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900">Detection Results</h3>
                    <div className="flex items-center space-x-2">
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

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-r-2 border-blue-500"></div>
                        <span className="ml-3 text-gray-600">Running detection...</span>
                    </div>
                ) : detections.length > 0 ? (
                    <div className="space-y-3">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Image with Annotations */}
                            <div>
                                <h4 className="text-sm font-medium text-gray-700 mb-2">Annotated Image</h4>
                                <div className="border rounded-lg overflow-hidden">
                                    <img
                                        src={annotatedImage || imageUrl}
                                        alt="Detection result"
                                        className="w-full h-auto"
                                    />
                                </div>
                            </div>

                            {/* Detection List */}
                            <div>
                                <h4 className="text-sm font-medium text-gray-700 mb-2">Detected Objects</h4>
                                <div className="space-y-2 max-h-96 overflow-y-auto">
                                    {detections.map((detection, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                                            <div className="flex items-center space-x-3">
                                                <span className="text-xl">
                                                    {getDetectionTypeIcon(detection)}
                                                </span>
                                                <div>
                                                    <h5 className="font-medium text-gray-900">
                                                        {detection.label}
                                                    </h5>
                                                    <p className="text-sm text-gray-600">
                                                        Confidence: {(detection.confidence * 100).toFixed(1)}%
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                {detection.threat_level && (
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getThreatLevelColor(detection.threat_level)}`}>
                                                        {detection.threat_level}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Statistics */}
                        <div className="mt-4 pt-4 border-t">
                            <h4 className="text-sm font-medium text-gray-700 mb-3">Detection Statistics</h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-blue-600">
                                        {detections.length}
                                    </div>
                                    <div className="text-sm text-gray-600">Total Objects</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-green-600">
                                        {detections.filter(d => d.detection_type === 'species').length}
                                    </div>
                                    <div className="text-sm text-gray-600">Species</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-red-600">
                                        {detections.filter(d => d.threat_level === 'CRITICAL').length}
                                    </div>
                                    <div className="text-sm text-gray-600">Critical</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-orange-600">
                                        {detections.filter(d => d.threat_level === 'MEDIUM').length}
                                    </div>
                                    <div className="text-sm text-gray-600">Medium</div>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-12">
                        <div className="text-gray-400 text-6xl mb-4">🔍</div>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No objects detected</h3>
                        <p className="text-gray-600">Try adjusting the detection mode or confidence threshold</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default EnhancedDetectionViewer;
