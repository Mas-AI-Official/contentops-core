import sys
import argparse
from huggingface_hub import hf_hub_download
import os

def download_model(repo_id, filename, local_dir, token=None):
    print(f"Downloading {filename} from {repo_id} to {local_dir}...")
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            token=token,
            local_dir_use_symlinks=False
        )
        print(f"Successfully downloaded to: {path}")
        return 0
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a file from Hugging Face Hub")
    parser.add_argument("repo_id", help="Repository ID (e.g. Lightricks/ltx-2)")
    parser.add_argument("filename", help="Filename to download")
    parser.add_argument("local_dir", help="Local directory to save the file")
    parser.add_argument("--token", help="Hugging Face token (optional)", default=None)
    
    args = parser.parse_args()
    
    sys.exit(download_model(args.repo_id, args.filename, args.local_dir, args.token))
