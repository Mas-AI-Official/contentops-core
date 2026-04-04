# VIDEO_EDITING_SKILL.md — ContentOps Creative Production Skill
> Living document. Update regularly with new tools, techniques, and creative insights.
> Last updated: 2026-04-04

---

## MISSION
Produce scroll-stopping, cinematic social media videos that look like they were made by a professional production team — not a bot. Every video must earn the viewer's attention in 3 seconds and hold it through the last frame.

---

## CURRENT TOOL STACK

### Video Assembly
| Tool | Role | Status |
|---|---|---|
| FFmpeg 7.1 | Primary compositor — B-roll montage, caption burn, audio mux, avatar overlay | Active |
| Remotion (React) | Programmatic video templates with animations | Planned Phase 2 |
| ComfyUI | AI video generation (AnimateDiff, Wan2.2) | Planned Phase 3 |

### Voice / Audio
| Tool | Role | Status |
|---|---|---|
| Kokoro-82M | Free local TTS, good quality, CPU | Active (default) |
| ElevenLabs | Premium TTS, voice cloning — Matilda voice ID: XrExE9yKIg1WjnnlVkGX | Active (production) |
| F5-TTS | Free local voice cloning from reference audio | Planned |
| CosyVoice 2 | Alibaba's zero-shot voice cloning | Research |

### Avatar / Face
| Tool | Role | Status |
|---|---|---|
| Avatar overlay via colorkey | Daena composited onto B-roll using FFmpeg colorkey filter | Active |
| MuseTalk | Lip sync, 30fps on RTX 4060 | Planned Phase 2 |
| SadTalker | Lip sync + head motion | Fallback |
| LivePortrait | Full body animation | Planned Phase 3 |

### B-Roll / Visuals
| Tool | Role | Status |
|---|---|---|
| Pexels API | Free video clips, no attribution needed | Active |
| Pixabay API | Free fallback B-roll | Planned |
| FLUX.1 / SDXL | AI-generated background images | Research |

### Captions / Text
| Tool | Role | Status |
|---|---|---|
| faster-whisper | Word-level timestamp generation | Active |
| FFmpeg drawtext | Text overlays and hook text | Active |
| FFmpeg subtitles | SRT caption burning | Active |

---

## DAENA PERSONA IN VIDEO

```
Name:           Daena
Title:          VP of MAS-AI Technologies
Energy:         Luxury executive — poised, authoritative, magnetic
Personality:    Confident, precise, data-driven, slightly witty
Aesthetic:      Blazer / structured top, dark professional tones
Brand Colors:   Dark slate #0F1419 | Gold #D4A843 | Teal #2DD4BF
Voice:          Warm, clear, authoritative (ElevenLabs Matilda)
Positioning:    The AI exec who explains complex tech with clarity and style
```

Daena is not a chatbot mascot. She is the face and voice of MAS-AI content. She presents with founder energy — the kind of person who walks into a boardroom and commands attention without raising her voice. Every frame she appears in should feel intentional, polished, and premium.

---

## AVATAR OVERLAY TECHNIQUE (colorkey compositing)

### How it works
Daena's avatar is recorded or rendered against a white background. FFmpeg's `colorkey` filter removes the white, making it transparent, then overlays Daena onto the B-roll video layer.

### Pipeline
```
Source MP4 (white bg) → crop → colorkey → scale → overlay on B-roll
```

### Key parameters
- **Colorkey filter:** `colorkey=0xFFFFFF:0.22:0.10`
  - `0xFFFFFF` = white background color to remove
  - `0.22` = similarity threshold (how close to white counts as transparent)
  - `0.10` = blend (edge softness to avoid harsh cutout edges)
- **Crop coordinates** (for "clear social" layout): `crop=290:300:430:600`
  - Extracts Daena's upper body from the full frame
- **Dynamic sizing:**
  - Big (55% of frame height) — used during HOOK and EMOTIONAL PEAK acts
  - Medium (40% of frame height) — used during CURIOSITY and CTA acts
  - Small (30% of frame height) — used during VALUE DELIVERY act (B-roll takes focus)

### Avatar source priority
1. **Clear social MP4** (white background) — best quality, easiest colorkey
2. **Cutout WebM** (pre-keyed alpha) — if available
3. **Transparent WebM** — direct alpha channel, no colorkey needed

### Fallback
If colorkey produces artifacts (hair edges, clothing bleed), fall back to **PiP rectangular overlay** — a clean rectangular picture-in-picture box in the corner. Less cinematic but always reliable.

---

## 5-ACT VISUAL DIRECTION

Each act in the script maps to a specific visual composition. This creates rhythm and keeps the viewer's eye engaged through intentional variation.

