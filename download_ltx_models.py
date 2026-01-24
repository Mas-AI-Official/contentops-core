#!/usr/bin/env python3
"""
Download ALL LTX-2 models to D:\Ideas\content_factory\models\ltx
Downloads all available models from the LTX-2 repository.
"""
import os
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files

# Configuration
PROJECT_ROOT = Path(r"D:\Ideas\content_factory")
MODELS_DIR = PROJECT_ROOT / "models" / "ltx"

# Ensure models directory exists
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 50)
print("Downloading ALL LTX-2 Models")
print("=" * 50)
print(f"\nModels will be saved to: {MODELS_DIR}")
print("\nThis will download ALL available LTX-2 models from HuggingFace.")
print("This may take a very long time and require significant disk space.")
print("\nModels to download:")
print("  Main Models:")
print("    - ltx-2-19b-dev-fp8.safetensors")
print("    - ltx-2-19b-dev.safetensors")
print("    - ltx-2-19b-distilled.safetensors")
print("    - ltx-2-19b-distilled-fp8.safetensors (RECOMMENDED for RTX 4060)")
print("  Upscalers:")
print("    - ltx-2-spatial-upscaler-x2-1.0.safetensors")
print("    - ltx-2-temporal-upscaler-x2-1.0.safetensors")
print("  LoRAs:")
print("    - ltx-2-19b-distilled-lora-384.safetensors")
print("    - All IC-LoRA and Camera Control LoRAs")
print("\nThis may take several hours depending on your connection...")
print()

# All models to download (from official LTX-2 repository)
models_to_download = [
    # Main model checkpoints
    "ltx-2-19b-dev-fp8.safetensors",
    "ltx-2-19b-dev.safetensors",
    "ltx-2-19b-distilled.safetensors",
    "ltx-2-19b-distilled-fp8.safetensors",  # Recommended for RTX 4060
    
    # Upscalers
    "ltx-2-spatial-upscaler-x2-1.0.safetensors",
    "ltx-2-temporal-upscaler-x2-1.0.safetensors",
    
    # Distilled LoRA
    "ltx-2-19b-distilled-lora-384.safetensors",
    
    # IC-LoRAs (Image Control)
    "LTX-2-19b-IC-LoRA-Canny-Control.safetensors",
    "LTX-2-19b-IC-LoRA-Depth-Control.safetensors",
    "LTX-2-19b-IC-LoRA-Detailer.safetensors",
    "LTX-2-19b-IC-LoRA-Pose-Control.safetensors",
    
    # Camera Control LoRAs
    "LTX-2-19b-LoRA-Camera-Control-Dolly-In.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Dolly-Left.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Dolly-Out.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Dolly-Right.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Jib-Down.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Jib-Up.safetensors",
    "LTX-2-19b-LoRA-Camera-Control-Static.safetensors",
]

repo_id = "Lightricks/ltx-2"

# Check which files actually exist in the repository
print("Checking available files in repository...")
try:
    available_files = list_repo_files(repo_id=repo_id, repo_type="model")
    print(f"Found {len(available_files)} files in repository.")
    
    # Filter to only .safetensors files
    available_models = [f for f in available_files if f.endswith('.safetensors')]
    print(f"Found {len(available_models)} model files (.safetensors).")
    print()
    
    # Update models_to_download to only include files that exist
    models_to_download = [m for m in models_to_download if m in available_models]
    
    # Also add any other .safetensors files we might have missed
    for model_file in available_models:
        if model_file not in models_to_download and 'ltx-2' in model_file.lower():
            models_to_download.append(model_file)
            print(f"  Added: {model_file}")
    
    print(f"\nTotal models to download: {len(models_to_download)}")
    print()
except Exception as e:
    print(f"Warning: Could not list repository files: {e}")
    print("Will attempt to download known model files...")
    print()

try:
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, model_file in enumerate(models_to_download, 1):
        # Check if file already exists
        file_path = MODELS_DIR / model_file
        if file_path.exists():
            size_gb = file_path.stat().st_size / (1024 * 1024 * 1024)
            print(f"[{i}/{len(models_to_download)}] Skipping {model_file} (already exists, {size_gb:.2f} GB)")
            skipped_count += 1
            continue
        
        print(f"[{i}/{len(models_to_download)}] Downloading {model_file}...")
        print(f"  Repository: {repo_id}")
        print(f"  Local dir: {MODELS_DIR}")
        print("  Starting download..."        try:
            # Use tqdm progress bar for better visibility
            from tqdm import tqdm
            import requests

            # First try with huggingface_hub
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=model_file,
                local_dir=str(MODELS_DIR),
                resume_download=True,
                force_download=False
            )
            file_size = os.path.getsize(downloaded_path) / (1024 * 1024 * 1024)  # GB
            print(f"  ✓ Downloaded: {model_file} ({file_size:.2f} GB)")
            downloaded_count += 1
        except KeyboardInterrupt:
            print(f"  ⚠ Download of {model_file} was interrupted by user")
            print("  You can resume this download later by running the script again")
            failed_count += 1
            break
        except Exception as e:
            print(f"  ✗ Error downloading {model_file}: {e}")
            failed_count += 1
            continue
        print()
    
    print("=" * 50)
    print("Download Summary")
    print("=" * 50)
    print(f"\nDownloaded: {downloaded_count} models")
    print(f"Skipped (already exist): {skipped_count} models")
    print(f"Failed: {failed_count} models")
    print(f"\nModels saved to: {MODELS_DIR}")
    print("\nVerifying downloaded files...")
    
    # Verify files
    all_downloaded = True
    total_size = 0
    for model_file in models_to_download:
        file_path = MODELS_DIR / model_file
        if file_path.exists():
            size_gb = file_path.stat().st_size / (1024 * 1024 * 1024)
            total_size += size_gb
            print(f"  ✓ {model_file} ({size_gb:.2f} GB)")
        else:
            print(f"  ✗ {model_file} - NOT FOUND")
            all_downloaded = False
    
    print(f"\nTotal size: {total_size:.2f} GB")
    
    if downloaded_count > 0 or skipped_count > 0:
        print(f"\n✓ Download complete! {downloaded_count + skipped_count} models available.")
    if failed_count > 0:
        print(f"\n⚠ {failed_count} models failed to download. Check errors above.")
        
except Exception as e:
    print(f"\n✗ Error during download: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
