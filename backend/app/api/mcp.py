"""
MCP-style connector endpoints for external APIs.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.mcp_service import mcp_service

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPForwardRequest(BaseModel):
    connector: str
    method: str = "GET"
    path: str
    json: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None


@router.get("/status")
async def mcp_status():
    return {
        "enabled": settings.mcp_enabled,
        "connectors": mcp_service.list_connectors()
    }


@router.get("/connectors")
async def list_connectors():
    return {"connectors": mcp_service.list_connectors()}


@router.post("/forward")
async def forward(req: MCPForwardRequest):
    if not settings.mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is disabled")

    result = await mcp_service.forward_request(
        connector_name=req.connector,
        method=req.method,
        path=req.path,
        json_body=req.json,
        params=req.params,
        headers=req.headers
    )
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result)
    return result
