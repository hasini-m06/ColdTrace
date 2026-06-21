import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [error, setError]       = useState('');
    const [loading, setLoading]   = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
            navigate('/');
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Login failed. Please try again.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-brand">
                    <div className="auth-brand-logo">
                        <ShieldIcon />
                        <h1>ColdTrace</h1>
                    </div>
                    <p>Predictive Cold Chain Monitoring</p>
                </div>

                <p className="auth-title">Officials Hub — Sign In</p>

                {error && (
                    <div className="auth-error" style={{ marginBottom: 16 }}>
                        <span>⚠</span>
                        <span>{error}</span>
                    </div>
                )}

                <form className="auth-form" onSubmit={handleSubmit}>
                    <div className="auth-field">
                        <label>Email address</label>
                        <input
                            type="email"
                            placeholder="official@health.gov.in"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>
                    <div className="auth-field">
                        <label>Password</label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <div style={{ textAlign: 'right', marginTop: -8 }}>
                        <button type="button" className="auth-link" onClick={() => navigate('/forgot-password')}>
                            Forgot password?
                        </button>
                    </div>

                    <button className="auth-btn" type="submit" disabled={loading}>
                        {loading && <span className="auth-spinner" />}
                        {loading ? 'Signing in…' : 'Sign In'}
                    </button>
                </form>

                <div className="auth-divider" />

                <div className="auth-footer">
                    Don't have an account?{' '}
                    <button className="auth-link" onClick={() => navigate('/register')}>
                        Request access
                    </button>
                </div>
            </div>
        </div>
    );
}
