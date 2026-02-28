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
    severity: str  # "blocking", "warning", "optional", "info"
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

    # 5. XTTS Server — blocking only when TTS provider is XTTS
    xtts_active = (settings.tts_provider or "xtts").lower() == "xtts"
    xtts_status = "warning"
    xtts_msg = "Not configured/available"
    xtts_severity = "blocking" if xtts_active else "optional"
    if not xtts_active:
        xtts_msg = "Inactive optional (TTS provider is not XTTS)"
        xtts_status = "ok"
    elif settings.xtts_server_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
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
    elif getattr(settings, "xtts_default_speaker_wav", None):
        xtts_status = "ok"
        xtts_msg = "CLI fallback available (speaker wav configured)"
    
    checks.append({
        "name": "xtts_server",
        "status": xtts_status,
        "severity": xtts_severity,
        "message": xtts_msg,
        "fix_steps": "Run XTTS server or set XTTS_SPEAKER_WAV / daena.wav; or use ElevenLabs.",
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

    # 7. ElevenLabs — optional fallback when TTS is XTTS
    tts_active = (settings.tts_provider or "xtts").lower()
    el_configured = bool(settings.elevenlabs_api_key)
    el_active = tts_active == "elevenlabs"
    el_severity = "blocking" if el_active else "optional"
    el_status = "ok" if el_configured else ("warning" if el_active else "ok")
    el_msg = "API Key configured" if el_configured else "API Key missing"
    if not el_active and el_configured:
        el_msg = "Configured optional fallback (XTTS is primary)"
    elif not el_active:
        el_msg = "Optional fallback only (XTTS is primary)"
    checks.append({
        "name": "elevenlabs",
        "status": el_status,
        "severity": el_severity,
        "message": el_msg,
        "fix_steps": "Add ELEVENLABS_API_KEY to .env if you want cloud TTS fallback.",
        "last_checked": datetime.now().isoformat()
    })

    # 8. HF Router — optional when LLM is Ollama
    llm_active = (settings.llm_provider or "ollama").lower()
    hf_configured = bool(settings.hf_router_api_key or (settings.get_env_value("HF_TOKEN") if hasattr(settings, "get_env_value") else None))
    hf_active = llm_active == "hf_router"
    hf_severity = "blocking" if hf_active else "optional"
    hf_status = "ok" if hf_configured else ("warning" if hf_active else "ok")
    hf_msg = "Not configured"
    if hf_active and hf_configured:
        hf_msg = "Active (LLM provider)"
    elif hf_configured:
        hf_msg = "Configured optional fallback (Ollama is active)"
    elif not hf_active:
        hf_msg = "Inactive optional (LLM provider is Ollama)"
    try:
        if hf_active and settings.hf_router_base_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{settings.hf_router_base_url.rstrip('/')}/models")
                if r.status_code == 200:
                    hf_status = "ok"
                    hf_msg = "Active (LLM provider)"
    except Exception:
        if hf_active:
            hf_status = "fail"
            hf_msg = "Could not reach HF Router"
    checks.append({
        "name": "hf_router",
        "status": hf_status,
        "severity": hf_severity,
        "message": hf_msg,
        "fix_steps": "Set LLM_PROVIDER=hf_router and HF_ROUTER_* in .env if you need API routing.",
        "last_checked": datetime.now().isoformat()
    })

    # 9. LTX Video — optional when VIDEO_GEN_PROVIDER is not ltx; when active verify model/API
    video_provider = (getattr(settings, "video_gen_provider", None) or "ffmpeg").lower()
    ltx_active = video_provider == "ltx"
    ltx_severity = "blocking" if ltx_active else "optional"
    ltx_status = "warning"
    ltx_msg = "Not configured"
    ltx_fix = "Set VIDEO_GEN_PROVIDER=ltx, LTX_MODEL_PATH (or MODELS_ROOT/ltx); optionally LTX_UPSCALER_PATH, LTX_LORA_PATH, LTX_API_URL."
    if not ltx_active:
        ltx_status = "ok"
        ltx_msg = "Installed but inactive (VIDEO_GEN_PROVIDER is not ltx)"
    else:
        ltx_model_path = getattr(settings, "ltx_model_path", None) or os.environ.get("LTX_MODEL_PATH")
        ltx_api_url = getattr(settings, "ltx_api_url", None) or os.environ.get("LTX_API_URL")
        model_ok = ltx_model_path and Path(ltx_model_path).exists()
        upscaler_path = getattr(settings, "ltx_upscaler_path", None) or os.environ.get("LTX_UPSCALER_PATH")
        lora_path = getattr(settings, "ltx_lora_path", None) or os.environ.get("LTX_LORA_PATH")
        upscaler_ok = not upscaler_path or Path(upscaler_path).exists()
        lora_ok = not lora_path or Path(lora_path).exists()
        api_ok = True
        if ltx_api_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(ltx_api_url.rstrip("/") + "/")
                    api_ok = r.status_code == 200
            except Exception:
                api_ok = False
        if model_ok and upscaler_ok and lora_ok and api_ok:
            ltx_status = "ok"
            parts = ["LTX model path OK"]
            if upscaler_path: parts.append("upscaler OK")
            if lora_path: parts.append("LoRA OK")
            if ltx_api_url: parts.append("API reachable")
            ltx_msg = "; ".join(parts)
        else:
            missing = []
            if not model_ok: missing.append("LTX_MODEL_PATH")
            if not upscaler_ok: missing.append("LTX_UPSCALER_PATH")
            if not lora_ok: missing.append("LTX_LORA_PATH")
            if ltx_api_url and not api_ok: missing.append("LTX_API_URL")
            ltx_msg = "Missing or invalid: " + ", ".join(missing)
    checks.append({
        "name": "ltx_video",
        "status": ltx_status,
        "severity": ltx_severity,
        "message": ltx_msg,
        "fix_steps": ltx_fix,
        "last_checked": datetime.now().isoformat()
    })

    # 10. MCP — optional, disabled by design
    mcp_status = "ok" if not settings.mcp_enabled else "warning"
    mcp_msg = "Disabled by design" if not settings.mcp_enabled else "Enabled"
    checks.append({
        "name": "mcp",
        "status": mcp_status,
        "severity": "optional",
        "message": mcp_msg,
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

    # Calculate stats (optional severity does not affect score)
    blocking_fails = [c for c in checks if c["severity"] == "blocking" and c["status"] == "fail"]
    warning_fails = [c for c in checks if c["severity"] == "warning" and c["status"] not in ("ok",)]
    
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