| Act | Duration | Daena Size | Daena Position | B-Roll | Text Overlay |
|---|---|---|---|---|---|
| 1 HOOK | 0-3s | Large (55%) | Center or center-right | Dimmed (50% overlay) | Bold glass-card hook text |
| 2 CURIOSITY | 3-15s | Medium (40%) | Off-center (rule of thirds) | Visible, thematic | Subtle keyword reinforcement |
| 3 VALUE | 15-45s | Small (30%) | Bottom-right corner | Full visibility, illustrative | Data/stats if relevant |
| 4 EMOTIONAL | 45-55s | Large (55%) | Centered | Dimmed or matched mood | Minimal — let Daena carry it |
| 5 CTA | 55-60s | Medium (40%) | Centered | Subtle or branded bg | CTA text (follow/save/share) |

### Rationale
- **Acts 1 and 4** use large Daena to create personal connection at the moments that matter most (first impression and emotional peak).
- **Act 3** shrinks Daena to let B-roll visuals illustrate the value being delivered.
- **Acts 2 and 5** use medium Daena as transitional — enough presence without dominating.

---

## CREATIVE PRINCIPLES (V1 LESSONS)

### What went WRONG in V1 (never repeat):
1. Raw scraped data dumped as text on screen
2. Static images with invisible Ken Burns (1.08x zoom)
3. Text WAS the content instead of supporting voiceover
4. No transitions between scenes (hard cuts)
5. PowerPoint aesthetic — no motion, no energy

### What makes viral videos work:
1. **First 3 seconds** — visual + audio hook simultaneously
2. **Avatar talks, visuals illustrate** — text reinforces keywords only
3. **Everything moves** — Ken Burns at 1.3x+, text slides in, elements pulse
4. **Pacing matches energy** — fast cuts for exciting, slower for educational
5. **Music bed sets mood** — low volume, tempo-matched, no lyrics in first 10s
6. **Clean captions** — 3 words at a time, bottom third, highlight current word
7. **Professional color** — dark backgrounds, accent colors on key words

---

## SUBTITLE STYLE GUIDE

### Current FFmpeg ASS style:
```
FontName=Arial
FontSize=18
Bold=1
PrimaryColour=&H00FFFFFF (white)
OutlineColour=&H00000000 (black)
Outline=2
Shadow=1
BackColour=&H80000000 (semi-transparent black)
BorderStyle=4 (opaque box)
Alignment=2 (bottom center)
MarginV=180
```

### Rules:
- 3 words per subtitle chunk (TikTok-style rapid flow)
- Bottom third of screen (never above 60% mark)
- White on dark — always readable against any B-roll
- No ALL CAPS unless it's a single emphasis word
- Key numbers/stats in accent color if possible

