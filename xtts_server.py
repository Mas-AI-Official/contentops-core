#!/usr/bin/env python3
"""
Content Factory XTTS server – exposes POST /tts_to_audio for the backend.
Uses the same model/config as start_xtts.bat but adds the endpoint the backend expects.
Run from repo root: python xtts_server.py --model_path <path> --config_path <config> --port 8020
"""
import argparse
import io
import os
import sys
from threading import Lock

# Ensure we can import TTS (venv or same env as start_xtts.bat)
from flask import Flask, request, send_file

# TTS is installed in venv
from TTS.utils.synthesizer import Synthesizer

app = Flask(__name__)
lock = Lock()
synthesizer = None


def create_parser():
    p = argparse.ArgumentParser(description="XTTS server with /tts_to_audio for Content Factory")
    p.add_argument("--model_path", type=str, required=True, help="Path to XTTS model dir or checkpoint")
    p.add_argument("--config_path", type=str, required=True, help="Path to model config.json")
    p.add_argument("--port", type=int, default=8020, help="Port to run on")
    p.add_argument("--use_cuda", action="store_true", help="Use CUDA")
    return p


@app.route("/")
def index():
    return {"status": "ok", "message": "Content Factory XTTS server. POST /tts_to_audio with JSON: text, speaker_wav, language."}, 200, {"Content-Type": "application/json"}


def _resolve_speaker_wav(path_or_name: str) -> str:
    """Resolve speaker_wav to an absolute path. If it's a name or relative path, look under XTTS_VOICES_ROOT."""
    if not path_or_name or not path_or_name.strip():
        return ""
    path_or_name = path_or_name.strip()
    if os.path.isabs(path_or_name) and os.path.isfile(path_or_name):
        return path_or_name
    if os.path.isfile(path_or_name):
        return os.path.abspath(path_or_name)
    voices_root = os.environ.get("XTTS_VOICES_ROOT", "")
    if voices_root and os.path.isdir(voices_root):
        base = os.path.basename(path_or_name)
        if not base.lower().endswith(".wav"):
            base = base + ".wav"
        candidate = os.path.join(voices_root, base)
        if os.path.isfile(candidate):
            return candidate
        if os.path.isfile(os.path.join(voices_root, path_or_name)):
            return os.path.abspath(os.path.join(voices_root, path_or_name))
    return path_or_name


@app.route("/tts_to_audio", methods=["POST"])
@app.route("/tts_to_audio/", methods=["POST"])
def tts_to_audio():
    """Accept JSON { text, speaker_wav, language } and return WAV bytes. speaker_wav is path or filename under XTTS_VOICES_ROOT."""
    global synthesizer
    if synthesizer is None:
        return {"error": "Synthesizer not loaded"}, 503
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    speaker_wav = _resolve_speaker_wav(data.get("speaker_wav") or "")
    language = (data.get("language") or "en").strip() or "en"
    if not text:
        return {"error": "Missing or empty 'text'"}, 400
    if not speaker_wav or not os.path.isfile(speaker_wav):
        return {"error": "Missing or invalid 'speaker_wav'. Use a path to a .wav file or a filename in XTTS_VOICES_ROOT (e.g. D:\\Ideas\\MODELS_ROOT\\xtts\\voices)"}, 400
    with lock:
        try:
            wavs = synthesizer.tts(
                text=text,
                speaker_name=None,
                language_name=language,
                speaker_wav=speaker_wav,
                style_wav=None,
            )
            out = io.BytesIO()
            synthesizer.save_wav(wavs, out)
            out.seek(0)
            return send_file(out, mimetype="audio/wav", as_attachment=False, download_name="speech.wav")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"TTS ERROR: {e}\n{tb}")
            return {"error": str(e) or repr(e), "traceback": tb[-500:]}, 500


def main():
    global synthesizer
    parser = create_parser()
    args = parser.parse_args()
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    model_path = os.path.abspath(args.model_path)
    config_path = os.path.abspath(args.config_path)

    # XTTS load_checkpoint expects a DIRECTORY path – it internally appends /model.pth.
    # Do NOT resolve to the .pth file or you'll get model.pth/model.pth.
    if os.path.isdir(model_path):
        # Verify that a recognized model file actually exists inside
        found_model = False
        for name in ["model.pth", "best_model.pth", "checkpoint.pth", "model.safetensors"]:
            if os.path.isfile(os.path.join(model_path, name)):
                found_model = True
                print(f"Found model file: {name} in {model_path}")
                break
        if not found_model:
            print(f"WARNING: No model file found in {model_path}. Expected model.pth or similar.")
        # Keep model_path as the directory – Synthesizer/XTTS will find the file inside
    elif os.path.isfile(model_path):
        # User passed a direct file path – use parent directory for XTTS
        print(f"Note: model_path is a file; using parent directory for XTTS: {os.path.dirname(model_path)}")
        model_path = os.path.dirname(model_path)

    if not os.path.isfile(config_path) and os.path.isdir(model_path):
        candidate = os.path.join(model_path, "config.json")
        if os.path.isfile(candidate):
            config_path = candidate
    print("Loading XTTS model...")
    print(f"  Model dir:  {model_path}")
    print(f"  Config:     {config_path}")
    synthesizer = Synthesizer(
        tts_checkpoint=model_path,
        tts_config_path=config_path,
        tts_speakers_file=None,
        tts_languages_file=None,
        vocoder_checkpoint=None,
        vocoder_config=None,
        encoder_checkpoint="",
        encoder_config="",
        use_cuda=args.use_cuda,
    )
    print("Model loaded. Serving on port", args.port)
    print("  GET  /         – health")
    print("  POST /tts_to_audio – JSON: { text, speaker_wav, language }")
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
