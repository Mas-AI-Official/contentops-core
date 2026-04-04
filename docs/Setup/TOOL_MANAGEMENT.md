# MULTI_TENANT.md — Agency Architecture

---

## TENANT MODEL

ContentOps supports multiple independent clients (tenants). Each tenant has:
- Their own brand identity, avatar, voice, niche
- Separate credentials for social platforms
- Isolated content pipeline and calendar
- Dedicated analytics tracking
- **Brand lane enforcement** — agents never mix content across tenants

### Tenant structure:
```
tenants/
├── mas-ai/
│   ├── config.json          ← Tenant settings
│   ├── brand.json           ← Brand guidelines
│   ├── avatars/             ← Avatar image set
│   ├── credentials.env      ← Platform API keys (gitignored)
│   ├── influencers.json     ← Tracked influencers for this niche
│   └── calendar.json        ← Content calendar
└── client-001/
    ├── config.json
    └── ...
```

### MAS-AI tenant config (mas-ai/config.json):
```json
{
  "tenant_id": "mas-ai",
  "display_name": "MAS-AI Technologies / Daena",
  "avatar_name": "Daena",
  "niche": "ai-tech-startups",
  "platforms": ["tiktok", "instagram", "youtube", "linkedin", "twitter"],
  "content_mix": {
    "educational": 0.40,
    "opinion": 0.25,
    "behind_scenes": 0.20,
    "news_commentary": 0.10,
    "community": 0.05
  },
  "posting_schedule": {
    "tiktok": {"days": ["tue","thu","fri","sat"], "times": ["07:00","12:00","19:00"]},
    "instagram": {"days": ["mon","wed","fri"], "times": ["08:00","11:00","17:00"]},
    "youtube": {"days": ["mon","wed","fri"], "times": ["14:00","20:00"]},
    "linkedin": {"days": ["tue","wed","thu"], "times": ["08:00","10:00"]},
    "twitter": {"days": ["mon","tue","wed","thu","fri"], "times": ["08:00","12:00","17:00"]}
  },
  "voice_id": "${DAENA_VOICE_ID}",
  "brand_color": "#00c8ff",
  "brand_accent": "#d4a853",
  "default_avatar": "daena_professional_dark.png",
  "cta_style": "follow_and_save",
  "active": true
}
```

---

# TOOL_MANAGEMENT.md — Token Economy

---

## THE PROBLEM

Running all agents and tools 24/7 = massive token burn + slow execution + VRAM conflicts.
Solution: Strict on/off management with pipeline-stage awareness.

## TOKEN BUDGET TARGETS

```
Per video production (target):
  Script generation:    ~$0.02  (mostly Ollama = free, QA = Haiku)
  Voice (ElevenLabs):   ~$0.15  (150 words × $0.0003/char × avg 5 chars/word)
  Video composition:    ~$0.00  (Remotion = local)
  Analytics calls:      ~$0.00  (platform APIs = free)
  ─────────────────────────────
  Total per video:      ~$0.17

Monthly target (30 videos):
  Local compute:        ~$0.00
  ElevenLabs:          ~$5.00  (30 × $0.17)
  Claude API:          ~$1.00  (QA gates only)
  Pexels/other APIs:   ~$0.00  (free tiers)
  ─────────────────────────────
  Total monthly:       ~$6-10
```

## TOOL STATE MACHINE

```
                    ┌─────────────────────────────────┐
                    │         IDLE STATE               │
                    │  Only running: Analytics Hawk    │
                    │  (polling every 6h, no GPU)      │
                    └─────────────┬───────────────────┘
                                  │ trigger
           ┌──────────────────────┼──────────────────────┐
           ↓                      ↓                       ↓
    SCOUTING STATE         SCRIPTING STATE         PRODUCING STATE
    ─────────────          ───────────────         ───────────────
    ON: yt-dlp             ON: ollama              ON: gpu-avatar
        whisper                claude-haiku             tts-engine
        gemini-cli             (for QA only)            remotion
                                                        pexels-api
                                                        ffmpeg
    OFF: all else          OFF: all else           OFF: all else

           ↓                      ↓                       ↓
    DISTRIBUTING STATE     MONITORING STATE        OPTIMIZING STATE
    ──────────────────     ────────────────        ────────────────
    ON: social-apis        ON: analytics           ON: ollama
                                                       (analysis)
    OFF: all else          OFF: all else           OFF: all else
```

## ToolManager Implementation

