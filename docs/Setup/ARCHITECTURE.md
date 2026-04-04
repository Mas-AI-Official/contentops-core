# ARCHITECTURE.md — Technical System Architecture

---

## SYSTEM ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTENTOPS SYSTEM                                    │
│                                                                               │
│  ┌──────────────┐   ┌──────────────────────────────────────────────────┐     │
│  │  OPERATOR    │   │              AGENT LAYER                          │     │
│  │  DASHBOARD   │◄──┤                                                   │     │
│  │  :8080       │   │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │     │
│  │              │   │  │ VirAI    │  │ Script   │  │ Daena Avatar │   │     │
│  │  • Queue     │   │  │ Scout    │  │ Maestro  │  │ Engine       │   │     │
│  │  • Analytics │   │  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │     │
│  │  • Methods   │   │       │              │               │            │     │
│  │  • Idea Drop │   │  ┌────▼─────┐  ┌────▼─────┐  ┌──────▼───────┐   │     │
│  └──────────────┘   │  │ Hook     │  │ Quality  │  │ Video        │   │     │
│                      │  │ Vault DB │  │ Gate QA  │  │ Composer     │   │     │
│                      │  └──────────┘  └──────────┘  └──────┬───────┘   │     │
│                      │                                       │            │     │
│                      │  ┌──────────┐  ┌──────────┐  ┌──────▼───────┐   │     │
│                      │  │Analytics │  │ Method   │  │ Distribution │   │     │
│                      │  │ Hawk     │  │Optimizer │  │ Engine       │   │     │
│                      │  └──────────┘  └──────────┘  └──────────────┘   │     │
│                      │                                                   │     │
│                      │  ┌─────────────────────────────────────────┐     │     │
│                      │  │           TOOL MANAGER                   │     │     │
│                      │  │  (controls all service activation)       │     │     │
│                      │  └─────────────────────────────────────────┘     │     │
│                      └──────────────────────────────────────────────────┘     │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                          COMPUTE LAYER                                 │   │
│  │                                                                        │   │
│  │  LOCAL (Free)                          CLOUD API ($)                  │   │
│  │  ├── Ollama (qwen2.5, gemma4:31b)      ├── Claude Haiku (QA gates)   │   │
│  │  ├── Whisper / Faster-Whisper          ├── ElevenLabs TTS (prod)      │   │
│  │  ├── SadTalker / MuseTalk (GPU)        ├── Pexels API (free)          │   │
│  │  ├── Kokoro TTS (CPU)                  ├── YouTube Data API (free)    │   │
│  │  ├── Remotion (Node.js)               ├── Platform APIs (free)        │   │
│  │  └── FFmpeg                            └── Gemini CLI (free tier)     │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                          DATA LAYER                                    │   │
│  │  SQLite DB (analytics, posts, methods)                                │   │
│  │  JSON files (hook_vault, method_scores, influencer_db, trend_cache)   │   │
│  │  File system (scraped/, transcripts/, scripts/, audio/, videos/)      │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## DATA FLOW

```
1. DISCOVER
   yt-dlp → raw_video
   raw_video → Faster-Whisper → transcript
   transcript + metadata → Gemini CLI → viral_pattern
   viral_pattern → hook_vault.json

2. SCRIPT
   hook_vault + trend → Ollama (S1) → insight
   insight → Ollama (S2) → hook_variants[3]
   best_hook + insight → Ollama (S3) → script_draft
   script_draft → Claude Haiku (S4) → quality_score
   if score >= 7.0 → approved_script
   else → retry with next hook variant

3. PRODUCE
   approved_script.text → Kokoro/ElevenLabs → audio.wav
   audio.wav + daena.png → SadTalker/MuseTalk → avatar.mp4
   avatar.mp4 + broll[] + music + captions → Remotion → final.mp4

4. PUBLISH
   final.mp4 + metadata → Platform APIs → post_id
   post_id → database → tracking started

5. MONITOR
   post_id → Platform Analytics API (polling) → metrics
   metrics → virality_score calculation → method_scores.json update
   if viral_signal → create_variations()

6. OPTIMIZE
   method_scores → ranking → promote/retire decisions
   new_hypotheses → update production queue
   influencer_db → refresh with new rising creators
```

---

## ORCHESTRATION: HOW CLAUDE CODE MANAGES THIS

Claude Code acts as the director. It:
1. Reads this CLAUDE.md file at session start
2. Checks BUILD_SEQUENCE.md for current position
3. Builds the next unchecked component
4. Verifies with a real test
5. Uses Codex CLI for repetitive code
6. Uses Gemini CLI for research tasks
7. Uses Ollama for local inference
8. Uses Claude API only for complex reasoning (QA gates, architecture)

### Cross-tool orchestration pattern:
```python
# How Claude Code orchestrates the other AI tools

class ContentOpsDirector:
    
    async def run_discovery(self, niche: str):
        # Use Gemini CLI (not Claude) for research
        subprocess.run(f'gemini -p "find top 5 {niche} influencers on TikTok and YouTube 2026" > intelligence/discovery.json')
        
        # Use Codex for boilerplate (save Claude tokens)
        subprocess.run('codex "Parse discovery.json and return only creators with >100K followers"')
        
        # Use Ollama locally for pattern analysis
        ollama_client.chat(model="qwen2.5:7b", messages=[{"role":"user","content":pattern_prompt}])
    
    async def run_scripting(self, source: str, platform: str):
        # Use Ollama for all draft generation (free)
        script = await script_maestro.create_script(source, platform)
        
        # Only call Claude Haiku for final QA (paid, minimal)
        if script.needs_qa_check:
            score = await claude_haiku_qa(script)
    
    async def run_production(self, script, mode="test"):
        # Use local tools only (GPU compute, no API cost)
        audio = avatar_engine.generate_voice(script, mode)
        avatar = avatar_engine.animate(audio, outfit=script.mood)
        video = video_composer.compose(avatar, script, platform)
```

---

## SECURITY CONSIDERATIONS

```
API Keys:
- All keys in .env (gitignored)
- Never hardcode in source files
- Rotate ElevenLabs key monthly (most sensitive)

Platform Accounts:
- Use dedicated Daena accounts (not personal)
- OAuth tokens stored in credentials/ (gitignored)
- Rate limit all platform API calls

Content Safety:
- All scripts reviewed by quality gate before production
- No generated content posted without passing score ≥ 7.0
- Brand guidelines enforced at tenant level

Data:
- Scraped content stored locally only
- No PII in database
- Logs rotated after 30 days
```

---

## SCALE CONSIDERATIONS (When We Add Tenants)

Current: 1 tenant, ~30 videos/month
With 5 tenants: ~150 videos/month

Bottlenecks at scale:
1. **GPU** — SadTalker/MuseTalk can only run one video at a time on RTX 4060. At 5 tenants, need to queue and run overnight. Or add cloud GPU render slot.
2. **ElevenLabs** — Cost scales linearly. At 150 videos, ~$25/month. Acceptable.
3. **Storage** — Each final video ~200MB. 150 videos = 30GB/month. Need external storage after 6 months.
4. **Platform API rate limits** — Each platform has daily limits. Spread posting throughout day.

Solutions:
- Batch production during off-peak hours (02:00–06:00)
- Cloud GPU fallback for production peaks (GCP credits we have)
- S3/GCP Storage for final videos (GCP credits)
- Platform API pooling across tenant accounts
