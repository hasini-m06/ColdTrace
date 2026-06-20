"""
ColdTrace API — main.py
Security layer:
  - CORS restricted to FRONTEND_URL env var (no wildcard).
  - POST /refresh requires X-Admin-Key header matching ADMIN_API_KEY env var → 401 otherwise.
  - Rate limiting via slowapi: 30/min on GET endpoints, 5/hour on /refresh.
  - Audit log (SQLite access_log table) records /refresh hits and failed auth attempts.
"""

import os
import json
import threading
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database.db import init_db, fetch_all, fetch_one, execute_query
from tasks.scheduler import run_cycle
from core.config import settings
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------
FRONTEND_URL  = os.getenv("FRONTEND_URL", "http://localhost:5173")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")   # Must be set on Render — see .env.example

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ColdTrace API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — restricted to actual frontend origin only
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],   # NOT "*" — only the deployed Vercel URL
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# APScheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler()


# ---------------------------------------------------------------------------
# Auth dependency for write/trigger endpoints
# ---------------------------------------------------------------------------
def require_admin_key(x_admin_key: str = Header(default="")):
    """
    FastAPI dependency: validates X-Admin-Key header against ADMIN_API_KEY env var.
    Returns 401 if missing or wrong. Public GET endpoints do NOT use this dependency.
    """
    if not ADMIN_API_KEY:
        # If env var not configured, block all access with a clear error
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_KEY environment variable not configured on server."
        )
    if x_admin_key != ADMIN_API_KEY:
        # Log the failed attempt before rejecting
        _audit_log("/refresh", "unknown", success=False)
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header.")


def _audit_log(endpoint: str, ip: str, success: bool = True):
    """Write an entry to the access_log table."""
    try:
        execute_query(
            "INSERT INTO access_log (endpoint, ip, success, timestamp) VALUES (?, ?, ?, ?)",
            (endpoint, ip, 1 if success else 0, datetime.utcnow().isoformat())
        )
    except Exception as e:
        print(f"[audit_log] Failed to write audit entry: {e}")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()   # creates all tables including access_log
    scheduler.add_job(run_cycle, 'interval', hours=settings.app.schedule_interval_hours)
    scheduler.start()
    # Trigger initial cycle asynchronously so startup is non-blocking
    threading.Thread(target=run_cycle, daemon=True).start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


# ---------------------------------------------------------------------------
# Public read-only endpoints (rate-limited, no auth required)
# ---------------------------------------------------------------------------
@app.get("/risk-scores")
@limiter.limit("30/minute")
def get_risk_scores(request: Request):
    query = """
    SELECT l.id, l.name, l.lat, l.lng, l.district, 
           s.score, s.temperature, s.wastage_rate, s.timestamp, s.top_features
    FROM locations l
    JOIN latest_scores s ON l.id = s.location_id
    """
    rows = fetch_all(query)
    for r in rows:
        if r['top_features']:
            try:
                r['top_features'] = json.loads(r['top_features'])
            except Exception:
                pass
    return rows


@app.get("/risk-scores/{location_id}")
@limiter.limit("30/minute")
def get_single_risk_score(location_id: int, request: Request):
    query = """
    SELECT l.id, l.name, l.lat, l.lng, l.district, 
           s.score, s.temperature, s.wastage_rate, s.timestamp, s.top_features
    FROM locations l
    JOIN latest_scores s ON l.id = s.location_id
    WHERE l.id = ?
    """
    row = fetch_one(query, (location_id,))
    if row and row['top_features']:
        try:
            row['top_features'] = json.loads(row['top_features'])
        except Exception:
            pass
    return row


@app.get("/history/{location_id}")
@limiter.limit("30/minute")
def get_history(location_id: int, request: Request):
    rows = fetch_all(
        "SELECT score, timestamp FROM risk_scores WHERE location_id=? ORDER BY timestamp ASC",
        (location_id,)
    )
    return rows


@app.get("/alert-status")
@limiter.limit("30/minute")
def get_alert_status(request: Request):
    query = """
    SELECT a.id, a.score, a.timestamp, a.message, l.name, l.district
    FROM alerts a
    JOIN locations l ON a.location_id = l.id
    ORDER BY a.timestamp DESC LIMIT 50
    """
    return fetch_all(query)


@app.get("/dashboard-summary")
@limiter.limit("30/minute")
def get_dashboard_summary(request: Request):
    query = "SELECT score FROM latest_scores"
    scores = [r['score'] for r in fetch_all(query)]

    red   = sum(1 for s in scores if s > 70)
    amber = sum(1 for s in scores if 50 < s <= 70)
    green = sum(1 for s in scores if s <= 50)

    return {"total": len(scores), "red": red, "amber": amber, "green": green}


@app.get("/model-metrics")
@limiter.limit("30/minute")
def get_model_metrics(request: Request):
    """Expose the last-run ML evaluation metrics (public read-only)."""
    metrics_path = os.path.join(os.path.dirname(__file__), "model_metrics.json")
    if not os.path.exists(metrics_path):
        return {"error": "Model metrics not yet generated. Trigger /refresh first."}
    with open(metrics_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Protected write endpoint (auth + strict rate limit + audit log)
# ---------------------------------------------------------------------------
@app.post("/refresh")
@limiter.limit("5/hour")
def refresh_data(
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_admin_key),   # 401 if key wrong/missing
):
    """
    Triggers a full data-pipeline cycle.
    Requires X-Admin-Key header matching ADMIN_API_KEY env var.
    Rate-limited to 5 calls per hour per IP.
    Every call is audit-logged.
    """
    ip = get_remote_address(request)
    _audit_log("/refresh", ip, success=True)
    background_tasks.add_task(run_cycle)
    return {"message": "Data refresh cycle triggered."}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
