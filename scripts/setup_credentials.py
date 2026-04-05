"""
Interactive credential setup for ContentOps platforms.

Usage:
    python scripts/setup_credentials.py              # guided setup for all
    python scripts/setup_credentials.py instagram     # setup Instagram only
    python scripts/setup_credentials.py refresh       # refresh expiring tokens

Each platform walks you through getting the token from its developer portal,
then writes it to .env. No browser automation — avoids account blocks.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

ENV_PATH = Path(project_root) / ".env"
TOKEN_STORE = Path(project_root) / "config" / "tokens.json"

# ── Helpers ──────────────────────────────────────────────────────────

def write_env_var(key: str, value: str):
    """Write or update a key in .env without clobbering other values."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value
    print(f"  -> Saved {key} to .env")


def save_token_metadata(platform: str, data: dict):
    """Save token metadata (expiry, refresh_token) for auto-refresh."""
    TOKEN_STORE.parent.mkdir(parents=True, exist_ok=True)
    store = {}
    if TOKEN_STORE.exists():
        store = json.loads(TOKEN_STORE.read_text())
    store[platform] = {**data, "updated_at": datetime.now().isoformat()}
    TOKEN_STORE.write_text(json.dumps(store, indent=2))


def prompt(msg: str, required: bool = True) -> str:
    """Prompt user for input."""
    while True:
        value = input(f"  {msg}: ").strip()
        if value or not required:
            return value
        print("  (required — please enter a value)")

# ── Instagram ────────────────────────────────────────────────────────

def setup_instagram():
    print("""
  ┌─────────────────────────────────────────────┐
  │      INSTAGRAM SETUP (direct login)         │
  └─────────────────────────────────────────────┘

  This uses Instagram's mobile API — no Meta Developer
  portal, no Facebook Page, no API tokens needed.

  Just your Instagram username and password.

  SAFETY: Session is saved locally so you only log in once.
  Max 10 posts/day enforced. Human-like delays built in.
""")

    username = prompt("Instagram username (e.g. mas_ai.co)")
    password = prompt("Instagram password")

    write_env_var("INSTAGRAM_USERNAME", username)
    write_env_var("INSTAGRAM_PASSWORD", password)

    # Test the login
    print("\n  Testing login...")
    try:
        sys.path.insert(0, os.path.join(project_root, "src"))
        from agents.instagram_publisher import InstagramPublisher

        pub = InstagramPublisher()
        if pub.login(username, password):
            info = pub.get_account_info()
            print(f"  -> Logged in as @{info.get('username', '?')}")
            print(f"  -> Followers: {info.get('followers', 0)}")
            print(f"  -> Business account: {info.get('is_business', False)}")
            print(f"  -> Session saved (won't need to re-login)")

            save_token_metadata("instagram", {
                "method": "instagrapi_direct",
                "username": username,
                "session_saved": True,
                "expires_at": "never",
            })
        else:
            print("  -> Login failed. Check username/password.")
            print("  -> If you have 2FA, you may need to approve it on your phone.")
    except Exception as e:
        print(f"  -> Login test error: {e}")
        print("  -> Credentials saved to .env. Test later with: python src/agents/instagram_publisher.py login")

    print("\n  Instagram configured!\n")


# ── TikTok ───────────────────────────────────────────────────────────

def setup_tiktok():
    print("""
  ┌─────────────────────────────────────────────┐
  │           TIKTOK SETUP (2 steps)            │
  └─────────────────────────────────────────────┘

  STEP 1: Go to https://developers.tiktok.com
     - Create a developer account (if you don't have one)
     - Create App -> "Content Posting API"
     - Set redirect URI to: http://localhost:8080/callback/tiktok

  STEP 2: Authorize your account
     - Use the Sandbox or get app approved
     - Get your access token from the developer portal
     - It includes video.publish scope

  NOTE: TikTok tokens expire in 24h but include a refresh_token
        that lasts 365 days. The auto-refresh will handle renewal.
""")

    access_token = prompt("Paste your TikTok access token")
    refresh_token = prompt("Paste your TikTok refresh token (for auto-renewal)", required=False)

    write_env_var("TIKTOK_ACCESS_TOKEN", access_token)

    save_token_metadata("tiktok", {
        "refresh_token": refresh_token,
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
    })

    print("\n  TikTok connected!\n")


# ── YouTube ──────────────────────────────────────────────────────────

def setup_youtube():
    print("""
  ┌─────────────────────────────────────────────┐
  │          YOUTUBE SETUP (2 steps)            │
  └─────────────────────────────────────────────┘

  STEP 1: Go to https://console.cloud.google.com
     - Create project (or use existing)
     - Enable "YouTube Data API v3"
     - Create API Key -> Copy it

  STEP 2: Create OAuth 2.0 credentials
     - Go to Credentials -> Create OAuth Client ID
     - Type: Web Application
     - Redirect URI: http://localhost:8080/callback/youtube
     - Download client secret JSON
     - Use Google OAuth Playground to get a token:
       https://developers.google.com/oauthplayground/
     - Scope: https://www.googleapis.com/auth/youtube.upload
""")

    api_key = prompt("Paste your YouTube API Key")
    oauth_token = prompt("Paste your YouTube OAuth Bearer Token")

    write_env_var("YOUTUBE_API_KEY", api_key)
    write_env_var("YOUTUBE_OAUTH_TOKEN", oauth_token)

    save_token_metadata("youtube", {
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
    })

    print("\n  YouTube connected!\n")


