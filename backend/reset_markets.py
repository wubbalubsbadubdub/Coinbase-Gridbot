import sqlite3
import os

def reset_markets():
    # Path relative to project root
    db_path = os.path.join("backend", "data", "gridbot.db")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"Connecting to {db_path}...")
        
        # Disable all markets
        cursor.execute("UPDATE markets SET enabled=0")
        changed = cursor.rowcount
        conn.commit()
        
        print(f"Successfully disabled {changed} markets.")
        
        # Verify
        cursor.execute("SELECT count(*) FROM markets WHERE enabled=1")
        count = cursor.fetchone()[0]
        print(f"Active markets remaining: {count}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_markets()
