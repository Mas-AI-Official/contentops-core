# AVATAR_SYSTEM.md — Daena Digital Human Engine

---

## OVERVIEW

Daena is MAS-AI's AI influencer. The goal is a realistic digital human that:
- Moves and talks like a real human (not a static talking head)
- Has different outfits/backgrounds based on content mood
- Can be produced 100% locally on the RTX 4060 (no cloud GPU cost)
- Scales from simple lip-sync today to full body animation in Phase 2

---

## PHASE 1: LIP SYNC TALKING HEAD (Build Now)

### Primary: MuseTalk (Tencent — Apache 2.0)
**Why:** 30+ FPS real-time on RTX 4060. Best quality/speed ratio for production use.

```bash
# Install
git clone https://github.com/TMElyralab/MuseTalk.git
cd MuseTalk
conda create -n musetalk python=3.10
conda activate musetalk
pip install -r requirements.txt

# Download models
python scripts/download_weights.py

# Run inference
python -m scripts.realtime_inference \
  --unet_model_path models/musetalkV15/unet.pth \
  --vae_model_path models/sd-vae-ft-mse \
  --audio_path {audio.wav} \
  --video_path {daena_portrait.png} \
  --bbox_shift 0 \
  --output_path {output.mp4}
```

### Fallback: SadTalker (CVPR 2023 — MIT License)
**Why:** More expressive head motion. Better for emotional content.

```bash
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio
pip install -r requirements.txt

python inference.py \
  --driven_audio {audio.wav} \
  --source_image {daena_portrait.png} \
  --enhancer gfpgan \
  --preprocess full \
  --still \
  --result_dir data/videos/
```

### Quality Enhancer: GFPGAN
Applied post-generation to upscale face quality. Included in SadTalker pipeline.

---

## PHASE 2: FULL BODY ANIMATION (Next Phase)

### Option A: LivePortrait (Kuaishou — MIT License)
Full portrait animation with body motion, not just face.

```bash
git clone https://github.com/KwaiVGI/LivePortrait.git
cd LivePortrait
pip install -r requirements.txt
# Download checkpoints from HuggingFace
python inference.py --source assets/examples/imgs/daena.png \
  --driving assets/examples/driving/d14.mp4 \
  --output output/daena_animated.mp4
```

### Option B: LiveAvatar (HuggingFace — Apache 2.0)
Streaming real-time avatar with infinite length. Requires Wan 2.2-S2V-14B base.
*Good for interactive use cases. Heavy download (~25GB). Skip for now, revisit Q3 2026.*

### Option C: ComfyUI + AnimateDiff (for full scene generation)
When you want Daena in a full environment (office, studio, outdoor).
Use img2vid workflows with Daena's consistent face via IP-Adapter.

---

## DAENA AVATAR ASSET SET

### Required images (create 5 variants):
```
tenants/mas-ai/avatars/
├── daena_professional_dark.png    # Dark background, tech professional
├── daena_casual_light.png         # Light background, approachable
├── daena_urgent_high_contrast.png # High contrast, direct address
├── daena_inspiring_warm.png       # Warm tones, uplifting content
└── daena_neutral.png              # Default — used when mood undetected
```

### Image specifications:
- Resolution: 512x512 minimum, 1024x1024 preferred
- Format: PNG with clean background OR subtle background
- Face: Front-facing, neutral expression, good lighting
- No accessories that would look unnatural in animation

### Outfit/mood mapping:
```python
MOOD_TO_AVATAR = {
    "technical": "daena_professional_dark.png",
    "casual": "daena_casual_light.png",
    "urgent": "daena_urgent_high_contrast.png",
    "inspiring": "daena_inspiring_warm.png",
    "educational": "daena_professional_dark.png",
    "controversial": "daena_urgent_high_contrast.png",
    "humorous": "daena_casual_light.png",
    "default": "daena_neutral.png"
}
```

---

## VOICE SYSTEM

### ElevenLabs (Production)
```python
import os
from elevenlabs import ElevenLabs

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

def generate_voice(text: str, script_id: str) -> str:
    audio = client.text_to_speech.convert(
        voice_id=os.environ["DAENA_VOICE_ID"],  # Store in .env
        text=text,
        model_id="eleven_turbo_v2_5",           # Fastest + cheapest
        output_format="wav_44100_128",
        voice_settings={
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.20,
            "use_speaker_boost": True
        }
    )
    output_path = f"data/audio/{script_id}.wav"
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return output_path
```

