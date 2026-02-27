import requests
import json
import time

API_URL = "http://localhost:8100/api"

def create_nature_job():
    print("Creating Nature Deep Truths job...")
    
    # 1. Get the niche ID
    response = requests.get(f"{API_URL}/niches/")
    niches = response.json()
    nature_niche = next((n for n in niches if n["slug"] == "nature_deep_truths"), None)
    
    if not nature_niche:
        print("Error: 'nature_deep_truths' niche not found!")
        return
    
    print(f"Found niche: {nature_niche['name']} (ID: {nature_niche['id']})")
    
    # 2. Create a job
    job_data = {
        "niche_id": nature_niche["id"],
        "topic": "The Secret Language of Trees",
        "job_type": "generate_only"
    }
    
    response = requests.post(f"{API_URL}/jobs/", json=job_data, params={"run_immediately": True})
    
    if response.status_code != 201:
        print(f"Error creating job: {response.text}")
        return
        
    job = response.json()
    print(f"Job created: ID {job['id']}")
    
    # 3. Monitor job
    print("Monitoring job...")
    while True:
        response = requests.get(f"{API_URL}/jobs/{job['id']}")
        job_status = response.json()
        
        status = job_status["status"]
        progress = job_status.get("progress_percent", 0)
        
        print(f"Status: {status} ({progress}%)")
        
        if status in ["ready_for_review", "published", "failed"]:
            break
            
        time.sleep(5)
        
    if status == "failed":
        print(f"Job failed: {job_status.get('error_message')}")
    else:
        print("Job completed successfully!")
        print(f"Video path: {job_status.get('video_path')}")
        if job_status.get('visual_cues'):
            print("\nVisual Cues Generated:")
            print(job_status['visual_cues'][:200] + "...")

if __name__ == "__main__":
    create_nature_job()