```python
# src/agents/tool_manager.py
import subprocess
import psutil
import logging
from typing import Optional
from dataclasses import dataclass

@dataclass
class ToolConfig:
    name: str
    type: str  # local, local-gpu, api, api-free
    start_cmd: Optional[str]
    stop_cmd: Optional[str]
    health_check: Optional[str]
    cost_estimate: str  # human readable

class ToolManager:
    TOOL_CONFIGS = {
        "ollama": ToolConfig(
            name="ollama",
            type="local-gpu",
            start_cmd="ollama serve",
            stop_cmd="pkill ollama",
            health_check="curl -s http://localhost:11434/api/version",
            cost_estimate="$0/use (local)"
        ),
        "whisper": ToolConfig(
            name="whisper",
            type="local-gpu",
            start_cmd=None,  # Python import, no daemon
            stop_cmd=None,
            health_check=None,
            cost_estimate="$0/use (local)"
        ),
        "sadtalker": ToolConfig(
            name="sadtalker",
            type="local-gpu",
            start_cmd=None,  # Python subprocess per call
            stop_cmd=None,
            health_check=None,
            cost_estimate="$0/use (local GPU)"
        ),
        "remotion": ToolConfig(
            name="remotion",
            type="local-cpu",
            start_cmd=None,  # CLI call per render
            stop_cmd=None,
            health_check=None,
            cost_estimate="$0/use (local)"
        ),
    }
    
    def __init__(self):
        self.active_tools = set()
        self.logger = logging.getLogger("ToolManager")
    
    def activate(self, tools: list[str]):
        """Activate tools, checking for VRAM conflicts."""
        gpu_tools = [t for t in tools if self.TOOL_CONFIGS.get(t, {}).get("type") == "local-gpu"]
        
        # Check VRAM availability before activating GPU tools
        if gpu_tools:
            available_vram = self._get_available_vram()
            required_vram = sum(self._estimate_vram(t) for t in gpu_tools)
            
            if required_vram > available_vram:
                # Deactivate conflicting GPU tools first
                for active in list(self.active_tools):
                    if active in self.TOOL_CONFIGS and self.TOOL_CONFIGS[active].get("type") == "local-gpu":
                        self.deactivate([active])
        
        for tool in tools:
            if tool not in self.active_tools:
                config = self.TOOL_CONFIGS.get(tool)
                if config and config.start_cmd:
                    subprocess.Popen(config.start_cmd, shell=True)
                self.active_tools.add(tool)
                self.logger.info(f"✅ Tool activated: {tool}")
    
    def deactivate(self, tools: list[str]):
        for tool in tools:
            if tool in self.active_tools:
                config = self.TOOL_CONFIGS.get(tool)
                if config and config.stop_cmd:
                    subprocess.run(config.stop_cmd, shell=True)
                self.active_tools.discard(tool)
                self.logger.info(f"🔴 Tool deactivated: {tool}")
    
    def _get_available_vram(self) -> int:
        """Returns available VRAM in MB."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                capture_output=True, text=True
            )
            return int(result.stdout.strip())
        except:
            return 8000  # Assume 8GB if can't detect
    
    def _estimate_vram(self, tool: str) -> int:
        """Estimated VRAM requirements in MB."""
        VRAM_REQUIREMENTS = {
            "ollama": 4096,    # qwen2.5:7b
            "sadtalker": 6144,
            "musetalk": 4096,
            "whisper": 4096,
        }
        return VRAM_REQUIREMENTS.get(tool, 0)
    
    def status(self) -> dict:
        return {
            "active": list(self.active_tools),
            "idle": [t for t in self.TOOL_CONFIGS if t not in self.active_tools],
            "vram_available_mb": self._get_available_vram()
        }
    
    def estimate_pipeline_cost(self, stages: list[str]) -> dict:
        """Estimate cost before running a pipeline."""
        estimates = {
            "discover": {"api_cost": "$0.002", "time_min": 5},
            "script": {"api_cost": "$0.02", "time_min": 3},
            "voice_test": {"api_cost": "$0.00", "time_min": 1},
            "voice_prod": {"api_cost": "$0.15", "time_min": 1},
            "animate": {"api_cost": "$0.00", "time_min": 10},
            "compose": {"api_cost": "$0.00", "time_min": 5},
            "distribute": {"api_cost": "$0.00", "time_min": 1},
        }
        total_api = sum(float(estimates[s]["api_cost"].replace("$","")) for s in stages if s in estimates)
        total_time = sum(estimates[s]["time_min"] for s in stages if s in estimates)
        return {"estimated_api_cost": f"${total_api:.3f}", "estimated_time_min": total_time}
```

## CODEX CLI INTEGRATION

Use Codex for repetitive code tasks to save Claude tokens:

```python
# When to use Codex vs Claude:
# Codex: Writing API wrappers, boilerplate, file operations, simple transforms
# Claude: Architecture decisions, complex reasoning, creative writing, QA

def use_codex(task: str, context: str = "") -> str:
    """
    Offload repetitive coding tasks to Codex CLI.
    Much cheaper than Claude for mechanical tasks.
    """
    cmd = f'codex --model gpt-4o-mini "{task}"'
    if context:
        # Write context to temp file, pass as input
        with open("/tmp/codex_context.txt", "w") as f:
            f.write(context)
        cmd += " < /tmp/codex_context.txt"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

# Examples of Codex tasks:
# use_codex("Write a Python function to download a video from a Pexels API response JSON")
# use_codex("Create a FastAPI route handler for POST /api/scripts/generate")
# use_codex("Write the ffmpeg command to trim a video to 60 seconds and output MP4")
```
