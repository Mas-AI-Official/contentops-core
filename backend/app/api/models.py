"""
API routes for Ollama model management.
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
from loguru import logger

from app.core.config import settings

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None
    digest: Optional[str] = None


class PullModelRequest(BaseModel):
    model_name: str


class ModelPullStatus(BaseModel):
    model_name: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None


# Track pull progress
_pull_progress = {}


@router.get("/", response_model=List[ModelInfo])
async def list_models():
    """List all available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            models = []
            for model in data.get("models", []):
                size_bytes = model.get("size", 0)
                size_gb = size_bytes / (1024 ** 3) if size_bytes else None
                
                models.append(ModelInfo(
                    name=model.get("name", ""),
                    size=f"{size_gb:.2f} GB" if size_gb else None,
                    modified_at=model.get("modified_at"),
                    digest=model.get("digest", "")[:12] if model.get("digest") else None
                ))
            
            return models
            
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Ollama: {str(e)}")


@router.get("/available")
async def list_available_models():
    """List popular models available for download (including hybrid / MoE)."""
    return {
        "recommended": [
            {
                "name": "llama3.1:8b",
                "description": "Meta's Llama 3.1 8B - Great balance of quality and speed",
                "size": "~4.7 GB",
                "use_case": "Main content generation"
            },
            {
                "name": "llama3.2:3b",
                "description": "Meta's Llama 3.2 3B - Fast for quick tasks",
                "size": "~2 GB",
                "use_case": "Topic generation, quick edits"
            },
            {
                "name": "mistral:7b",
                "description": "Mistral 7B - Excellent reasoning",
                "size": "~4.1 GB",
                "use_case": "Script writing"
            },
            {
                "name": "gemma2:9b",
                "description": "Google's Gemma 2 9B - High quality",
                "size": "~5.4 GB",
                "use_case": "Creative content"
            },
            {
                "name": "phi3:mini",
                "description": "Microsoft Phi-3 Mini - Very fast",
                "size": "~2.3 GB",
                "use_case": "Quick iterations"
            },
            {
                "name": "qwen2:7b",
                "description": "Alibaba Qwen2 7B - Multilingual",
                "size": "~4.4 GB",
                "use_case": "Multi-language content"
            },
        ],
        "hybrid": [
            {
                "name": "minimaxm2.5:latest",
                "description": "MiniMax M2.5 hybrid - Strong quality/speed balance",
                "size": "~8–12 GB",
                "use_case": "Script & topic (set OLLAMA_MODEL or OLLAMA_FAST_MODEL)"
            },
            {
                "name": "glm-5qwen3.5:latest",
                "description": "GLM-5 Qwen 3.5 hybrid - Multimodal / reasoning",
                "size": "varies",
                "use_case": "Script generation, reasoning (OLLAMA_MODEL / OLLAMA_REASONING_MODEL)"
            },
            {
                "name": "qwen2.5:14b-instruct",
                "description": "Qwen 2.5 14B - Default main model",
                "size": "~9 GB",
                "use_case": "Main script generation"
            },
            {
                "name": "qwen2.5:7b-instruct",
                "description": "Qwen 2.5 7B - Fast model",
                "size": "~4.7 GB",
                "use_case": "Topic generation, fast edits"
            },
        ],
        "large": [
            {
                "name": "llama3.1:70b",
                "description": "Meta's Llama 3.1 70B - Highest quality",
                "size": "~40 GB",
                "use_case": "Premium content (requires 48GB+ VRAM)"
            },
            {
                "name": "mixtral:8x7b",
                "description": "Mixtral 8x7B MoE - Very capable",
                "size": "~26 GB",
                "use_case": "Complex scripts"
            },
        ]
    }


@router.post("/pull")
async def pull_model(
    request: PullModelRequest,
    background_tasks: BackgroundTasks
):
    """Start pulling/downloading a model."""
    model_name = request.model_name
    
    # Check if already pulling
    if model_name in _pull_progress and _pull_progress[model_name].get("status") == "pulling":
        return {"message": f"Already pulling {model_name}", "status": "in_progress"}
    
    # Initialize progress
    _pull_progress[model_name] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing download..."
    }
    
    # Start pull in background
    background_tasks.add_task(pull_model_task, model_name)
    
    return {"message": f"Started pulling {model_name}", "status": "started"}


