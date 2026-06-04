from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db, fetch_all, fetch_one
from tasks.scheduler import run_cycle
from core.config import settings
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn
import json
import threading

app = FastAPI(title="ColdTrace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    init_db()
    scheduler.add_job(run_cycle, 'interval', hours=settings.app.schedule_interval_hours)
    scheduler.start()
    
    # Trigger initial run asynchronously
    threading.Thread(target=run_cycle).start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/risk-scores")
def get_risk_scores():
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
            except:
                pass
    return rows

@app.get("/risk-scores/{location_id}")
def get_single_risk_score(location_id: int):
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
        except:
            pass
    return row

@app.get("/history/{location_id}")
def get_history(location_id: int):
    rows = fetch_all("SELECT score, timestamp FROM risk_scores WHERE location_id=? ORDER BY timestamp ASC", (location_id,))
    return rows

@app.get("/alert-status")
def get_alert_status():
    query = """
    SELECT a.id, a.score, a.timestamp, a.message, l.name, l.district
    FROM alerts a
    JOIN locations l ON a.location_id = l.id
    ORDER BY a.timestamp DESC LIMIT 50
    """
    return fetch_all(query)

@app.get("/dashboard-summary")
def get_dashboard_summary():
    query = "SELECT score FROM latest_scores"
    scores = [r['score'] for r in fetch_all(query)]
    
    red = sum(1 for s in scores if s > 70)
    amber = sum(1 for s in scores if 50 < s <= 70)
    green = sum(1 for s in scores if s <= 50)
    
    return {
        "total": len(scores),
        "red": red,
        "amber": amber,
        "green": green
    }

@app.post("/refresh")
def refresh_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_cycle)
    return {"message": "Data refresh cycle triggered."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
