"""
API routes for account management.
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_async_session
from app.models import (
    Account, AccountCreate, AccountUpdate, AccountRead,
    AccountStatus, AccountStatusCheck, Platform
)
from app.core.config import settings
from app.services import publish_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


def check_account_status(account: Account) -> AccountStatus:
    """Check the connection status of an account."""
    
    if account.platform == Platform.YOUTUBE:
        if settings.youtube_client_id and settings.youtube_refresh_token:
            return AccountStatus.CONNECTED
        return AccountStatus.MISSING_CONFIG
    
    elif account.platform == Platform.INSTAGRAM:
        if settings.instagram_access_token and settings.instagram_business_account_id:
            return AccountStatus.CONNECTED
        return AccountStatus.MISSING_CONFIG
    
    elif account.platform == Platform.TIKTOK:
        if settings.tiktok_access_token and settings.tiktok_open_id:
            return AccountStatus.CONNECTED
        return AccountStatus.MISSING_CONFIG
    
    return AccountStatus.MISSING_CONFIG


@router.get("/", response_model=List[AccountRead])
async def list_accounts(
    platform: Platform = None,
    session: Session = Depends(get_async_session)
):
    """List all accounts."""
    query = select(Account)
    if platform:
        query = query.where(Account.platform == platform)
    
    result = await session.execute(query)
    accounts = result.scalars().all()
    
    # Add status to each account
    result_list = []
    for account in accounts:
        account_dict = account.model_dump()
        account_dict["status"] = check_account_status(account)
        result_list.append(AccountRead(**account_dict))
    
    return result_list


@router.get("/status")
async def get_platform_status():
    """Get connection status for all platforms."""
    return publish_service.get_platform_status()


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: int,
    session: Session = Depends(get_async_session)
):
    """Get a specific account."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account_dict = account.model_dump()
    account_dict["status"] = check_account_status(account)
    return AccountRead(**account_dict)


@router.post("/", response_model=AccountRead, status_code=201)
async def create_account(
    account: AccountCreate,
    session: Session = Depends(get_async_session)
):
    """Create a new account reference."""
    db_account = Account.model_validate(account)
    session.add(db_account)
    await session.commit()
    await session.refresh(db_account)
    
    account_dict = db_account.model_dump()
    account_dict["status"] = check_account_status(db_account)
    return AccountRead(**account_dict)


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int,
    account_update: AccountUpdate,
    session: Session = Depends(get_async_session)
):
    """Update an account."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = account_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    
    account.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(account)
    
    account_dict = account.model_dump()
    account_dict["status"] = check_account_status(account)
    return AccountRead(**account_dict)


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    session: Session = Depends(get_async_session)
):
    """Delete an account."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await session.delete(account)
    await session.commit()
    return {"message": "Account deleted"}


@router.post("/{account_id}/verify")
async def verify_account(
    account_id: int,
    session: Session = Depends(get_async_session)
):
    """Verify account credentials (test connection)."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    status = check_account_status(account)
    
    # Update last verified
    if status == AccountStatus.CONNECTED:
        account.last_verified = datetime.utcnow()
        await session.commit()
    
    return AccountStatusCheck(
        id=account.id,
        platform=account.platform,
        account_name=account.account_name,
        status=status,
        message="Connected" if status == AccountStatus.CONNECTED else "Missing credentials in .env file"
    )