### Keyword highlighting (future — Remotion):
- Current word: brand color (#00c8ff) background highlight
- Numbers/stats: gold (#D4A843) color
- Product names: bold + glow effect

---

## B-ROLL SELECTION GUIDE

### Keywords that produce good Pexels results:
```
"futuristic technology" — clean tech B-roll
"coding programming" — screens with code
"startup office" — modern workspace
"artificial intelligence" — abstract tech visuals
"data analytics dashboard" — screen recordings
"business meeting" — professional context
"city skyline night" — establishing shots
```

### Rules:
- Always PORTRAIT orientation for TikTok/Reels/Shorts
- Prefer VIDEO clips (not images) — movement is essential
- Each clip: 5-8 seconds, then transition
- Loop clips if needed to fill audio duration
- Dark overlay (30-50% opacity) for text readability

---

## AUDIO SYNC RULES

### Critical:
- Video duration = audio duration + 2 seconds (pad end)
- Never use `-shortest` — always let audio play fully
- 0.5s silence padding at start (thumbnail frame)
- 1s fade-out at end
- Music bed: -15dB under voice (barely audible)

### Voice pacing:
- Target: 2.5 words/second for conversational
- 3.0 words/second for energetic/TikTok
- 2.0 words/second for educational/LinkedIn

---

## COMPOSITION LAYERS (bottom to top)

```
Layer 1: B-roll video (full screen, scaled + cropped to spec)
Layer 2: Dark overlay (30% opacity black — readability)
Layer 3: Daena avatar (colorkey overlay, dynamic sizing — ACTIVE)
Layer 4: Hook text overlay (first 3 seconds only — glass card effect)
Layer 5: Captions (bottom third — word-by-word)
Layer 6: Progress bar (subtle, bottom edge — increases watch time)
Layer 7: Brand watermark (small, top-right — optional)
```

---

## PLATFORM-SPECIFIC SPECS

| Platform | Resolution | FPS | Duration | Format |
|---|---|---|---|---|
| TikTok | 1080x1920 | 30 | 15-60s | H.264 MP4 |
| Instagram Reel | 1080x1920 | 30 | 15-60s | H.264 MP4 |
| YouTube Short | 1080x1920 | 30 | 15-60s | H.264 MP4 |
| LinkedIn | 1920x1080 | 30 | 30-180s | H.264 MP4 |
| X/Twitter | 1080x1920 | 30 | 15-60s | H.264 MP4 |

---

## CONTINUOUS IMPROVEMENT LOOP

### Weekly creative research (automated by VirAI Scout):
1. Scan top 5 viral videos in niche
2. Analyze: pacing, transitions, text style, hook technique
3. Update this skill doc with new techniques
4. A/B test new approaches via Method Optimizer

### Monthly tool evaluation:
1. Check for new TTS models (HuggingFace trending)
2. Check for new video generation models
3. Compare output quality vs current stack
4. Upgrade if measurable improvement

### Tools to watch:
- **Wan 2.2** — Video generation from text/image (requires cloud GPU)
- **CogVideo X** — Open source video generation
- **Hailuo AI** — Fast video generation API
- **Kling AI** — Lip sync + full body
- **HeyGen** — API for avatar videos (paid)
- **Synthesia** — Enterprise avatar platform

### Metrics that matter (from Method Optimizer):
- Completion rate > 70% → video holds attention
- Share rate > 3% → content resonates emotionally
- Save rate > 2% → content has utility value
- Rewatch rate > 15% → hook/payoff loop works

---

## FFMPEG RECIPES

### Ken Burns on image (aggressive):
```bash
ffmpeg -loop 1 -i image.jpg -vf "scale=1920:1080,zoompan=z='min(zoom+0.0015,1.35)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920" -t 5 -c:v libx264 out.mp4
```

### Crossfade transition between clips:
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex "xfade=transition=fade:duration=0.5:offset=4.5" out.mp4
```

### Glass card text effect:
```bash
drawtext=text='Your text':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:box=1:boxcolor=black@0.4:boxborderw=12:x=(w-text_w)/2:y=h*0.35
```

### Audio fade out (last 2 seconds):
```bash
ffmpeg -i input.mp4 -af "afade=t=out:st=58:d=2" -c:v copy output.mp4
```

### Loop B-roll to match audio duration:
```bash
ffmpeg -stream_loop -1 -i broll.mp4 -i audio.wav -c:v libx264 -c:a aac -shortest -movflags +faststart out.mp4
```

### Colorkey avatar overlay (Daena on B-roll):
```bash
ffmpeg -i broll.mp4 -i daena_avatar.mp4 -filter_complex \
  "[1:v]crop=290:300:430:600,colorkey=0xFFFFFF:0.22:0.10,scale=-1:h*0.55[avatar]; \
   [0:v][avatar]overlay=W-w-40:H-h-40[out]" \
  -map "[out]" -map 0:a -c:v libx264 -c:a aac output.mp4
```

### Crop + scale + colorkey chain (reusable avatar prep):
```bash
# Step 1: Crop Daena from full frame
# Step 2: Remove white background via colorkey
# Step 3: Scale to target height (55% = hook, 40% = mid, 30% = value)
[1:v]crop=290:300:430:600,colorkey=0xFFFFFF:0.22:0.10,scale=-1:ih*0.55[avatar_large];
[1:v]crop=290:300:430:600,colorkey=0xFFFFFF:0.22:0.10,scale=-1:ih*0.40[avatar_medium];
[1:v]crop=290:300:430:600,colorkey=0xFFFFFF:0.22:0.10,scale=-1:ih*0.30[avatar_small];
```

### Full composition example (B-roll + avatar + captions):
```bash
ffmpeg -stream_loop -1 -i broll.mp4 -i daena_avatar.mp4 -i voice.wav \
  -filter_complex \
  "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg]; \
   [bg]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.3:t=fill[bg_dim]; \
   [1:v]crop=290:300:430:600,colorkey=0xFFFFFF:0.22:0.10,scale=-1:1056[avatar]; \
   [bg_dim][avatar]overlay=W-w-40:H-h-40[composed]" \
  -map "[composed]" -map 2:a \
  -c:v libx264 -preset medium -crf 18 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output.mp4
```

---

## SKILL EVOLUTION LOG

| Date | Change | Impact |
|---|---|---|
| 2026-04-04 | Initial skill document created | Baseline |
| 2026-04-04 | Fixed B-roll sync (loop to audio length) | Voiceover no longer cut off |
| 2026-04-04 | Fixed subtitle style (18px, bottom third, 3 words) | Cleaner captions |
| 2026-04-04 | Avatar colorkey overlay working (Daena on B-roll) | Daena composited live onto B-roll via FFmpeg colorkey |
| 2026-04-04 | Persona system created | Daena identity locked as VP of MAS-AI, luxury executive energy |
| 2026-04-04 | faster-whisper installed for captions | Word-level timestamps for TikTok-style subtitle sync |
| 2026-04-04 | 5-Act visual direction system added | Dynamic avatar sizing per act for visual rhythm |
| 2026-04-04 | ElevenLabs Matilda voice ID documented | Production voice locked: XrExE9yKIg1WjnnlVkGX |
| | | |

> This document is updated after every production run and creative research session.
> The Method Optimizer feeds performance data back into creative decisions.
