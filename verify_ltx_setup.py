#!/usr/bin/env python3
"""
Verify LTX-2 Setup and Configuration
"""
import os
import sys
from pathlib import Path

def main():
    print("LTX-2 Setup Verification")
    print("=" * 50)
    
    # 1. Check Models
    models_dir = Path("models/ltx")
    required_models = [
        "ltx-2-19b-distilled-fp8.safetensors",
        "ltx-2-spatial-upscaler-x2-1.0.safetensors",
        "ltx-2-temporal-upscaler-x2-1.0.safetensors",
        "ltx-2-19b-distilled-lora-384.safetensors"
    ]
    
    print(f"Checking models in: {models_dir.absolute()}")
    missing_models = []
    
    if not models_dir.exists():
        print(f"[ERROR] Models directory not found: {models_dir}")
        missing_models = required_models
    else:
        for model in required_models:
            model_path = models_dir / model
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] {model} ({size_mb:.1f} MB)")
            else:
                print(f"  [MISSING] {model}")
                missing_models.append(model)
    
    if missing_models:
        print("\n[ACTION REQUIRED] Run 'python download_ltx_simple.py' to download missing models.")
    else:
        print("\n[OK] All LTX-2 models found.")

    # 2. Check Configuration
    print("\nChecking Configuration (.env)")
    env_path = Path("backend/.env")
    
    if not env_path.exists():
        print(f"[ERROR] .env file not found at {env_path}")
        return
        
    env_content = env_path.read_text(encoding="utf-8")
    
    # Check settings
    settings_to_check = {
        "VIDEO_GEN_PROVIDER": "ltx",
        "LTX_MODEL_PATH": str(models_dir.absolute()).replace("\\", "/")
    }
    
    updates_needed = {}
    
    for key, expected_value in settings_to_check.items():
        found = False
        for line in env_content.splitlines():
            if line.strip().startswith(f"{key}="):
                current_value = line.split("=", 1)[1].strip()
                print(f"  Current {key}: {current_value}")
                if key == "VIDEO_GEN_PROVIDER" and current_value != "ltx":
                    updates_needed[key] = "ltx"
                found = True
                break
        
        if not found:
            print(f"  [MISSING] {key}")
            updates_needed[key] = expected_value

    # 3. Auto-fix
    if updates_needed:
        print("\n[ACTION] Updating .env configuration...")
        new_lines = []
        
        # Read existing lines
        existing_keys = set()
        for line in env_content.splitlines():
            key = line.split("=")[0].strip() if "=" in line else None
            if key in updates_needed:
                new_lines.append(f"{key}={updates_needed[key]}")
                existing_keys.add(key)
                print(f"  Updated {key} to {updates_needed[key]}")
            else:
                new_lines.append(line)
        
        # Append new keys
        for key, value in updates_needed.items():
            if key not in existing_keys:
                new_lines.append(f"{key}={value}")
                print(f"  Added {key}={value}")
        
        # Write back
        env_path.write_text("\n".join(new_lines), encoding="utf-8")
        print("[SUCCESS] Configuration updated.")
        print("Please restart the backend for changes to take effect.")
    else:
        print("\n[OK] Configuration looks correct.")

if __name__ == "__main__":
    main()
