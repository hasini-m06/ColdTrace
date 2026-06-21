"""
ColdTrace API — main.py
Security layer:
  - CORS restricted to FRONTEND_URL env var (no wildcard), credentials allowed.
  - POST /refresh is public but rate-limited (5/hour per IP) and audit-logged.
  - Full JWT auth via /auth/* endpoints (see routers/auth.py).
  - Rate limiting via slowapi: 30/min on GET, 5/hour on /refresh.
  - Audit log (SQLite access_log table) records key events.
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
from core.config import settings, FRONTEND_URL
from routers.auth import router as auth_router
from routers.alerts_router import router as alerts_router
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------
# FRONTEND_URL is imported from core/config.py (single source of truth).
# ADMIN_API_KEY is reserved for future internal-only endpoints — see comment below.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")   # Must be set on Render — see .env.example

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="ColdTrace API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth_router)          # /auth/*
app.include_router(alerts_router)        # /alerts/* (protected)

# ---------------------------------------------------------------------------
# CORS — restricted to actual frontend origin, credentials enabled
# ---------------------------------------------------------------------------
# allow_credentials=True is required for httpOnly cookies to be sent
# cross-origin (Vercel frontend → Render backend).
# With allow_credentials=True the origin MUST be explicit — no wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],  # explicit, never "*"
    allow_credentials=True,   # required for cookie-based auth
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# APScheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler()


# ---------------------------------------------------------------------------
# Auth dependency — RESERVED for future internal-only endpoints
# ---------------------------------------------------------------------------
# IMPORTANT: Do NOT attach require_admin_key to any endpoint that has a
# public-facing UI button. VITE_ env vars are compiled into the JS bundle
# and visible to anyone in devtools — sending a secret from the browser
# provides zero real protection. Use rate limiting (slowapi) for public
# endpoints instead. ADMIN_API_KEY is kept here for future admin-only
# debug/export routes that have NO public UI trigger.
def require_admin_key(x_admin_key: str = Header(default="")):
    """
    FastAPI dependency for FUTURE INTERNAL-ONLY endpoints.
    Do NOT use on any endpoint triggered by the public dashboard.
    """
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_KEY environment variable not configured on server."
        )
    if x_admin_key != ADMIN_API_KEY:
        _audit_log("admin_endpoint", "unknown", success=False)
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
# Public trigger endpoint — protected by rate limit only (5/hour per IP)
# ---------------------------------------------------------------------------
# NOTE: No secret key auth here. VITE_ env vars are bundled into the public
# JS and visible in devtools — a key sent from the browser is not a secret.
# Server-side rate limiting (slowapi) is the correct abuse protection at
# this tier. Every call is still audit-logged for traceability.
@app.post("/refresh")
@limiter.limit("5/hour")
def refresh_data(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Triggers a full data-pipeline cycle.
    Public endpoint — rate-limited to 5 calls/hour per IP.
    Every call is audit-logged.
    """
    ip = get_remote_address(request)
    _audit_log("/refresh", ip, success=True)
    background_tasks.add_task(run_cycle)
    return {"message": "Data refresh cycle triggered."}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
