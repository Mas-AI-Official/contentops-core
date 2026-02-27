import os
from pathlib import Path
import stat

def make_writable(path: str):
    p = Path(path)
    if not p.exists():
        return
    for item in p.rglob('*'):
        if item.is_file():
            try:
                os.chmod(item, stat.S_IWRITE)
                print(f"Made writable: {item}")
            except Exception as e:
                print(f"Failed {item}: {e}")

if __name__ == "__main__":
    make_writable("D:/Ideas/contentops-core/data/niches")
