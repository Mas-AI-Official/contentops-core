# TTS (XTTS) server requirements

If you run an external XTTS server (e.g. Flask on port 8020), Content Factory calls it for speech synthesis.

## Required endpoint

The server **must** expose:

- **Method:** `POST`
- **Path:** `/tts_to_audio/` or `/tts_to_audio`
- **Body (JSON):** `{ "text": string, "speaker_wav": string | null, "language": string }`
- **Response:** Raw audio bytes (e.g. `audio/wav` or `audio/mpeg`)

If this route is missing, you will see **404** in the server log when generating video, and audio will not be produced. Add a route that:

1. Accepts the JSON body.
2. Runs XTTS (or your TTS engine) with the given text and optional speaker reference.
3. Returns the generated audio in the response body with an appropriate `Content-Type` header.

## Torch warning

If the server logs a PyTorch warning about `weights_only=True`, that is from loading XTTS model files. It is safe to ignore for local use, or set `weights_only=True` in `torch.load()` where the speaker/model is loaded.
