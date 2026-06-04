import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model.joblib")

def is_monsoon():
    month = datetime.now().month
    return 1 if 6 <= month <= 9 else 0

def extract_features(location, current_temp, temp_delta, wastage_rate, outage_count, equip_score):
    # Features for a single location
    return {
        "historical_wastage_rate": wastage_rate,
        "max_forecast_temp_delta_48h": temp_delta if temp_delta is not None else 0.0,
        "rolling_power_outage_count_7d": outage_count,
        "monsoon_season_flag": is_monsoon(),
        "equipment_reliability_score": equip_score,
        "days_since_last_maintenance": np.random.randint(10, 180), # Proxy for missing data
        "stock_utilization_pct": np.random.uniform(40, 95) # Proxy for missing data
    }

def train_initial_model(locations, all_wastage, all_outages, all_temp_deltas):
    """
    Bootstrap the initial model by synthesizing a target variable 
    (breach within 72h) based on historical wastage patterns and heat.
    """
    data = []
    targets = []
    
    # Calculate medians for fallback
    median_wastage = np.median(list(all_wastage.values())) if all_wastage else 0.05
    median_outage = np.median(list(all_outages.values())) if all_outages else 2
    
    # Calculate initial risk scores for all locations
    all_scores = []
    location_data = []
    for loc in locations:
        dist = loc['district'].lower()
        wastage = all_wastage.get(dist, median_wastage)
        outage = all_outages.get(dist, median_outage)
        temp_delta = all_temp_deltas.get(loc['id'], 5.0)
        
        # Base features
        features = extract_features(loc, 30.0, temp_delta, wastage, outage, 48)
        
        risk_score = (wastage * 10) + (temp_delta * 0.1) + (outage * 0.2)
        risk_score += np.random.normal(0, 0.5)
        all_scores.append(risk_score)
        location_data.append(features)
        
    threshold = np.percentile(all_scores, 85) if all_scores else 1.5

    for i, score in enumerate(all_scores):
        target = 1 if score > threshold else 0
        data.append(location_data[i])
        targets.append(target)
        
    df = pd.DataFrame(data)
    y = np.array(targets)
    
    if sum(y) == 0:
        # Force some positives if none were created
        indices = np.random.choice(len(y), size=int(0.1*len(y)), replace=False)
        y[indices] = 1

    # Address class imbalance
    smote = SMOTE(random_state=42)
    # SMOTE needs > 1 samples in minority class
    if sum(y) > 5 and len(y) - sum(y) > 5:
        X_res, y_res = smote.fit_resample(df, y)
    else:
        X_res, y_res = df, y

    # Train Random Forest
    rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
    rf.fit(X_res, y_res)
    
    joblib.dump(rf, MODEL_PATH)
    print(f"Model trained and saved to {MODEL_PATH}")

def predict_risk(features_dict):
    """
    Returns risk probability 0-100 and top contributing features.
    """
    if not os.path.exists(MODEL_PATH):
        # Return dummy if model not trained yet
        return 50.0, ["model_not_trained"]
        
    model = joblib.load(MODEL_PATH)
    df = pd.DataFrame([features_dict])
    
    # Get probability of class 1
    prob = model.predict_proba(df)[0][1] * 100
    
    # Simple feature importance explanation based on feature values and model feature importances
    importances = model.feature_importances_
    feat_names = df.columns
    
    # Multiply importance by normalized feature value to get contribution (rough approximation)
    contributions = {}
    for i, name in enumerate(feat_names):
        contributions[name] = importances[i] * features_dict[name]
        
    top_features = sorted(contributions, key=contributions.get, reverse=True)[:3]
    
    return float(prob), top_features