async def pull_model_task(model_name: str):
    """Background task to pull a model."""
    try:
        _pull_progress[model_name] = {
            "status": "pulling",
            "progress": 0,
            "message": "Downloading..."
        }
        
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/pull",
                json={"name": model_name},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            
                            if "completed" in data and "total" in data:
                                progress = (data["completed"] / data["total"]) * 100
                                _pull_progress[model_name] = {
                                    "status": "pulling",
                                    "progress": progress,
                                    "message": data.get("status", "Downloading...")
                                }
                            elif data.get("status") == "success":
                                _pull_progress[model_name] = {
                                    "status": "completed",
                                    "progress": 100,
                                    "message": "Download complete!"
                                }
                            else:
                                _pull_progress[model_name]["message"] = data.get("status", "Processing...")
                                
                        except json.JSONDecodeError:
                            pass
        
        _pull_progress[model_name] = {
            "status": "completed",
            "progress": 100,
            "message": "Model ready!"
        }
        
    except Exception as e:
        logger.error(f"Failed to pull model {model_name}: {e}")
        _pull_progress[model_name] = {
            "status": "failed",
            "progress": 0,
            "message": str(e)
        }


@router.get("/pull/{model_name}/status")
async def get_pull_status(model_name: str):
    """Get the status of a model pull operation."""
    if model_name not in _pull_progress:
        return ModelPullStatus(
            model_name=model_name,
            status="not_started",
            message="No pull operation found"
        )
    
    progress = _pull_progress[model_name]
    return ModelPullStatus(
        model_name=model_name,
        status=progress["status"],
        progress=progress.get("progress"),
        message=progress.get("message")
    )


@router.delete("/{model_name}")
async def delete_model(model_name: str):
    """Delete a model from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{settings.ollama_base_url}/api/delete",
                json={"name": model_name}
            )
            
            if response.status_code == 200:
                return {"message": f"Model {model_name} deleted successfully"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to delete model")
                
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_ltx_model_path():
    """Resolve LTX model directory: explicit path, then MODELS_ROOT/ltx, then config paths."""
    from app.services.ltx_service import ltx_service
    
    candidates = []
    if ltx_service.model_path:
        candidates.append(Path(ltx_service.model_path))
    models_root = os.environ.get("MODELS_ROOT")
    if models_root:
        candidates.append(Path(models_root) / "ltx")
    candidates.append(settings.models_path / "ltx")
    candidates.append(Path(settings.base_path) / "models" / "ltx")
    # Content OPS / repo-relative
    try:
        repo = Path(__file__).resolve().parents[2]
        candidates.append(repo / "models" / "ltx")
        candidates.append(Path("D:/Ideas/MODELS_ROOT") / "ltx")
    except Exception:
        pass
    
    for path in candidates:
        if path and path.exists():
            return path
    return Path(ltx_service.model_path) if ltx_service.model_path else (settings.models_path / "ltx")


@router.get("/ltx")
async def list_ltx_models():
    """List all available LTX-2 models (tries multiple path fallbacks)."""
    from app.services.ltx_service import ltx_service
    
    model_path = _resolve_ltx_model_path()
    if not model_path.exists():
        return {
            "models": [],
            "total": 0,
            "total_size_gb": 0,
            "model_path": str(model_path),
            "message": f"LTX model directory not found. Set LTX_MODEL_PATH or MODELS_ROOT in .env (e.g. MODELS_ROOT=D:\\Ideas\\MODELS_ROOT). VIDEO_GEN_PROVIDER=ltx to use LTX."
        }
    
    models = []
    model_files = list(model_path.glob("*.safetensors"))
    
    for model_file in model_files:
        size_bytes = model_file.stat().st_size
        size_gb = size_bytes / (1024 ** 3)
        
        # Categorize models
        category = "other"
        recommended = False
        description = ""
        
        name_lower = model_file.name.lower()
        
        if "distilled-fp8" in name_lower:
            category = "main"
            recommended = True
            description = "Distilled FP8 - Recommended for RTX 4060 8GB (fastest, lowest VRAM)"
        elif "distilled" in name_lower and "fp8" not in name_lower:
            category = "main"
            description = "Distilled - Good balance of quality and speed"
        elif "dev-fp8" in name_lower:
            category = "main"
            description = "Development FP8 - High quality with FP8 quantization"
        elif "dev" in name_lower:
            category = "main"
            description = "Development - Highest quality (requires more VRAM)"
        elif "upscaler" in name_lower:
            category = "upscaler"
            description = "Spatial upscaler - 2x resolution enhancement"
        elif "temporal" in name_lower:
            category = "upscaler"
            description = "Temporal upscaler - Frame rate enhancement"
        elif "lora" in name_lower or "LoRA" in model_file.name:
            category = "lora"
            if "ic-lora" in name_lower or "IC-LoRA" in model_file.name:
                description = "Image Control LoRA - Control generation with images"
            elif "camera" in name_lower:
                description = "Camera Control LoRA - Control camera movements"
            else:
                description = "LoRA adapter - Fine-tuned model variant"
        
        models.append({
            "name": model_file.name,
            "path": str(model_file),
            "size_gb": round(size_gb, 2),
            "size": f"{size_gb:.2f} GB",
            "category": category,
            "recommended": recommended,
            "description": description
        })
    
    # Sort: recommended first, then by category, then by name
    models.sort(key=lambda x: (
        not x["recommended"],
        {"main": 0, "upscaler": 1, "lora": 2, "other": 3}.get(x["category"], 4),
        x["name"]
    ))
    
    return {
        "models": models,
        "total": len(models),
        "total_size_gb": round(sum(m["size_gb"] for m in models), 2),
        "model_path": str(model_path),
        "message": None if models else f"No .safetensors files in {model_path}. Add LTX-2 checkpoints (e.g. ltx-2-19b-distilled-fp8.safetensors)."
    }


@router.get("/current")
async def get_current_models():
    """Get currently configured models."""
    return {
        "main_model": settings.ollama_model,
        "fast_model": settings.ollama_fast_model,
        "ollama_url": settings.ollama_base_url
    }


@router.post("/test/{model_name}")
async def test_model(model_name: str):
    """Test a model with a simple prompt."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Say 'Hello, I am working!' in exactly 5 words.",
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "model": model_name,
                "status": "working",
                "response": data.get("response", "")[:200],
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration")
            }
            
    except Exception as e:
        logger.error(f"Model test failed: {e}")
        return {
            "model": model_name,
            "status": "failed",
            "error": str(e)
        }


