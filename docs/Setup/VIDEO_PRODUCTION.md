# VIDEO_PRODUCTION.md — Remotion Video Production System

---

## SETUP

```bash
# In D:\contentops\src\video\remotion\
npx create-video@latest
# Select: "Hello World" template
# Install dependencies
npm install

# Additional packages
npm install @remotion/google-fonts @remotion/media-utils
npm install axios pexels

# For rendering
npm install @remotion/renderer
```

---

## TEMPLATE STRUCTURE

Each platform gets its own template component.

### TikTok / Reels Template (9:16, 60s)

```tsx
// src/video/remotion/templates/TikTokShort.tsx
import { Composition, useCurrentFrame, useVideoConfig, Video, Audio, 
         interpolate, spring, Sequence, AbsoluteFill } from 'remotion';
import { AvatarOverlay } from '../components/AvatarOverlay';
import { CaptionBurner } from '../components/CaptionBurner';
import { BRollLayer } from '../components/BRollLayer';
import { HookText } from '../components/HookText';
import { ProgressBar } from '../components/ProgressBar';

interface TikTokProps {
  avatarVideoPath: string;
  brollPaths: string[];
  musicPath: string;
  captions: CaptionWord[];
  hookText: string;
  avatarMode: "corner" | "fullscreen" | "split";
  brandColor: string;
}

export const TikTokShort: React.FC<TikTokProps> = ({
  avatarVideoPath,
  brollPaths,
  musicPath,
  captions,
  hookText,
  avatarMode = "corner",
  brandColor = "#00c8ff"
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  
  return (
    <AbsoluteFill style={{ backgroundColor: "#060810" }}>
      
      {/* Layer 1: B-Roll background */}
      <BRollLayer clips={brollPaths} />
      
      {/* Layer 2: Subtle dark overlay for readability */}
      <AbsoluteFill style={{ backgroundColor: "rgba(0,0,0,0.3)" }} />
      
      {/* Layer 3: Daena Avatar */}
      <AvatarOverlay
        videoSrc={avatarVideoPath}
        mode={avatarMode}
        brandColor={brandColor}
      />
      
      {/* Layer 4: Hook text (first 3 seconds only) */}
      <Sequence from={0} durationInFrames={fps * 3}>
        <HookText text={hookText} brandColor={brandColor} />
      </Sequence>
      
      {/* Layer 5: Captions (full video) */}
      <CaptionBurner words={captions} brandColor={brandColor} />
      
      {/* Layer 6: Progress bar (subtle, increases watch time) */}
      <ProgressBar color={brandColor} />
      
      {/* Audio: Music (background, low volume) */}
      <Audio src={musicPath} volume={0.15} />
      
    </AbsoluteFill>
  );
};
```

---

### CaptionBurner Component (Viral Karaoke Style)

```tsx
// src/video/remotion/components/CaptionBurner.tsx
import { useCurrentFrame, interpolate } from 'remotion';

interface CaptionWord {
  word: string;
  start: number;  // frame number
  end: number;    // frame number
}

export const CaptionBurner: React.FC<{words: CaptionWord[], brandColor: string}> = ({
  words, brandColor
}) => {
  const frame = useCurrentFrame();
  
  // Group words into visible lines (3-4 words per line)
  const currentWordIndex = words.findIndex(w => frame >= w.start && frame <= w.end);
  
  // Show current word group (window of 4 words centered on current)
  const windowStart = Math.max(0, currentWordIndex - 1);
  const windowEnd = Math.min(words.length - 1, windowStart + 3);
  const visibleWords = words.slice(windowStart, windowEnd + 1);
  
  return (
    <div style={{
      position: "absolute",
      bottom: "15%",
      left: "5%",
      right: "5%",
      textAlign: "center"
    }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 6 }}>
        {visibleWords.map((w, i) => {
          const isActive = frame >= w.start && frame <= w.end;
          return (
            <span key={i} style={{
              fontSize: 36,
              fontWeight: 800,
              fontFamily: "Inter, sans-serif",
              color: isActive ? brandColor : "white",
              textShadow: "0 2px 8px rgba(0,0,0,0.9)",
              backgroundColor: isActive ? "rgba(0,200,255,0.15)" : "transparent",
              padding: "2px 4px",
              borderRadius: 4,
              transition: "all 0.1s ease"
            }}>
              {w.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};
```

---

### HookText Component (First 3 seconds — the scroll stopper)

```tsx
// src/video/remotion/components/HookText.tsx
import { useCurrentFrame, spring, useVideoConfig, interpolate } from 'remotion';

export const HookText: React.FC<{text: string, brandColor: string}> = ({text, brandColor}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Punch-in animation
  const scale = spring({ fps, frame, config: { damping: 12, stiffness: 200 } });
  const opacity = interpolate(frame, [fps * 2.5, fps * 3], [1, 0], { extrapolateRight: "clamp" });
  
  return (
    <div style={{
      position: "absolute",
      top: "25%",
      left: "5%",
      right: "5%",
      textAlign: "center",
      transform: `scale(${scale})`,
      opacity
    }}>
      <p style={{
        fontSize: 48,
        fontWeight: 900,
        color: "white",
        textShadow: `0 0 20px ${brandColor}, 0 2px 8px rgba(0,0,0,0.9)`,
        lineHeight: 1.2,
        margin: 0
      }}>
        {text}
      </p>
    </div>
  );
};
```

