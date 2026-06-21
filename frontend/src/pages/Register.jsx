import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function Register() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm]   = useState('');
    const [error, setError]       = useState('');
    const [success, setSuccess]   = useState('');
    const [loading, setLoading]   = useState(false);

    // Password validation rule helper (min 8 chars, letter + number)
    const isPasswordStrong = (pass) => {
        return pass.length >= 8 && /[a-zA-Z]/.test(pass) && /\d/.test(pass);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        // Client-side validations
        if (!email.trim() || !password || !confirm) {
            setError('All fields are required.');
            return;
        }

        if (password !== confirm) {
            setError('Passwords do not match.');
            return;
        }

        if (!isPasswordStrong(password)) {
            setError('Password must be at least 8 characters long and contain both a letter and a number.');
            return;
        }

        setLoading(true);
        try {
            const res = await register(email.trim(), password);
            setSuccess(res.message || 'Registration successful! You can now log in directly.');
            setEmail('');
            setPassword('');
            setConfirm('');
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

                <p className="auth-title">Register Officials Account</p>

                <div className="auth-info" style={{ marginBottom: 20 }}>
                    Create an account to access the Officials Alert Hub.
                    Once registered, you can log in directly.
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
                                disabled={loading}
                            />
                        </div>
                        <div className="auth-field">
                            <label>
                                Password{' '}
                                <span style={{ color: password && !isPasswordStrong(password) ? '#ef4444' : '#64748b', fontWeight: 400 }}>
                                    (min 8 chars, letter + number)
                                </span>
                            </label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                disabled={loading}
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
                                disabled={loading}
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
                    <button 
                        className="auth-link" 
                        onClick={() => navigate('/login')}
                        disabled={loading}
                    >
                        Sign in
                    </button>
                </div>
            </div>
        </div>
    );
}
