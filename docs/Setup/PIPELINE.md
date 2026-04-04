# PIPELINE.md — The Complete ContentOps Pipeline

---

## OVERVIEW

```
[DISCOVER] → [ANALYZE] → [SCRIPT] → [VOICE] → [ANIMATE] → [COMPOSE] → [REVIEW] → [DISTRIBUTE] → [MONITOR] → [OPTIMIZE]
     ↑                                                                                                              |
     └──────────────────────────────── FEEDBACK LOOP (auto, daily) ────────────────────────────────────────────────┘
```

---

## STAGE 1: DISCOVER — Viral Intelligence Gathering

**Agent:** VirAI Scout
**Tools ON:** yt-dlp, Playwright/Selenium, Whisper, Gemini CLI
**Tools OFF after:** All of the above
**Output:** `data/scraped/{topic}/{influencer}/`

### What happens:
1. Load `intelligence/influencer_db.json` for the target niche
2. For each tracked influencer (top 5 per niche):
   - Fetch recent videos via YouTube Data API / TikTok Research API
   - Rank by views, shares, and rewatch rate (proxy: comment velocity)
   - Select top 3 videos from last 30 days
3. Use `yt-dlp` to download video + metadata
4. Run Faster-Whisper locally to transcribe audio → `transcripts/`
5. Use Gemini CLI to analyze video structure:
   - Hook type (question / bold claim / pattern interrupt / relatable / shocking stat)
   - Script structure (does it follow 5-act? where is each act?)
   - Visual style (B-roll heavy / talking head / screenshare / text-only)
   - Timing of key moments (hook, payoff, CTA)
   - Engagement triggers (open loops, identity statements, curiosity gaps)
6. Store analysis in `intelligence/hook_vault.json`

### yt-dlp command pattern:
```bash
yt-dlp --write-info-json --write-thumbnail --no-playlist \
  -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4" \
  --output "data/scraped/{niche}/{influencer}/%(id)s.%(ext)s" \
  {video_url}
```

### Influencer tracking (AI niche — default list):
```json
[
  {"handle": "@aiexplained", "platform": "youtube", "niche": "ai-education"},
  {"handle": "@levelsio", "platform": "twitter", "niche": "indie-founder"},
  {"handle": "@gregisenberg", "platform": "tiktok", "niche": "startup-ideas"},
  {"handle": "@alexhormozi", "platform": "youtube", "niche": "business"},
  {"handle": "@sama", "platform": "twitter", "niche": "ai-leadership"}
]
```
*Update this list weekly based on Method Optimizer recommendations.*

---

## STAGE 2: ANALYZE — Viral Pattern Extraction

**Agent:** VirAI Scout (continued)
**Tools ON:** Ollama (qwen2.5:7b)
**Output:** `intelligence/hook_vault.json` entries

### Pattern analysis prompt (Ollama):
```
Given this transcript and video metadata, analyze:

1. HOOK TYPE: What is the exact opening line/moment? Which category:
   - Shocking stat ("X% of AI startups fail in 6 months")
   - Bold claim ("AI will replace your job—but not how you think")
   - Curiosity gap ("Most people don't know this about GPT-4")
   - Relatable problem ("You've probably noticed AI responses getting worse")
   - Pattern interrupt (visual or audio unexpected element)

2. SCRIPT STRUCTURE: Map each section to timestamps
3. EMOTIONAL TRIGGERS: List all used (identity, fear, curiosity, hope, humor)
4. CALL TO ACTION: Exact phrasing and placement
5. VIRAL SCORE ESTIMATE: 1-10 based on hook strength + emotional density + CTA clarity

Output as JSON.
```

### Hook Vault entry format:
```json
{
  "id": "hook_001",
  "source_url": "https://...",
  "influencer": "@aiexplained",
  "views": 2400000,
  "hook_text": "ChatGPT just quietly deleted a feature most people didn't know existed",
  "hook_type": "curiosity_gap",
  "opening_visual": "screen recording of ChatGPT UI",
  "script_structure": "5-act",
  "emotional_triggers": ["curiosity", "loss_aversion"],
  "cta": "Follow for more hidden AI features",
  "viral_score": 9.2,
  "date_analyzed": "2026-04-04",
  "method_used": "curiosity_gap_product_reveal",
  "niche": "ai-tools"
}
```

