"""
ColdTrace ML Pipeline
---------------------
Cold-start label bootstrapping strategy:
  Since no real historical vaccine cold-chain failure data exists for these PHC locations,
  we synthesise a binary target variable by labelling the top-15th-percentile of a
  domain-expert heuristic risk formula as "high risk" (label=1).
  This is a legitimate cold-start method — it is NOT ground-truth supervision.
  Once real failure event logs become available, replace `targets` with actual labels.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    recall_score, precision_score, f1_score,
    confusion_matrix, classification_report
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model.joblib")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "model_metrics.json")

# ---------------------------------------------------------------------------
# Deterministic placeholder constants (pending real data integration)
# ---------------------------------------------------------------------------
# PLACEHOLDER: days_since_last_maintenance — set to 90 days (3-month median
# maintenance cycle for Karnataka PHCs per HMIS guidelines).
# Replace with real CMMS/facility data when available.
PLACEHOLDER_DAYS_SINCE_MAINTENANCE = 90

# PLACEHOLDER: stock_utilization_pct — set to 72% (estimated median cold-chain
# stock utilisation for Karnataka PHCs from published HMIS 2022-23 reports).
# Replace with real inventory management system data when available.
PLACEHOLDER_STOCK_UTILIZATION_PCT = 72.0


def is_monsoon() -> int:
    """Returns 1 if current month is within Indian monsoon season (Jun-Sep)."""
    month = datetime.now().month
    return 1 if 6 <= month <= 9 else 0


def extract_features(location, current_temp, temp_delta, wastage_rate, outage_count, equip_score) -> dict:
    """
    Build the feature vector for a single PHC location.

    Notes:
    - days_since_last_maintenance: deterministic constant (see PLACEHOLDER comment above).
    - stock_utilization_pct: deterministic constant (see PLACEHOLDER comment above).
    - These were previously np.random calls which caused non-reproducible training.
    """
    return {
        "historical_wastage_rate":        wastage_rate,
        "max_forecast_temp_delta_48h":    temp_delta if temp_delta is not None else 0.0,
        "rolling_power_outage_count_7d":  outage_count,
        "monsoon_season_flag":            is_monsoon(),
        "equipment_reliability_score":    equip_score,
        # PLACEHOLDER — deterministic constant, not random noise (see module docstring)
        "days_since_last_maintenance":    PLACEHOLDER_DAYS_SINCE_MAINTENANCE,
        # PLACEHOLDER — deterministic constant, not random noise (see module docstring)
        "stock_utilization_pct":          PLACEHOLDER_STOCK_UTILIZATION_PCT,
    }


def train_initial_model(locations, all_wastage, all_outages, all_temp_deltas):
    """
    Bootstrap initial RandomForest model using a heuristic-synthesised target variable.

    Label strategy (cold-start bootstrap):
      - Compute a domain-expert heuristic risk score for every location.
      - Label the top-15th-percentile as positive (label=1 = "high-risk facility").
      - THIS LABEL IS NOT GROUND TRUTH. It encodes the heuristic, not observed failures.

    Evaluation:
      - Uses stratified 5-fold CV when n_samples >= 50, else a simple 80/20 stratified
        train/test split, to produce honest in-distribution metrics.
      - Metrics are saved to model_metrics.json for citation in reports.
    """
    # ------------------------------------------------------------------
    # 1. Build feature matrix & heuristic labels
    # ------------------------------------------------------------------
    median_wastage = np.median(list(all_wastage.values())) if all_wastage else 0.05
    median_outage  = np.median(list(all_outages.values())) if all_outages else 2

    all_scores    = []
    location_data = []

    for loc in locations:
        dist      = loc['district'].lower()
        wastage   = all_wastage.get(dist, median_wastage)
        outage    = all_outages.get(dist, median_outage)
        temp_delta = all_temp_deltas.get(loc['id'], 5.0)

        # Use a fixed equipment score seeded by location id for reproducibility
        equip_score = int((loc['id'] * 37) % 80) + 20  # deterministic 20-100 range

        features = extract_features(loc, 30.0, temp_delta, wastage, outage, equip_score)

        # Heuristic risk formula (domain-expert weighted combination)
        risk_score = (
            (wastage * 10)
            + (temp_delta * 0.1)
            + (outage * 0.2)
            + (features['days_since_last_maintenance'] * 0.02)
            - (equip_score * 0.01)
        )
        all_scores.append(risk_score)
        location_data.append(features)

    # ------------------------------------------------------------------
    # 2. Synthesise binary labels (heuristic bootstrap — NOT ground truth)
    # ------------------------------------------------------------------
    threshold = np.percentile(all_scores, 85) if all_scores else 1.5
    targets   = np.array([1 if s > threshold else 0 for s in all_scores])

    # Ensure at least some positives exist
    if targets.sum() == 0:
        top_idx = np.argsort(all_scores)[-max(1, int(0.15 * len(all_scores))):]
        targets[top_idx] = 1

    pos_frac = targets.mean()
    print(f"[ColdTrace ML] Heuristic label stats: {targets.sum()} positive / "
          f"{len(targets)} total ({pos_frac:.1%} labelled high-risk). "
          f"NOTE: labels are heuristic bootstraps, not ground truth.")

    df = pd.DataFrame(location_data)
    y  = targets

    # ------------------------------------------------------------------
    # 3. Evaluate with stratified CV (or fallback split)
    # ------------------------------------------------------------------
    rf_eval = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    # Platt scaling calibration: maps raw RF probabilities to smooth 0–1 curve
    # so predict_proba doesn't snap to 0.0/1.0 on in-distribution examples.
    calibrated_eval = CalibratedClassifierCV(rf_eval, method='sigmoid', cv=3)

    n_samples  = len(y)
    min_class  = min(y.sum(), n_samples - y.sum())
    use_kfold  = (n_samples >= 50) and (min_class >= 5)

    all_y_true, all_y_pred = [], []

    if use_kfold:
        k = 5
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        print(f"[ColdTrace ML] Running stratified {k}-fold CV on {n_samples} samples...")
        for fold, (train_idx, test_idx) in enumerate(skf.split(df, y), 1):
            X_tr, X_te = df.iloc[train_idx], df.iloc[test_idx]
            y_tr, y_te = y[train_idx], y[test_idx]
            calibrated_eval.fit(X_tr, y_tr)
            preds = calibrated_eval.predict(X_te)
            all_y_true.extend(y_te.tolist())
            all_y_pred.extend(preds.tolist())
            print(f"  Fold {fold}: recall={recall_score(y_te, preds, zero_division=0):.3f}  "
                  f"precision={precision_score(y_te, preds, zero_division=0):.3f}")
        eval_method = f"stratified_{k}fold_cv"
    else:
        # Fallback: single stratified 80/20 split
        print(f"[ColdTrace ML] n_samples={n_samples} too small for 5-fold CV — "
              f"using 80/20 stratified split...")
        X_tr, X_te, y_tr, y_te = train_test_split(
            df, y, test_size=0.2, stratify=y, random_state=42
        )
        calibrated_eval.fit(X_tr, y_tr)
        all_y_true = y_te.tolist()
        all_y_pred = calibrated_eval.predict(X_te).tolist()
        eval_method = "stratified_80_20_split"

    # ------------------------------------------------------------------
    # 4. Compute & persist metrics
    # ------------------------------------------------------------------
    y_true_arr = np.array(all_y_true)
    y_pred_arr = np.array(all_y_pred)

    recall    = recall_score(y_true_arr, y_pred_arr, zero_division=0)
    precision = precision_score(y_true_arr, y_pred_arr, zero_division=0)
    f1        = f1_score(y_true_arr, y_pred_arr, zero_division=0)
    cm        = confusion_matrix(y_true_arr, y_pred_arr).tolist()

    metrics = {
        "eval_method":        eval_method,
        "n_samples":          n_samples,
        "positive_label_frac": round(float(pos_frac), 4),
        "label_type":         "heuristic_bootstrap_NOT_ground_truth",
        "recall":             round(float(recall), 4),
        "precision":          round(float(precision), 4),
        "f1":                 round(float(f1), 4),
        "confusion_matrix":   cm,
        "classification_report": classification_report(
            y_true_arr, y_pred_arr, zero_division=0
        ),
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "features_used": list(df.columns),
        "placeholder_features": [
            "days_since_last_maintenance",
            "stock_utilization_pct",
        ],
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"[ColdTrace ML] Evaluation complete → "
          f"recall={recall:.3f}  precision={precision:.3f}  F1={f1:.3f}")
    print(f"[ColdTrace ML] Confusion matrix (TN FP / FN TP): {cm}")
    print(f"[ColdTrace ML] Metrics saved to {METRICS_PATH}")

    # ------------------------------------------------------------------
    # 5. Re-train final model on FULL dataset (standard practice after CV)
    # ------------------------------------------------------------------
    rf_final = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    final_calibrated = CalibratedClassifierCV(rf_final, method='sigmoid', cv=3)
    final_calibrated.fit(df, y)
    joblib.dump(final_calibrated, MODEL_PATH)
    print(f"[ColdTrace ML] Final calibrated model trained on full dataset and saved to {MODEL_PATH}")


def predict_risk(features_dict) -> tuple:
    """
    Returns (risk_probability_0_to_100, top_3_contributing_features).
    """
    if not os.path.exists(MODEL_PATH):
        return 50.0, ["model_not_trained"]

    model = joblib.load(MODEL_PATH)
    df    = pd.DataFrame([features_dict])

    prob = model.predict_proba(df)[0][1] * 100

    # Feature contribution: importance × normalised absolute feature value
    importances  = model.feature_importances_
    feat_names   = df.columns
    contributions = {}
    for i, name in enumerate(feat_names):
        val = features_dict[name]
        contributions[name] = importances[i] * abs(float(val)) if val is not None else 0.0

    top_features = sorted(contributions, key=contributions.get, reverse=True)[:3]
    return float(prob), top_features
