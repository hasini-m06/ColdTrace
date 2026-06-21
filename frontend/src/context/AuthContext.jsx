import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authMe, authLogin, authLogout, authRegister } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser]       = useState(null);   // null = not logged in
    const [loading, setLoading] = useState(true);   // true while checking session

    // On mount, check if there's a valid session cookie
    useEffect(() => {
        authMe()
            .then(setUser)
            .catch(() => setUser(null))
            .finally(() => setLoading(false));
    }, []);

    const login = useCallback(async (email, password) => {
        await authLogin(email, password);
        const me = await authMe();
        setUser(me);
        return me;
    }, []);

    const logout = useCallback(async () => {
        await authLogout();
        setUser(null);
    }, []);

    const register = useCallback(async (email, password) => {
        return authRegister(email, password);
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, register }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
