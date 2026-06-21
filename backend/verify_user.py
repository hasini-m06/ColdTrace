import sys
import sqlite3
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_user.py <email>")
        sys.exit(1)
        
    email = sys.argv[1].strip()
    db_path = os.path.join(os.path.dirname(__file__), "coldtrace.db")
    
    if not os.path.exists(db_path):
        # check data/ subdirectory just in case
        db_path = os.path.join(os.path.dirname(__file__), "data", "coldtrace.db")
        
    if not os.path.exists(db_path):
        print(f"Error: coldtrace.db database file not found.")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, is_verified FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Error: User with email '{email}' not found in database.")
            sys.exit(1)
            
        # Update user
        cursor.execute("UPDATE users SET is_verified = 1, verification_token = NULL, verification_expires = NULL WHERE email = ?", (email,))
        conn.commit()
        print(f"✅ Successfully verified user '{email}' directly in the database!")
        
    except Exception as e:
        print(f"Error updating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
