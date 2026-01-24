"""
Publisher Service - Hybrid publishing with API-first and Browser Assist fallback.

Modes:
- AUTO_API: Fully automated via official APIs (YouTube, Instagram, TikTok)
- BROWSER_ASSIST: Playwright-based assisted publishing with manual login
- AUTO_SMART: Try API first, fall back to Browser Assist if unavailable

Features:
- Live browser view (Manus-style)
- Confirm before publish (Mode A) or Auto-confirm (Mode B)
- Rate limiting and safety protections
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from loguru import logger

from app.core.config import settings


class PublishMode(str, Enum):
    AUTO_API = "auto_api"
    BROWSER_ASSIST = "browser_assist"
    AUTO_SMART = "auto_smart"


class PublishStatus(str, Enum):
    PENDING = "pending"
    CONNECTING = "connecting"
    NEEDS_LOGIN = "needs_login"
    CHALLENGE_DETECTED = "challenge_detected"
    UPLOADING = "uploading"
    READY_TO_POST = "ready_to_post"
    WAITING_CONFIRM = "waiting_confirm"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Platform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


@dataclass
class AccountConfig:
    """Configuration for a connected account."""
    id: str
    platform: Platform
    handle: str
    display_name: str
    mode: PublishMode = PublishMode.AUTO_SMART
    status: str = "disconnected"
    api_connected: bool = False
    browser_profile_path: Optional[str] = None
    posting_limits: Dict[str, int] = field(default_factory=lambda: {"per_day": 2, "min_hours_between": 2})
    auto_confirm: bool = False  # Mode B: auto publish without confirmation
    last_post_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def can_post_now(self) -> bool:
        """Check if we're within rate limits."""
        if not self.last_post_at:
            return True
        hours_since_last = (datetime.utcnow() - self.last_post_at).total_seconds() / 3600
        return hours_since_last >= self.posting_limits.get("min_hours_between", 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "handle": self.handle,
            "display_name": self.display_name,
            "mode": self.mode.value,
            "status": self.status,
            "api_connected": self.api_connected,
            "browser_profile_path": self.browser_profile_path,
            "posting_limits": self.posting_limits,
            "auto_confirm": self.auto_confirm,
            "last_post_at": self.last_post_at.isoformat() if self.last_post_at else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PublishJob:
    """A publishing job."""
    id: str
    post_id: str
    account_id: str
    platform: Platform
    mode: PublishMode
    status: PublishStatus = PublishStatus.PENDING
    video_path: Optional[str] = None
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    result_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_log(self, message: str):
        self.logs.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {message}")
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "post_id": self.post_id,
            "account_id": self.account_id,
            "platform": self.platform.value,
            "mode": self.mode.value,
            "status": self.status.value,
            "video_path": self.video_path,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "title": self.title,
            "logs": self.logs,
            "error": self.error,
            "result_url": self.result_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class PublisherService:
    """
    Hybrid publishing service supporting both API and Browser Assist modes.
    """
    
    def __init__(self):
        self.accounts: Dict[str, AccountConfig] = {}
        self.jobs: Dict[str, PublishJob] = {}
        self._accounts_file = settings.data_path / "accounts.json"
        self._browser_profiles_dir = settings.data_path / "browser_profiles"
        self._playwright_context = None
        self._playwright_page = None
        self._screenshot_callback: Optional[Callable] = None
        self._active_job_id: Optional[str] = None
        self._load_accounts()
    
    def _load_accounts(self):
        """Load saved accounts from disk."""
        if self._accounts_file.exists():
            try:
                with open(self._accounts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for acc_data in data.get("accounts", []):
                    acc = AccountConfig(
                        id=acc_data["id"],
                        platform=Platform(acc_data["platform"]),
                        handle=acc_data["handle"],
                        display_name=acc_data["display_name"],
                        mode=PublishMode(acc_data.get("mode", "auto_smart")),
                        status=acc_data.get("status", "disconnected"),
                        api_connected=acc_data.get("api_connected", False),
                        browser_profile_path=acc_data.get("browser_profile_path"),
                        posting_limits=acc_data.get("posting_limits", {"per_day": 2, "min_hours_between": 2}),
                        auto_confirm=acc_data.get("auto_confirm", False)
                    )
                    self.accounts[acc.id] = acc
                logger.info(f"Loaded {len(self.accounts)} accounts")
            except Exception as e:
                logger.error(f"Failed to load accounts: {e}")
    
    def _save_accounts(self):
        """Save accounts to disk."""
        try:
            self._accounts_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._accounts_file, "w", encoding="utf-8") as f:
                json.dump({
                    "accounts": [acc.to_dict() for acc in self.accounts.values()],
                    "updated_at": datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
    
    # === Account Management ===
    
    def add_account(
        self,
        platform: Platform,
        handle: str,
        display_name: str,
        mode: PublishMode = PublishMode.AUTO_SMART,
        auto_confirm: bool = False
    ) -> AccountConfig:
        """Add a new account."""
        import uuid
        account_id = str(uuid.uuid4())[:8]
        
        # Create browser profile directory
        profile_path = self._browser_profiles_dir / f"{platform.value}_{handle}_{account_id}"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        account = AccountConfig(
            id=account_id,
            platform=platform,
            handle=handle,
            display_name=display_name,
            mode=mode,
            status="needs_login",
            browser_profile_path=str(profile_path),
            auto_confirm=auto_confirm
        )
        
        self.accounts[account_id] = account
        self._save_accounts()
        
        logger.info(f"Added account: {platform.value}/{handle} (id: {account_id})")
        return account
    
    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """Get an account by ID."""
        return self.accounts.get(account_id)
    
    def list_accounts(self, platform: Optional[Platform] = None) -> List[AccountConfig]:
        """List all accounts, optionally filtered by platform."""
        accounts = list(self.accounts.values())
        if platform:
            accounts = [a for a in accounts if a.platform == platform]
        return accounts
    
    def update_account(self, account_id: str, **updates) -> Optional[AccountConfig]:
        """Update an account."""
        account = self.accounts.get(account_id)
        if not account:
            return None
        
        for key, value in updates.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        self._save_accounts()
        return account
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        if account_id in self.accounts:
            del self.accounts[account_id]
            self._save_accounts()
            return True
        return False
    
    # === API Publishing ===
    
    async def _check_api_available(self, platform: Platform) -> bool:
        """Check if API publishing is available for a platform."""
        if platform == Platform.YOUTUBE:
            return bool(settings.youtube_client_id and settings.youtube_refresh_token)
        elif platform == Platform.INSTAGRAM:
            return bool(settings.instagram_access_token and settings.instagram_business_account_id)
        elif platform == Platform.TIKTOK:
            return bool(settings.tiktok_access_token and settings.tiktok_verified)
        return False
    
    async def publish_via_api(
        self,
        job: PublishJob,
        account: AccountConfig
    ) -> bool:
        """Publish via official API."""
        job.add_log(f"Starting API publish to {account.platform.value}")
        job.status = PublishStatus.UPLOADING
        
        try:
            if account.platform == Platform.YOUTUBE:
                return await self._publish_youtube_api(job, account)
            elif account.platform == Platform.INSTAGRAM:
                return await self._publish_instagram_api(job, account)
            elif account.platform == Platform.TIKTOK:
                return await self._publish_tiktok_api(job, account)
            else:
                job.error = f"Unsupported platform: {account.platform}"
                job.status = PublishStatus.FAILED
                return False
        except Exception as e:
            logger.error(f"API publish failed: {e}")
            job.error = str(e)
            job.status = PublishStatus.FAILED
            return False
    
    async def _publish_youtube_api(self, job: PublishJob, account: AccountConfig) -> bool:
        """Publish to YouTube via API."""
        job.add_log("Authenticating with YouTube...")
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            
            credentials = Credentials(
                token=None,
                refresh_token=settings.youtube_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.youtube_client_id,
                client_secret=settings.youtube_client_secret
            )
            
            youtube = build("youtube", "v3", credentials=credentials)
            
            job.add_log("Uploading video to YouTube...")
            
            body = {
                "snippet": {
                    "title": job.title or job.caption[:100],
                    "description": job.caption,
                    "tags": job.hashtags,
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }
            
            media = MediaFileUpload(
                job.video_path,
                mimetype="video/mp4",
                resumable=True
            )
            
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = request.execute()
            video_id = response.get("id")
            
            job.result_url = f"https://youtube.com/shorts/{video_id}"
            job.status = PublishStatus.POSTED
            job.add_log(f"Published! URL: {job.result_url}")
            
            account.last_post_at = datetime.utcnow()
            self._save_accounts()
            
            return True
            
        except ImportError:
            job.error = "Google API client not installed. Run: pip install google-api-python-client google-auth"
            job.status = PublishStatus.FAILED
            return False
        except Exception as e:
            job.error = f"YouTube API error: {e}"
            job.status = PublishStatus.FAILED
            return False
    
    async def _publish_instagram_api(self, job: PublishJob, account: AccountConfig) -> bool:
        """Publish to Instagram via Graph API (Business accounts only)."""
        job.add_log("Instagram Graph API publishing...")
        
        # Instagram requires video to be hosted publicly first
        # This is a simplified implementation
        job.error = "Instagram API requires business account and hosted video URL. Use Browser Assist for personal accounts."
        job.status = PublishStatus.FAILED
        return False
    
    async def _publish_tiktok_api(self, job: PublishJob, account: AccountConfig) -> bool:
        """Publish to TikTok via API."""
        job.add_log("TikTok API publishing...")
        
        if not settings.tiktok_verified:
            job.error = "TikTok API requires verified developer app. Use Browser Assist instead."
            job.status = PublishStatus.FAILED
            return False
        
        # TikTok API implementation would go here
        job.error = "TikTok API integration pending verification"
        job.status = PublishStatus.FAILED
        return False
    
    # === Browser Assist Publishing ===
    
    async def _get_browser_context(self, account: AccountConfig):
        """Get or create a Playwright browser context for the account."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        
        if self._playwright_context and not self._playwright_context.browser.is_connected():
            self._playwright_context = None
            self._playwright_page = None
        
        if not self._playwright_context:
            playwright = await async_playwright().start()
            
            browser = await playwright.chromium.launch(
                headless=False,  # Show browser for Manus-style viewing
                slow_mo=50
            )
            
            # Use persistent profile for session cookies
            profile_path = account.browser_profile_path or str(
                self._browser_profiles_dir / f"{account.platform.value}_{account.id}"
            )
            
            self._playwright_context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                storage_state=f"{profile_path}/state.json" if Path(f"{profile_path}/state.json").exists() else None
            )
            
            self._playwright_page = await self._playwright_context.new_page()
        
        return self._playwright_context, self._playwright_page
    
    async def open_login_window(self, account_id: str) -> Dict[str, Any]:
        """Open browser for manual login."""
        account = self.accounts.get(account_id)
        if not account:
            return {"error": "Account not found"}
        
        try:
            context, page = await self._get_browser_context(account)
            
            # Navigate to platform login
            urls = {
                Platform.YOUTUBE: "https://accounts.google.com/signin",
                Platform.INSTAGRAM: "https://www.instagram.com/accounts/login/",
                Platform.TIKTOK: "https://www.tiktok.com/login"
            }
            
            await page.goto(urls.get(account.platform, "https://google.com"))
            
            account.status = "needs_login"
            self._save_accounts()
            
            return {
                "status": "browser_opened",
                "message": f"Please log into {account.platform.value} manually. The session will be saved.",
                "account_id": account_id
            }
            
        except Exception as e:
            logger.error(f"Failed to open login window: {e}")
            return {"error": str(e)}
    
    async def verify_login(self, account_id: str) -> Dict[str, Any]:
        """Verify that user is logged in and save session."""
        account = self.accounts.get(account_id)
        if not account:
            return {"error": "Account not found"}
        
        if not self._playwright_page:
            return {"error": "No browser session active"}
        
        try:
            page = self._playwright_page
            
            # Check login status based on platform
            is_logged_in = False
            
            if account.platform == Platform.YOUTUBE:
                await page.goto("https://studio.youtube.com")
                is_logged_in = "studio.youtube.com" in page.url and "accounts.google.com" not in page.url
            elif account.platform == Platform.INSTAGRAM:
                await page.goto("https://www.instagram.com/")
                is_logged_in = await page.query_selector("[aria-label='Home']") is not None
            elif account.platform == Platform.TIKTOK:
                await page.goto("https://www.tiktok.com/creator-center/content")
                is_logged_in = "login" not in page.url.lower()
            
            if is_logged_in:
                # Save session
                profile_path = account.browser_profile_path
                if profile_path:
                    Path(profile_path).mkdir(parents=True, exist_ok=True)
                    await self._playwright_context.storage_state(path=f"{profile_path}/state.json")
                
                account.status = "connected"
                self._save_accounts()
                
                return {"status": "logged_in", "account_id": account_id}
            else:
                account.status = "needs_login"
                self._save_accounts()
                return {"status": "not_logged_in", "message": "Please complete login in the browser"}
                
        except Exception as e:
            logger.error(f"Failed to verify login: {e}")
            return {"error": str(e)}
    
    async def publish_via_browser(
        self,
        job: PublishJob,
        account: AccountConfig
    ) -> bool:
        """Publish via Browser Assist (Playwright)."""
        job.add_log(f"Starting Browser Assist publish to {account.platform.value}")
        job.status = PublishStatus.CONNECTING
        
        try:
            context, page = await self._get_browser_context(account)
            self._active_job_id = job.id
            
            if account.platform == Platform.YOUTUBE:
                return await self._browser_publish_youtube(job, account, page)
            elif account.platform == Platform.INSTAGRAM:
                return await self._browser_publish_instagram(job, account, page)
            elif account.platform == Platform.TIKTOK:
                return await self._browser_publish_tiktok(job, account, page)
            else:
                job.error = f"Browser Assist not implemented for {account.platform}"
                job.status = PublishStatus.FAILED
                return False
                
        except Exception as e:
            logger.error(f"Browser Assist failed: {e}")
            job.error = str(e)
            job.status = PublishStatus.FAILED
            return False
    
    async def _browser_publish_youtube(self, job: PublishJob, account: AccountConfig, page) -> bool:
        """Publish to YouTube via browser automation."""
        job.add_log("Navigating to YouTube Studio...")
        
        await page.goto("https://studio.youtube.com")
        await asyncio.sleep(2)
        
        # Check if logged in
        if "accounts.google.com" in page.url:
            job.status = PublishStatus.NEEDS_LOGIN
            job.add_log("Login required. Please log in manually.")
            return False
        
        job.add_log("Opening upload dialog...")
        
        # Click Create button
        create_button = await page.query_selector("#create-icon")
        if create_button:
            await create_button.click()
            await asyncio.sleep(1)
        
        # Click Upload video
        upload_option = await page.query_selector('tp-yt-paper-item:has-text("Upload video")')
        if upload_option:
            await upload_option.click()
            await asyncio.sleep(2)
        
        job.add_log("Uploading video file...")
        job.status = PublishStatus.UPLOADING
        
        # Upload file
        file_input = await page.query_selector('input[type="file"]')
        if file_input and job.video_path:
            await file_input.set_input_files(job.video_path)
            await asyncio.sleep(5)  # Wait for upload to start
        
        job.add_log("Filling video details...")
        
        # Fill title
        title_input = await page.query_selector('#textbox[aria-label="Add a title that describes your video"]')
        if title_input:
            await title_input.fill(job.title or job.caption[:100])
        
        # Fill description
        desc_input = await page.query_selector('#textbox[aria-label="Tell viewers about your video"]')
        if desc_input:
            full_text = f"{job.caption}\n\n{' '.join(['#' + h for h in job.hashtags])}"
            await desc_input.fill(full_text)
        
        # Select "Not made for kids"
        not_for_kids = await page.query_selector('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
        if not_for_kids:
            await not_for_kids.click()
        
        # Click Next buttons to reach visibility
        for _ in range(3):
            next_btn = await page.query_selector('#next-button')
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(1)
        
        job.status = PublishStatus.READY_TO_POST
        job.add_log("Ready to publish. Waiting for confirmation...")
        
        # Check auto_confirm setting
        if account.auto_confirm:
            job.add_log("Auto-confirm enabled. Publishing...")
            
            # Click Public radio
            public_radio = await page.query_selector('tp-yt-paper-radio-button[name="PUBLIC"]')
            if public_radio:
                await public_radio.click()
            
            # Click Publish
            publish_btn = await page.query_selector('#done-button')
            if publish_btn:
                await publish_btn.click()
                await asyncio.sleep(3)
            
            job.status = PublishStatus.POSTED
            job.add_log("Published successfully!")
            
            account.last_post_at = datetime.utcnow()
            self._save_accounts()
            
            return True
        else:
            job.status = PublishStatus.WAITING_CONFIRM
            job.add_log("Waiting for manual confirmation. Click 'Confirm Publish' in the UI.")
            return True  # Waiting for user confirmation
    
    async def _browser_publish_instagram(self, job: PublishJob, account: AccountConfig, page) -> bool:
        """Publish to Instagram via browser automation."""
        job.add_log("Navigating to Instagram...")
        
        await page.goto("https://www.instagram.com/")
        await asyncio.sleep(2)
        
        # Check login
        if "login" in page.url.lower():
            job.status = PublishStatus.NEEDS_LOGIN
            job.add_log("Login required. Please log in manually.")
            return False
        
        job.add_log("Instagram browser publishing - manual upload required")
        job.add_log("Please upload the video manually using the + button")
        job.status = PublishStatus.WAITING_CONFIRM
        
        return True
    
    async def _browser_publish_tiktok(self, job: PublishJob, account: AccountConfig, page) -> bool:
        """Publish to TikTok via browser automation."""
        job.add_log("Navigating to TikTok Creator Center...")
        
        await page.goto("https://www.tiktok.com/creator-center/upload")
        await asyncio.sleep(2)
        
        if "login" in page.url.lower():
            job.status = PublishStatus.NEEDS_LOGIN
            job.add_log("Login required. Please log in manually.")
            return False
        
        job.add_log("TikTok browser publishing...")
        job.status = PublishStatus.UPLOADING
        
        # Upload file
        file_input = await page.query_selector('input[type="file"]')
        if file_input and job.video_path:
            await file_input.set_input_files(job.video_path)
            await asyncio.sleep(5)
        
        # Fill caption
        caption_input = await page.query_selector('[data-e2e="caption-input"]')
        if caption_input:
            full_text = f"{job.caption} {' '.join(['#' + h for h in job.hashtags])}"
            await caption_input.fill(full_text)
        
        job.status = PublishStatus.READY_TO_POST
        
        if account.auto_confirm:
            post_btn = await page.query_selector('[data-e2e="post-button"]')
            if post_btn:
                await post_btn.click()
                await asyncio.sleep(3)
            
            job.status = PublishStatus.POSTED
            job.add_log("Posted to TikTok!")
            return True
        else:
            job.status = PublishStatus.WAITING_CONFIRM
            job.add_log("Waiting for manual confirmation.")
            return True
    
    async def confirm_publish(self, job_id: str) -> Dict[str, Any]:
        """Manually confirm a publish job (Mode A)."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        if job.status != PublishStatus.WAITING_CONFIRM:
            return {"error": f"Job is not waiting for confirmation. Status: {job.status}"}
        
        account = self.accounts.get(job.account_id)
        if not account:
            return {"error": "Account not found"}
        
        try:
            page = self._playwright_page
            if not page:
                return {"error": "No active browser session"}
            
            job.add_log("Manual confirmation received. Publishing...")
            
            if account.platform == Platform.YOUTUBE:
                public_radio = await page.query_selector('tp-yt-paper-radio-button[name="PUBLIC"]')
                if public_radio:
                    await public_radio.click()
                publish_btn = await page.query_selector('#done-button')
                if publish_btn:
                    await publish_btn.click()
            elif account.platform == Platform.TIKTOK:
                post_btn = await page.query_selector('[data-e2e="post-button"]')
                if post_btn:
                    await post_btn.click()
            
            await asyncio.sleep(3)
            job.status = PublishStatus.POSTED
            job.add_log("Published successfully!")
            
            account.last_post_at = datetime.utcnow()
            self._save_accounts()
            
            return {"status": "published", "job_id": job_id}
            
        except Exception as e:
            job.error = str(e)
            job.status = PublishStatus.FAILED
            return {"error": str(e)}
    
    # === Main Publish Method ===
    
    async def publish(
        self,
        post_id: str,
        account_id: str,
        video_path: str,
        caption: str,
        hashtags: List[str] = None,
        title: str = None,
        mode: PublishMode = PublishMode.AUTO_SMART
    ) -> PublishJob:
        """
        Main publish method.
        
        Uses AUTO_SMART mode by default:
        1. Try API first
        2. Fall back to Browser Assist if API unavailable
        """
        import uuid
        
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        
        job = PublishJob(
            id=str(uuid.uuid4())[:8],
            post_id=post_id,
            account_id=account_id,
            platform=account.platform,
            mode=mode,
            video_path=video_path,
            caption=caption,
            hashtags=hashtags or [],
            title=title
        )
        
        self.jobs[job.id] = job
        
        # Check rate limits
        if not account.can_post_now():
            job.error = "Rate limit: minimum time between posts not met"
            job.status = PublishStatus.FAILED
            return job
        
        # Choose publish method
        use_mode = mode if mode != PublishMode.AUTO_SMART else account.mode
        
        if use_mode == PublishMode.AUTO_SMART:
            # Try API first
            api_available = await self._check_api_available(account.platform)
            if api_available and account.api_connected:
                job.add_log("Using API mode (AUTO_SMART)")
                success = await self.publish_via_api(job, account)
                if success:
                    return job
                job.add_log("API failed, falling back to Browser Assist")
            
            # Fall back to browser
            job.mode = PublishMode.BROWSER_ASSIST
            await self.publish_via_browser(job, account)
        
        elif use_mode == PublishMode.AUTO_API:
            await self.publish_via_api(job, account)
        
        elif use_mode == PublishMode.BROWSER_ASSIST:
            await self.publish_via_browser(job, account)
        
        return job
    
    async def get_screenshot(self) -> Optional[bytes]:
        """Get current browser screenshot for live view."""
        if self._playwright_page:
            try:
                return await self._playwright_page.screenshot(type="jpeg", quality=50)
            except Exception:
                pass
        return None
    
    def get_job(self, job_id: str) -> Optional[PublishJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self, limit: int = 50) -> List[PublishJob]:
        """List recent jobs."""
        jobs = sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


# Global instance
publisher_service = PublisherService()
