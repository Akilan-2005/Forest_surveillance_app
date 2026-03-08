import React, { createContext, useContext, useEffect, useState } from 'react';
import { io } from 'socket.io-client';
import { useAuth } from './AuthContext';
import toast from 'react-hot-toast';

const SocketContext = createContext();

export const useSocket = () => {
    const context = useContext(SocketContext);
    if (!context) {
        throw new Error('useSocket must be used within a SocketProvider');
    }
    return context;
};

export const SocketProvider = ({ children }) => {
    const [socket, setSocket] = useState(null);
    const [connected, setConnected] = useState(false);
    const { user } = useAuth();

    useEffect(() => {
        if (user) {
            const newSocket = io('http://localhost:5000', {
                transports: ['websocket'],
                autoConnect: true
            });

            newSocket.on('connect', () => {
                console.log('Connected to server');
                setConnected(true);

                // Join officials room if user is an official
                if (user.role === 'official') {
                    newSocket.emit('join_officials');
                }
            });

            newSocket.on('disconnect', () => {
                console.log('Disconnected from server');
                setConnected(false);
            });

            newSocket.on('new_report', (data) => {
                if (user.role === 'official') {
                    toast.success(data.message, {
                        duration: 5000,
                        style: {
                            background: '#363636',
                            color: '#fff',
                        },
                    });
                }
            });

            newSocket.on('status_update', (data) => {
                if (user.role === 'official') {
                    toast(`Report ${data.report_id} status updated to ${data.status}`, {
                        duration: 3000,
                        icon: 'ℹ️',
                    });
                }
            });

            setSocket(newSocket);

            return () => {
                newSocket.close();
            };
        }
    }, [user]);

    const value = {
        socket,
        connected
    };

    return (
        <SocketContext.Provider value={value}>
            {children}
        </SocketContext.Provider>
    );
};
