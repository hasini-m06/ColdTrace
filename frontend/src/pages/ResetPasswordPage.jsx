import React, { useState, useEffect } from 'react';
import { authResetPassword } from '../services/api';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function ResetPasswordPage({ onNavigate }) {
    const [token, setToken]       = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm]   = useState('');
    const [error, setError]       = useState('');
    const [success, setSuccess]   = useState('');
    const [loading, setLoading]   = useState(false);

    // Read token from URL query param ?token=xxx
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const t = params.get('token');
        if (t) setToken(t);
        else setError('No reset token found in URL. Please use the link from your email.');
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirm) { setError('Passwords do not match.'); return; }
        setLoading(true);
        try {
            const res = await authResetPassword(token, password);
            setSuccess(res.message);
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Reset failed. The link may have expired.';
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

                <p className="auth-title">Set New Password</p>

                {error   && <div className="auth-error"   style={{ marginBottom: 16 }}><span>⚠</span><span>{error}</span></div>}
                {success && <div className="auth-success" style={{ marginBottom: 16 }}><span>✓</span><span>{success}</span></div>}

                {!success && !error.includes('No reset token') && (
                    <form className="auth-form" onSubmit={handleSubmit}>
                        <div className="auth-field">
                            <label>New password <span style={{ color: '#475569', fontWeight: 400 }}>(min 8 chars, letter + number)</span></label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                autoFocus
                            />
                        </div>
                        <div className="auth-field">
                            <label>Confirm new password</label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={confirm}
                                onChange={e => setConfirm(e.target.value)}
                                required
                            />
                        </div>
                        <button className="auth-btn" type="submit" disabled={loading || !token}>
                            {loading && <span className="auth-spinner" />}
                            {loading ? 'Saving…' : 'Set New Password'}
                        </button>
                    </form>
                )}

                {success && (
                    <button className="auth-btn" style={{ marginTop: 8 }} onClick={() => onNavigate('login')}>
                        Go to Sign In
                    </button>
                )}

                <div className="auth-divider" />
                <div className="auth-footer">
                    <button className="auth-link" onClick={() => onNavigate('login')}>
                        ← Back to sign in
                    </button>
                </div>
            </div>
        </div>
    );
}
