from database.db import get_db, execute_query, fetch_all, fetch_one
from fetchers.overpass import fetch_phc_locations
from fetchers.datagovin import fetch_hmis_wastage, fetch_power_outage
from fetchers.openmeteo import fetch_temperature_forecast
from fetchers.whopis import get_equipment_reliability
from ml.pipeline import train_initial_model, predict_risk, extract_features
from services.alerts import trigger_alerts
from core.config import settings
import json
import time

def run_cycle():
    print("Starting ColdTrace Data Cycle...")
    
    locations = fetch_phc_locations()
    if not locations:
        print("No locations found, aborting cycle.")
        return
        
    for loc in locations:
        existing = fetch_one("SELECT id FROM locations WHERE name=? AND lat=? AND lng=?", 
                             (loc['name'], loc['lat'], loc['lng']))
        if not existing:
            execute_query("INSERT INTO locations (name, lat, lng, district) VALUES (?, ?, ?, ?)",
                          (loc['name'], loc['lat'], loc['lng'], loc['district']))
            
    db_locations = fetch_all("SELECT * FROM locations")
    
    # For demo purposes, we limit processing to 50 locations to avoid API rate limits and timeouts
    db_locations = db_locations[:50]
    
    all_wastage = fetch_hmis_wastage()
    all_outages = fetch_power_outage()
    
    temp_deltas = {}
    current_temps = {}
    for loc in db_locations:
        ct, delta = fetch_temperature_forecast(loc['lat'], loc['lng'])
        if delta is not None:
            temp_deltas[loc['id']] = delta
            current_temps[loc['id']] = ct
        time.sleep(0.1)
            
    print("Training ML model...")
    train_initial_model(db_locations, all_wastage, all_outages, temp_deltas)
    
    print("Predicting scores...")
    for loc in db_locations:
        dist = loc['district'].lower()
        wastage = all_wastage.get(dist, 0.05)
        outage = all_outages.get(dist, 2)
        temp_delta = temp_deltas.get(loc['id'], 5.0)
        ct = current_temps.get(loc['id'], 30.0)
        
        equip_score = 48
        
        features = extract_features(loc, ct, temp_delta, wastage, outage, equip_score)
        score, top_feats = predict_risk(features)
        
        feats_json = json.dumps(top_feats)
        execute_query("INSERT INTO risk_scores (location_id, score, top_features) VALUES (?, ?, ?)",
                      (loc['id'], score, feats_json))
                      
        execute_query('''
            INSERT OR REPLACE INTO latest_scores 
            (location_id, score, timestamp, top_features, temperature, wastage_rate) 
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
        ''', (loc['id'], score, feats_json, ct, wastage))
        
        if score >= settings.alerts.score_threshold:
            trigger_alerts(loc['id'], loc['name'], loc['district'], score, top_feats)

    print("Cycle complete.")
