import sys
import os
from sqlmodel import SQLModel, create_engine

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models import *

# Use an in-memory DB for testing
engine = create_engine("sqlite:///:memory:")

print("Creating tables...")
try:
    SQLModel.metadata.create_all(engine)
    print("Tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {e}")
    import traceback
    traceback.print_exc()