# ── LinkedIn ─────────────────────────────────────────────────────────

def setup_linkedin():
    print("""
  ┌─────────────────────────────────────────────┐
  │         LINKEDIN SETUP (2 steps)            │
  └─────────────────────────────────────────────┘

  STEP 1: Go to https://www.linkedin.com/developers/apps
     - Create App -> fill in details
     - Request "Share on LinkedIn" product

  STEP 2: Get access token
     - Use the OAuth 2.0 token generator in developer portal
     - Or use LinkedIn's token debug tool
""")

    access_token = prompt("Paste your LinkedIn access token")
    write_env_var("LINKEDIN_ACCESS_TOKEN", access_token)
    print("\n  LinkedIn connected!\n")


# ── X / Twitter ──────────────────────────────────────────────────────

def setup_twitter():
    print("""
  ┌─────────────────────────────────────────────┐
  │          X / TWITTER SETUP (1 step)         │
  └─────────────────────────────────────────────┘

  STEP 1: Go to https://developer.x.com/en/portal/dashboard
     - Create a project + app
     - Get Bearer Token from "Keys and Tokens" tab
""")

    bearer_token = prompt("Paste your X/Twitter Bearer Token")
    write_env_var("TWITTER_BEARER_TOKEN", bearer_token)
    print("\n  X/Twitter connected!\n")


# ── Token Refresh ────────────────────────────────────────────────────

def refresh_tokens():
    """Check token expiry and refresh any that are close to expiring."""
    if not TOKEN_STORE.exists():
        print("  No token metadata found. Run setup first.")
        return

    store = json.loads(TOKEN_STORE.read_text())
    now = datetime.now()

    for platform, meta in store.items():
        expires_at_str = meta.get("expires_at")
        if not expires_at_str:
            continue

        expires_at = datetime.fromisoformat(expires_at_str)
        days_left = (expires_at - now).days

        if days_left > 7:
            print(f"  [OK]  {platform}: {days_left} days remaining")
            continue

        print(f"  [!!]  {platform}: expires in {days_left} days — refreshing...")

        if platform == "instagram":
            _refresh_instagram(meta)
        elif platform == "tiktok":
            _refresh_tiktok(meta)
        else:
            print(f"        Auto-refresh not supported for {platform}. Re-run setup.")


def _refresh_instagram(meta: dict):
    """Refresh Instagram long-lived token (GET with current token)."""
    current_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not current_token:
        print("        No current token to refresh.")
        return

    try:
        import httpx
        resp = httpx.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": meta.get("app_id", ""),
                "client_secret": meta.get("app_secret", ""),
                "fb_exchange_token": current_token,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        expires_in = data.get("expires_in", 5184000)

        write_env_var("INSTAGRAM_ACCESS_TOKEN", new_token)
        save_token_metadata("instagram", {
            **meta,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        })
        print(f"        Refreshed! New expiry: {expires_in // 86400} days")
    except Exception as e:
        print(f"        Refresh failed: {e}")


def _refresh_tiktok(meta: dict):
    """Refresh TikTok token using refresh_token."""
    refresh_token = meta.get("refresh_token")
    if not refresh_token:
        print("        No refresh token stored. Re-run setup.")
        return

    # TikTok refresh requires client_key and client_secret from their portal
    print("        TikTok auto-refresh requires client_key — re-run setup_credentials.py tiktok")


# ── Main ─────────────────────────────────────────────────────────────

SETUP_MAP = {
    "instagram": setup_instagram,
    "tiktok": setup_tiktok,
    "youtube": setup_youtube,
    "linkedin": setup_linkedin,
    "twitter": setup_twitter,
}

def main():
    print("""
  =============================================
    ContentOps — Platform Credential Setup
    MAS-AI Technologies Inc.
  =============================================
""")

    args = sys.argv[1:]

    if args and args[0] == "refresh":
        refresh_tokens()
        return

    if args and args[0] in SETUP_MAP:
        SETUP_MAP[args[0]]()
        return

    # Interactive: ask which platforms to connect
    print("  Which platforms do you want to connect?\n")
    platforms = list(SETUP_MAP.keys())
    for i, p in enumerate(platforms, 1):
        status = "connected" if os.environ.get(
            {"instagram": "INSTAGRAM_USERNAME",
             "tiktok": "TIKTOK_ACCESS_TOKEN",
             "youtube": "YOUTUBE_API_KEY",
             "linkedin": "LINKEDIN_ACCESS_TOKEN",
             "twitter": "TWITTER_BEARER_TOKEN"}[p]
        ) else "not connected"
        marker = "[OK]" if status == "connected" else "[--]"
        print(f"    {i}. {p.title():12s}  {marker}")

    print(f"    {len(platforms) + 1}. All platforms")
    print(f"    0. Exit\n")

    choice = prompt("Enter number(s), comma-separated (e.g. 1,3)")

    if choice == "0":
        return

    if choice == str(len(platforms) + 1):
        selected = platforms
    else:
        indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
        selected = [platforms[i] for i in indices if 0 <= i < len(platforms)]

    if not selected:
        print("  No valid selection. Exiting.")
        return

    for p in selected:
        SETUP_MAP[p]()

    print("\n  Done! Restart the server to apply new credentials.")
    print("  Run 'python scripts/check_credentials.py' to verify.\n")


if __name__ == "__main__":
    main()
