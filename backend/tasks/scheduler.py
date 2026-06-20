from database.db import get_db, execute_query, fetch_all, fetch_one
from fetchers.overpass import fetch_phc_locations
from fetchers.datagovin import fetch_hmis_wastage, fetch_power_outage
from fetchers.whopis import get_equipment_reliability
from ml.pipeline import train_initial_model, predict_risk, extract_features
from services.alerts import trigger_alerts
from core.config import settings
import json
import time
import numpy as np

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
    
    # Increase limit to 500 to show a large number of centres on the map
    db_locations = db_locations[:500]
    
    all_wastage = fetch_hmis_wastage()
    all_outages = fetch_power_outage()
    from fetchers.openmeteo import fetch_weather_batch
    
    # Batch fetch all weather in 5 requests instead of 500!
    weather_results = fetch_weather_batch(db_locations)
    
    temp_deltas = {k: v[1] for k, v in weather_results.items() if v[1] is not None}
    current_temps = {k: v[0] for k, v in weather_results.items() if v[0] is not None}
            
    print("Training ML model...")
    train_initial_model(db_locations, all_wastage, all_outages, temp_deltas)
    
    print("Predicting scores...")
    for loc in db_locations:
        dist = loc['district'].lower()
        # Use same deterministic fallback values as training — random fallbacks
        # cause train/predict distribution mismatch that snaps scores to 0 or 100.
        median_wastage = 0.05
        median_outage  = 2
        wastage    = all_wastage.get(dist, median_wastage)
        outage     = all_outages.get(dist, median_outage)
        temp_delta = temp_deltas.get(loc['id'], 5.0)
        ct         = current_temps.get(loc['id'], 30.0)

        # Same deterministic formula as pipeline.py training — must match exactly
        equip_score = int((loc['id'] * 37) % 80) + 20
        
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
