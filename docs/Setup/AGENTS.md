# AGENTS.md — ContentOps Agent Team

---

## AGENT ROSTER

### 1. VirAI Scout
**File:** `src/agents/virai_scout.py`
**Role:** Intelligence Gathering & Viral Pattern Analysis
**Tools:** yt-dlp, Playwright, Whisper, Gemini CLI
**Trigger:** Scheduled daily at 03:00 OR on-demand `scout {topic}`
**Output:** Hook Vault entries + influencer performance data

```python
class VirAIScout:
    """
    Scrapes and analyzes viral content from tracked influencers.
    Uses Gemini CLI for video analysis (saves Claude tokens).
    Falls back to Ollama if Gemini unavailable.
    """
    
    async def run(self, niche: str, influencers: list):
        tool_manager.activate(["yt-dlp", "whisper", "gemini-cli"])
        try:
            videos = await self.fetch_top_videos(influencers)
            transcripts = await self.transcribe_all(videos)
            patterns = await self.analyze_viral_patterns(transcripts)
            self.update_hook_vault(patterns)
        finally:
            tool_manager.deactivate(["yt-dlp", "whisper", "gemini-cli"])
```

**Gemini CLI analysis command:**
```bash
gemini -p "Analyze this YouTube video transcript and extract: 
1. Hook type and opening line
2. Script structure map with timestamps  
3. Viral triggers used
4. What makes this likely to go viral

Transcript: {transcript}" \
--model gemini-2.0-flash-exp
```

---

### 2. Script Maestro
**File:** `src/agents/script_maestro.py`
**Role:** Story-Driven Script Generation
**Tools:** Ollama (primary), Claude Haiku API (QA gate only)
**Trigger:** On-demand OR post-Scout automatically
**Output:** Approved script JSON

```python
class ScriptMaestro:
    """
    4-stage script pipeline. Never outputs raw scraped content as a script.
    Runs S1-S3 entirely local (Ollama). Calls Claude API only for S4 QA.
    """
    
    async def create_script(self, source_material: str, platform: str) -> Script:
        insight = await self.extract_insight(source_material)      # Ollama
        hooks = await self.generate_hook_variants(insight)          # Ollama + Hook Vault
        script_draft = await self.build_5act_structure(insight, hooks[0], platform)  # Ollama
        qa_result = await self.quality_check(script_draft)          # Claude Haiku
        
        if not qa_result.passed:
            return await self.retry_with_new_angle(insight, hooks[1:], platform)
        return script_draft
```

---

### 3. Daena Avatar Engine
**File:** `src/agents/avatar_engine.py`
**Role:** Voice Generation + Lip Sync Animation
**Tools:** Kokoro TTS (test) / ElevenLabs API (prod), SadTalker / MuseTalk
**Trigger:** Post-Script-Approval
**Output:** `{script_id}_avatar.mp4`

```python
class AvatarEngine:
    """
    Handles full Daena avatar production:
    - Voice: ElevenLabs (production) or Kokoro (testing)
    - Lip sync: MuseTalk (speed) or SadTalker (quality)
    - Selects outfit image based on content_mood
    """
    
    async def produce(self, script: Script, mode: str = "test") -> str:
        tool_manager.activate(["tts", "gpu-avatar"])
        try:
            audio_path = await self.generate_voice(script, mode)
            avatar_image = self.select_outfit(script.mood)
            video_path = await self.animate_avatar(audio_path, avatar_image)
            return video_path
        finally:
            tool_manager.deactivate(["tts", "gpu-avatar"])
```

**MuseTalk setup (RTX 4060 compatible):**
```bash
git clone https://github.com/TMElyralab/MuseTalk
cd MuseTalk
pip install -r requirements.txt
# Run inference:
python -m scripts.inference --unet_model_path models/musetalkV15/unet.pth \
  --audio_path data/audio/{script_id}.wav \
  --video_path tenants/mas-ai/daena_avatar.png \
  --output_path data/videos/{script_id}_avatar.mp4
```

---

### 4. Video Composer
**File:** `src/agents/video_composer.py`
**Role:** Full Video Assembly via Remotion
**Tools:** Remotion (Node.js), Pexels API, FFmpeg
**Trigger:** Post-Avatar-Production
**Output:** Platform-ready MP4

```python
class VideoComposer:
    """
    Orchestrates Remotion to build final video.
    Fetches B-roll from Pexels (free).
    Auto-generates captions with word-level timing.
    Selects music from royalty-free library.
    """
    
    async def compose(self, script: Script, avatar_video: str, platform: str) -> str:
        tool_manager.activate(["remotion", "pexels-api", "ffmpeg"])
        try:
            broll = await self.fetch_broll(script.visual_keywords)
            music = self.select_music(script.energy_level, script.duration)
            captions = self.generate_caption_data(script)
            
            # Write Remotion props file
            props = {
                "platform": platform,
                "avatarVideoPath": avatar_video,
                "brollPaths": broll,
                "musicPath": music,
                "captions": captions,
                "hookText": script.acts[0].text,
                "brandColor": "#00c8ff"
            }
            
            # Trigger Remotion render
            video_path = await self.render_remotion(platform, props)
            return video_path
        finally:
            tool_manager.deactivate(["remotion", "pexels-api", "ffmpeg"])
```

---