---

### BRollLayer Component

```tsx
// src/video/remotion/components/BRollLayer.tsx
import { Video, useCurrentFrame, useVideoConfig, OffthreadVideo } from 'remotion';

export const BRollLayer: React.FC<{clips: string[]}> = ({clips}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  
  if (!clips.length) return (
    <div style={{ width: "100%", height: "100%", backgroundColor: "#0a0a1a" }} />
  );
  
  // Cycle through clips, 5s each
  const clipDuration = fps * 5;
  const currentClipIndex = Math.floor(frame / clipDuration) % clips.length;
  
  return (
    <OffthreadVideo
      src={clips[currentClipIndex]}
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
      muted
    />
  );
};
```

---

## CAPTION GENERATION

Convert script to frame-level word timing using audio analysis:

```python
# src/video/caption_generator.py
import whisper
import json

def generate_caption_data(audio_path: str, fps: int = 30) -> list:
    """
    Uses Whisper word-level timestamps to generate Remotion caption data.
    """
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    caption_words = []
    for segment in result["segments"]:
        for word in segment.get("words", []):
            caption_words.append({
                "word": word["word"].strip(),
                "start": int(word["start"] * fps),
                "end": int(word["end"] * fps)
            })
    
    return caption_words
```

---

## RENDER COMMAND

```python
# src/agents/video_composer.py
import subprocess
import json

def render_remotion_video(
    template: str,
    props: dict,
    output_path: str,
    platform: str
) -> str:
    """
    Renders a Remotion composition to MP4.
    """
    specs = {
        "tiktok": {"width": 1080, "height": 1920, "fps": 30},
        "youtube_short": {"width": 1080, "height": 1920, "fps": 30},
        "instagram_reel": {"width": 1080, "height": 1920, "fps": 30},
        "instagram_post": {"width": 1080, "height": 1080, "fps": 30},
        "youtube": {"width": 1920, "height": 1080, "fps": 30},
        "linkedin": {"width": 1920, "height": 1080, "fps": 30},
    }
    
    spec = specs.get(platform, specs["tiktok"])
    props_path = f"/tmp/{template}_props.json"
    
    with open(props_path, "w") as f:
        json.dump(props, f)
    
    cmd = [
        "npx", "remotion", "render",
        f"src/video/remotion/index.ts",
        template,
        output_path,
        f"--props={props_path}",
        f"--width={spec['width']}",
        f"--height={spec['height']}",
        f"--fps={spec['fps']}",
        "--codec=h264",
        "--concurrency=2"  # RTX 4060 — don't over-parallelize
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="src/video/remotion")
    
    if result.returncode != 0:
        raise Exception(f"Remotion render failed: {result.stderr}")
    
    return output_path
```

---

## PEXELS B-ROLL FETCHER

```python
# src/video/broll_fetcher.py
import requests
import os

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]  # Free tier: 200 req/hour

def fetch_broll_clips(visual_keywords: list[str], count: int = 3) -> list[str]:
    """
    Fetches relevant B-roll clips from Pexels (free, no attribution required).
    Downloads to data/broll/ and returns local paths.
    """
    clips = []
    for keyword in visual_keywords[:2]:  # Max 2 queries per video
        response = requests.get(
            f"https://api.pexels.com/videos/search",
            params={"query": keyword, "per_page": count, "orientation": "portrait"},
            headers={"Authorization": PEXELS_API_KEY}
        )
        
        if response.status_code == 200:
            for video in response.json().get("videos", [])[:2]:
                # Get highest quality under 720p (keep file size manageable)
                file_url = next(
                    (vf["link"] for vf in video["video_files"] 
                     if vf.get("height", 0) <= 720 and vf.get("file_type") == "video/mp4"),
                    video["video_files"][0]["link"]
                )
                local_path = download_clip(file_url, keyword)
                clips.append(local_path)
    
    return clips
```

---

## MUSIC SYSTEM

```python
# src/video/music_selector.py
import os
import random

# Royalty-free music library (download once, reuse)
MUSIC_LIBRARY = {
    "high_energy": [
        "data/music/high_energy_tech_01.mp3",
        "data/music/high_energy_beat_02.mp3",
    ],
    "medium": [
        "data/music/medium_ambient_01.mp3",
        "data/music/medium_chill_02.mp3",
    ],
    "reflective": [
        "data/music/soft_piano_01.mp3",
        "data/music/ambient_space_02.mp3",
    ]
}

def select_music(energy_level: str, duration: float) -> str:
    """
    Returns path to appropriate royalty-free music file.
    If library file doesn't match duration, FFmpeg will loop/trim automatically.
    """
    options = MUSIC_LIBRARY.get(energy_level, MUSIC_LIBRARY["medium"])
    return random.choice(options)

# Sources for free music (download scripts in scripts/download_music.py):
# - Free Music Archive: https://freemusicarchive.org (CC licensed)
# - ccMixter: http://ccmixter.org
# - Incompetech: https://incompetech.com (CC BY)
# - Pixabay Music: https://pixabay.com/music (free commercial use)
```
