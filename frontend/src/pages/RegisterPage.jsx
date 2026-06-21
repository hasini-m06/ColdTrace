import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function RegisterPage() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm]   = useState('');
    const [error, setError]       = useState('');
    const [success, setSuccess]   = useState('');
    const [loading, setLoading]   = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (password !== confirm) {
            setError('Passwords do not match.');
            return;
        }

        setLoading(true);
        try {
            const res = await register(email, password);
            setSuccess(res.message || 'Check your email for a verification link!');
            setEmail(''); setPassword(''); setConfirm('');
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Registration failed. Please try again.';
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

                <p className="auth-title">Request Officials Access</p>

                <div className="auth-info" style={{ marginBottom: 20 }}>
                    After registering, you'll receive a verification email. Once verified,
                    you can log in to the Officials Alert Hub.
                </div>

                {error   && <div className="auth-error"   style={{ marginBottom: 16 }}><span>⚠</span><span>{error}</span></div>}
                {success && <div className="auth-success" style={{ marginBottom: 16 }}><span>✓</span><span>{success}</span></div>}

                {!success && (
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
                            <label>Password <span style={{ color: '#475569', fontWeight: 400 }}>(min 8 chars, letter + number)</span></label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                            />
                        </div>
                        <div className="auth-field">
                            <label>Confirm password</label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={confirm}
                                onChange={e => setConfirm(e.target.value)}
                                required
                            />
                        </div>

                        <button className="auth-btn" type="submit" disabled={loading}>
                            {loading && <span className="auth-spinner" />}
                            {loading ? 'Creating account…' : 'Create Account'}
                        </button>
                    </form>
                )}

                <div className="auth-divider" />
                <div className="auth-footer">
                    Already have an account?{' '}
                    <button className="auth-link" onClick={() => navigate('/login')}>
                        Sign in
                    </button>
                </div>
            </div>
        </div>
    );
}
