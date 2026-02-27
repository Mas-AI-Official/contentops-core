import sqlite3
import json
from datetime import datetime, timedelta

def check_jobs():
    conn = sqlite3.connect('D:/Ideas/contentops-core/data/contentops_v2.db')
    cursor = conn.cursor()
    
    print("Latest 5 Jobs:")
    cursor.execute("SELECT id, status, topic, error_message FROM jobs ORDER BY id DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | Status: {row[1]} | Topic: {row[2][:50]}... | Error: {row[3]}")
    
    # Ensure job 19 is QUEUED for the next worker cycle
    cursor.execute("UPDATE jobs SET status = 'QUEUED', error_message = NULL, scheduled_at = ? WHERE id = 19 AND status != 'PROCESSING'", ((datetime.utcnow() - timedelta(minutes=5)).isoformat(),))
    conn.commit()
    print("\nEnsured Job 19 is QUEUED.")
    
    print("\nLogs for Job 19:")
    cursor.execute("SELECT message, level, timestamp FROM job_logs WHERE job_id = 19 ORDER BY timestamp ASC")
    for row in cursor.fetchall():
        print(f"[{row[1]}] {row[0]} (@{row[2]})")
        
    conn.close()

if __name__ == '__main__':
    check_jobs()
