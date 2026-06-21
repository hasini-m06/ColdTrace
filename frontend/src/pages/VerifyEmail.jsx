import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/auth.css';

const ShieldIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
);

export default function VerifyEmail() {
    const { verifyEmail } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [status, setStatus] = useState('verifying'); // 'verifying' | 'success' | 'error'
    const [errorMsg, setErrorMsg] = useState('');
    const [successMsg, setSuccessMsg] = useState('');

    useEffect(() => {
        const token = searchParams.get('token');
        if (!token) {
            setStatus('error');
            setErrorMsg('No verification token found in URL. Please click the link in your email.');
            return;
        }

        const runVerification = async () => {
            try {
                const res = await verifyEmail(token);
                setStatus('success');
                setSuccessMsg(res.message || 'Email verified successfully!');
                
                // Redirect to login after 3 seconds on success
                setTimeout(() => {
                    navigate('/login');
                }, 3000);
            } catch (err) {
                setStatus('error');
                const msg = err?.response?.data?.detail || 'Verification failed. The link may have expired or is invalid.';
                setErrorMsg(msg);
            }
        };

        runVerification();
    }, [searchParams, verifyEmail, navigate]);

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

                <p className="auth-title">Email Verification</p>

                {status === 'verifying' && (
                    <div style={{ textAlign: 'center', color: '#94a3b8', padding: '20px 0' }}>
                        <span className="auth-spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
                        <p style={{ marginTop: 16 }}>Verifying your email address…</p>
                    </div>
                )}

                {status === 'success' && (
                    <>
                        <div className="auth-success" style={{ marginBottom: 24, fontSize: 15 }}>
                            <span>✓</span>
                            <span>{successMsg}</span>
                        </div>
                        <div className="auth-info" style={{ textAlign: 'center', marginBottom: 20 }}>
                            Redirecting to sign in page in 3 seconds…
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
                            <span>{errorMsg}</span>
                        </div>
                        <button className="auth-btn" onClick={() => navigate('/register')}>
                            Register Again
                        </button>
                    </>
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
