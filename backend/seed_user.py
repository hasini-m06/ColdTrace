import sqlite3
import os
from database.db import get_db, init_db
from core.security import hash_password

def run_seed():
    print("Running database user seed & wipe...")
    
    # Ensure tables exist
    init_db()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 1. Clear existing users and preferences
        cursor.execute("DELETE FROM alert_preferences")
        cursor.execute("DELETE FROM users")
        
        # 2. Add eventgridsmiths@gmail.com
        email = "eventgridsmiths@gmail.com"
        password = "ColdTraceDemo123!"
        hashed_password = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (email, password_hash, is_verified) 
            VALUES (?, ?, 1)
        ''', (email, hashed_password))
        
        user_id = cursor.lastrowid
        
        # 3. Subscribe to all alerts
        cursor.execute('''
            INSERT INTO alert_preferences (user_id, location_id, channel)
            VALUES (?, NULL, 'email')
        ''', (user_id,))
        
        conn.commit()
        print(f"✅ Successfully wiped users and seeded {email} with password: {password}")
    except Exception as e:
        print(f"Failed to seed user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_seed()
