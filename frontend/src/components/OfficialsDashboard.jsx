import React, { useState, useEffect } from 'react';
import { getAlerts } from '../services/api';

const OfficialsDashboard = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await getAlerts();
        setAlerts(data);
      } catch (error) {
        console.error("Error fetching alerts:", error);
      }
      setLoading(false);
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, []);

  const formatDate = (ts) => {
    return new Date(ts).toLocaleString();
  };

  const getScoreColor = (score) => {
    if (score > 70) return '#ef4444';
    if (score > 50) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div style={{ padding: '32px', height: '100%', overflowY: 'auto', background: '#0f172a', width: '100%' }}>
      <h2 style={{ fontSize: '28px', fontWeight: '800', marginBottom: '24px', background: 'linear-gradient(to right, #60a5fa, #c084fc)', WebkitBackgroundClip: 'text', color: 'transparent' }}>
        Officials Alert Dashboard
      </h2>
      
      {loading ? (
        <p style={{ color: '#94a3b8' }}>Loading alerts...</p>
      ) : alerts.length === 0 ? (
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '32px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', textAlign: 'center' }}>
          <h3 style={{ margin: 0, color: '#94a3b8' }}>No Critical Alerts</h3>
          <p style={{ margin: '8px 0 0 0', color: '#64748b' }}>The cold chain is currently operating within safe parameters.</p>
        </div>
      ) : (
        <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '16px', color: '#94a3b8', fontWeight: 600, fontSize: '14px' }}>Time</th>
                <th style={{ padding: '16px', color: '#94a3b8', fontWeight: 600, fontSize: '14px' }}>Facility</th>
                <th style={{ padding: '16px', color: '#94a3b8', fontWeight: 600, fontSize: '14px' }}>District</th>
                <th style={{ padding: '16px', color: '#94a3b8', fontWeight: 600, fontSize: '14px' }}>Risk Score</th>
                <th style={{ padding: '16px', color: '#94a3b8', fontWeight: 600, fontSize: '14px' }}>Risk Factor Details</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s' }}>
                  <td style={{ padding: '16px', fontSize: '14px', color: '#e2e8f0' }}>{formatDate(alert.timestamp)}</td>
                  <td style={{ padding: '16px', fontSize: '14px', fontWeight: 600, color: '#f8fafc' }}>{alert.name}</td>
                  <td style={{ padding: '16px', fontSize: '14px', color: '#cbd5e1' }}>{alert.district}</td>
                  <td style={{ padding: '16px', fontSize: '14px' }}>
                    <span style={{ 
                      background: `${getScoreColor(alert.score)}33`, 
                      color: getScoreColor(alert.score),
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontWeight: 'bold'
                    }}>
                      {alert.score.toFixed(1)}
                    </span>
                  </td>
                  <td style={{ padding: '16px', fontSize: '13px', color: '#94a3b8', maxWidth: '300px', lineHeight: '1.4' }}>
                    {alert.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default OfficialsDashboard;
