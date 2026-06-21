import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { 
    authMe, 
    authLogin, 
    authLogout, 
    authRegister, 
    authForgotPassword, 
    authResetPassword 
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser]             = useState(null);
    const [isLoading, setIsLoading]   = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const me = await authMe();
            setUser(me);
        } catch (err) {
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    const login = useCallback(async (email, password) => {
        await authLogin(email, password);
        const me = await authMe();
        setUser(me);
        return me;
    }, []);

    const logout = useCallback(async () => {
        try {
            await authLogout();
        } finally {
            setUser(null);
        }
    }, []);

    const register = useCallback(async (email, password) => {
        return await authRegister(email, password);
    }, []);

    const forgotPassword = useCallback(async (email) => {
        return await authForgotPassword(email);
    }, []);

    const resetPassword = useCallback(async (token, newPassword) => {
        return await authResetPassword(token, newPassword);
    }, []);

    const isAuthenticated = !!user;

    return (
        <AuthContext.Provider value={{ 
            user, 
            isLoading, 
            isAuthenticated, 
            login, 
            logout, 
            register, 
            forgotPassword, 
            resetPassword 
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
