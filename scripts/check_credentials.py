"""Check which platform credentials are configured in .env."""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

def _tiktok_cookies_exist():
    """TikTok uses cookie file, not env var."""
    cookie_path = os.environ.get("TIKTOK_COOKIES_PATH", "config/tiktok_cookies.txt")
    return os.path.exists(os.path.join(project_root, cookie_path))

PLATFORMS = {
    "Instagram": {
        "keys": ["INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD"],
        "help": "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env",
    },
    "TikTok": {
        "keys": ["TIKTOK_COOKIES_PATH"],
        "check": _tiktok_cookies_exist,
        "help": "Export cookies from Chrome to config/tiktok_cookies.txt",
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
        "keys": ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"],
        "help": "Get OAuth 1.0a keys from console.x.com",
    },
    "ElevenLabs": {
        "keys": ["ELEVENLABS_API_KEY"],
        "help": "Add ELEVENLABS_API_KEY to .env",
    },
    "Pexels": {
        "keys": ["PEXELS_API_KEY"],
        "help": "Add PEXELS_API_KEY to .env",
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
    custom_check = info.get("check")
    if custom_check:
        all_set = custom_check()
    else:
        all_set = all(os.environ.get(k) for k in keys)
    if all_set:
        print(f"  {GREEN}[OK]{RESET}  {name}")
        connected += 1
    else:
        if custom_check:
            print(f"  {RED}[--]{RESET}  {name}  ({info['help']})")
        else:
            missing = [k for k in keys if not os.environ.get(k)]
            print(f"  {RED}[--]{RESET}  {name}  (missing: {', '.join(missing)})")

print(f"\n  {connected}/{total} platforms connected")

if connected < 3:
    print(f"\n  {YELLOW}Tip:{RESET} Run setup_credentials.py to connect platforms interactively.")