### 5. Distribution Engine
**File:** `src/agents/distributor.py`
**Role:** Multi-Platform Publishing
**Tools:** Platform APIs (only activated at post time)
**Trigger:** Scheduled OR immediate post-production

```python
class DistributionEngine:
    """
    Posts to all configured platforms for the tenant.
    Uses platform-specific metadata formatting.
    Respects optimal posting time windows.
    Implements rate limiting and retry logic.
    """
    
    def schedule_posts(self, video: Video, tenant: str, platforms: list):
        for platform in platforms:
            optimal_time = self.get_optimal_time(platform, tenant)
            metadata = self.format_metadata(video, platform, tenant)
            self.scheduler.add_job(
                func=self.post_to_platform,
                trigger="date",
                run_date=optimal_time,
                args=[platform, video, metadata]
            )
```

---

### 6. Analytics Hawk
**File:** `src/agents/analytics_hawk.py`
**Role:** Performance Data Collection + Viral Signal Detection
**Tools:** Platform Analytics APIs (read-only)
**Schedule:** Polling every 6h for first 48h, then daily

```python
class AnalyticsHawk:
    """
    Monitors performance metrics for all published posts.
    Detects viral signals (>10K views in 6h).
    Tags each post with the method used for performance attribution.
    Feeds data to Method Optimizer.
    """
    
    async def collect_metrics(self, post_id: str, platform: str):
        # Lightweight polling — no heavy processing in this agent
        raw_metrics = await self.fetch_platform_metrics(post_id, platform)
        normalized = self.normalize_metrics(raw_metrics)
        self.update_method_scores(post_id, normalized)
        
        if self.is_viral_signal(normalized):
            await self.escalate_viral_signal(post_id, normalized)
```

---

### 7. Method Optimizer
**File:** `src/agents/method_optimizer.py`
**Role:** Self-Tuning Performance Loop
**Tools:** Ollama + Claude Haiku (weekly deep analysis)
**Schedule:** Daily 02:00

```python
class MethodOptimizer:
    """
    The self-improvement brain.
    Scores all methods with enough data.
    Promotes winners, retires losers.
    Generates new test hypotheses.
    Updates Hook Vault and influencer tracking.
    """
    
    def daily_optimization(self):
        scores = self.score_all_methods()
        self.promote_winners(scores)
        self.retire_underperformers(scores)
        hypotheses = self.generate_test_hypotheses(scores)
        self.update_production_queue(hypotheses)
        self.generate_daily_report()
```

---

### 8. Tool Manager
**File:** `src/agents/tool_manager.py`
**Role:** Token Economy + Service Activation
**CRITICAL — Every other agent calls this before starting and after finishing**

```python
class ToolManager:
    """
    Central control for all service activation/deactivation.
    Tracks which tools are running, their estimated cost per minute,
    and enforces the rule: only activate what you need right now.
    """
    
    TOOLS = {
        "yt-dlp": {"type": "local", "cost_per_min": 0, "startup_sec": 1},
        "whisper": {"type": "local-gpu", "cost_per_min": 0, "startup_sec": 5},
        "gemini-cli": {"type": "api", "cost_per_1k_tokens": 0.001, "startup_sec": 2},
        "ollama": {"type": "local-gpu", "cost_per_min": 0, "startup_sec": 8},
        "claude-haiku": {"type": "api", "cost_per_1k_tokens": 0.0008, "startup_sec": 2},
        "tts-kokoro": {"type": "local-cpu", "cost_per_min": 0, "startup_sec": 3},
        "tts-elevenlabs": {"type": "api", "cost_per_char": 0.0003, "startup_sec": 1},
        "gpu-avatar": {"type": "local-gpu", "cost_per_min": 0, "startup_sec": 15},
        "remotion": {"type": "local-cpu", "cost_per_min": 0, "startup_sec": 10},
        "pexels-api": {"type": "api-free", "cost_per_request": 0, "startup_sec": 0},
        "ffmpeg": {"type": "local-cpu", "cost_per_min": 0, "startup_sec": 0},
        "social-apis": {"type": "api", "cost_per_post": 0, "startup_sec": 2},
        "analytics": {"type": "api", "cost_per_call": 0, "startup_sec": 1},
    }
    
    def activate(self, tools: list[str]):
        for tool in tools:
            self._start_service(tool)
            self.log_activation(tool)
    
    def deactivate(self, tools: list[str]):
        for tool in tools:
            self._stop_service(tool)
            self.log_deactivation(tool)
    
    def status(self) -> dict:
        return {t: "running" if self._is_running(t) else "idle" for t in self.TOOLS}
    
    def estimated_cost(self, pipeline_stage: str) -> float:
        # Returns estimated API cost for this pipeline stage
        ...
```

---

### 9. Dashboard API
**File:** `src/api/dashboard.py`
**Role:** Operator interface — the single view Masoud opens
**Tech:** FastAPI backend + React frontend
**Port:** 8080

#### Dashboard panels:
1. **Today's Queue** — Scripts ready, videos rendering, posts scheduled
2. **Live Analytics** — Views, engagement, trending posts
3. **Method Scoreboard** — Which hooks and methods are winning
4. **Influencer Radar** — What top creators are doing right now
5. **Idea Drop** — Text box to give the agents a new topic or direction
6. **Agent Status** — Which agents are running, which tools are ON/OFF
7. **Tenant Selector** — Switch between MAS-AI and other client tenants
8. **Viral Alerts** — Real-time notification when a post hits viral threshold
