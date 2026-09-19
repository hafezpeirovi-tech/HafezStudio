"""Validated, portable visual design tokens for Hafez Studio.

This module is the single Python adapter between the shared brand JSON and
Premiere/After Effects control values.  The UI reads the same JSON directly,
so a job cannot silently drift to a different palette.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from runtime_paths import studio_root


DEFAULT_BRAND_TOKENS: dict[str, Any] = {
    "schemaVersion": 1,
    "id": "hafez-premium-neon",
    "palette": {
        "canvas": "#020303",
        "surface": "#0A0C0B",
        "surfaceElevated": "#111412",
        "surfaceActive": "#142019",
        "primaryAccent": "#55FF72",
        "primaryAccentSoft": "#2FD65B",
        "negativeAccent": "#FF5964",
        "textPrimary": "#FFFFFF",
        "textSecondary": "#9DA5A0",
        "borderSubtle": "#FFFFFF0A",
    },
    "radius": {"card": 40, "control": 24, "compact": 16, "pill": 999},
    "glow": {"intensity": 0.72, "corePx": 4, "radiusPx": 34, "bloomPx": 76, "outerAlpha": 0.28},
    "motion": {"surfaceOpacity": 0.9, "borderOpacity": 0.32, "highlightGlow": 0.58},
    "rules": {"grainAllowed": False, "inactiveUsesNegativeAccent": False, "templateFamilyLimit": 4},
}

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def brand_tokens_path() -> Path:
    override = os.environ.get("HERMES_BRAND_TOKENS", "").strip()
    return Path(override).expanduser() if override else studio_root() / "config" / "brand-tokens.json"


def _validated(tokens: dict[str, Any]) -> dict[str, Any]:
    palette = tokens["palette"]
    for name, value in palette.items():
        if not isinstance(value, str) or not _HEX.fullmatch(value):
            raise ValueError(f"Invalid Hafez brand color {name}: {value!r}")
    tokens["radius"]["card"] = max(20, min(48, int(tokens["radius"]["card"])))
    tokens["radius"]["control"] = max(14, min(36, int(tokens["radius"]["control"])))
    tokens["glow"]["intensity"] = max(0.0, min(1.0, float(tokens["glow"]["intensity"])))
    tokens["glow"]["radiusPx"] = max(8, min(96, int(tokens["glow"]["radiusPx"])))
    if bool(tokens.get("rules", {}).get("grainAllowed", False)):
        raise ValueError("Hafez Studio production tokens must never enable grain")
    return tokens


def load_brand_tokens() -> dict[str, Any]:
    path = brand_tokens_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {}
    return _validated(_merge(DEFAULT_BRAND_TOKENS, payload))


def hex_rgba(value: str) -> tuple[int, int, int, int]:
    raw = value.lstrip("#")
    if len(raw) == 6:
        raw += "FF"
    return tuple(int(raw[index : index + 2], 16) for index in range(0, 8, 2))  # type: ignore[return-value]


def rgb8(tokens: Mapping[str, Any], name: str) -> tuple[int, int, int]:
    return hex_rgba(str(tokens["palette"][name]))[:3]


def rgb01(tokens: Mapping[str, Any], name: str) -> list[float]:
    return [round(channel / 255.0, 6) for channel in rgb8(tokens, name)] + [1.0]


def mogrt_control_values(tokens: Mapping[str, Any], glow_override: float | None = None) -> dict[str, Any]:
    """Return the stable Essential Graphics control contract."""
    glow = float(tokens["glow"]["intensity"] if glow_override is None else glow_override)
    glow = max(0.0, min(1.0, glow))
    return {
        "Canvas Color": rgb01(tokens, "canvas"),
        "Primary Accent": rgb01(tokens, "primaryAccent"),
        "Negative Accent": rgb01(tokens, "negativeAccent"),
        "Surface Color": rgb01(tokens, "surface"),
        "Surface Elevated": rgb01(tokens, "surfaceElevated"),
        "Text Primary": rgb01(tokens, "textPrimary"),
        "Text Secondary": rgb01(tokens, "textSecondary"),
        # Names exposed by the owner's fourteen AE templates.
        "Background Color": rgb01(tokens, "canvas"),
        "Champagne Border": rgb01(tokens, "primaryAccent"),
        "Cool Accent": rgb01(tokens, "primaryAccentSoft"),
        "Sand Accent": rgb01(tokens, "primaryAccent"),
        "Glass Surface": rgb01(tokens, "surface"),
        "Glow Intensity": round(glow * 100.0, 1),
        "Glow Radius": float(tokens["glow"]["radiusPx"]),
        "Corner Radius": float(tokens["radius"]["card"]),
        "Border Opacity": round(float(tokens["motion"]["borderOpacity"]) * 100.0, 1),
    }
