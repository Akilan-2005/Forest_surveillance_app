import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SocketProvider } from './contexts/SocketContext';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import UserDashboard from './components/user/UserDashboard';
import ReportForm from './components/user/ReportForm';
import OfficialsDashboard from './components/officials/OfficialsDashboard';
import Analytics from './components/officials/Analytics';
import ProtectedRoute from './components/common/ProtectedRoute';
import Navbar from './components/common/Navbar';
import LoadingSpinner from './components/common/LoadingSpinner';

function AppContent() {
    const { user, loading } = useAuth();

    if (loading) {
        return <LoadingSpinner />;
    }

    return (
        <Router>
            <div className="min-h-screen bg-gray-50">
                {user && <Navbar />}
                <Routes>
                    <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
                    <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

                    <Route path="/" element={
                        <ProtectedRoute>
                            {user?.role === 'user' ? <UserDashboard /> : <OfficialsDashboard />}
                        </ProtectedRoute>
                    } />

                    <Route path="/report" element={
                        <ProtectedRoute allowedRoles={['user']}>
                            <ReportForm />
                        </ProtectedRoute>
                    } />

                    <Route path="/analytics" element={
                        <ProtectedRoute allowedRoles={['official']}>
                            <Analytics />
                        </ProtectedRoute>
                    } />

                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
                <Toaster position="top-right" />
            </div>
        </Router>
    );
}

function App() {
    return (
        <AuthProvider>
            <SocketProvider>
                <AppContent />
            </SocketProvider>
        </AuthProvider>
    );
}

export default App;
