
import sys
import os
from pathlib import Path

# Add backend to sys.path so we can simulate app environment
sys.path.append(os.getcwd())

try:
    from ltx_pipelines import TI2VidOneStagePipeline
    print("SUCCESS: Imported TI2VidOneStagePipeline")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"FAILURE: {type(e).__name__}: {e}")
