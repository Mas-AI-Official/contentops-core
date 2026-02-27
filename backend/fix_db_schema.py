import sqlite3
from app.core.config import settings

def fix_schema():
    db_path = settings.database_url.replace("sqlite:///", "")
    print(f"Fixing schema for DB at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check columns in jobs table
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in cursor.fetchall()]
    
    print(f"Current columns: {columns}")
    
    if "voice_id" not in columns:
        print("Adding voice_id column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN voice_id TEXT")
        
    if "voice_name" not in columns:
        print("Adding voice_name column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN voice_name TEXT")
        
    if "video_model" not in columns:
        print("Adding video_model column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN video_model TEXT")
        
    if "visual_cues" not in columns:
        print("Adding visual_cues column...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN visual_cues TEXT")
        
    conn.commit()
    conn.close()
    print("Schema fix complete.")

if __name__ == "__main__":
    fix_schema()
