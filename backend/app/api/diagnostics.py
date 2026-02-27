from fastapi import APIRouter, HTTPException, BackgroundTasks
import shutil
import os
import re
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi.routing import APIRoute

from app.core.config import settings
from app.db.database import sync_engine as engine
from sqlmodel import text

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

class PipelineIssue(BaseModel):
    name: str
    status: str  # "ok", "warning", "fail"
    severity: str  # "blocking", "warning", "info"
    message: str
    fix_steps: str
    links: List[str] = []
    last_checked: str

class PipelineStatus(BaseModel):
    health_score: int
    blocking_count: int
    warning_count: int
    checks: List[PipelineIssue]

def count_files_recursive(directory: Path) -> int:
    """Count files recursively in a directory."""
    if not directory.exists():
        return 0
    return sum(len(files) for _, _, files in os.walk(directory))


def _normalize_frontend_path(path: str) -> str:
    p = re.sub(r"\$\{[^}]+\}", "{param}", path or "")
    p = p.split("?", 1)[0].strip()
    if not p.startswith("/"):
        p = "/" + p
    # Frontend api client uses baseURL=/api
    p = "/api" + p if not p.startswith("/api/") else p
    if p != "/" and p.endswith("/"):
        p = p[:-1]
    return p


def _path_pattern(path: str) -> str:
    esc = re.escape(path)
    esc = esc.replace(r"\{", "{").replace(r"\}", "}")
    esc = re.sub(r"\{[^/]+\}", r"[^/]+", esc)
    return f"^{esc}$"


def _load_backend_routes() -> List[Dict[str, str]]:
    from app.api import api_router

    routes: List[Dict[str, str]] = []
    for route in api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = {m.upper() for m in route.methods or []}
        for method in sorted(methods.intersection({"GET", "POST", "PUT", "PATCH", "DELETE"})):
            path = route.path.rstrip("/") if route.path != "/" else route.path
            routes.append({"method": method, "path": path})
    return routes


def _load_frontend_routes() -> List[Dict[str, str]]:
    api_file = Path(settings.base_path) / "frontend" / "src" / "api.js"
    if not api_file.exists():
        return []
    text = api_file.read_text(encoding="utf-8", errors="ignore")
    patterns = [
        r"api\.(get|post|put|patch|delete)\(\s*`([^`]+)`",
        r"api\.(get|post|put|patch|delete)\(\s*'([^']+)'",
        r'api\.(get|post|put|patch|delete)\(\s*"([^"]+)"',
    ]
    found: List[Dict[str, str]] = []
    for pat in patterns:
        for method, raw_path in re.findall(pat, text):
            found.append(
                {
                    "method": method.upper(),
                    "path": _normalize_frontend_path(raw_path),
                }
            )
    dedup = {(r["method"], r["path"]): r for r in found}
    return list(dedup.values())


def _match_route(frontend_route: Dict[str, str], backend_routes: List[Dict[str, str]]) -> bool:
    method = frontend_route["method"]
    path = frontend_route["path"]
    for candidate in backend_routes:
        if candidate["method"] != method:
            continue
        if re.match(_path_pattern(candidate["path"]), path):
            return True
    return False


def _check_contracts() -> Dict[str, Any]:
    frontend_routes = _load_frontend_routes()
    backend_routes = _load_backend_routes()
    missing = [r for r in frontend_routes if not _match_route(r, backend_routes)]
    return {
        "frontend_count": len(frontend_routes),
        "backend_count": len(backend_routes),
        "missing_count": len(missing),
        "missing": missing[:50],
    }

