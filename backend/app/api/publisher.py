"""
API routes for hybrid publishing - API-first with Browser Assist fallback.
"""
import asyncio
import base64
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.publisher_service import (
    publisher_service, 
    PublishMode, 
    PublishStatus,
    Platform
)

router = APIRouter(prefix="/publishing", tags=["publishing"])


# === Request Models ===

class AddAccountRequest(BaseModel):
    platform: str  # youtube, instagram, tiktok
    handle: str
    display_name: str
    mode: str = "auto_smart"  # auto_api, browser_assist, auto_smart
    auto_confirm: bool = False


class PublishRequest(BaseModel):
    post_id: str
    account_id: str
    video_path: str
    caption: str
    hashtags: List[str] = []
    title: Optional[str] = None
    mode: str = "auto_smart"


class UpdateAccountRequest(BaseModel):
    handle: Optional[str] = None
    display_name: Optional[str] = None
    mode: Optional[str] = None
    auto_confirm: Optional[bool] = None
    posting_limits: Optional[dict] = None


# === Account Management ===

@router.get("/accounts")
async def list_accounts(platform: Optional[str] = None):
    """List all connected accounts."""
    platform_enum = Platform(platform) if platform else None
    accounts = publisher_service.list_accounts(platform_enum)
    return {
        "accounts": [acc.to_dict() for acc in accounts],
        "total": len(accounts)
    }


@router.post("/accounts")
async def add_account(request: AddAccountRequest):
    """Add a new account for publishing."""
    try:
        platform = Platform(request.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {request.platform}")
    
    try:
        mode = PublishMode(request.mode)
    except ValueError:
        mode = PublishMode.AUTO_SMART
    
    account = publisher_service.add_account(
        platform=platform,
        handle=request.handle,
        display_name=request.display_name,
        mode=mode,
        auto_confirm=request.auto_confirm
    )
    
    return {
        "status": "created",
        "account": account.to_dict()
    }


@router.get("/accounts/{account_id}")
async def get_account(account_id: str):
    """Get account details."""
    account = publisher_service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account.to_dict()


@router.patch("/accounts/{account_id}")
async def update_account(account_id: str, request: UpdateAccountRequest):
    """Update account settings."""
    updates = request.model_dump(exclude_unset=True)
    
    if "mode" in updates:
        try:
            updates["mode"] = PublishMode(updates["mode"])
        except ValueError:
            del updates["mode"]
    
    account = publisher_service.update_account(account_id, **updates)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account.to_dict()


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """Delete an account."""
    if publisher_service.delete_account(account_id):
        return {"status": "deleted", "account_id": account_id}
    raise HTTPException(status_code=404, detail="Account not found")


# === Browser Assist ===

@router.post("/accounts/{account_id}/open-login")
async def open_login_window(account_id: str):
    """Open browser window for manual login (Browser Assist mode)."""
    result = await publisher_service.open_login_window(account_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/accounts/{account_id}/verify-login")
async def verify_login(account_id: str):
    """Verify login status and save session."""
    result = await publisher_service.verify_login(account_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# === Publishing ===

@router.post("/publish")
async def publish_content(request: PublishRequest, background_tasks: BackgroundTasks):
    """Publish content to a platform."""
    try:
        mode = PublishMode(request.mode)
    except ValueError:
        mode = PublishMode.AUTO_SMART
    
    try:
        job = await publisher_service.publish(
            post_id=request.post_id,
            account_id=request.account_id,
            video_path=request.video_path,
            caption=request.caption,
            hashtags=request.hashtags,
            title=request.title,
            mode=mode
        )
        
        return {
            "job_id": job.id,
            "status": job.status.value,
            "mode": job.mode.value,
            "logs": job.logs
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    """List recent publish jobs."""
    jobs = publisher_service.list_jobs(limit)
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs)
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get publish job details."""
    job = publisher_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.post("/jobs/{job_id}/confirm")
async def confirm_publish(job_id: str):
    """
    Manually confirm a publish job (Mode A).
    
    Call this when a job is in WAITING_CONFIRM status.
    """
    result = await publisher_service.confirm_publish(job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending publish job."""
    job = publisher_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in [PublishStatus.POSTED, PublishStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    job.status = PublishStatus.CANCELLED
    job.add_log("Job cancelled by user")
    
    return {"status": "cancelled", "job_id": job_id}


# === Live Browser View (Manus-style) ===

@router.get("/browser/screenshot")
async def get_browser_screenshot():
    """Get current browser screenshot for live view."""
    screenshot = await publisher_service.get_screenshot()
    
    if not screenshot:
        raise HTTPException(status_code=404, detail="No active browser session")
    
    # Return as base64
    return {
        "image": base64.b64encode(screenshot).decode("utf-8"),
        "format": "jpeg"
    }


@router.websocket("/browser/live")
async def live_browser_feed(websocket: WebSocket):
    """WebSocket for live browser screenshot feed."""
    await websocket.accept()
    
    try:
        while True:
            screenshot = await publisher_service.get_screenshot()
            
            if screenshot:
                await websocket.send_json({
                    "type": "screenshot",
                    "image": base64.b64encode(screenshot).decode("utf-8")
                })
            else:
                await websocket.send_json({
                    "type": "status",
                    "message": "No active browser session"
                })
            
            # Send active job info
            active_job = None
            for job in publisher_service.jobs.values():
                if job.status not in [PublishStatus.POSTED, PublishStatus.FAILED, PublishStatus.CANCELLED]:
                    active_job = job
                    break
            
            if active_job:
                await websocket.send_json({
                    "type": "job_update",
                    "job": active_job.to_dict()
                })
            
            await asyncio.sleep(1)  # 1 FPS for live view
            
    except WebSocketDisconnect:
        pass
