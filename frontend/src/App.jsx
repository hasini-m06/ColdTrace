import React, { useState, useEffect } from 'react';
import MapComponent from './components/Map';
import Sidebar from './components/Sidebar';
import OfficialsDashboard from './components/OfficialsDashboard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { getRiskScores, getDashboardSummary, refreshData } from './services/api';

// ── URL-based page detection (no react-router needed) ────────────────────────
function getPageFromURL() {
    const path = window.location.pathname;
    const params = new URLSearchParams(window.location.search);
    if (path.includes('verify-email'))   return 'verify-email';
    if (path.includes('reset-password')) return 'reset-password';
    if (params.get('verified') === '1')  return 'verify-email';
    return 'app';  // default: main dashboard
}

// ── Inner app — rendered after AuthProvider is ready ─────────────────────────
function InnerApp() {
    const { user, loading: authLoading, logout } = useAuth();

    const [locations, setLocations]           = useState([]);
    const [summary, setSummary]               = useState({ total: 0, red: 0, amber: 0, green: 0 });
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [loading, setLoading]               = useState(true);
    const [currentView, setCurrentView]       = useState('map');

    // Auth page state — 'app' | 'login' | 'register' | 'forgot' | 'reset-password' | 'verify-email'
    const [authPage, setAuthPage] = useState(() => getPageFromURL());

    const loadData = async () => {
        setLoading(true);
        try {
            const [scoresData, summaryData] = await Promise.all([
                getRiskScores(),
                getDashboardSummary(),
            ]);
            setLocations(scoresData);
            setSummary(summaryData);
            if (scoresData.length > 0 && !selectedLocation) {
                setSelectedLocation(scoresData[0]);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
        }
        setLoading(false);
    };

    useEffect(() => {
        if (authPage === 'app') {
            loadData();
            const interval = setInterval(loadData, 6 * 60 * 60 * 1000);
            return () => clearInterval(interval);
        }
    }, [authPage]);

    const handleRefresh = async () => {
        setLoading(true);
        try {
            await refreshData();
            alert('✅ Data cycle triggered! Waiting 90 seconds for processing…');
            setTimeout(loadData, 90000);
        } catch (err) {
            const status = err?.response?.status;
            const detail = err?.response?.data?.detail || err.message;
            if (status === 429) {
                alert('⏳ Rate limited — wait a few minutes and try again.');
            } else {
                alert(`❌ Refresh failed (${status || 'network error'}): ${detail}`);
            }
            setLoading(false);
        }
    };

    // Officials Hub tab clicked — require login
    const handleViewChange = (view) => {
        if (view === 'officials' && !user) {
            setAuthPage('login');
            return;
        }
        setCurrentView(view);
    };

    // ── Auth page router ──────────────────────────────────────────────────────
    if (authPage === 'verify-email') {
        return <VerifyEmailPage onNavigate={setAuthPage} />;
    }
    if (authPage === 'reset-password') {
        return <ResetPasswordPage onNavigate={setAuthPage} />;
    }

    // If user just logged in from the auth flow, return to the Officials Hub
    if (authPage === 'login' || authPage === 'register' || authPage === 'forgot') {
        if (user) {
            // Already authenticated — go straight to Officials Hub
            setAuthPage('app');
            setCurrentView('officials');
            return null;
        }
        if (authPage === 'login')    return <LoginPage    onNavigate={setAuthPage} />;
        if (authPage === 'register') return <RegisterPage onNavigate={setAuthPage} />;
        if (authPage === 'forgot')   return <ForgotPasswordPage onNavigate={setAuthPage} />;
    }

    // ── Main dashboard ────────────────────────────────────────────────────────
    if (authLoading) {
        // Don't flash auth pages while checking session cookie
        return (
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', background: '#0f172a', color: '#64748b' }}>
                Loading…
            </div>
        );
    }

    return (
        <div className="app-container">
            <Sidebar
                summary={summary}
                location={selectedLocation}
                onRefresh={handleRefresh}
                loading={loading}
                currentView={currentView}
                onViewChange={handleViewChange}
                user={user}
                onLogout={logout}
            />
            <div className="map-container">
                {currentView === 'map' ? (
                    <MapComponent
                        locations={locations}
                        onSelectLocation={setSelectedLocation}
                        selectedId={selectedLocation?.id}
                    />
                ) : (
                    // Officials Hub — only reachable if user is logged in (enforced above)
                    <OfficialsDashboard user={user} />
                )}
            </div>
        </div>
    );
}

// ── Root export wraps everything in AuthProvider ──────────────────────────────
export default function App() {
    return (
        <AuthProvider>
            <InnerApp />
        </AuthProvider>
    );
}
