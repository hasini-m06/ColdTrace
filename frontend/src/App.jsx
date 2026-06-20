import React, { useState, useEffect } from 'react';
import MapComponent from './components/Map';
import Sidebar from './components/Sidebar';
import OfficialsDashboard from './components/OfficialsDashboard';
import { getRiskScores, getDashboardSummary, refreshData } from './services/api';

function App() {
  const [locations, setLocations] = useState([]);
  const [summary, setSummary] = useState({ total: 0, red: 0, amber: 0, green: 0 });
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('map'); // 'map' or 'officials'

  const loadData = async () => {
    setLoading(true);
    try {
      const [scoresData, summaryData] = await Promise.all([
        getRiskScores(),
        getDashboardSummary()
      ]);
      setLocations(scoresData);
      setSummary(summaryData);
      if (scoresData.length > 0 && !selectedLocation) {
        setSelectedLocation(scoresData[0]);
      }
    } catch (error) {
      console.error("Failed to load data:", error);
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
      alert("✅ Data cycle triggered! Waiting 90 seconds for the AI to process all 500 locations...");
      setTimeout(loadData, 90000);
    } catch (error) {
      console.error("Refresh failed:", error);
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail || error.message;
      if (status === 401) {
        alert(`❌ Authentication failed (401). The VITE_ADMIN_API_KEY on Vercel may not have been applied yet. Try redeploying on Vercel.\n\nDetail: ${detail}`);
      } else if (status === 429) {
        alert("⏳ Rate limited — you've triggered the cycle too many times this hour. Wait a few minutes and try again.");
      } else {
        alert(`❌ Refresh failed (${status || 'network error'}): ${detail}\n\nCheck the browser console (F12) for more details.`);
      }
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar 
        summary={summary} 
        location={selectedLocation} 
        onRefresh={handleRefresh}
        loading={loading}
        currentView={currentView}
        onViewChange={setCurrentView}
      />
      <div className="map-container">
        {currentView === 'map' ? (
          <MapComponent 
            locations={locations} 
            onSelectLocation={setSelectedLocation}
            selectedId={selectedLocation?.id}
          />
        ) : (
          <OfficialsDashboard />
        )}
      </div>
    </div>
  );
}

export default App;