@router.get("/pipeline", response_model=PipelineStatus)
async def check_pipeline_health(refresh: bool = False):
    """
    Run a full diagnostic check of the pipeline components.
    Splits issues into Blocking vs Warnings.
    """
    checks = []
    
    # === BLOCKING CHECKS (Core functionality) ===

    # 1. Python Environment
    import sys
    checks.append({
        "name": "python_env",
        "status": "ok",
        "severity": "blocking",
        "message": f"Python {sys.version.split()[0]} running",
        "fix_steps": "Reinstall Python 3.11+",
        "last_checked": datetime.now().isoformat()
    })

    # 2. Database Connection
    db_status = "fail"
    db_msg = "Connection failed"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "ok"
            db_msg = "Connected to SQLite"
    except Exception as e:
        db_msg = str(e)
        
    checks.append({
        "name": "database",
        "status": db_status,
        "severity": "blocking",
        "message": db_msg,
        "fix_steps": "Check permissions on contentops.db file.",
        "last_checked": datetime.now().isoformat()
    })

    # 3. FFmpeg (Required for video processing)
    ffmpeg_path = shutil.which("ffmpeg")
    checks.append({
        "name": "ffmpeg",
        "status": "ok" if ffmpeg_path else "fail",
        "severity": "blocking",
        "message": f"Found at {ffmpeg_path}" if ffmpeg_path else "FFmpeg binary not found in PATH",
        "fix_steps": "1. Download FFmpeg\n2. Extract to tools folder\n3. Add bin folder to System PATH",
        "links": ["https://ffmpeg.org/download.html"],
        "last_checked": datetime.now().isoformat()
    })

    # 4. Ollama Service (Required for script generation)
    ollama_status = "fail"
    ollama_msg = "Could not connect to Ollama"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Try version endpoint first
            try:
                resp = await client.get(f"{settings.ollama_base_url}/api/version")
                if resp.status_code == 200:
                    ollama_status = "ok"
                    ollama_msg = f"Running version {resp.json().get('version')}"
            except:
                # Fallback to root
                resp = await client.get(f"{settings.ollama_base_url}/")
                if resp.status_code == 200:
                    ollama_status = "ok"
                    ollama_msg = "Ollama is running"
    except Exception as e:
        ollama_msg = f"Could not connect to Ollama: {str(e)}"
    
    checks.append({
        "name": "ollama_service",
        "status": ollama_status,
        "severity": "blocking",
        "message": ollama_msg,
        "fix_steps": "Run start_ollama.bat or ensure Ollama service is active.",
        "last_checked": datetime.now().isoformat()
    })

    # 5. XTTS Server (Required for TTS if using local)
    # Only blocking if TTS provider is set to XTTS globally or in any niche
    # For now, we treat it as blocking if configured
    xtts_status = "warning"
    xtts_msg = "Not configured/available"
    xtts_severity = "blocking"
    
    if settings.xtts_server_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # XTTS server root returns 200 OK
                resp = await client.get(f"{settings.xtts_server_url}/")
                if resp.status_code == 200:
                    xtts_status = "ok"
                    xtts_msg = "XTTS Server is ready"
                else:
                    xtts_status = "fail"
                    xtts_msg = f"XTTS Server returned {resp.status_code}"
        except Exception:
            xtts_status = "fail"
            xtts_msg = "Could not reach XTTS Server"
    
    checks.append({
        "name": "xtts_server",
        "status": xtts_status,
        "severity": xtts_severity,
        "message": xtts_msg,
        "fix_steps": "Run XTTS server separately or use ElevenLabs.",
        "last_checked": datetime.now().isoformat()
    })

    # === WARNING CHECKS (Optional features) ===

    # 6. FFprobe (Good to have)
    ffprobe_path = shutil.which("ffprobe")
    checks.append({
        "name": "ffprobe",
        "status": "ok" if ffprobe_path else "warning",
        "severity": "warning",
        "message": f"Found at {ffprobe_path}" if ffprobe_path else "FFprobe binary not found",
        "fix_steps": "Usually installed with FFmpeg.",
        "last_checked": datetime.now().isoformat()
    })

    # 7. ElevenLabs (Optional)
    el_status = "ok" if settings.elevenlabs_api_key else "warning"
    checks.append({
        "name": "elevenlabs",
        "status": el_status,
        "severity": "warning",
        "message": "API Key configured" if el_status == "ok" else "API Key missing",
        "fix_steps": "Add ELEVENLABS_API_KEY to .env if you want to use cloud TTS.",
        "last_checked": datetime.now().isoformat()
    })

    # 8. HF Router (Optional)
    hf_status = "warning"
    checks.append({
        "name": "hf_router",
        "status": "warning", # Assuming not configured by default
        "severity": "warning",
        "message": "Not configured",
        "fix_steps": "Configure HF Router if you need API routing.",
        "last_checked": datetime.now().isoformat()
    })

    # 9. LTX Video (Optional)
    ltx_status = "warning"
    checks.append({
        "name": "ltx_video",
        "status": "warning",
        "severity": "warning",
        "message": "Not configured",
        "fix_steps": "Configure LTX if you want AI video generation.",
        "last_checked": datetime.now().isoformat()
    })

    # 10. MCP (Optional)
    checks.append({
        "name": "mcp",
        "status": "warning",
        "severity": "warning",
        "message": "Disabled",
        "fix_steps": "Enable MCP in settings if needed.",
        "last_checked": datetime.now().isoformat()
    })

    # 11. Model Directories
    required_dirs = [
        ("whisper_cache", settings.whisper_cache_path),
        ("xtts_cache", settings.xtts_cache_path),
        ("image_models", settings.image_models_path),
        ("hf_cache", Path(os.environ.get("HF_HOME", settings.models_path / "hf")))
    ]
    
    for name, path in required_dirs:
        exists = path.exists()
        checks.append({
            "name": f"dir_{name}",
            "status": "ok" if exists else "fail",
            "severity": "blocking" if name in ["whisper_cache"] else "warning",
            "message": f"Exists: {path}" if exists else f"Missing: {path}",
            "fix_steps": "Restart backend to auto-create directories.",
            "last_checked": datetime.now().isoformat()
        })

    # 12. Frontend/API contract check
    contracts = _check_contracts()
    checks.append({
        "name": "route_contracts",
        "status": "ok" if contracts["missing_count"] == 0 else "warning",
        "severity": "warning",
        "message": (
            "Frontend routes are fully mapped to backend endpoints"
            if contracts["missing_count"] == 0
            else f"{contracts['missing_count']} frontend API route(s) missing backend handlers"
        ),
        "fix_steps": "Run /api/diagnostics/contracts and implement missing endpoints or update frontend API calls.",
        "last_checked": datetime.now().isoformat()
    })

    # Calculate stats
    blocking_fails = [c for c in checks if c["severity"] == "blocking" and c["status"] == "fail"]
    warning_fails = [c for c in checks if c["severity"] == "warning" and c["status"] != "ok"]
    
    health_score = 100
    if blocking_fails:
        health_score = 0
    elif warning_fails:
        health_score = max(50, 100 - (len(warning_fails) * 10))
    
    return {
        "health_score": health_score,
        "blocking_count": len(blocking_fails),
        "warning_count": len(warning_fails),
        "checks": checks
    }

@router.post("/fix")
async def run_pipeline_fix(background_tasks: BackgroundTasks):
    """
    Attempt to fix common pipeline issues.
    """
    results = []
    
    # 1. Create missing directories
    try:
        dirs_to_create = [
            settings.whisper_cache_path,
            settings.xtts_cache_path,
            settings.image_models_path,
            settings.models_path / "hf",
            settings.models_path / "checkpoints",
            settings.models_path / "ollama"
        ]
        for d in dirs_to_create:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                results.append(f"Created directory: {d}")
    except Exception as e:
        results.append(f"Failed to create directories: {e}")

    # 2. Check/Install Python deps (basic check)
    # We won't auto-install here as it might block, but we could trigger a background task
    
    return {"message": "Fixes applied", "details": results}

@router.get("/health")
async def health_check():
    """Simple health check for the doctor."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/contracts")
async def check_route_contracts():
    """Compare frontend API client calls with backend registered routes."""
    return _check_contracts()