@router.post("/ltx/install")
async def install_ltx_models(background_tasks: BackgroundTasks):
    """Trigger LTX model installation."""
    if "ltx_install" in _pull_progress and _pull_progress["ltx_install"].get("status") == "pulling":
        return {"message": "LTX installation already in progress", "status": "in_progress"}
    
    _pull_progress["ltx_install"] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing LTX download..."
    }
    
    background_tasks.add_task(install_ltx_task)
    return {"message": "Started LTX installation", "status": "started"}


async def install_ltx_task():
    """Background task to run LTX downloader script."""
    import subprocess
    import sys
    from pathlib import Path
    
    try:
        _pull_progress["ltx_install"] = {
            "status": "pulling",
            "progress": 0,
            "message": "Starting download script..."
        }
        
        script_path = settings.base_path / "download_ltx_simple.py"
        if not script_path.exists():
            raise FileNotFoundError(f"Download script not found at {script_path}")
            
        # Run the script and capture output
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output for progress
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            if line:
                line = line.strip()
                if line:
                    logger.info(f"LTX Install: {line}")
                    
                    # Update status based on output
                    if "[DOWNLOAD]" in line:
                        _pull_progress["ltx_install"]["message"] = f"Downloading: {line.split(']')[-1].strip()}"
                    elif "[SUCCESS]" in line:
                         _pull_progress["ltx_install"]["message"] = line
                    elif "[ERROR]" in line:
                         _pull_progress["ltx_install"]["message"] = f"Error: {line}"
        
        if process.returncode == 0:
            _pull_progress["ltx_install"] = {
                "status": "completed",
                "progress": 100,
                "message": "LTX models installed successfully!"
            }
        else:
            raise RuntimeError(f"Installer exited with code {process.returncode}")
            
    except Exception as e:
        logger.error(f"LTX installation failed: {e}")
        _pull_progress["ltx_install"] = {
            "status": "failed",
            "progress": 0,
            "message": str(e)
        }
