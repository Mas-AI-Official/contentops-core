"""
Helper utility functions.
"""
import re
import hashlib
import uuid
from pathlib import Path
from datetime import datetime


def generate_unique_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())[:8]


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """Sanitize a string for use as a filename."""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces and other chars with underscores
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove non-ASCII characters
    name = name.encode('ascii', 'ignore').decode('ascii')
    # Truncate
    if len(name) > max_length:
        name = name[:max_length]
    # Remove trailing underscores
    name = name.strip('_')
    return name or 'untitled'


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """Calculate hash of a file."""
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def timestamp_filename(base_name: str, extension: str) -> str:
    """Generate a filename with timestamp."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"
