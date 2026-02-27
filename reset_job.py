import sqlite3

def reset_job(job_id):
    conn = sqlite3.connect('D:/Ideas/contentops-core/data/contentops_v2.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = 'QUEUED', error_message = NULL WHERE id = ?", (job_id,))
    conn.commit()
    print(f"Job {job_id} reset to QUEUED.")
    conn.close()

if __name__ == '__main__':
    reset_job(19)
