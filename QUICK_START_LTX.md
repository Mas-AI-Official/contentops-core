# LTX Video Generation - Quick Setup Guide

## What is LTX?

**LTX (Lightricks)** is an open-source AI video generation model that can create videos from text prompts. It's one of the newest and best open-source video models available.

## Can I Run It on My RTX 4060 Laptop?

**Yes, but with limitations:**
- ✅ **480p resolution** (854×480)
- ✅ **3-5 second clips** max
- ✅ **Distilled/FP8 models** required
- ⚠️ **Slower processing** than high-end GPUs

## Setup Steps

### Option 1: Automatic Setup (Recommended)

```batch
setup_ltx.bat
```

This will:
1. Clone ComfyUI-LTXVideo repository
2. Install dependencies
3. Guide you through model download

### Option 2: Manual Setup

1. **Install ComfyUI-LTXVideo**
   ```batch
   git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git comfyui_ltx
   cd comfyui_ltx
   python -m pip install -r requirements.txt
   ```

2. **Download LTX Models**
   ```batch
   huggingface-cli download Lightricks/ltx-video-distilled --local-dir D:\Ideas\content_factory\models\ltx
   ```

3. **Run ComfyUI with Low VRAM**
   ```batch
   cd comfyui_ltx
   python main.py --lowvram --use-split-cross-attention --disable-smart-memory
   ```

4. **Configure Content Factory**
   
   Edit `backend\.env`:
   ```env
   VIDEO_GEN_PROVIDER=ltx
   LTX_API_URL=http://127.0.0.1:8188
   ```

5. **Verify Connection**
   
   Open Settings page in dashboard → Check "ltx_video" status

## How It Works in the Pipeline

When LTX is enabled:

1. **Script Generated** → Full text script ready
2. **LTX Generates Base Video** → AI creates 480p video from script text (3-5 seconds)
3. **FFmpeg Composites** → Adds:
   - Narration audio
   - Subtitles (burned in)
   - Logo watermark
   - Background music
   - Scales to 1080×1920
4. **Final Video** → Ready for review

## Troubleshooting

### ComfyUI Won't Start
- Check Python version: `python --version` (should be 3.11)
- Install dependencies: `pip install -r requirements.txt`
- Try: `python main.py --lowvram --cpu-vae`

### Out of Memory Errors
- Use **FP8 quantized** model
- Reduce resolution to **480p**
- Reduce clip length to **3 seconds**
- Close other GPU applications
- Use `--cpu-vae` flag

### LTX API Not Responding
- Verify ComfyUI is running: `http://127.0.0.1:8188`
- Check `LTX_API_URL` in `backend\.env`
- Restart backend after changing env vars

### Video Generation Fails
- Check ComfyUI console for errors
- Verify model files are in `models/ltx/`
- Try FFmpeg fallback (set `VIDEO_GEN_PROVIDER=ffmpeg`)

## Performance Tips

1. **Use Distilled Models**: `ltx-video-distilled-fp8`
2. **Batch Process**: Generate multiple clips during off-hours
3. **Monitor VRAM**: Use Task Manager → Performance → GPU
4. **CPU Fallback**: Use `--cpu-vae` if CUDA OOM

## Resources

- [LTX Documentation](https://docs.ltx.video/)
- [ComfyUI LTX Memory Guide](https://deepwiki.com/Lightricks/ComfyUI-LTXVideo/4.3-memory-management)
- [LTX on Hugging Face](https://huggingface.co/Lightricks/ltx-video-distilled)

---

**Ready to generate AI videos locally!** 🎬
