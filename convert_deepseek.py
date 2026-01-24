#!/usr/bin/env python3
"""
Convert PyTorch DeepSeek model to GGUF format for Ollama
Usage: python convert_deepseek.py E:\Daena\models\llm\deepseek-r2
"""

import sys
import os
from pathlib import Path
import subprocess
import shutil

def convert_pytorch_to_gguf(model_path: str):
    """
    Convert PyTorch model to GGUF format using llama.cpp
    """
    model_path = Path(model_path)
    if not model_path.exists():
        print(f"❌ Model path {model_path} does not exist")
        return False

    print(f"🔄 Converting model from {model_path}")
    print("This requires llama.cpp to be installed")

    # Check if llama.cpp is available
    llama_cpp_dir = Path.cwd() / "llama.cpp"
    if not llama_cpp_dir.exists():
        print("❌ llama.cpp not found. Please install it first:")
        print("git clone https://github.com/ggerganov/llama.cpp")
        print("cd llama.cpp && make")
        return False

    # Convert to GGUF
    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        print(f"❌ Conversion script not found at {convert_script}")
        return False

    output_file = model_path.parent / f"{model_path.name}.gguf"

    print(f"📦 Converting to GGUF format...")
    cmd = [
        sys.executable, str(convert_script),
        "--model", str(model_path),
        "--output", str(output_file),
        "--format", "q4_k_m"  # Good balance of size/quality
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Conversion successful: {output_file}")
            print(f"📁 You can now import this model into Ollama:")
            print(f"ollama create deepseek-r2 -f {output_file}")
            return True
        else:
            print(f"❌ Conversion failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_deepseek.py <model_path>")
        print("Example: python convert_deepseek.py E:\\Daena\\models\\llm\\deepseek-r2")
        sys.exit(1)

    model_path = sys.argv[1]
    success = convert_pytorch_to_gguf(model_path)
    sys.exit(0 if success else 1)