# Deliverables: Diagnostics, Paths, Voice, Review Mode, LTX

## Changed files

### Backend
- **app/core/config.py** – Project/model paths from env (PROJECT_ROOT, MODELS_ROOT); default base_path=`D:\Ideas\contentops-core`, models_path=`D:\Ideas\MODELS_ROOT`; `database_url` via `get_database_url()`; `generation_mode` (review_first | auto_publish); `ltx_upscaler_path`, `ltx_lora_path`.
- **app/db/database.py** – Uses `settings.get_database_url()`.
- **app/db/migrations.py** – Migration for `generation_mode` on `niches`.
- **fix_db_schema.py** – Uses `settings.get_database_url()`.
- **app/api/diagnostics.py** – Severity levels: ok, optional, warning, blocking. Optional providers (HF Router, ElevenLabs, LTX, MCP) show “inactive optional” / “configured optional fallback” when not active; only active provider is blocking. LTX check verifies model path, upscaler, lora, API when VIDEO_GEN_PROVIDER=ltx.
- **app/api/settings.py** – `generation_mode` in SettingsResponse and get_settings.
- **app/models/niche.py** – `generation_mode` on Niche (optional, overrides global).
- **app/models/voice.py** – New: VoiceProfile, NicheVoiceRule, AccountVoiceRule, SceneSpeakerMap, VoiceStyle.
- **app/models/__init__.py** – Exports voice models.

### Frontend
- No changes required for path display: Settings page already shows `settings.base_path` and `settings.models_path` from API (now correct by default or via PROJECT_ROOT / MODELS_ROOT).

## Smoke test steps

1. **Paths**
   - Set in backend `.env`: `PROJECT_ROOT=D:\Ideas\contentops-core`, `MODELS_ROOT=D:\Ideas\MODELS_ROOT` (or rely on defaults).
   - Start backend; open Settings.
   - Confirm **Project Path** = `D:\Ideas\contentops-core`, **Models Path** = `D:\Ideas\MODELS_ROOT`.

2. **Diagnostics**
   - GET `/api/diagnostics/pipeline`.
   - With LLM_PROVIDER=ollama: **hf_router** severity=optional, message like “Configured optional fallback” or “Inactive optional”.
   - With TTS_PROVIDER=xtts: **elevenlabs** severity=optional, message like “Optional fallback only”.
   - With VIDEO_GEN_PROVIDER≠ltx: **ltx_video** severity=optional, message “Installed but inactive”.
   - MCP: severity=optional, “Disabled by design”.
   - Only active providers (ollama, xtts when xtts, etc.) are blocking; health score not reduced by optional inactive items.

3. **Voices**
   - GET `/api/voice/voices`: list includes Daena and any `.wav` from MODELS_ROOT/xtts/voices (when MODELS_ROOT set).
   - Generator: voice dropdown shows those voices; selection is sent as `voice_id`/`voice_name` and used for TTS.

4. **Draft preview and manual approve**
   - Create a job (Generator → generate video); wait until status `ready_for_review`.
   - Queue: open job row; use View to see video preview.
   - Use “Approve & Publish” or “Approve only” (existing flow).
   - Confirm draft shows video/audio/script (existing Queue/Generator behavior).

5. **LTX**
   - Set `VIDEO_GEN_PROVIDER=ltx`, `LTX_MODEL_PATH` (or MODELS_ROOT/ltx), optionally `LTX_UPSCALER_PATH`, `LTX_LORA_PATH`, `LTX_API_URL`.
   - GET `/api/diagnostics/pipeline`: **ltx_video** severity=blocking when active; message confirms model/upscaler/lora/API.
   - LTX remains scene generator; FFmpeg/Remotion used for composition (existing pipeline).

## Optional / follow-up

- **Review Studio** – Queue page already has preview and approve; extend with caption/edit, rating, comment, deny/regenerate as needed.
- **Voice routing** – Use VoiceProfile / NicheVoiceRule / AccountVoiceRule in TTS resolution (priority: job voice_id → niche → account → default).
- **Output routing** – Niche→platform→account rules (niche_account_map / platform flags already exist; persist and enforce in publish step).
