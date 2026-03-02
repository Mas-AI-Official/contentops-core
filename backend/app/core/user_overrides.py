"""
User-overridable settings (e.g. subtitles) stored in data/user_settings.json.
Takes precedence over .env for rendering. No server restart needed.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

USER_SETTINGS_FILENAME = "user_settings.json"
SUBTITLE_KEYS = ("subtitle_enabled", "subtitle_font_size", "subtitle_font_name")


def _path(data_path: Path) -> Path:
    return Path(data_path) / USER_SETTINGS_FILENAME


def get_subtitle_overrides(data_path: Path) -> Dict[str, Any]:
    """Read subtitle overrides from data/user_settings.json. Returns only subtitle keys."""
    p = _path(data_path)
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: data[k] for k in SUBTITLE_KEYS if k in data}
    except Exception:
        return {}


def set_subtitle_overrides(data_path: Path, subtitle_enabled: Optional[bool] = None,
                          subtitle_font_size: Optional[int] = None,
                          subtitle_font_name: Optional[str] = None) -> Dict[str, Any]:
    """Write subtitle overrides and return current merged overrides."""
    p = _path(data_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    current = get_subtitle_overrides(data_path)
    if subtitle_enabled is not None:
        current["subtitle_enabled"] = bool(subtitle_enabled)
    if subtitle_font_size is not None:
        current["subtitle_font_size"] = max(8, min(72, int(subtitle_font_size)))
    if subtitle_font_name is not None and str(subtitle_font_name).strip():
        current["subtitle_font_name"] = str(subtitle_font_name).strip()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current
