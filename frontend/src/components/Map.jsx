import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const getColor = (score) => {
  if (score > 70) return '#ef4444';
  if (score > 50) return '#f59e0b';
  return '#10b981';
};

const MapComponent = ({ locations, onSelectLocation, selectedId }) => {
  const defaultCenter = [15.3173, 75.7139];

  return (
    <MapContainer 
      center={defaultCenter} 
      zoom={7} 
      style={{ height: '100%', width: '100%', background: '#0f172a' }}
      zoomControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
      />
      
      {locations.map((loc) => {
        const isSelected = loc.id === selectedId;
        const color = getColor(loc.score);
        
        return (
          <CircleMarker
            key={loc.id}
            center={[loc.lat, loc.lng]}
            pathOptions={{
              fillColor: color,
              color: isSelected ? '#ffffff' : color,
              weight: isSelected ? 3 : 0,
              fillOpacity: loc.score > 50 ? 0.9 : 0.4,
            }}
            radius={isSelected ? 10 : (loc.score > 70 ? 8 : (loc.score > 50 ? 6 : 1.5))}
            eventHandlers={{
              click: () => onSelectLocation(loc),
            }}
          >
            <Popup>
              <div style={{ color: '#000' }}>
                <strong>{loc.name}</strong><br/>
                District: {loc.district}<br/>
                Score: <strong>{loc.score?.toFixed(1)}</strong>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
};

export default MapComponent;
