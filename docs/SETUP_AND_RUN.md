# Content Factory - Setup & Run Guide

## 1. Prerequisites
- Python 3.10 or 3.11
- FFmpeg installed and in PATH
- CUDA-capable GPU (recommended for LTX/Whisper)

## 2. Installation
Run the setup script to install dependencies and download models:

```batch
setup.bat
```
Select **Option 1** to setup everything.

## 3. Configuration
1. Copy `.env.example` to `.env` (or let the app generate it).
2. Configure your keys:
   - `HF_TOKEN`: For LTX downloader and HF Router.
   - `OPENAI_API_KEY`: If using MCP/OpenAI.
   - `ELEVENLABS_API_KEY`: If using ElevenLabs TTS.

## 4. Running the App
Start the backend and frontend:

```batch
launch.bat
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

## 5. New Features Guide

### Autopilot Mode
1. Go to **Generator**.
2. Click **Autopilot Mode** toggle at the top.
3. Select a niche.
4. Click **Enable Autopilot**.
   - The system will now automatically generate, render, and publish videos based on the niche's schedule.

### LTX Video Generation
1. Go to **Models**.
2. Click **Install LTX Models** (or run `python download_ltx_simple.py`).
3. In **Generator**, select a topic and generate a script.
4. Select an LTX model (e.g., `ltx-2-19b-distilled-fp8.safetensors`).
5. Click **Generate Full Video**.

### Hugging Face Router (LLM)
1. In `.env`, set:
   ```env
   LLM_PROVIDER=hf_router
   HF_TOKEN=your_token
   HF_ROUTER_MODEL=moonshotai/Kimi-K2-Instruct
   ```
2. The system will now use HF Router for script generation with enhanced reasoning.

### RSS Topic Automation
1. In **Niches**, add RSS feed URLs to your niche.
2. In **Generator**, click the **RSS** button next to the topic input.
3. The system will pull an unused topic from the feeds.

## 6. Troubleshooting
- **Backend fails to start**: Check `data/logs/backend.log`.
- **Database errors**: The system attempts to auto-migrate. If issues persist, rename `data/content_factory.db` to reset.
- **LTX download fails**: Run `python download_ltx_simple.py` manually to see detailed errors.