---

## STAGE 3: SCRIPT — The Core Production

**Agent:** Script Maestro
**Tools ON:** Ollama (primary), Claude Haiku API (QA only)
**Tools OFF after:** Both
**Output:** `data/scripts/{script_id}.json`

### MANDATORY 4-STAGE SCRIPT PIPELINE

#### S1: EXTRACT (Ollama - fast model)
Pull the single most interesting, useful, or surprising insight from the source material.
Do NOT summarize everything. Extract ONE sharp insight.

Prompt template:
```
Source material: {scraped_content}
Task: Extract the single sharpest, most surprising, or most useful insight from this content.
Rules: One sentence max. Must be something an AI founder or builder would find genuinely valuable.
Output: {"insight": "...", "source_type": "...", "credibility": 1-10}
```

#### S2: ANGLE (Ollama + Hook Vault lookup)
Match the insight to a proven viral angle from the Hook Vault.
Generate 3 hook variants. Score each.

Prompt template:
```
Insight: {insight}
Target audience: AI founders, builders, tech professionals
Platform: {platform}
Hook Vault (top 10 performing hooks in this niche): {hook_vault_sample}

Generate 3 different hook options for this insight using different hook types.
For each: write the opening 2-3 sentences and estimate viral score 1-10.
Output as JSON array.
```

#### S3: STRUCTURE (Ollama - quality model)
Build the full script using 5-Act Structure.
Each act is timed for the target platform.

Prompt template:
```
Insight: {insight}
Hook: {selected_hook}
Platform: {platform} (TikTok = 60s, YouTube Short = 60s, Reel = 30-60s)
Speaker: Daena — AI expert, confident, founder energy, accessible

Write a full voiceover script in 5 acts:
- Act 1 (0-3s): HOOK — Use exactly: "{hook_text}"  
- Act 2 (3-15s): CURIOSITY BUILD — Expand the problem/question
- Act 3 (15-45s): VALUE DELIVERY — Explain, prove, demonstrate
- Act 4 (45-55s): EMOTIONAL PEAK — Relatable moment or identity trigger
- Act 5 (55-60s): CTA — "Follow Daena for more" or "Save this" based on platform

Rules:
- Every sentence must earn its place
- No filler phrases ("So today we're going to talk about...")
- Spoken language only (contractions, natural rhythm)
- One idea per sentence
- End sentences with punchy single words when possible

Output: {acts: [{act: 1, text: "...", duration_estimate: "3s", emotion: "curiosity"},...]}
```

#### S4: QUALITY CHECK (Claude Haiku — runs only if Ollama output passes basic filter)
```
Score this voiceover script on a scale of 1-10 for:
- NARRATIVE COHERENCE: Does it flow as one connected story? (weight: 40%)
- HOOK STRENGTH: Will someone stop scrolling in first 3 seconds? (weight: 30%)
- VALUE DENSITY: Does every sentence contain signal, not noise? (weight: 20%)
- CTA CLARITY: Is the ask clear and natural? (weight: 10%)

Composite score must be ≥ 7.0 to proceed.
If < 7.0, identify the weakest act and output: {"pass": false, "weak_act": N, "fix_suggestion": "..."}
If ≥ 7.0, output: {"pass": true, "score": X.X, "script_approved": true}
```

**If script fails QA: loop back to S2 with a different angle from Hook Vault. Max 3 attempts.**
**If 3 attempts fail: escalate to operator with the issue flagged.**

### Script output format:
```json
{
  "script_id": "script_20260404_001",
  "tenant": "mas-ai",
  "platform": "tiktok",
  "niche": "ai-tools",
  "insight_source": "{url or topic}",
  "hook_type": "curiosity_gap",
  "hook_vault_ref": "hook_001",
  "acts": [...],
  "full_voiceover_text": "...",
  "word_count": 145,
  "estimated_duration": "58s",
  "quality_score": 8.2,
  "production_status": "approved",
  "created_at": "2026-04-04T14:00:00Z",
  "method_tag": "curiosity_gap_product_reveal_v3"
}
```

