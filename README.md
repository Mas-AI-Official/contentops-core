<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=34&duration=3500&pause=900&color=D4A843&center=true&vCenter=true&width=760&height=50&lines=ContentOps;Autonomous+AI+Media+Agency" alt="ContentOps" />

### 🎬 Trend → Script → Avatar Video → Publish — end-to-end, no human in the loop

**A [MAS-AI Technologies](https://github.com/Mas-AI-Official) product · governed by [Daena](https://daena.mas-ai.co)**

[![Python CI](https://github.com/Mas-AI-Official/contentops-core/actions/workflows/python-ci.yml/badge.svg)](https://github.com/Mas-AI-Official/contentops-core/actions/workflows/python-ci.yml)
[![Python](https://img.shields.io/badge/-Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](#)
[![Remotion](https://img.shields.io/badge/-Remotion-000000?style=flat-square&logo=react&logoColor=61DAFB)](#)
[![License](https://img.shields.io/badge/license-Proprietary-F59E0B?style=flat-square)](#license)
[![MAS-AI](https://img.shields.io/badge/MAS--AI-Official-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/Mas-AI-Official)

</div>

---

# ContentOps — Autonomous AI Media Agency

**MAS-AI Technologies Inc.**

ContentOps is a fully autonomous, multi-tenant AI media agency. It runs the complete content loop:

```
TREND DISCOVERY → VIRAL ANALYSIS → SCRIPT → AVATAR VIDEO → PUBLISH → MONITOR → OPTIMIZE
```

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/Mas-AI-Official/contentops-core.git
cd contentops-core
python -m venv venv
venv\Scripts\pip install -r requirements.txt

# 2. Configure
cp .env.template .env
# Edit .env with your API keys

# 3. Start dashboard
venv\Scripts\python scripts\start_server.py
# Open http://localhost:8080/docs

# 4. Generate content
venv\Scripts\python scripts\run_pipeline.py "Your topic here" --platform tiktok
```

## Architecture

- **Tool Manager** — Token economy controller with VRAM conflict prevention
- **Script Maestro** — 4-stage pipeline: Extract → Angle → Structure → QA
- **Avatar Engine** — Voice generation (Kokoro free / ElevenLabs production)
- **Dashboard API** — FastAPI with 14 endpoints for full system control
- **Multi-Tenant** — Each client gets isolated brand, credentials, and content pipeline

## Multi-Tenant (Agency Model)

Each client is a tenant with their own:
- Brand identity and guidelines
- Avatar and voice configuration
- Content calendar and posting schedule
- Platform credentials
- Analytics tracking

Create a new client:
```bash
curl -X POST http://localhost:8080/api/tenant/create \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"client-001","display_name":"Client Corp","avatar_name":"BotName","niche":"fitness"}'
```

## Tech Stack

| Component | Primary | Fallback |
|---|---|---|
| Script LLM | Ollama (local, free) | Claude API (QA only) |
| Voice TTS | ElevenLabs | Kokoro-82M (free) |
| Video | Remotion (React) | FFmpeg |
| B-Roll | Pexels API (free) | Pixabay |
| Dashboard | FastAPI | - |
| Analytics | Platform APIs | SQLite |

## License

Proprietary — MAS-AI Technologies Inc.
