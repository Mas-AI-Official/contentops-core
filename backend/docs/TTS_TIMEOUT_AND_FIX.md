# TTS CLI Timeout – Root Cause and Fix

## What was happening

- **Symptom:** Job failed with: `Command '['tts', ...]' timed out after 416 seconds`
- **Content:** The script sent to TTS was a long film brief (director’s instructions, scene descriptions, 4000+ characters), not short narration.

## Root causes

1. **Single long run** – The whole script was sent to the TTS CLI in one call. XTTS can take a long time for large texts, so the process hit the subprocess timeout (5–7 minutes).
2. **Content type** – The job’s `full_script` contained a full creative brief. That’s valid (user can paste anything), but it makes the TTS run much longer than typical narration.

## Fix (implemented in `app/services/tts_service.py`)

1. **Chunking**
   - Scripts longer than **2000 characters** are split at sentence boundaries into chunks.
   - Each chunk is sent to the TTS CLI in a **separate subprocess** with a **per-chunk timeout** (7 minutes).
   - Output WAVs are concatenated with **pydub** into a single `narration.wav`.
   - Long scripts no longer depend on one very long run, so timeouts are avoided.

2. **Per-chunk timeout**
   - Each chunk uses a fixed **420 s** timeout (`TTS_CHUNK_TIMEOUT`). No single call runs indefinitely.

3. **Existing safeguards** (unchanged)
   - **Sanitization** – Emoji and problematic Unicode are removed so the CLI doesn’t hit `UnicodeEncodeError` on Windows.
   - **UTF-8** – `PYTHONIOENCODING=utf-8` so the subprocess stdout/stderr don’t break on special characters.
   - **Success check** – We require an existing, non-empty output file; non-zero exit is only a warning when the file is valid.

## Validation

- `_split_tts_chunks()` was tested: ~5000 chars → 3 chunks as expected.
- `_sanitize_text_for_tts_cli()` was tested: emoji removed.
- Re-run the same job: TTS should complete via chunked generation and produce one `narration.wav`.

## If you still see timeouts

- Increase `TTS_CHUNK_TIMEOUT` in `tts_service.py` (default 420 s).
- Reduce `MAX_CHARS_PER_TTS_CHUNK` (e.g. to 1500) so chunks are smaller and faster.
- Prefer the **XTTS server** (e.g. `start_xtts.bat`) when available; the server path does not use chunking and can handle long text in one request.
