"""Start ContentOps dashboard server."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.dashboard:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        log_level="info",
    )
