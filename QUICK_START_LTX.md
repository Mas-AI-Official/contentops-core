# LTX Video Generation - Quick Setup Guide

## What is LTX-2?

**LTX-2 (Lightricks)** is the official open-source AI video generation model. It's the first DiT-based audio-video foundation model with synchronized audio/video, high fidelity, and production-ready outputs.

**Official Repository**: https://github.com/Lightricks/LTX-2

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

Choose option **1** for direct Python API (fastest) or **2** for ComfyUI API.

### Option 2A: Direct Python API (Recommended - Faster)

1. **Install LTX-2 Python Package**
   ```batch
   cd D:\Ideas\content_factory
   call venv\Scripts\activate.bat
   pip install git+https://github.com/Lightricks/LTX-2.git#subdirectory=packages/ltx-core
   pip install git+https://github.com/Lightricks/LTX-2.git#subdirectory=packages/ltx-pipelines
   ```

2. **Download LTX-2 Models** (from HuggingFace)
   ```batch
   huggingface-cli download Lightricks/ltx-2 --local-dir D:\Ideas\content_factory\models\ltx
   ```
   
   **For 8GB VRAM, download these specific files:**
   - `ltx-2-19b-distilled-fp8.safetensors` (main model - REQUIRED)
   - `ltx-2-spatial-upscaler-x2-1.0.safetensors` (upscaler - REQUIRED)
   - `ltx-2-19b-distilled-lora-384.safetensors` (LoRA - REQUIRED)

3. **Configure Content Factory**
   
   Edit `backend\.env`:
   ```env
   VIDEO_GEN_PROVIDER=ltx
   LTX_MODEL_PATH=D:/Ideas/content_factory/models/ltx
   LTX_USE_FP8=true
   ```

### Option 2B: ComfyUI API (Alternative)

1. **Install ComfyUI-LTXVideo**
   ```batch
   git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git comfyui_ltx
   cd comfyui_ltx
   python -m pip install -r requirements.txt
   ```

2. **Download Models** (same as Option 2A)

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

When LTX-2 is enabled:

1. **Script Generated** → Full text script ready
2. **LTX-2 Generates Base Video** → 
   - Uses `DistilledPipeline` (fastest, 8 steps)
   - FP8 quantization for 8GB VRAM
   - AI creates 480p video from script text (3-5 seconds)
3. **FFmpeg Composites** → Adds:
   - Narration audio
   - Subtitles (burned in)
   - Logo watermark
   - Background music
   - Scales to 1080×1920
4. **Final Video** → Ready for review

**Mode Selection:**
- **Direct Python API** (preferred): Faster, no HTTP overhead
- **ComfyUI API** (fallback): If Python package not installed

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

- [LTX-2 Official GitHub](https://github.com/Lightricks/LTX-2)
- [LTX-2 on Hugging Face](https://huggingface.co/Lightricks/ltx-2)
- [LTX Documentation](https://docs.ltx.video/)
- [ComfyUI LTX Memory Guide](https://deepwiki.com/Lightricks/ComfyUI-LTXVideo/4.3-memory-management)

---

**Ready to generate AI videos locally!** 🎬
