import React, { useState, useEffect, useRef } from 'react';

/**
 * DetectionViewer Component
 * 
 * Displays an image with YOLO detection bounding boxes overlay.
 * Shows detected objects, confidence scores, and allows interaction.
 * 
 * @param {Object} props
 * @param {string} props.imageUrl - Base64 encoded image data or URL
 * @param {Array} props.detections - Array of detection objects: [{label, confidence, box: [x1,y1,x2,y2]}]
 * @param {number} props.maxWidth - Maximum width for the viewer (default: 800)
 * @param {boolean} props.showLabels - Whether to show labels on bounding boxes (default: true)
 * @param {number} props.confidenceThreshold - Minimum confidence to show detection (default: 0.25)
 */
const DetectionViewer = ({ 
    imageUrl, 
    detections = [], 
    maxWidth = 800,
    showLabels = true,
    confidenceThreshold = 0.25
}) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);
    const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
    const [selectedDetection, setSelectedDetection] = useState(null);
    const [hoveredDetection, setHoveredDetection] = useState(null);

    // Color palette for different classes
    const getClassColor = (label, index) => {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
            '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
            '#1ABC9C', '#E91E63', '#FF5722', '#795548', '#607D8B'
        ];
        // Generate consistent color based on label hash or index
        const hash = label.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return colors[hash % colors.length];
    };

    // Filter detections by confidence threshold
    const filteredDetections = detections.filter(
        d => d.confidence >= confidenceThreshold
    );

    // Sort by confidence (highest first)
    const sortedDetections = [...filteredDetections].sort(
        (a, b) => b.confidence - a.confidence
    );

    useEffect(() => {
        if (!imageUrl || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
            // Calculate scaled dimensions
            const scale = Math.min(maxWidth / img.width, 1);
            const scaledWidth = img.width * scale;
            const scaledHeight = img.height * scale;

            // Set canvas size
            canvas.width = scaledWidth;
            canvas.height = scaledHeight;

            // Store image size for coordinate calculations
            setImageSize({
                width: img.width,
                height: img.height,
                scaledWidth,
                scaledHeight,
                scale
            });

            // Draw image
            ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);

            setImageLoaded(true);
            setImageError(false);
        };

        img.onerror = () => {
            console.error('Failed to load image');
            setImageLoaded(false);
            setImageError(true);
        };

        // Handle base64 or URL - ensure proper data URL format
        let imageSrc = imageUrl;
        if (!imageUrl.startsWith('data:') && !imageUrl.startsWith('http')) {
            // Assume it's raw base64, add JPEG data URL prefix as default
            imageSrc = `data:image/jpeg;base64,${imageUrl}`;
        }
        img.src = imageSrc;
    }, [imageUrl, maxWidth]);

    // Draw bounding boxes when image is loaded or detections change
    useEffect(() => {
        if (!imageLoaded || !canvasRef.current || !imageSize.scale) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
            // Clear and redraw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, imageSize.scaledWidth, imageSize.scaledHeight);

            // Draw bounding boxes
            sortedDetections.forEach((detection, index) => {
                const { label, confidence, box } = detection;
                const [x1, y1, x2, y2] = box;
                const color = getClassColor(label, index);
                const isHovered = hoveredDetection === index;
                const isSelected = selectedDetection === index;

                // Scale coordinates
                const sx1 = x1 * imageSize.scale;
                const sy1 = y1 * imageSize.scale;
                const sx2 = x2 * imageSize.scale;
                const sy2 = y2 * imageSize.scale;
                const width = sx2 - sx1;
                const height = sy2 - sy1;

                // Draw box with glow effect for hover/selection
                ctx.save();
                
                if (isHovered || isSelected) {
                    ctx.shadowColor = color;
                    ctx.shadowBlur = 10;
                    ctx.lineWidth = 3;
                } else {
                    ctx.lineWidth = 2;
                }

                // Draw rectangle
                ctx.strokeStyle = color;
                ctx.strokeRect(sx1, sy1, width, height);

                // Fill with slight transparency on hover
                if (isHovered || isSelected) {
                    ctx.fillStyle = color + '20'; // 20 = ~12% opacity in hex
                    ctx.fillRect(sx1, sy1, width, height);
                }

                ctx.restore();

                // Draw label background
                if (showLabels) {
                    const labelText = `${label} ${(confidence * 100).toFixed(0)}%`;
                    ctx.font = 'bold 12px Arial, sans-serif';
                    const textMetrics = ctx.measureText(labelText);
                    const textWidth = textMetrics.width;
                    const textHeight = 16;
                    const padding = 4;

                    // Label background
                    ctx.fillStyle = color;
                    ctx.fillRect(
                        sx1, 
                        sy1 - textHeight - padding, 
                        textWidth + padding * 2, 
                        textHeight
                    );

                    // Label text
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillText(
                        labelText, 
                        sx1 + padding, 
                        sy1 - padding - 2
                    );
                }
            });
        };

        if (imageUrl.startsWith('data:')) {
            img.src = imageUrl;
        } else {
            img.src = imageUrl;
        }
    }, [imageLoaded, sortedDetections, imageSize, hoveredDetection, selectedDetection, showLabels, imageUrl]);

    // Handle canvas click
    const handleCanvasClick = (e) => {
        if (!canvasRef.current || !imageSize.scale) return;

        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // Find clicked detection (reverse order to select top-most first)
        let clickedIndex = null;
        for (let i = sortedDetections.length - 1; i >= 0; i--) {
            const { box } = sortedDetections[i];
            const [x1, y1, x2, y2] = box;
            const sx1 = x1 * imageSize.scale;
            const sy1 = y1 * imageSize.scale;
            const sx2 = x2 * imageSize.scale;
            const sy2 = y2 * imageSize.scale;

            if (clickX >= sx1 && clickX <= sx2 && clickY >= sy1 && clickY <= sy2) {
                clickedIndex = i;
                break;
            }
        }

        setSelectedDetection(clickedIndex);
    };

    // Handle mouse move for hover effect
    const handleMouseMove = (e) => {
        if (!canvasRef.current || !imageSize.scale) return;

        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Find hovered detection
        let hoveredIndex = null;
        for (let i = sortedDetections.length - 1; i >= 0; i--) {
            const { box } = sortedDetections[i];
            const [x1, y1, x2, y2] = box;
            const sx1 = x1 * imageSize.scale;
            const sy1 = y1 * imageSize.scale;
            const sx2 = x2 * imageSize.scale;
            const sy2 = y2 * imageSize.scale;

            if (mouseX >= sx1 && mouseX <= sx2 && mouseY >= sy1 && mouseY <= sy2) {
                hoveredIndex = i;
                break;
            }
        }

        setHoveredDetection(hoveredIndex);
    };

    if (!imageUrl) {
        return (
            <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <p className="text-gray-500">No image available</p>
            </div>
        );
    }

    return (
        <div className="detection-viewer" ref={containerRef}>
            {/* Image with bounding boxes */}
            <div className="relative bg-gray-900 rounded-lg overflow-hidden shadow-lg">
                <canvas
                    ref={canvasRef}
                    onClick={handleCanvasClick}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={() => setHoveredDetection(null)}
                    className="cursor-crosshair block mx-auto"
                    style={{ maxWidth: '100%', height: 'auto' }}
                />
                
                {!imageLoaded && !imageError && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                )}

                {imageError && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100">
                        <svg className="w-16 h-16 text-red-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <p className="text-gray-500 font-medium">Failed to load image</p>
                        <p className="text-gray-400 text-sm">Image data may be corrupted</p>
                    </div>
                )}

                {/* Detection count badge */}
                {imageLoaded && sortedDetections.length > 0 && (
                    <div className="absolute top-2 right-2 bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-medium shadow">
                        {sortedDetections.length} object{sortedDetections.length !== 1 ? 's' : ''} detected
                    </div>
                )}
            </div>

            {/* Detections list */}
            {sortedDetections.length > 0 && (
                <div className="mt-4 bg-white rounded-lg shadow p-4">
                    <h4 className="text-lg font-semibold text-gray-900 mb-3">
                        Detected Objects
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {sortedDetections.map((detection, index) => {
                            const { label, confidence, box } = detection;
                            const color = getClassColor(label, index);
                            const isSelected = selectedDetection === index;
                            const isHovered = hoveredDetection === index;

                            return (
                                <div
                                    key={index}
                                    onClick={() => setSelectedDetection(isSelected ? null : index)}
                                    onMouseEnter={() => setHoveredDetection(index)}
                                    onMouseLeave={() => setHoveredDetection(null)}
                                    className={`
                                        flex items-center justify-between p-3 rounded-lg cursor-pointer
                                        transition-all duration-200
                                        ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'}
                                    `}
                                >
                                    <div className="flex items-center space-x-3">
                                        {/* Color indicator */}
                                        <div
                                            className="w-4 h-4 rounded-full flex-shrink-0"
                                            style={{ backgroundColor: color }}
                                        />
                                        
                                        {/* Label and confidence */}
                                        <div>
                                            <p className="font-medium text-gray-900 capitalize">
                                                {label}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                Box: [{box.join(', ')}]
                                            </p>
                                        </div>
                                    </div>

                                    {/* Confidence badge */}
                                    <div className={`
                                        px-3 py-1 rounded-full text-sm font-medium
                                        ${confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                                          confidence >= 0.5 ? 'bg-yellow-100 text-yellow-800' :
                                          'bg-red-100 text-red-800'}
                                    `}>
                                        {(confidence * 100).toFixed(1)}%
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Summary statistics */}
                    <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="grid grid-cols-3 gap-4 text-center">
                            <div className="bg-gray-50 rounded-lg p-2">
                                <p className="text-2xl font-bold text-gray-900">
                                    {sortedDetections.length}
                                </p>
                                <p className="text-xs text-gray-500 uppercase">Total Objects</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-2">
                                <p className="text-2xl font-bold text-green-600">
                                    {(sortedDetections.reduce((acc, d) => acc + d.confidence, 0) / sortedDetections.length * 100).toFixed(0)}%
                                </p>
                                <p className="text-xs text-gray-500 uppercase">Avg Confidence</p>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-2">
                                <p className="text-2xl font-bold text-blue-600">
                                    {new Set(sortedDetections.map(d => d.label)).size}
                                </p>
                                <p className="text-xs text-gray-500 uppercase">Unique Classes</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* No detections message */}
            {imageLoaded && sortedDetections.length === 0 && (
                <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-yellow-800 text-center">
                        No objects detected with confidence ≥ {(confidenceThreshold * 100).toFixed(0)}%
                    </p>
                </div>
            )}
        </div>
    );
};

export default DetectionViewer;