### Kokoro TTS (Free Local Fallback)
```python
# pip install kokoro-onnx soundfile numpy
from kokoro_onnx import Kokoro
import soundfile as sf

def generate_voice_free(text: str, script_id: str) -> str:
    kokoro = Kokoro("models/kokoro-v0_19.onnx", "models/voices.bin")
    samples, sample_rate = kokoro.create(
        text,
        voice="af_bella",  # Best English female voice
        speed=1.05,          # Slightly faster = more energy
        lang="en-us"
    )
    output_path = f"data/audio/{script_id}.wav"
    sf.write(output_path, samples, sample_rate)
    return output_path
```

### Voice decision:
```python
def get_voice_generator(mode: str):
    if mode == "test" or os.environ.get("BUDGET_MODE") == "true":
        return generate_voice_free
    return generate_voice
```

---

## VIDEO POSITIONING — Where Daena Appears

### Corner mode (current avatar behavior):
```
Daena appears bottom-right, small circular crop, B-roll fills background
Good for: Educational content, data reveals
```

### Full screen mode:
```
Daena fills the frame, subtle background behind her
Good for: Opinion pieces, direct-to-camera style
```

### Split mode:
```
Left half: Daena talking | Right half: Content being discussed (screen, data)
Good for: Technical breakdowns, comparisons
```

### Remotion component:
```tsx
const AvatarOverlay: React.FC<{
  videoSrc: string;
  mode: "corner" | "fullscreen" | "split";
  brandColor: string;
}> = ({ videoSrc, mode, brandColor }) => {
  const styles = {
    corner: { width: "30%", position: "absolute", bottom: "5%", right: "2%" },
    fullscreen: { width: "100%", height: "100%" },
    split: { width: "50%", position: "absolute", left: 0 }
  };
  
  return (
    <div style={styles[mode]}>
      {mode === "corner" && (
        <div style={{ borderRadius: "50%", overflow: "hidden", border: `3px solid ${brandColor}` }}>
          <Video src={videoSrc} />
        </div>
      )}
      {mode !== "corner" && <Video src={videoSrc} />}
    </div>
  );
};
```

---

## FUTURE: TRUE HUMAN-LIKE DAENA (Phase 3)

### What's needed for fully human Daena:
1. **Consistent character model** — Use DreamBooth or IP-Adapter to create a stable character
2. **Full body generation** — Wan2.2 + AnimateDiff for full-body motion
3. **Clothing variation** — FLUX ControlNet for wardrobe changes on same character
4. **Gesture sync** — Audio-driven body gesture models (still emerging)
5. **Scene generation** — Stable Diffusion XL for backgrounds behind Daena

### Recommended local stack for Phase 3:
- ComfyUI (workflow orchestration)
- FLUX.1-dev (high quality image generation)
- AnimateDiff (motion application)
- IP-Adapter (character consistency)
- ControlNet (pose control)
- Wan2.2-S2V-14B (video generation base — 31GB VRAM required → need cloud for this)

### Cloud option when Phase 3 ready:
- Replicate.com API ($0.002/sec) — use GCP credits
- Fal.ai (fast, cheap inference)
- Keep local as fallback for Phase 1/2

---

## RTX 4060 VRAM BUDGET

```
Model                  VRAM Usage    Status
─────────────────────────────────────────────
MuseTalk               ~4GB          ✅ Fits
SadTalker + GFPGAN     ~6GB          ✅ Fits
Kokoro TTS (CPU)       0GB GPU       ✅ CPU
Whisper Large v2       ~4GB          ✅ Fits
Qwen2.5-7B (Ollama)    ~8GB          ✅ Fits (q4_0)
Gemma 4 31B (Ollama)   ~20GB         ⚠️  May need offload
LiveAvatar + Wan2.2    ~40GB+        ❌ Cloud only
─────────────────────────────────────────────
RTX 4060 has 8GB VRAM — run models sequentially, not simultaneously
```

**Important:** Never run MuseTalk + Ollama simultaneously. Tool Manager handles this.
