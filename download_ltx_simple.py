#!/usr/bin/env python3
"""
Simple LTX-2 Model Downloader with Progress and Verification
"""

import os
import sys
from pathlib import Path
import time

# Force direct download to avoid Windows cache locking issues with huggingface_hub
HAS_HF_HUB = False
try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Installing dependencies...")
    os.system(f"{sys.executable} -m pip install requests tqdm")
    import requests
    from tqdm import tqdm

# Configuration
REPO_ID = "Lightricks/ltx-2"
MODELS_DIR = Path("models/ltx")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Models to download (prioritize the most important ones)
MODELS_TO_DOWNLOAD = [
    "ltx-2-19b-distilled-fp8.safetensors",  # Recommended for RTX 4060
    "ltx-2-spatial-upscaler-x2-1.0.safetensors",  # Spatial upscaler
    "ltx-2-temporal-upscaler-x2-1.0.safetensors",  # Temporal upscaler
    "ltx-2-19b-distilled-lora-384.safetensors",  # LoRA
]

def download_file_requests(url, destination, filename):
    """Download file with progress bar using requests (fallback)"""
    print(f"\n[DOWNLOAD] {filename}")
    print(f"   URL: {url}")
    print(f"   Destination: {destination}")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    block_size = 8192

    with open(destination, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                file.write(chunk)
                pbar.update(len(chunk))

    return destination

def main():
    print("LTX-2 Model Downloader (Direct Mode)")
    print("=" * 50)
    print(f"Repository: {REPO_ID}")
    print(f"Download dir: {MODELS_DIR.absolute()}")
    print(f"Models to download: {len(MODELS_TO_DOWNLOAD)}")
    print(f"Using huggingface_hub: {HAS_HF_HUB}")
    print()

    downloaded_count = 0
    failed_count = 0

    for i, model_file in enumerate(MODELS_TO_DOWNLOAD, 1):
        print(f"\n[{i}/{len(MODELS_TO_DOWNLOAD)}] Processing {model_file}")

        destination = MODELS_DIR / model_file
        
        # Check if file already exists and is valid size
        if destination.exists():
            size_bytes = destination.stat().st_size
            if size_bytes < 1024 * 1024: # Less than 1MB
                print(f"  [WARNING] Found incomplete file, re-downloading...")
                try:
                    destination.unlink()
                except PermissionError:
                    print(f"  [ERROR] Cannot delete incomplete file. Please close any programs using it.")
                    failed_count += 1
                    continue
            else:
                print(f"  [OK] File exists: {destination}")
                downloaded_count += 1
                continue

        try:
            # Always use direct download
            url = f"https://huggingface.co/{REPO_ID}/resolve/main/{model_file}"
            download_file_requests(url, destination, model_file)
            print(f"  [SUCCESS] Downloaded: {destination}")
            downloaded_count += 1
        except KeyboardInterrupt:
            print(f"\n[INTERRUPTED] Download of {model_file} interrupted by user")
            break
        except Exception as e:
            print(f"[ERROR] Failed to download {model_file}: {e}")
            failed_count += 1
            continue

    print("\n" + "=" * 50)
    print("Download Summary")
    print("=" * 50)
    print(f"[SUCCESS] Downloaded: {downloaded_count}")
    print(f"[FAILED] Failed: {failed_count}")
    print(f"[LOCATION] {MODELS_DIR.absolute()}")

    if downloaded_count > 0:
        print("\nNext steps:")
        print("1. Set LTX_MODEL_PATH in your .env file")
        print("2. Restart your application")
        print("3. LTX-2 video generation will be available!")

    return downloaded_count > 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)