---

## STAGE 4: VOICE — TTS Generation

**Agent:** Daena Avatar Engine (voice module)
**Tools ON:** Kokoro TTS (test) OR ElevenLabs API (production)
**Tools OFF after:** TTS engine
**Output:** `data/audio/{script_id}.wav`

### Voice decision logic:
```python
if production_mode == "test":
    use_kokoro_tts(script.full_voiceover_text)      # Free, local
elif production_mode == "production":
    use_elevenlabs_api(script.full_voiceover_text)   # $$ — final only
```

### Kokoro TTS (local fallback):
```bash
# pip install kokoro-onnx soundfile
python -c "
from kokoro_onnx import Kokoro
kokoro = Kokoro('kokoro-v0_19.onnx', 'voices.bin')
samples, sample_rate = kokoro.create('{text}', voice='af_bella', speed=1.0, lang='en-us')
import soundfile as sf
sf.write('data/audio/{script_id}.wav', samples, sample_rate)
"
```

### ElevenLabs (production):
```python
from elevenlabs import ElevenLabs
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
audio = client.text_to_speech.convert(
    voice_id=os.environ["DAENA_VOICE_ID"],
    text=script.full_voiceover_text,
    model_id="eleven_turbo_v2_5",
    output_format="wav_44100_128"
)
```

---

## STAGE 5: ANIMATE — Daena Avatar Lip Sync

**Agent:** Daena Avatar Engine (animation module)
**Tools ON:** SadTalker (via Python subprocess) OR MuseTalk
**GPU:** RTX 4060 required
**Tools OFF after:** Avatar engine
**Output:** `data/videos/{script_id}_avatar.mp4`

### Model selection:
```
Speed priority:  MuseTalk (30+ FPS real-time on RTX 4060)
Quality priority: SadTalker with GFPGAN enhancer
Full body:        ComfyUI + AnimateDiff (Phase 2 feature)
```

### SadTalker command:
```bash
python inference.py \
  --driven_audio data/audio/{script_id}.wav \
  --source_image tenants/mas-ai/daena_avatar.png \
  --enhancer gfpgan \
  --preprocess full \
  --still \
  --result_dir data/videos/
```

### Avatar wardrobe system (Phase 2):
- Maintain 5+ Daena avatar images with different outfits/backgrounds
- Select based on content_mood from script metadata:
  - "technical" → dark professional look
  - "casual" → lighter, approachable
  - "urgent" → high contrast, direct
  - "inspiring" → warm tones, upbeat

---

## STAGE 6: COMPOSE — Full Video Assembly

**Agent:** Video Composer
**Tools ON:** Remotion, Pexels API, FFmpeg
**Tools OFF after:** All
**Output:** `data/videos/{script_id}_final.mp4`

### Remotion composition pipeline:
```
1. Load platform template (9:16 / 16:9 / 1:1)
2. Layer: Background (B-roll from Pexels or generated)
3. Layer: Avatar video (SadTalker output, positioned bottom-right corner or full-screen)
4. Layer: Caption burner (auto-generated from script with word-level timing)
5. Layer: Hook text overlay (first 3 seconds — large, bold, high contrast)
6. Layer: Progress bar (optional — increases watch time)
7. Layer: Music track (royalty-free, tempo matched to content energy)
8. Render: Platform-spec MP4
```

### Platform specs:
```
TikTok/Reels:  1080x1920 (9:16), 30fps, max 60s, H.264
YouTube Short: 1080x1920 (9:16), 30fps, max 60s, H.264
LinkedIn:      1920x1080 (16:9), 30fps, max 3min, H.264
Instagram Post: 1080x1080 (1:1), 30fps, max 60s
```

### B-roll sourcing (Pexels API — free):
```python
import requests
def get_broll(query, count=3):
    headers = {"Authorization": os.environ["PEXELS_API_KEY"]}
    r = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page={count}", headers=headers)
    return [v["video_files"][0]["link"] for v in r.json()["videos"]]
```

