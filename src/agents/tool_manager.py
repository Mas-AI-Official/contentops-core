"""
Tool Manager — Token Economy & Service Activation Controller.
Every agent activates/deactivates tools through this manager.
Prevents VRAM conflicts on RTX 4060 (8GB).
"""
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


logger = logging.getLogger("contentops.tool_manager")


@dataclass
class ToolConfig:
    name: str
    type: str  # local-cpu, local-gpu, api, api-free
    vram_mb: int = 0
    cost_per_use: float = 0.0
    cost_unit: str = "free"
    health_check_cmd: Optional[str] = None


@dataclass
class ToolSession:
    tool: str
    activated_at: datetime = field(default_factory=datetime.now)


class ToolManager:
    """Central controller for all service activation/deactivation."""

    TOOLS: dict[str, ToolConfig] = {
        "ollama": ToolConfig("ollama", "local-gpu", vram_mb=4096, health_check_cmd="curl -s http://localhost:11434/api/version"),
        "whisper": ToolConfig("whisper", "local-gpu", vram_mb=4096),
        "musetalk": ToolConfig("musetalk", "local-gpu", vram_mb=4096),
        "sadtalker": ToolConfig("sadtalker", "local-gpu", vram_mb=6144),
        "kokoro-tts": ToolConfig("kokoro-tts", "local-cpu"),
        "elevenlabs": ToolConfig("elevenlabs", "api", cost_per_use=0.15, cost_unit="per_video"),
        "remotion": ToolConfig("remotion", "local-cpu"),
        "ffmpeg": ToolConfig("ffmpeg", "local-cpu"),
        "pexels": ToolConfig("pexels", "api-free"),
        "yt-dlp": ToolConfig("yt-dlp", "local-cpu"),
        "claude-haiku": ToolConfig("claude-haiku", "api", cost_per_use=0.02, cost_unit="per_script"),
        "gemini-cli": ToolConfig("gemini-cli", "api-free"),
        "social-apis": ToolConfig("social-apis", "api-free"),
        "analytics": ToolConfig("analytics", "api-free"),
    }

    PIPELINE_COSTS = {
        "discover": {"tools": ["yt-dlp", "whisper", "gemini-cli"], "api_cost": 0.002, "time_min": 5},
        "script": {"tools": ["ollama", "claude-haiku"], "api_cost": 0.02, "time_min": 3},
        "voice_test": {"tools": ["kokoro-tts"], "api_cost": 0.0, "time_min": 1},
        "voice_prod": {"tools": ["elevenlabs"], "api_cost": 0.15, "time_min": 1},
        "animate": {"tools": ["musetalk"], "api_cost": 0.0, "time_min": 10},
        "compose": {"tools": ["remotion", "pexels", "ffmpeg"], "api_cost": 0.0, "time_min": 5},
        "distribute": {"tools": ["social-apis"], "api_cost": 0.0, "time_min": 1},
        "monitor": {"tools": ["analytics"], "api_cost": 0.0, "time_min": 1},
    }

    MAX_VRAM_MB = 8000  # RTX 4060

    def __init__(self):
        self._active: dict[str, ToolSession] = {}
        self._total_api_cost: float = 0.0

    def activate(self, tools: list[str]) -> list[str]:
        """Activate tools. Auto-deactivates conflicting GPU tools if needed."""
        activated = []
        for tool_name in tools:
            config = self.TOOLS.get(tool_name)
            if not config:
                logger.warning(f"Unknown tool: {tool_name}")
                continue
            if tool_name in self._active:
                continue

            # Check VRAM conflicts
            if config.vram_mb > 0:
                current_gpu_vram = sum(
                    self.TOOLS[t].vram_mb for t in self._active if self.TOOLS[t].vram_mb > 0
                )
                if current_gpu_vram + config.vram_mb > self.MAX_VRAM_MB:
                    # Deactivate current GPU tools to make room
                    gpu_active = [t for t in self._active if self.TOOLS[t].vram_mb > 0]
                    for gt in gpu_active:
                        self.deactivate([gt])
                    logger.info(f"Freed GPU VRAM by deactivating: {gpu_active}")

            self._active[tool_name] = ToolSession(tool=tool_name)
            activated.append(tool_name)
            logger.info(f"Activated: {tool_name}")

        return activated

    def deactivate(self, tools: list[str]) -> list[str]:
        """Deactivate tools."""
        deactivated = []
        for tool_name in tools:
            if tool_name in self._active:
                del self._active[tool_name]
                deactivated.append(tool_name)
                logger.info(f"Deactivated: {tool_name}")
        return deactivated

    def deactivate_all(self):
        """Deactivate all tools. Called between pipeline stages."""
        all_active = list(self._active.keys())
        self.deactivate(all_active)

    def get_available_vram(self) -> int:
        """Returns available VRAM in MB."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
        # Estimate based on active tools
        used = sum(self.TOOLS[t].vram_mb for t in self._active if self.TOOLS[t].vram_mb > 0)
        return self.MAX_VRAM_MB - used

    def status(self) -> dict:
        """Full status report."""
        return {
            "active": list(self._active.keys()),
            "idle": [t for t in self.TOOLS if t not in self._active],
            "gpu_vram_used_mb": sum(self.TOOLS[t].vram_mb for t in self._active if self.TOOLS[t].vram_mb > 0),
            "gpu_vram_available_mb": self.get_available_vram(),
            "total_api_cost_session": round(self._total_api_cost, 4),
        }

    def estimate_pipeline_cost(self, stages: list[str]) -> dict:
        """Estimate cost before running a full pipeline."""
        total_cost = sum(self.PIPELINE_COSTS.get(s, {}).get("api_cost", 0) for s in stages)
        total_time = sum(self.PIPELINE_COSTS.get(s, {}).get("time_min", 0) for s in stages)
        return {
            "estimated_api_cost": f"${total_cost:.3f}",
            "estimated_time_min": total_time,
            "stages": stages,
        }

    def log_api_cost(self, tool: str, cost: float):
        """Track cumulative API spending."""
        self._total_api_cost += cost
        logger.info(f"API cost logged: {tool} = ${cost:.4f} (session total: ${self._total_api_cost:.4f})")

    def for_stage(self, stage: str) -> list[str]:
        """Get tool list for a pipeline stage."""
        stage_config = self.PIPELINE_COSTS.get(stage)
        if not stage_config:
            return []
        return stage_config["tools"]


# Singleton
tool_manager = ToolManager()


if __name__ == "__main__":
    import json
    tm = ToolManager()
    print("=== ContentOps Tool Manager ===")
    print(json.dumps(tm.status(), indent=2))
    print("\nPipeline cost estimate (full run):")
    print(json.dumps(tm.estimate_pipeline_cost(["discover", "script", "voice_prod", "animate", "compose", "distribute"]), indent=2))
