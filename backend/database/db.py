import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "coldtrace.db")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # PHC Locations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        lat REAL,
        lng REAL,
        district TEXT
    )
    ''')
    
    # Risk Scores (history)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS risk_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER,
        score REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        top_features TEXT,
        FOREIGN KEY(location_id) REFERENCES locations(id)
    )
    ''')
    
    # Latest Risk Scores (for fast map querying)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS latest_scores (
        location_id INTEGER PRIMARY KEY,
        score REAL,
        timestamp DATETIME,
        top_features TEXT,
        temperature REAL,
        wastage_rate REAL,
        FOREIGN KEY(location_id) REFERENCES locations(id)
    )
    ''')

    # Alerts history
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER,
        score REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        message TEXT,
        FOREIGN KEY(location_id) REFERENCES locations(id)
    )
    ''')

    # Security audit log — records /refresh hits and failed auth attempts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        ip TEXT,
        success INTEGER DEFAULT 1,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── Auth tables ───────────────────────────────────────────────────────────

    # Registered users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        email                   TEXT UNIQUE NOT NULL,
        password_hash           TEXT NOT NULL,
        is_verified             INTEGER DEFAULT 0,
        verification_token      TEXT,
        verification_expires    DATETIME,
        reset_token             TEXT,
        reset_expires           DATETIME,
        created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
        failed_login_attempts   INTEGER DEFAULT 0,
        locked_until            DATETIME
    )
    ''')

    # Per-user alert subscription preferences
    # location_id NULL means "subscribe to all locations"
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alert_preferences (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
        channel     TEXT NOT NULL DEFAULT 'email',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

def execute_query(query: str, params: tuple = ()) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    lastrowid = cursor.lastrowid
    conn.commit()
    conn.close()
    return lastrowid

def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
    
def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
