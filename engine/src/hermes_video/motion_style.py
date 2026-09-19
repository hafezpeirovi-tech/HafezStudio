"""Validated Hafez editorial motion language.

The contract deliberately sits beside the UI brand tokens.  Templates, preview
renderers and Premiere plans all read the same material, timing and audio rules
so a vendor MOGRT can never silently become the product's visual identity.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from runtime_paths import studio_root


DEFAULT_MOTION_STYLE: dict[str, Any] = {
    "schemaVersion": 1,
    "id": "hafez-motion-language-2026",
    "brandTokenId": "hafez-premium-neon",
    "material": {
        "name": "Hafez Liquid Glass",
        "surfaceOpacity": 0.9,
        "innerLightOpacity": 0.2,
        "borderOpacity": 0.32,
        "shadowBlurPx": 34,
        "shadowOffsetPx": 12,
        "grainAllowed": False,
    },
    "motion": {
        "entryCurve": [0.16, 0.84, 0.22, 1.0],
        "exitCurve": [0.4, 0.0, 0.2, 1.0],
        "entryFrames": 18,
        "settleFrames": 9,
        "exitFrames": 12,
        "liftPx": 42,
        "blurPx": 9,
        "maximumOvershootPercent": 1.5,
        "linearAllowed": False,
        "motionBlur": True,
    },
    "typography": {
        "englishDisplayFamily": "Relaxe",
        "englishControl": "EN Display Title",
        "persianControl": "FA Semantic Subtitle",
        "layout": "large-en-small-fa-single-glass",
    },
    "families": {},
    "visualLimits": {
        "maximumFamiliesPerVideo": 4,
        "maximumLuminousCardsPerFrame": 2,
        "vendorTemplateSkinAllowed": False,
        "vendorTemplateChoreographyAllowed": True,
    },
    "audio": {
        "sampleRate": 48_000,
        "channels": 2,
        "format": "pcm_s24le",
        "truePeakCeilingDbfs": -12.0,
        "duckingTarget": "background-music-only",
        "voiceUntouched": True,
        "recipes": {},
    },
}


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def motion_style_path() -> Path:
    override = os.environ.get("HERMES_MOTION_STYLE", "").strip()
    return Path(override).expanduser() if override else studio_root() / "config" / "motion-style-contract.json"


def _curve(value: Any, name: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{name} must contain four cubic-bezier values")
    curve = [float(item) for item in value]
    if any(item < 0.0 or item > 1.0 for item in curve):
        raise ValueError(f"{name} must stay inside the unit square")
    return curve


def _validated(style: dict[str, Any]) -> dict[str, Any]:
    if bool(style["material"].get("grainAllowed", False)):
        raise ValueError("Hafez motion material must remain grain-free")
    if bool(style["motion"].get("linearAllowed", False)):
        raise ValueError("Linear editorial motion is forbidden")
    style["motion"]["entryCurve"] = _curve(style["motion"].get("entryCurve"), "entryCurve")
    style["motion"]["exitCurve"] = _curve(style["motion"].get("exitCurve"), "exitCurve")
    family_limit = int(style["visualLimits"].get("maximumFamiliesPerVideo", 4))
    if not 1 <= family_limit <= 4:
        raise ValueError("Hafez motion family limit must be between one and four")
    style["visualLimits"]["maximumFamiliesPerVideo"] = family_limit
    if bool(style["visualLimits"].get("vendorTemplateSkinAllowed", True)):
        raise ValueError("Vendor template skins cannot be used as Hafez final artwork")
    if int(style["audio"].get("sampleRate", 0)) != 48_000:
        raise ValueError("Hafez editorial SFX must be 48 kHz")
    if not bool(style["audio"].get("voiceUntouched", False)):
        raise ValueError("Dialogue must stay untouched by music ducking")
    return style


def load_motion_style() -> dict[str, Any]:
    try:
        payload = json.loads(motion_style_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        payload = {}
    return _validated(_merge(DEFAULT_MOTION_STYLE, payload))


def family_for_kind(kind: str, style: Mapping[str, Any] | None = None) -> dict[str, Any]:
    contract = dict(style or load_motion_style())
    normalized = str(kind).casefold()
    # Hooks and chapter breaks are deliberate full-frame editorial moments.
    # They use the fullscreen Hafez canvas; ordinary statements remain spatial
    # overlays that must stay outside the tracked presenter union.
    if normalized in {"hook", "chapter"}:
        fullscreen = contract.get("families", {}).get("fullscreen-glass")
        if fullscreen:
            return dict(fullscreen)
    for family in contract.get("families", {}).values():
        roles = {str(value).casefold() for value in family.get("semanticRoles", [])}
        if normalized in roles:
            return dict(family)
    fallback = contract.get("families", {}).get("insight-card", {})
    return dict(fallback)


def motion_rule_payload(style: Mapping[str, Any] | None = None) -> dict[str, Any]:
    contract = style or load_motion_style()
    motion = contract["motion"]
    return {
        "entry_easing": "hafez-ui-entry",
        "exit_easing": "hafez-ui-exit",
        "entry_curve": list(motion["entryCurve"]),
        "exit_curve": list(motion["exitCurve"]),
        "entry_frames": int(motion["entryFrames"]),
        "settle_frames": int(motion["settleFrames"]),
        "exit_frames": int(motion["exitFrames"]),
        "linear_allowed": False,
        "motion_blur": bool(motion["motionBlur"]),
        "entry_offset_px": int(motion["liftPx"]),
        "entry_blur_px": int(motion["blurPx"]),
        "maximum_overshoot_percent": float(motion["maximumOvershootPercent"]),
        "entry_opacity": 0,
        "settled_opacity": 100,
    }
