import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "coldtrace.db")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:coldtrace2026@db.wonmczmuemkgqwmeawke.supabase.co:5432/postgres")

def get_db():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        return conn, "postgres"
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def init_db():
    conn, db_type = get_db()
    cursor = conn.cursor()
    
    if db_type == "postgres":
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            name TEXT,
            lat REAL,
            lng REAL,
            district TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_scores (
            id SERIAL PRIMARY KEY,
            location_id INTEGER,
            score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            top_features TEXT,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS latest_scores (
            location_id INTEGER PRIMARY KEY,
            score REAL,
            timestamp TIMESTAMP,
            top_features TEXT,
            temperature REAL,
            wastage_rate REAL,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            location_id INTEGER,
            score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        )
        ''')
    else:
        # SQLite
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            lat REAL,
            lng REAL,
            district TEXT
        )
        ''')
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

    conn.commit()
    cursor.close()
    conn.close()

def execute_query(query: str, params: tuple = ()) -> int:
    conn, db_type = get_db()
    cursor = conn.cursor()
    if db_type == "postgres":
        query = query.replace("?", "%s")
        # Handle SQLite's INSERT OR REPLACE vs Postgres' INSERT ... ON CONFLICT
        if "INSERT OR REPLACE" in query:
            query = query.replace("INSERT OR REPLACE INTO", "INSERT INTO")
            query += " ON CONFLICT (location_id) DO UPDATE SET score = EXCLUDED.score, timestamp = EXCLUDED.timestamp, top_features = EXCLUDED.top_features, temperature = EXCLUDED.temperature, wastage_rate = EXCLUDED.wastage_rate"
            
        if query.strip().upper().startswith("INSERT") and "RETURNING" not in query:
            query += " RETURNING id"
        cursor.execute(query, params)
        try:
            lastrowid = cursor.fetchone()[0]
        except Exception:
            lastrowid = 0
    else:
        cursor.execute(query, params)
        lastrowid = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return lastrowid

def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn, db_type = get_db()
    if db_type == "postgres":
        import psycopg2.extras
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = query.replace("?", "%s")
    else:
        cursor = conn.cursor()
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]
    
def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn, db_type = get_db()
    if db_type == "postgres":
        import psycopg2.extras
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = query.replace("?", "%s")
    else:
        cursor = conn.cursor()
        
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
