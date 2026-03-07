import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useSocket } from '../../contexts/SocketContext';

const Navbar = () => {
    const { user, logout } = useAuth();
    const { connected } = useSocket();
    const navigate = useNavigate();
    const location = useLocation();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const isActive = (path) => {
        return location.pathname === path;
    };

    return (
        <nav className="bg-white shadow-lg border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                    <div className="flex items-center">
                        <Link to="/" className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                                <span className="text-white font-bold text-lg">🌲</span>
                            </div>
                            <span className="text-xl font-bold text-gray-900">
                                Wildlife Protection
                            </span>
                        </Link>
                    </div>

                    <div className="flex items-center space-x-4">
                        {/* Connection Status */}
                        <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                            <span className="text-sm text-gray-600">
                                {connected ? 'Connected' : 'Disconnected'}
                            </span>
                        </div>

                        {/* Navigation Links */}
                        <div className="hidden md:flex items-center space-x-4">
                            {user?.role === 'user' && (
                                <>
                                    <Link
                                        to="/"
                                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/')
                                                ? 'bg-primary-100 text-primary-700'
                                                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                            }`}
                                    >
                                        Dashboard
                                    </Link>
                                    <Link
                                        to="/report"
                                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/report')
                                                ? 'bg-primary-100 text-primary-700'
                                                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                            }`}
                                    >
                                        Report Offence
                                    </Link>
                                </>
                            )}

                            {user?.role === 'official' && (
                                <>
                                    <Link
                                        to="/"
                                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/')
                                                ? 'bg-primary-100 text-primary-700'
                                                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                            }`}
                                    >
                                        Reports
                                    </Link>
                                    <Link
                                        to="/analytics"
                                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/analytics')
                                                ? 'bg-primary-100 text-primary-700'
                                                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                            }`}
                                    >
                                        Analytics
                                    </Link>
                                </>
                            )}
                        </div>

                        {/* User Menu */}
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                                    <span className="text-primary-600 font-medium text-sm">
                                        {user?.name?.charAt(0).toUpperCase()}
                                    </span>
                                </div>
                                <div className="hidden md:block">
                                    <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                                    <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
                                </div>
                            </div>

                            <button
                                onClick={handleLogout}
                                className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