### Caption format (viral style):
- Word-by-word karaoke style (high engagement)
- Bold font, high contrast, centered or bottom-third
- Highlight current word in accent color (#00c8ff for MAS-AI brand)

### Music selection:
```python
def select_music(content_energy: str, duration: float):
    # content_energy: "high" | "medium" | "reflective"
    # Source: Free Music Archive API (no cost)
    # Fallback: local royalty-free library in data/music/
    # Rules: Tempo matches content energy, no lyrics in first 10s
```

---

## STAGE 7: REVIEW — Quality Gate

**Agent:** Auto-reviewer (Claude Haiku)
**Threshold:** Auto-approve if all scores ≥ threshold, else flag for human
**Output:** Approved → Stage 8. Flagged → Operator notification

### Auto-review checks:
```
[ ] Audio sync with video (Whisper re-transcribe + align check)
[ ] Script QA score ≥ 7.0 (already checked in Stage 3)
[ ] Video duration within platform spec
[ ] No dead air > 0.5s
[ ] Hook text overlay present and readable
[ ] CTA present in final 5 seconds
[ ] Brand elements correct for tenant
```

---

## STAGE 8: DISTRIBUTE — Multi-Platform Publishing

**Agent:** Distribution Engine
**Tools ON:** Platform APIs (only the ones being posted to)
**Tools OFF after:** Platform APIs
**Output:** `data/published/{script_id}_posts.json`

### Optimal posting times (2026 data):
```json
{
  "tiktok": ["07:00", "12:00", "19:00"],
  "instagram": ["08:00", "11:00", "17:00", "21:00"],
  "youtube": ["14:00", "16:00", "20:00"],
  "linkedin": ["08:00", "10:00", "12:00"],
  "twitter": ["08:00", "12:00", "17:00", "21:00"]
}
```
*(All times = audience's local time. Detect from follower demographics.)*

### Post metadata per platform:
```
TikTok:   caption (max 2200 chars), 3-5 hashtags (niche only), trending sound if available
Instagram: caption, 3-5 hashtags, alt text, location tag optional
YouTube:  title (SEO), description (500+ chars), tags, thumbnail
LinkedIn: professional framing, no hashtag spam (max 3), tag relevant people
X/Twitter: thread or single post, 1-2 hashtags, timing matters most
```

---

## STAGE 9: MONITOR — Performance Intelligence

**Agent:** Analytics Hawk
**Tools ON:** Platform analytics APIs (lightweight, polling only)
**Schedule:** Every 6 hours for first 48h, then daily
**Output:** `intelligence/method_scores.json` updates

### Metrics tracked per video:
```json
{
  "video_id": "...",
  "method_tag": "curiosity_gap_product_reveal_v3",
  "platform": "tiktok",
  "metrics": {
    "views": 0,
    "watch_time_pct": 0.0,
    "shares": 0,
    "saves": 0,
    "comments": 0,
    "follows_gained": 0,
    "viral_threshold_hit": false
  },
  "viral_score": 0.0,
  "method_performance": "pending"
}
```

### Viral signal detection:
- Views > 10K in first 6 hours → **HIGH SIGNAL** → immediately analyze and create 3 variations
- Shares/views ratio > 5% → mark method as WINNER → boost production of same method
- Watch time < 40% → mark method as WEAK → reduce production of same method

---

## STAGE 10: OPTIMIZE — Self-Tuning Loop

**Agent:** Method Optimizer
**Tools ON:** Ollama (analysis), Claude Haiku (recommendation generation)
**Schedule:** Daily at 02:00 local time
**Output:** Updated `intelligence/method_scores.json`, `intelligence/influencer_db.json`

### Daily optimization tasks:
1. Score all methods with ≥ 5 data points
2. Rank hooks by composite virality score
3. Identify underperforming methods (score < 5.0)
4. Generate 3 test hypotheses for next week
5. Update influencer tracking list (add rising creators, remove declining)
6. Refresh trend cache for next 7 days
7. Report to operator dashboard

### Method promotion logic:
```
Score ≥ 8.5: PROMOTED — this becomes the default method for 7 days
Score 6-8.5: ACTIVE — mixed with other methods
Score 4-6:   TESTING — 20% of production slots
Score < 4:   RETIRED — archive, do not use for 30 days, then retest
```
