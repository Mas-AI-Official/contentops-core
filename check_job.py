import sys
from pathlib import Path
from sqlmodel import Session, select
sys.path.append(str(Path("d:/Ideas/contentops-core/backend")))
from app.db import sync_engine
from app.models import Job

with Session(sync_engine) as session:
    jobs = session.exec(select(Job).order_by(Job.id.desc()).limit(1)).all()
    if jobs:
        j = jobs[0]
        print(f"Job ID: {j.id}, Status: {j.status}, Progress: {j.progress_percent}%")
        print(f"Error: {j.error_message}")
        print(f"Logs:")
        # Let's get the job logs as well
        from app.models import JobLog
        logs = session.exec(select(JobLog).where(JobLog.job_id == j.id).order_by(JobLog.id)).all()
        for l in logs:
            print(f" [{l.level}] {l.message}")
    else:
        print("No jobs found")
