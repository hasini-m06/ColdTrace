import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { getHistory } from '../services/api';
import { Activity, Thermometer, AlertTriangle, RefreshCw } from 'lucide-react';

const Sidebar = ({ summary, location, onRefresh, loading, currentView, onViewChange, user, onLogout }) => {
  const [history, setHistory] = useState([]);

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

      {/* Logged-in user indicator */}
      {user && currentView === 'officials' && (
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
          <span style={{ color: '#6ee7b7', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>
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
      )}

      <div className="stats-grid">
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
              <div>
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
