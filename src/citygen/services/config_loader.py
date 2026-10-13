"""YAML profile loader with `extends:` preset inheritance."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from citygen.core.types import Profile


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_profile(path: str | Path, preset: str | None = None) -> Profile:
    path = Path(path)
    raw = yaml.safe_load(path.read_text()) or {}

    if preset:
        preset_path = Path("config/presets") / f"{preset}.yaml"
        if not preset_path.exists():
            raise FileNotFoundError(f"preset not found: {preset_path}")
        preset_raw = yaml.safe_load(preset_path.read_text()) or {}
        preset_raw.pop("extends", None)
        raw = _deep_merge(raw, preset_raw)

    if "extends" in raw:
        parent = Path("config") / f"{raw.pop('extends')}.yaml"
        if parent.exists() and parent != path:
            raw = _deep_merge(yaml.safe_load(parent.read_text()) or {}, raw)

    return Profile.model_validate(raw)