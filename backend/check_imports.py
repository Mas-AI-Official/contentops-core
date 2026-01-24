import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "app"))

print("Checking imports...")
try:
    from app.models import Job, Niche, Video
    print("Models imported successfully.")
    
    from app.services.scheduler_service import content_scheduler
    print("Scheduler service imported successfully.")
    
    from app.services.analytics_service import analytics_service
    print("Analytics service imported successfully.")
    
    from app.services.growth_engine_service import growth_engine
    print("Growth engine service imported successfully.")
    
    print("All imports successful.")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
