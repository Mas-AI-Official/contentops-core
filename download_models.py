#!/usr/bin/env python3
"""
Unified Model Downloader for Content OPS AI.
Downloads both Ollama LLM models and LTX Video models.
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Configuration
MODELS_ROOT = Path(r"D:\Ideas\MODELS_ROOT")
OLLAMA_MODELS_DIR = MODELS_ROOT / "ollama"
LTX_MODELS_DIR = MODELS_ROOT / "ltx"

# Models to download
OLLAMA_MODELS = [
    "qwen2.5:14b-instruct",   # Main generator
    "qwen2.5:7b-instruct",    # Fast/Fallback
    "deepseek-r1:14b",        # Reasoning
    "deepseek-r1:7b",         # Fallback Reasoning
    "nomic-embed-text",       # Embeddings
    "bge-m3",                 # Reranking
    "llama3.1:8b"             # Legacy/Copy
]

LTX_FILES = [
    "ltx-2-19b-distilled-fp8.safetensors",
    "ltx-2-spatial-upscaler-x2-1.0.safetensors",
    "ltx-2-19b-distilled-lora-384.safetensors"
]

def setup_env():
    """Setup environment variables."""
    print(f"[INFO] Setting OLLAMA_MODELS to {OLLAMA_MODELS_DIR}")
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR)
    
    # Ensure directories exist
    OLLAMA_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LTX_MODELS_DIR.mkdir(parents=True, exist_ok=True)

def check_ollama():
    """Check if Ollama is running."""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            print(f"[INFO] Ollama is running: {response.json()['version']}")
            return True
    except:
        pass
    
    print("[WARN] Ollama is NOT running. Attempting to start...")
    try:
        # Start Ollama in background
        subprocess.Popen(["ollama", "serve"], env=os.environ)
        print("[INFO] Waiting for Ollama to start...")
        for _ in range(10):
            time.sleep(2)
            try:
                if requests.get("http://localhost:11434/api/version", timeout=1).status_code == 200:
                    print("[INFO] Ollama started successfully.")
                    return True
            except:
                continue
    except FileNotFoundError:
        print("[ERROR] 'ollama' command not found. Please install Ollama first.")
        return False
        
    print("[ERROR] Failed to start Ollama.")
    return False

def pull_ollama_models():
    """Pull Ollama models."""
    print("\n=== Downloading LLM Models (Ollama) ===")
    
    for model in OLLAMA_MODELS:
        print(f"\n[INFO] Pulling {model}...")
        try:
            # Use subprocess to show progress bar
            subprocess.run(["ollama", "pull", model], check=True, env=os.environ)
            print(f"[SUCCESS] {model} ready.")
        except subprocess.CalledProcessError:
            print(f"[ERROR] Failed to pull {model}")

def download_ltx_models():
    """Download LTX models using huggingface-cli."""
    print("\n=== Downloading LTX Video Models ===")
    
    # Check for huggingface-cli
    try:
        subprocess.run(["huggingface-cli", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[INFO] Installing huggingface_hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub[cli]"], check=True)

    repo_id = "Lightricks/ltx-2"
    
    for filename in LTX_FILES:
        dest_path = LTX_MODELS_DIR / filename
        if dest_path.exists() and dest_path.stat().st_size > 0:
            print(f"[SKIP] {filename} already exists.")
            continue
            
        print(f"\n[INFO] Downloading {filename}...")
        try:
            cmd = [
                "huggingface-cli", "download", 
                repo_id,
                "--include", filename,
                "--local-dir", str(LTX_MODELS_DIR)
            ]
            subprocess.run(cmd, check=True)
            print(f"[SUCCESS] {filename} downloaded.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to download {filename}: {e}")

def main():
    print("Content OPS AI - Unified Model Downloader")
    print("=========================================")
    
    setup_env()
    
    if check_ollama():
        pull_ollama_models()
    else:
        print("[ERROR] Skipping LLM downloads because Ollama is not available.")
    
    download_ltx_models()
    
    print("\n[DONE] All tasks completed.")
    print(f"LLM Models: {OLLAMA_MODELS_DIR}")
    print(f"LTX Models: {LTX_MODELS_DIR}")

if __name__ == "__main__":
    main()
