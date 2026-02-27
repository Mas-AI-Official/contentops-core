import os
import sys
import subprocess
import time
import requests
from pathlib import Path
from huggingface_hub import hf_hub_download

# Configuration
MODELS_ROOT = Path(r"D:\Ideas\MODELS_ROOT")
OLLAMA_MODELS_DIR = MODELS_ROOT / "ollama"
XTTS_MODELS_DIR = MODELS_ROOT / "xtts"
LTX_MODELS_DIR = MODELS_ROOT / "ltx"

# Ensure directories exist
for d in [OLLAMA_MODELS_DIR, XTTS_MODELS_DIR, LTX_MODELS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    print(f"[SETUP] {msg}")

def check_ollama():
    """Check if Ollama is running."""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            log(f"Ollama is running: {response.json()['version']}")
            return True
    except:
        pass
    
    log("Ollama is NOT running. Attempting to start...")
    try:
        # Start Ollama in background
        subprocess.Popen(["ollama", "serve"], env=os.environ, shell=True)
        log("Waiting for Ollama to start...")
        for _ in range(15):
            time.sleep(2)
            try:
                if requests.get("http://localhost:11434/api/version", timeout=1).status_code == 200:
                    log("Ollama started successfully.")
                    return True
            except:
                continue
    except FileNotFoundError:
        log("ERROR: 'ollama' command not found. Please install Ollama first.")
        return False
        
    log("ERROR: Failed to start Ollama.")
    return False

def pull_ollama_models():
    """Pull required Ollama models."""
    models = [
        "llama3.1:8b",
        "mistral",
        "glm4",
        "glm4:9b",
        "qwen2.5:14b-instruct",
        "qwen2.5:7b-instruct",
        "deepseek-r1:14b",
        "deepseek-r1:7b",
        "nomic-embed-text"
    ]
    
    log("Checking Ollama models...")
    for model in models:
        log(f"Pulling {model}...")
        try:
            subprocess.run(["ollama", "pull", model], check=True)
            log(f"Successfully pulled {model}")
        except Exception as e:
            log(f"Failed to pull {model}: {e}")
            log("  - If 'Access is denied', try closing other Ollama instances or running as Admin.")

def download_xtts_models():
    """Download XTTS v2 models."""
    log("Checking XTTS models...")
    repo_id = "coqui/XTTS-v2"
    files = ["model.pth", "config.json", "vocab.json", "speakers_xtts.pth", "dvae.pth", "mel_stats.pth"]
    
    for filename in files:
        dest = XTTS_MODELS_DIR / filename
        if dest.exists():
            log(f"XTTS {filename} already exists.")
            continue
            
        log(f"Downloading XTTS {filename}...")
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(XTTS_MODELS_DIR)
            )
            log(f"Downloaded {filename}")
        except Exception as e:
            log(f"Failed to download {filename}: {e}")

def download_file_with_retry(repo_id, filename, local_dir, retries=3):
    """Download a file from HF with retries."""
    import gc
    for i in range(retries):
        try:
            log(f"Downloading {filename} from {repo_id} (Attempt {i+1}/{retries})...")
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir)
            )
            log(f"Downloaded {filename}")
            gc.collect()  # Force garbage collection to free up memory
            return True
        except Exception as e:
            log(f"Error downloading {filename}: {e}")
            time.sleep(2)
            gc.collect()
    log(f"FAILED to download {filename} after {retries} attempts.")
    return False

def download_ltx_models():
    """Download LTX models."""
    log("Checking LTX models...")
    
    # Main LTX-2 Models
    main_repo = "Lightricks/LTX-2"
    main_files = [
        "ltx-2-19b-dev-fp8.safetensors",
        # "ltx-2-19b-dev.safetensors",
        # "ltx-2-19b-distilled.safetensors",
        # "ltx-2-19b-distilled-fp8.safetensors",
        "ltx-2-spatial-upscaler-x2-1.0.safetensors",
        "ltx-2-temporal-upscaler-x2-1.0.safetensors",
        # "ltx-2-19b-distilled-lora-384.safetensors",
        "model_index.json"
    ]

    # Check for duplicates in common cache locations
    potential_duplicate_paths = [
        MODELS_ROOT / "ltx" / ".cache",
        MODELS_ROOT / "hf" / "hub" / "models--Lightricks--ltx-2"
    ]
    
    for dup_path in potential_duplicate_paths:
        if dup_path.exists():
            log(f"[WARNING] Found potential duplicate/cache folder at: {dup_path}")
            log("  - Recommendation: Delete this folder to save space if 'ltx-2-19b-dev.safetensors' is already in the main ltx folder.")

    for filename in main_files:
        dest = LTX_MODELS_DIR / filename
        if dest.exists():
            size_gb = dest.stat().st_size / (1024 * 1024 * 1024)
            log(f"LTX {filename} already exists at {dest} ({size_gb:.2f} GB). Skipping download.")
            continue
        download_file_with_retry(main_repo, filename, LTX_MODELS_DIR)

    # LoRA Models (Separate Repos)
    # Format: (Repo Name, Filename)
    lora_models = [
        ("Lightricks/LTX-2-19b-IC-LoRA-Canny-Control", "ltx-2-19b-ic-lora-canny-control.safetensors"),
        ("Lightricks/LTX-2-19b-IC-LoRA-Depth-Control", "ltx-2-19b-ic-lora-depth-control.safetensors"),
        ("Lightricks/LTX-2-19b-IC-LoRA-Detailer", "ltx-2-19b-ic-lora-detailer.safetensors"),
        ("Lightricks/LTX-2-19b-IC-LoRA-Pose-Control", "ltx-2-19b-ic-lora-pose-control.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-In", "ltx-2-19b-lora-camera-control-dolly-in.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left", "ltx-2-19b-lora-camera-control-dolly-left.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Out", "ltx-2-19b-lora-camera-control-dolly-out.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Right", "ltx-2-19b-lora-camera-control-dolly-right.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Down", "ltx-2-19b-lora-camera-control-jib-down.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Jib-Up", "ltx-2-19b-lora-camera-control-jib-up.safetensors"),
        ("Lightricks/LTX-2-19b-LoRA-Camera-Control-Static", "ltx-2-19b-lora-camera-control-static.safetensors"),
    ]

    for repo, filename in lora_models:
        dest = LTX_MODELS_DIR / filename
        if dest.exists():
            log(f"LTX LoRA {filename} already exists. Skipping.")
            continue
        download_file_with_retry(repo, filename, LTX_MODELS_DIR)

def main():
    log("Starting comprehensive model verification and download...")
    
    # 1. Ollama
    if check_ollama():
        pull_ollama_models()
    
    # 2. XTTS
    download_xtts_models()
    
    # 3. LTX
    download_ltx_models()
    
    log("All tasks completed.")

if __name__ == "__main__":
    main()
