import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import toast from 'react-hot-toast';

const NotificationCenter = () => {
    const [notifications, setNotifications] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [socket, setSocket] = useState(null);
    const [unreadCount, setUnreadCount] = useState(0);

    useEffect(() => {
        initializeSocket();

        return () => {
            if (socket) {
                socket.disconnect();
            }
        };
    }, []);

    const initializeSocket = () => {
        const newSocket = io(process.env.REACT_APP_API_URL || 'http://localhost:5000');

        newSocket.on('connect', () => {
            console.log('Notification center connected');
            newSocket.emit('join_officials');
        });

        newSocket.on('new_report', (data) => {
            const notification = {
                id: Date.now(),
                type: 'new_report',
                title: 'New Wildlife Report',
                message: `${data.report.severity} severity report: ${data.report.title}`,
                timestamp: new Date(),
                read: false,
                severity: data.report.severity
            };

            addNotification(notification);

            // Show toast notification
            if (data.report.severity === 'Critical') {
                toast.error(`🚨 CRITICAL: ${data.report.title}`, {
                    duration: 10000,
                    position: 'top-right'
                });
            } else {
                toast.success(`📋 New Report: ${data.report.title}`, {
                    duration: 5000,
                    position: 'top-right'
                });
            }
        });

        newSocket.on('status_update', (data) => {
            const notification = {
                id: Date.now(),
                type: 'status_update',
                title: 'Report Status Updated',
                message: `Report status changed to: ${data.status}`,
                timestamp: new Date(),
                read: false
            };

            addNotification(notification);
            toast(`📝 Status Update: ${data.status}`, {
                duration: 3000,
                position: 'top-right',
                icon: 'ℹ️'
            });
        });

        setSocket(newSocket);
    };

    const addNotification = (notification) => {
        setNotifications(prev => [notification, ...prev.slice(0, 49)]); // Keep last 50 notifications
        setUnreadCount(prev => prev + 1);
    };

    const markAsRead = (id) => {
        setNotifications(prev =>
            prev.map(notif =>
                notif.id === id ? { ...notif, read: true } : notif
            )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
    };

    const markAllAsRead = () => {
        setNotifications(prev =>
            prev.map(notif => ({ ...notif, read: true }))
        );
        setUnreadCount(0);
    };

    const clearAll = () => {
        setNotifications([]);
        setUnreadCount(0);
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'Critical': return 'text-red-600 bg-red-100';
            case 'Medium': return 'text-orange-600 bg-orange-100';
            case 'Low': return 'text-green-600 bg-green-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    const formatTime = (timestamp) => {
        const now = new Date();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return `${days}d ago`;
    };

    return (
        <div className="relative">
            {/* Notification Bell */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-full"
            >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Notification Panel */}
            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                    <div className="p-4 border-b border-gray-200">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-medium text-gray-900">Notifications</h3>
                            <div className="flex space-x-2">
                                <button
                                    onClick={markAllAsRead}
                                    className="text-sm text-blue-600 hover:text-blue-800"
                                >
                                    Mark all read
                                </button>
                                <button
                                    onClick={clearAll}
                                    className="text-sm text-red-600 hover:text-red-800"
                                >
                                    Clear all
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="p-4 text-center text-gray-500">
                                <div className="text-4xl mb-2">🔔</div>
                                <p>No notifications yet</p>
                            </div>
                        ) : (
                            notifications.map((notification) => (
                                <div
                                    key={notification.id}
                                    className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${!notification.read ? 'bg-blue-50' : ''
                                        }`}
                                    onClick={() => markAsRead(notification.id)}
                                >
                                    <div className="flex items-start space-x-3">
                                        <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${!notification.read ? 'bg-blue-500' : 'bg-gray-300'
                                            }`}></div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm font-medium text-gray-900">
                                                    {notification.title}
                                                </p>
                                                {notification.severity && (
                                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(notification.severity)}`}>
                                                        {notification.severity}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-600 mt-1">
                                                {notification.message}
                                            </p>
                                            <p className="text-xs text-gray-500 mt-1">
                                                {formatTime(notification.timestamp)}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {notifications.length > 0 && (
                        <div className="p-4 border-t border-gray-200 bg-gray-50">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="w-full text-sm text-gray-600 hover:text-gray-800"
                            >
                                Close
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default NotificationCenter;


