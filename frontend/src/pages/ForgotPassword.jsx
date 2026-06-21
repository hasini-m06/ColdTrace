import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function ForgotPassword() {
    const { forgotPassword } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail]     = useState('');
    const [error, setError]     = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!email.trim()) {
            setError('Please enter your email address.');
            return;
        }

        setLoading(true);
        try {
            const res = await forgotPassword(email.trim());
            setSuccess(res.message || 'If an account exists, a password reset link has been sent.');
            setEmail('');
        } catch (err) {
            const msg = err?.response?.data?.detail || 'Something went wrong. Please try again.';
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

                <p className="auth-title">Reset Password</p>

                {!success ? (
                    <>
                        <div className="auth-info" style={{ marginBottom: 20 }}>
                            Enter your registered email address and we'll send you a
                            password reset link valid for 1 hour.
                        </div>

                        {error && <div className="auth-error" style={{ marginBottom: 16 }}><span>⚠</span><span>{error}</span></div>}

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
                                    disabled={loading}
                                />
                            </div>
                            <button className="auth-btn" type="submit" disabled={loading}>
                                {loading && <span className="auth-spinner" />}
                                {loading ? 'Sending…' : 'Send Reset Link'}
                            </button>
                        </form>
                    </>
                ) : (
                    <div className="auth-success" style={{ marginBottom: 20 }}>
                        <span>✓</span>
                        <span>{success}</span>
                    </div>
                )}

                <div className="auth-divider" />
                <div className="auth-footer">
                    <button className="auth-link" onClick={() => navigate('/login')} disabled={loading}>
                        ← Back to sign in
                    </button>
                </div>
            </div>
        </div>
    );
}
