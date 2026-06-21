import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function VerifyEmailPage() {
    const navigate = useNavigate();
    // The backend redirects to /verify-email?verified=1 on success,
    // or the user lands here after clicking the backend's redirect.
    const [status, setStatus] = useState('checking'); // 'checking' | 'success' | 'error'

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get('verified') === '1') {
            setStatus('success');
        } else if (params.get('token')) {
            // Direct backend verification link — token is handled server-side via redirect.
            // If user lands here with a token but no verified=1, it means they manually
            // navigated here. Show a helpful message.
            setStatus('manual');
        } else {
            setStatus('error');
        }
    }, []);

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

                {status === 'checking' && (
                    <div style={{ textAlign: 'center', color: '#94a3b8', padding: '20px 0' }}>
                        <span className="auth-spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
                        <p style={{ marginTop: 16 }}>Verifying your email…</p>
                    </div>
                )}

                {status === 'success' && (
                    <>
                        <div className="auth-success" style={{ marginBottom: 24, fontSize: 15 }}>
                            <span>✓</span>
                            <span>Email verified successfully! You can now sign in to the Officials Hub.</span>
                        </div>
                        <button className="auth-btn" onClick={() => navigate('/login')}>
                            Sign In Now
                        </button>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <div className="auth-error" style={{ marginBottom: 24 }}>
                            <span>⚠</span>
                            <span>Verification link is invalid or has expired. Please request a new one.</span>
                        </div>
                        <button className="auth-btn" onClick={() => navigate('/register')}>
                            Register Again
                        </button>
                    </>
                )}

                {status === 'manual' && (
                    <div className="auth-info">
                        This link should be opened directly from your email. If you were redirected here, 
                        your email has been verified — try signing in.
                    </div>
                )}

                <div className="auth-divider" />
                <div className="auth-footer">
                    <button className="auth-link" onClick={() => navigate('/login')}>
                        ← Back to sign in
                    </button>
                </div>
            </div>
        </div>
    );
}
