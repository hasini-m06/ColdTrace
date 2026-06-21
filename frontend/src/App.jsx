import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import MapComponent from './components/Map';
import Sidebar from './components/Sidebar';
import OfficialsDashboard from './components/OfficialsDashboard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import { useAuth } from './context/AuthContext';
import { getRiskScores, getDashboardSummary, refreshData } from './services/api';

// ── ProtectedRoute wrapper component ─────────────────────────────────────────
function ProtectedRoute({ children }) {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return (
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', background: '#0f172a', color: '#64748b' }}>
                Loading…
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children;
}

// ── Dashboard / Main App Layout ──────────────────────────────────────────────
function DashboardLayout() {
    const { user, logout } = useAuth();

    const [locations, setLocations]           = useState([]);
    const [summary, setSummary]               = useState({ total: 0, red: 0, amber: 0, green: 0 });
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [loading, setLoading]               = useState(true);
    const [currentView, setCurrentView]       = useState('map');

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
        loadData();
        const interval = setInterval(loadData, 6 * 60 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

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

    const handleViewChange = (view) => {
        setCurrentView(view);
    };

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
                    <OfficialsDashboard user={user} />
                )}
            </div>
        </div>
    );
}

// ── Root export using Routes ──────────────────────────────────────────────────
export default function App() {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return (
            <div style={{ height: '100vh', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', background: '#0f172a', color: '#64748b' }}>
                Loading…
            </div>
        );
    }

    return (
        <Routes>
            <Route 
                path="/login" 
                element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} 
            />
            <Route 
                path="/register" 
                element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />} 
            />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route 
                path="/" 
                element={
                    <ProtectedRoute>
                        <DashboardLayout />
                    </ProtectedRoute>
                } 
            />
            {/* Fallback to default route */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
