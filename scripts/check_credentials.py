"""Check which platform credentials are configured in .env."""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

PLATFORMS = {
    "Instagram": {
        "keys": ["INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD"],
        "help": "Run: python scripts/setup_credentials.py instagram",
    },
    "TikTok": {
        "keys": ["TIKTOK_ACCESS_TOKEN"],
        "help": "Run: python scripts/setup_credentials.py tiktok",
    },
    "YouTube": {
        "keys": ["YOUTUBE_API_KEY", "YOUTUBE_OAUTH_TOKEN"],
        "help": "Run: python scripts/setup_credentials.py youtube",
    },
    "LinkedIn": {
        "keys": ["LINKEDIN_ACCESS_TOKEN"],
        "help": "Run: python scripts/setup_credentials.py linkedin",
    },
    "X / Twitter": {
        "keys": ["TWITTER_BEARER_TOKEN"],
        "help": "Run: python scripts/setup_credentials.py twitter",
    },
    "ElevenLabs": {
        "keys": ["ELEVENLABS_API_KEY"],
        "help": "Already configured" if os.environ.get("ELEVENLABS_API_KEY") else "Add to .env",
    },
    "Pexels": {
        "keys": ["PEXELS_API_KEY"],
        "help": "Already configured" if os.environ.get("PEXELS_API_KEY") else "Add to .env",
    },
}

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

connected = 0
total = len(PLATFORMS)

for name, info in PLATFORMS.items():
    keys = info["keys"]
    all_set = all(os.environ.get(k) for k in keys)
    if all_set:
        print(f"  {GREEN}[OK]{RESET}  {name}")
        connected += 1
    else:
        missing = [k for k in keys if not os.environ.get(k)]
        print(f"  {RED}[--]{RESET}  {name}  (missing: {', '.join(missing)})")

print(f"\n  {connected}/{total} platforms connected")

if connected < 3:
    print(f"\n  {YELLOW}Tip:{RESET} Run setup_credentials.py to connect platforms interactively.")
