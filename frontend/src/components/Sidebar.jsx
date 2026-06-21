import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { 
  getHistory, 
  getMySubscriptions, 
  subscribeToAlerts, 
  unsubscribeFromAlerts 
} from '../services/api';
import { Activity, Thermometer, AlertTriangle, RefreshCw } from 'lucide-react';

const Sidebar = ({ summary, location, onRefresh, loading, currentView, onViewChange, user, onLogout }) => {
  const [history, setHistory] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const navigate = useNavigate();

  // Load history when selected location changes
  useEffect(() => {
    if (location) {
      getHistory(location.id).then(data => {
        const formatted = data.map(d => ({
          ...d,
          time: new Date(d.timestamp).toLocaleDateString()
        }));
        setHistory(formatted);
      });
    }
  }, [location]);

  // Load subscriptions for logged-in user
  const fetchSubscriptions = useCallback(async () => {
    if (!user) return;
    try {
      const data = await getMySubscriptions();
      setSubscriptions(data);
    } catch (err) {
      console.error('Error fetching subscriptions:', err);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      fetchSubscriptions();
    } else {
      setSubscriptions([]);
    }
  }, [user, fetchSubscriptions]);

  // Toggle subscription for current location
  const handleLocationSubscriptionToggle = async () => {
    if (!location || !user) return;
    try {
      const subCurrent = subscriptions.find(sub => sub.location_id === location.id);
      if (subCurrent) {
        await unsubscribeFromAlerts(subCurrent.id);
      } else {
        await subscribeToAlerts(location.id);
      }
      fetchSubscriptions();
    } catch (err) {
      console.error('Error toggling location subscription:', err);
    }
  };

  // Toggle global subscription (all locations)
  const handleSubscribeToAllToggle = async () => {
    if (!user) return;
    try {
      const subAll = subscriptions.find(sub => sub.location_id === null);
      if (subAll) {
        await unsubscribeFromAlerts(subAll.id);
      } else {
        await subscribeToAlerts(null);
      }
      fetchSubscriptions();
    } catch (err) {
      console.error('Error toggling global subscription:', err);
    }
  };

  // Unsubscribe helper
  const handleUnsubscribe = async (subId) => {
    try {
      await unsubscribeFromAlerts(subId);
      fetchSubscriptions();
    } catch (err) {
      console.error('Error unsubscribing:', err);
    }
  };

  const isSubscribedToCurrentLocation = location
    ? !!subscriptions.find(sub => sub.location_id === location.id)
    : false;

  const isSubscribedToAll = !!subscriptions.find(sub => sub.location_id === null);

  return (
    <div className="sidebar-container">
      <div className="header">
        <h1>ColdTrace</h1>
        <p>Predictive Cold Chain Monitoring</p>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button 
          onClick={() => onViewChange('map')}
          style={{ 
            flex: 1, 
            padding: '8px', 
            borderRadius: '6px', 
            border: 'none', 
            background: currentView === 'map' ? '#3b82f6' : 'rgba(255,255,255,0.05)',
            color: currentView === 'map' ? '#ffffff' : '#94a3b8',
            cursor: 'pointer',
            fontWeight: 600,
            transition: 'background 0.2s'
          }}
        >
          Live Map
        </button>
        <button 
          onClick={() => onViewChange('officials')}
          style={{ 
            flex: 1, 
            padding: '8px', 
            borderRadius: '6px', 
            border: 'none', 
            background: currentView === 'officials' ? '#3b82f6' : 'rgba(255,255,255,0.05)',
            color: currentView === 'officials' ? '#ffffff' : '#94a3b8',
            cursor: 'pointer',
            fontWeight: 600,
            transition: 'background 0.2s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '5px'
          }}
        >
          {!user && <span style={{ fontSize: 11 }}>🔒</span>}
          Officials Hub
        </button>
      </div>

      {/* Logged-in user / Guest indicator - Always visible */}
      {user ? (
        <div style={{
          background: 'rgba(16,185,129,0.08)',
          border: '1px solid rgba(16,185,129,0.2)',
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '12px'
        }}>
          <span style={{ color: '#6ee7b7', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '160px' }}>
            ✓ {user.email}
          </span>
          <button
            onClick={onLogout}
            style={{
              background: 'none', border: 'none', color: '#94a3b8',
              cursor: 'pointer', fontSize: '11px', fontWeight: 600,
              padding: '2px 6px', borderRadius: '4px',
              transition: 'color 0.2s'
            }}
            onMouseEnter={e => e.target.style.color = '#ef4444'}
            onMouseLeave={e => e.target.style.color = '#94a3b8'}
          >
            Sign out
          </button>
        </div>
      ) : (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '8px',
          padding: '8px 12px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '12px'
        }}>
          <span style={{ color: '#94a3b8' }}>Guest View Only</span>
          <button
            onClick={() => navigate('/login')}
            style={{
              background: '#3b82f6', border: 'none', color: '#fff',
              cursor: 'pointer', fontSize: '11px', fontWeight: 600,
              padding: '4px 10px', borderRadius: '4px',
              transition: 'background 0.2s'
            }}
            onMouseEnter={e => e.target.style.background = '#2563eb'}
            onMouseLeave={e => e.target.style.background = '#3b82f6'}
          >
            Sign In
          </button>
        </div>
      )}

      <div className="stats-grid" style={{ marginBottom: '16px' }}>
        <div className="stat-box red">
          <div className="stat-value text-red">{summary.red}</div>
          <div className="stat-label">Critical</div>
        </div>
        <div className="stat-box amber">
          <div className="stat-value text-amber">{summary.amber}</div>
          <div className="stat-label">Warning</div>
        </div>
        <div className="stat-box green">
          <div className="stat-value text-green">{summary.green}</div>
          <div className="stat-label">Healthy</div>
        </div>
      </div>

      {/* "My Alerts" Panel — Gated behind login */}
      {user && (
        <div className="card" style={{ marginBottom: '16px', padding: '16px' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: 13 }}>🔔</span> My Alert Subscriptions
          </h3>
          
          {/* Subscribe to All Toggle */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '6px 0', 
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            marginBottom: '8px'
          }}>
            <span style={{ fontSize: '13px', color: '#cbd5e1' }}>All High-Risk Alerts</span>
            <button
              onClick={handleSubscribeToAllToggle}
              style={{
                background: isSubscribedToAll ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: isSubscribedToAll ? '#ef4444' : '#10b981',
                border: isSubscribedToAll ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '4px',
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {isSubscribedToAll ? 'Unsubscribe' : 'Subscribe'}
            </button>
          </div>

          {/* Subscriptions List */}
          <div style={{ maxHeight: '110px', overflowY: 'auto', fontSize: '12px' }}>
            {subscriptions.length === 0 ? (
              <div style={{ color: '#64748b', fontStyle: 'italic', padding: '4px 0' }}>
                No active subscriptions.
              </div>
            ) : (
              subscriptions.map(sub => (
                <div key={sub.id} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '5px 0',
                  color: '#94a3b8',
                  borderBottom: '1px solid rgba(255,255,255,0.02)'
                }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>
                    {sub.location_name ? `📍 ${sub.location_name}` : '🌐 All Locations'}
                  </span>
                  <button
                    onClick={() => handleUnsubscribe(sub.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#64748b',
                      cursor: 'pointer',
                      fontSize: '12px',
                      padding: '2px 4px',
                      transition: 'color 0.2s'
                    }}
                    onMouseEnter={e => e.target.style.color = '#ef4444'}
                    onMouseLeave={e => e.target.style.color = '#64748b'}
                    title="Unsubscribe"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {location ? (
        <>
          <div className="card">
            <h2 style={{ margin: '0 0 16px 0', fontSize: '18px' }}>{location.name}</h2>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>District</div>
                <div style={{ fontWeight: '500', textTransform: 'capitalize' }}>{location.district}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Current Risk</div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: 'bold',
                  color: location.score > 70 ? 'var(--red)' : location.score > 50 ? 'var(--amber)' : 'var(--green)'
                }}>
                  {location.score?.toFixed(1)}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Thermometer size={16} color="var(--amber)" />
                <span style={{ fontSize: '14px' }}>{location.temperature?.toFixed(1)}°C</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--accent)" />
                <span style={{ fontSize: '14px' }}>{(location.wastage_rate * 100).toFixed(1)}% Wastage</span>
              </div>
            </div>

            {location.top_features && location.top_features.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Top Risk Factors</div>
                <div>
                  {location.top_features.map((feat, idx) => (
                    <span key={idx} className="feature-tag">
                      {feat.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Subscribe toggle or Login prompt */}
            {user ? (
              <button 
                onClick={handleLocationSubscriptionToggle}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: isSubscribedToCurrentLocation ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid rgba(59, 130, 246, 0.2)',
                  background: isSubscribedToCurrentLocation ? 'rgba(239, 68, 68, 0.08)' : 'rgba(59, 130, 246, 0.08)',
                  color: isSubscribedToCurrentLocation ? '#ef4444' : '#3b82f6',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '13px',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                {isSubscribedToCurrentLocation ? '🔔 Subscribed (Click to Unsubscribe)' : '🔕 Subscribe to alerts for this location'}
              </button>
            ) : (
              <div style={{ 
                padding: '12px', 
                background: 'rgba(255,255,255,0.02)', 
                borderRadius: '6px', 
                border: '1px dashed rgba(255,255,255,0.1)', 
                textAlign: 'center', 
                fontSize: '13px' 
              }}>
                <span style={{ color: '#94a3b8' }}>Want real-time breach alerts?</span>
                <button 
                  onClick={() => navigate('/login')} 
                  style={{ 
                    display: 'block', 
                    margin: '8px auto 0 auto', 
                    background: '#3b82f6', 
                    color: '#fff', 
                    border: 'none', 
                    borderRadius: '4px', 
                    padding: '6px 12px', 
                    cursor: 'pointer', 
                    fontWeight: 600, 
                    fontSize: '12px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={e => e.target.style.background = '#2563eb'}
                  onMouseLeave={e => e.target.style.background = '#3b82f6'}
                >
                  Log in to get alerts
                </button>
              </div>
            )}
          </div>

          <div className="card" style={{ flex: 1, minHeight: '200px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-muted)' }}>Risk Trend (7 Days)</h3>
            <ResponsiveContainer width="100%" height="80%">
              <LineChart data={history}>
                <XAxis dataKey="time" stroke="#475569" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#475569" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
                  itemStyle={{ color: '#60a5fa' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="score" 
                  stroke="#3b82f6" 
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#3b82f6', strokeWidth: 0 }}
                  activeDot={{ r: 6, fill: '#60a5fa' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <AlertTriangle size={32} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <p>Select a facility on the map to view details</p>
          </div>
        </div>
      )}

      <button className="btn-refresh" onClick={onRefresh} disabled={loading}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          {loading ? 'Refreshing...' : 'Trigger Data Cycle'}
        </div>
      </button>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default Sidebar;
