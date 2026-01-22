"""
MCP-style connector service for external APIs.
Provides a simple allowlist-based proxy to outside providers.
"""
import json
from typing import Any, Dict, List, Optional
import httpx
from loguru import logger

from app.core.config import settings


class MCPService:
    """Minimal connector manager for external APIs."""

    def __init__(self):
        self._connectors = self._load_connectors()

    def _load_connectors(self) -> List[Dict[str, Any]]:
        if not settings.mcp_connectors_json:
            return []
        try:
            data = json.loads(settings.mcp_connectors_json)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning(f"Failed to parse MCP connectors JSON: {exc}")
            return []

    def list_connectors(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": c.get("name"),
                "base_url": c.get("base_url"),
                "type": c.get("type", "generic")
            }
            for c in self._connectors
            if c.get("name") and c.get("base_url")
        ]

    def get_connector(self, name: str) -> Optional[Dict[str, Any]]:
        for c in self._connectors:
            if c.get("name") == name:
                return c
        return None

    async def forward_request(
        self,
        connector_name: str,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        connector = self.get_connector(connector_name)
        if not connector:
            return {"error": "connector_not_found"}

        base_url = connector.get("base_url", "").rstrip("/")
        if not base_url:
            return {"error": "invalid_connector"}

        url = f"{base_url}/{path.lstrip('/')}"
        auth_header = connector.get("auth_header")
        auth_env = connector.get("auth_env")
        auth_prefix = connector.get("auth_prefix", "")

        req_headers = headers or {}
        if auth_header and auth_env:
            token = settings.get_env_value(auth_env)
            if token:
                req_headers[auth_header] = f"{auth_prefix}{token}"

        timeout = connector.get("timeout_seconds", settings.mcp_default_timeout)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=json_body,
                    params=params,
                    headers=req_headers
                )
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response.json() if "application/json" in response.headers.get("content-type", "") else response.text
                }
        except Exception as exc:
            logger.error(f"MCP forward failed: {exc}")
            return {"error": "request_failed", "message": str(exc)}


mcp_service = MCPService()
