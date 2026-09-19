"""Deterministic professional YouTube edit planning for Hafez Studio.

The module complements LLM suggestions with a pacing-safe Director Cut plan:
exclusive two-camera intervals, varied semantic punch-ins and verified
editable MOGRT instructions. Preview PNGs are never inserted into final XML.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from brand_tokens import load_brand_tokens, mogrt_control_values, rgb8
from editorial_elements import (
    SUBSCRIBE_ELEMENT_ID,
    catalog_plan_payload,
    contains_exact_phrase,
    exact_subscribe_segments,
    load_editorial_catalog,
    resolve_catalog_mogrt,
    select_editorial_element,
)
from motion_style import family_for_kind, load_motion_style
from sound_design import recipe_asset
from curation_rules import (
    TEXT_ANIMATION_TITLE,
    TEXT_ANIMATION_SFX,
    bilingual_typography_contract,
    copy_grounding,
    curate_complete_statement,
    is_complete_statement,
    load_template_family_history,
    resolve_relaxe_font,
    resolve_text_animation_title,
    save_template_family_history,
    select_template_families,
    template_rule_payload,
)
from runtime_paths import adobe_mogrt_root, face_model_path, font_candidates, studio_root
from smart_crop import _union_normalized_boxes
from body_tracking import detect_subject_box_unions
from spoken_trigger import exact_trigger_timing


TEMPLATE_ROOT = adobe_mogrt_root()
DEFAULT_FONT_CANDIDATES = tuple(font_candidates())
MOTION_PACK_ROOT = Path(
    os.environ.get("HERMES_MOTION_PACK", str(studio_root() / "motion-pack" / "dist"))
)
BRAND_TOKENS = load_brand_tokens()
BRAND_PRIMARY = rgb8(BRAND_TOKENS, "primaryAccent")
BRAND_PRIMARY_SOFT = rgb8(BRAND_TOKENS, "primaryAccentSoft")
BRAND_NEGATIVE = rgb8(BRAND_TOKENS, "negativeAccent")
BRAND_SURFACE = rgb8(BRAND_TOKENS, "surface")
BRAND_TEXT = rgb8(BRAND_TOKENS, "textPrimary")
BRAND_MUTED = rgb8(BRAND_TOKENS, "textSecondary")
BRAND_CARD_RADIUS = int(BRAND_TOKENS["radius"]["card"])
BRAND_GLOW_RADIUS = int(BRAND_TOKENS["glow"]["radiusPx"])
MOTION_STYLE = load_motion_style()

# Shared with completion validation: preserve the existing scheduling policy.
CAMERA_INITIAL_HOLD_SECONDS = 24.0
CAMERA_BOUNDARY_WINDOW_SECONDS = 7.0
CAMERA_SCHEDULE_TAIL_SECONDS = 0.05

TEMPLATE_MAP = {
    "hook": "Text Intro 1.mogrt",
    "number": "13. Typewriter.mogrt",
    "chapter": "Text Intro 1.mogrt",
    "keyword": "11. Highlight Paragraph Multi Word.mogrt",
    "typewriter": "13. Typewriter.mogrt",
    "lower_third": "Liquid Glass Lower Third 01.mogrt",
}

CUSTOM_TEMPLATE_MAP = {
    "hook": "Hafez Chapter Billboard.mogrt",
    "chapter": "Hafez Chapter Billboard.mogrt",
    "statement": "Hafez Word Lift Statement.mogrt",
    "keyword": "Hafez Face Safe Corner Note.mogrt",
    "kinetic": "Hafez Subject Occlusion Keyword.mogrt",
    "number": "Hafez Big Number Reveal.mogrt",
    "hud": "Hafez Glass HUD Metric.mogrt",
    "flowchart": "Hafez Compact Flowchart.mogrt",
    "compare": "Hafez Split Compare.mogrt",
    "typewriter": "Hafez Decision Depth Typography.mogrt",
}

REGION_SPECS: dict[str, dict[str, float]] = {
    "top-left": {"x": 0.195, "y": 0.17, "w": 0.28, "h": 0.20},
    "top-right": {"x": 0.805, "y": 0.17, "w": 0.28, "h": 0.20},
    "side-left": {"x": 0.175, "y": 0.57, "w": 0.25, "h": 0.38},
    "side-right": {"x": 0.825, "y": 0.57, "w": 0.25, "h": 0.38},
    "bottom-dock": {"x": 0.50, "y": 0.86, "w": 0.58, "h": 0.17},
    "top-banner": {"x": 0.50, "y": 0.09, "w": 0.58, "h": 0.13},
}

TITLE_SAFE_AREA = (0.05, 0.05, 0.90, 0.90)
SUBJECT_CLEARANCE = 0.018
MAX_SAFE_OVERLAP = 0.001
MIN_LAYOUT_SCALE = 0.58
NATIVE_GLASS_PROFILE = "hafez-glass-review-8-v1"
# Local term labels only: none of these entries asserts a fact about a person,
# strategy or result. Eligibility still requires an anchored complete clause.
NATIVE_GLASS_TERM_LABELS = {
    "فلج تحلیلی": "ANALYSIS PARALYSIS",
    "کامیونیتی": "COMMUNITY",
    "اسکرینر": "SCREENER",
    "بک‌تست": "BACKTEST",
    "هوش مصنوعی": "ARTIFICIAL INTELLIGENCE",
    "تریدر باهوش": "SMART TRADER",
}
NATIVE_GLASS_CONTROLS = frozenset({
    "Title", "Body", "Layout Position", "Layout Scale", "Show Background",
    "Background Color", "Champagne Border", "Cool Accent", "Sand Accent",
    "Glass Surface", "Text Primary", "Glow Intensity", "Glow Radius", "Glass Opacity",
    "Duration Seconds", "Title · Text Color", "Title · Line Spacing", "Title · Tracking",
    "Body · Text Color", "Body · Line Spacing", "Body · Tracking",
})

INCOMPLETE_ENDINGS = {
    "که", "و", "یا", "اما", "اگر", "برای", "از", "به", "با", "تا", "روی", "در",
    "مثل", "مثلا", "یک", "این", "اون", "آن", "سیگنال", "الگوریتمی",
}

SAFE_ENGLISH_KICKERS = (
    (("سیگنال", "تریدینگ ویو"), "SIGNAL GENERATION"),
    (("سرعت", "تأخیر", "میلی"), "EXECUTION LATENCY"),
    (("هوش مصنوعی", "یادگیری"), "AI INTELLIGENCE"),
    (("پایتون", "کد", "برنامه"), "AUTOMATION ENGINE"),
    (("بروکر", "سفارش", "معامله"), "TRADE EXECUTION"),
    (("داده", "اطلاعات", "تحلیل"), "DATA PIPELINE"),
    (("مشکل", "اشتباه", "ریسک"), "CRITICAL INSIGHT"),
)

IMPORTANCE_CUES = (
    "نکته", "مهم", "مشکل", "اشتباه", "اما", "یعنی", "دلیل", "نتیجه",
    "سرعت", "تأخیر", "مقایسه", "در واقع", "دقت", "هشدار", "آینده",
    "هوش مصنوعی", "ربات", "سیستم", "بروکر", "متاتریدر", "پایتون",
)


def _font_path(role: str = "body") -> Path:
    """Return a Persian font that renders correctly without Pillow RAQM.

    The packaged Pillow build intentionally stays small and does not include
    libraqm.  Static Persian fonts work correctly with our reshaper/bidi
    fallback, while Estedad-VF requires a complex-layout engine and otherwise
    produces disconnected, over-spaced glyphs.  Prefer a role-specific static
    font installed by the editor and keep Tahoma as the universal Windows
    fallback.
    """
    explicit = os.environ.get(
        "HERMES_TITLE_FONT_PATH" if role == "title" else "HERMES_BODY_FONT_PATH",
        "",
    ).strip()
    if explicit:
        selected = Path(explicit).expanduser()
        incompatible_variable = selected.name.casefold() == "estedad-vf.ttf"
        if (
            selected.is_file()
            and selected.suffix.casefold() in {".ttf", ".otf"}
            and not incompatible_variable
        ):
            return selected

    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    roots = (local / "Microsoft" / "Windows" / "Fonts", windows / "Fonts")
    names = (
        (
            "YekanBakh-ExtraBlack.ttf",
            "Peyda-ExtraBold.ttf",
            "IRANSansX-ExtraBold.ttf",
            "Dana-ExtraBold.ttf",
            "AbarHighFaNum-Black.ttf",
            "AbarHighFaNum-ExtraBold.ttf",
            "AbarHigh-ExtraBold.ttf",
            "Kalameh-ExtraBold.ttf",
            "tahomabd.ttf",
        )
        if role == "title"
        else (
            "YekanBakh-Regular.ttf",
            "Peyda-Regular.ttf",
            "IRANSansX-Regular.ttf",
            "Dana-Regular.ttf",
            "AbarHighFaNum-Regular.ttf",
            "AbarHighFaNum-SemiBold.ttf",
            "AbarHigh-Regular.ttf",
            "Kalameh_Regular.ttf",
            "tahoma.ttf",
        )
    )
    for name in names:
        for root in roots:
            candidate = root / name
            if candidate.is_file():
                return candidate
    for candidate in DEFAULT_FONT_CANDIDATES:
        if candidate.exists() and candidate.name.casefold() != "estedad-vf.ttf":
            return candidate
    raise FileNotFoundError("هیچ فونت فارسی مناسب برای گرافیک Hafez پیدا نشد.")


def _font_family(role: str) -> str:
    variable = "HERMES_TITLE_FONT_FAMILY" if role == "title" else "HERMES_BODY_FONT_FAMILY"
    return os.environ.get(variable, "Abar High FaNum").strip() or "Abar High FaNum"


def _font_weight(role: str) -> int:
    variable = "HERMES_TITLE_FONT_WEIGHT" if role == "title" else "HERMES_BODY_FONT_WEIGHT"
    fallback = 800 if role == "title" else 400
    try:
        return max(100, min(900, int(os.environ.get(variable, fallback))))
    except (TypeError, ValueError):
        return fallback


def _load_font(path: Path, size: int, weight: int) -> ImageFont.FreeTypeFont:
    """Load static fonts and set the weight axis when a variable font exposes it."""
    font = ImageFont.truetype(str(path), size)
    try:
        axes = font.get_variation_axes()
        values: list[float] = []
        for axis in axes:
            raw_name = axis.get("name", "")
            name = raw_name.decode("utf-8", "ignore") if isinstance(raw_name, bytes) else str(raw_name)
            minimum = float(axis.get("minimum", 0))
            maximum = float(axis.get("maximum", 1000))
            default = float(axis.get("default", minimum))
            values.append(max(minimum, min(maximum, float(weight))) if "weight" in name.casefold() else default)
        if values:
            font.set_variation_by_axes(values)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return font


def _cue_font_role(kind: str) -> str:
    return "title" if kind in {"hook", "chapter", "number", "kinetic", "hud", "compare"} else "body"


def _typography_motion(kind: str) -> str:
    if kind in {"hook", "chapter", "kinetic"}:
        return "variable-weight + adaptive-tracking + editorial-scale"
    if kind in {"number", "hud", "compare"}:
        return "metric-pulse + condensed-tracking"
    if kind == "flowchart":
        return "progressive-hierarchy + node-reveal"
    return "restrained-weight-emphasis + readable-statement"


def _shape_rtl(text: str) -> str:
    """Shape Persian when optional pure-Python helpers are installed."""
    try:
        import arabic_reshaper  # type: ignore
        from bidi.algorithm import get_display  # type: ignore

        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text


def _nearest_boundary(segments: list[dict[str, Any]], ideal: float, floor: float) -> float:
    candidates = [
        float(item["start"])
        for item in segments
        if float(item["start"]) >= floor + 3.5 and abs(float(item["start"]) - ideal) <= CAMERA_BOUNDARY_WINDOW_SECONDS
    ]
    if not candidates:
        return max(floor + 3.5, ideal)
    return min(candidates, key=lambda value: abs(value - ideal))


def build_camera_schedule(
    segments: list[dict[str, Any]],
    duration: float,
    markers: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Create an exclusive CAM1/CAM2 schedule aligned to speech boundaries.

    CAM1 remains the hero angle. CAM2 is used in shorter bursts, producing a
    professional 2-camera rhythm without mechanical fixed-interval switching.
    """
    if duration <= 0:
        return []
    cam1_lengths = (CAMERA_INITIAL_HOLD_SECONDS, 29.0, 21.0, 27.0, 32.0, 23.0)
    cam2_lengths = (8.0, 11.0, 9.0, 13.0, 10.0)
    schedule: list[dict[str, Any]] = []
    cursor = 0.0
    camera = "cam1"
    index1 = index2 = 0
    while cursor < duration - CAMERA_SCHEDULE_TAIL_SECONDS:
        if camera == "cam1":
            shot_length = cam1_lengths[index1 % len(cam1_lengths)]
            index1 += 1
        else:
            shot_length = cam2_lengths[index2 % len(cam2_lengths)]
            index2 += 1
        ideal = min(duration, cursor + shot_length)
        end = duration if ideal >= duration - 2.0 else _nearest_boundary(segments, ideal, cursor)
        end = min(duration, max(cursor + 3.5, end))
        nearby = min(
            segments,
            key=lambda item: abs(float(item["start"]) - cursor),
            default={"text": ""},
        )
        reason = str(nearby.get("text", "")).strip()[:90]
        schedule.append(
            {
                "start": round(cursor, 3),
                "end": round(end, 3),
                "camera": camera,
                "reason": reason or ("نمای اصلی" if camera == "cam1" else "تنوع زاویه"),
            }
        )
        cursor = end
        camera = "cam2" if camera == "cam1" else "cam1"

    # Honor high-confidence explicit camera suggestions by changing the shot
    # that contains their timestamp. Exclusivity is preserved by construction.
    for marker in markers:
        marker_type = str(marker.get("type", "")).upper()
        if marker_type not in {"CAM1", "CAM2"}:
            continue
        moment = float(marker.get("start", -1.0))
        for shot in schedule:
            if float(shot["start"]) <= moment < float(shot["end"]):
                shot["camera"] = marker_type.casefold()
                shot["reason"] = str(marker.get("comment", shot["reason"]))[:120]
                break

    # Merge adjacent shots only if an explicit override made them identical.
    merged: list[dict[str, Any]] = []
    for shot in schedule:
        if merged and merged[-1]["camera"] == shot["camera"]:
            merged[-1]["end"] = shot["end"]
            continue
        merged.append(dict(shot))
    return merged


def split_track_for_camera(
    clips: list[list[int]] | list[tuple[int, int, int, int]],
    schedule: list[dict[str, Any]],
    fps: float,
    camera: str,
) -> list[list[int | bool]]:
    """Split source clips at camera cuts and attach a per-clip enabled flag."""
    output: list[list[int | bool]] = []
    for raw in clips:
        tl_start, tl_end, media_in, _media_out = map(int, raw[:4])
        for shot in schedule:
            shot_start = int(round(float(shot["start"]) * fps))
            shot_end = int(round(float(shot["end"]) * fps))
            start = max(tl_start, shot_start)
            end = min(tl_end, shot_end)
            if end <= start:
                continue
            source_start = media_in + (start - tl_start)
            output.append(
                [start, end, source_start, source_start + (end - start), shot["camera"] == camera]
            )
    return output


def _semantic_importance(segment: dict[str, Any]) -> float:
    text = str(segment.get("text", ""))
    hits = sum(1 for cue in IMPORTANCE_CUES if cue in text)
    number_bonus = 1.2 if re.search(r"[0-9۰-۹]", text) else 0.0
    question_bonus = 0.5 if "؟" in text or "?" in text else 0.0
    length_bonus = 0.25 if 28 <= len(text) <= 105 else 0.0
    return hits * 0.65 + number_bonus + question_bonus + length_bonus


def _importance(segment: dict[str, Any], target: float) -> float:
    start = float(segment.get("start", 0.0))
    proximity = max(0.0, 0.35 - abs(start - target) / 60.0)
    return _semantic_importance(segment) + proximity


def _overlay_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text)).strip(" ،؛.-")
    cleaned = re.sub(r"^(خب|حالا|ببینید|ببین|یعنی|در واقع)\s+", "", cleaned)
    words = cleaned.split()
    numeric = next((i for i, word in enumerate(words) if re.search(r"[0-9۰-۹]", word)), None)
    if numeric is not None:
        left = max(0, numeric - 3)
        right = min(len(words), numeric + 4)
        words = words[left:right]
    else:
        words = words[:8]
    result = " ".join(words).strip(" ،؛")
    return result[:72]


def _normalize_statement(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text)).strip(" ،؛:-")
    value = re.sub(r"^(خب|حالا|ببینید|ببین|یعنی|در واقع|مثلا|مثلاً)\s+", "", value)
    value = re.sub(r"\b(من من|که که|و و)\b", lambda match: match.group(0).split()[0], value)
    return value.strip()


def _looks_complete(text: str) -> bool:
    return is_complete_statement(text)


def _has_spoken_verb(text: str) -> bool:
    value = _normalize_statement(text).casefold()
    patterns = (
        r"\b(?:است|هست|نیست|بود|شد|کرد|دارم|داره|دارن|نداره|ندارم)\b",
        r"(?:می|نمی)[‌\-]?(?:کن|شه|شین|رس|فرست|گیر|بین|زن|ساز|د|اد|خواد|گ)\S*",
        r"\b(?:بزن|بزنه|بده|بگم|بگی|بریم|تموم شده|انجام بده)\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)


def _best_spoken_clause(text: str) -> str:
    """Extract one understandable colloquial clause without formal rewriting."""
    raw_clauses = [
        _normalize_statement(part)
        for part in re.split(r"[،؛.!؟?]+", str(text))
        if _normalize_statement(part)
    ]
    candidates: list[str] = []
    for index, clause in enumerate(raw_clauses):
        for count in (1, 2):
            combined = _normalize_statement("، ".join(raw_clauses[index : index + count]))
            words = combined.split()
            if not 4 <= len(words) <= 18 or len(combined) > 112:
                continue
            if words[-1].casefold() in INCOMPLETE_ENDINGS:
                continue
            if _has_spoken_verb(combined):
                candidates.append(combined)
    if not candidates:
        return ""
    best = max(
        candidates,
        key=lambda value: (
            2 if 7 <= len(value.split()) <= 14 else 1,
            sum(1 for cue in IMPORTANCE_CUES if cue in value),
            -abs(len(value.split()) - 10),
        ),
    )
    return best if best.endswith((".", "!", "؟", "?")) else best + "."


def _complete_statement(
    segments: list[dict[str, Any]],
    selected_index: int,
    marker: dict[str, Any],
) -> str:
    """Return only copy accepted by the deterministic curation contract."""
    decision = _complete_statement_decision(segments, selected_index, marker)
    return str(decision["text"]) if decision else ""


def _complete_statement_decision(
    segments: list[dict[str, Any]],
    selected_index: int,
    marker: dict[str, Any],
) -> dict[str, Any] | None:
    return curate_complete_statement(
        segments,
        selected_index,
        (marker.get("headline_fa", ""), marker.get("overlay_text", ""), marker.get("summary_fa", "")),
    )


def _rect_from_region(region: str) -> tuple[float, float, float, float]:
    spec = REGION_SPECS[region]
    return (spec["x"] - spec["w"] / 2, spec["y"] - spec["h"] / 2, spec["w"], spec["h"])


def _intersection_ratio(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    area = max(0.0, right - left) * max(0.0, bottom - top)
    return area / max(0.0001, aw * ah)


def _fit_region_outside_subject(
    region: str,
    subject: tuple[float, float, float, float],
) -> tuple[tuple[float, float, float, float], float, bool]:
    """Fit a region inside title-safe while keeping its full box off the presenter."""
    safe_x, safe_y, safe_w, safe_h = TITLE_SAFE_AREA
    safe_right, safe_bottom = safe_x + safe_w, safe_y + safe_h
    subject_x, subject_y, subject_w, subject_h = subject
    subject_right, subject_bottom = subject_x + subject_w, subject_y + subject_h
    spec = REGION_SPECS[region]
    desired_w, desired_h = spec["w"], spec["h"]

    if "left" in region:
        zone = (safe_x, safe_y, max(0.0, subject_x - SUBJECT_CLEARANCE - safe_x), safe_h)
        align_x, align_y = "left", "center"
    elif "right" in region:
        left = max(safe_x, subject_right + SUBJECT_CLEARANCE)
        zone = (left, safe_y, max(0.0, safe_right - left), safe_h)
        align_x, align_y = "right", "center"
    elif region == "top-banner":
        zone = (safe_x, safe_y, safe_w, max(0.0, subject_y - SUBJECT_CLEARANCE - safe_y))
        align_x, align_y = "center", "top"
    else:
        top = max(safe_y, subject_bottom + SUBJECT_CLEARANCE)
        zone = (safe_x, top, safe_w, max(0.0, safe_bottom - top))
        align_x, align_y = "center", "bottom"

    zone_x, zone_y, zone_w, zone_h = zone
    scale = min(1.0, zone_w / max(0.0001, desired_w), zone_h / max(0.0001, desired_h))
    fitted_w, fitted_h = desired_w * scale, desired_h * scale
    if align_x == "left":
        left = zone_x
    elif align_x == "right":
        left = zone_x + zone_w - fitted_w
    else:
        left = zone_x + (zone_w - fitted_w) / 2.0
    if align_y == "top":
        top = zone_y
    elif align_y == "bottom":
        top = zone_y + zone_h - fitted_h
    else:
        desired_top = spec["y"] - fitted_h / 2.0
        top = max(zone_y, min(zone_y + zone_h - fitted_h, desired_top))
    rect = (left, top, fitted_w, fitted_h)
    contained = (
        left >= safe_x - 0.0001
        and top >= safe_y - 0.0001
        and left + fitted_w <= safe_right + 0.0001
        and top + fitted_h <= safe_bottom + 0.0001
    )
    return rect, scale, contained


def _fit_native_glass_region(region, subject):
    """Fit the audited 720x380 plate plus halo, not a generic card aspect ratio.

    Free top/bottom bands are valid even when the subject spans most of the
    image width. Keep all generic clearance/overlap rules unchanged.
    """
    sx, sy, sw, sh = TITLE_SAFE_AREA
    x, y, w, h = subject
    if region == "top-banner":
        zone = (sx, sy, sw, max(0.0, y - SUBJECT_CLEARANCE - sy))
    elif region == "bottom-dock":
        top = max(sy, y + h + SUBJECT_CLEARANCE)
        zone = (sx, top, sw, max(0.0, sy + sh - top))
    elif "left" in region:
        zone = (sx, sy, max(0.0, x - SUBJECT_CLEARANCE - sx), sh)
    else:
        left = max(sx, x + w + SUBJECT_CLEARANCE)
        zone = (left, sy, max(0.0, sx + sw - left), sh)
    zx, zy, zw, zh = zone
    scale = max(0.0, min(.88, (zw * 1920 - 24) / 720, (zh * 1080 - 24) / 380))
    if scale <= 0:
        return (zx, zy, 0.0, 0.0), 0.0, False
    rw, rh = (720 * scale + 24) / 1920, (380 * scale + 24) / 1080
    left = zx if "left" in region else zx + zw - rw if "right" in region else zx + (zw - rw) / 2
    if region == "top-banner":
        top = zy
    elif region == "bottom-dock":
        top = zy + zh - rh
    else:
        top = max(zy, min(zy + zh - rh, REGION_SPECS[region]["y"] - rh / 2))
    return (left, top, rw, rh), scale, True


def _unverified_motion_overlap(clips, start, end, fps, events):
    """Reject uncalibrated FCPCurve spans, including the XML entrance/exit ramp.

    prepare_track_motion uses at most 12 ramp frames, half outside each event.
    This does not pretend a raw-source union proves safety after a camera zoom.
    """
    a, b = round(start * fps), round(end * fps)
    for clip in clips:
        if len(clip) >= 5 and not clip[4]:
            continue
        ca, cb = map(int, clip[:2])
        for event in events:
            ea, eb = max(ca, round(float(event["start"]) * fps)), min(cb, round(float(event["end"]) * fps))
            if eb - ea >= 2 and max(a, ca, ea - 6) < min(b, cb, eb + 7):
                return True
    return False


def build_sfx_cue(cue: dict[str, Any], fps: float) -> dict[str, Any] | None:
    """Resolve a layered Hafez recipe and lock its transient to frame one."""
    if cue.get("review_blocked") or cue.get("needs_manual_copy"):
        return None
    family = family_for_kind(str(cue.get("kind", "statement")), MOTION_STYLE)
    recipe = str(cue.get("sfx_recipe") or family.get("sfxRecipe", "insight-air"))
    try:
        asset, details = recipe_asset(recipe)
    except (FileNotFoundError, RuntimeError, KeyError, ValueError):
        return None
    start_frame = max(0, int(round(float(cue.get("start", 0.0)) * fps)))
    start = start_frame / max(1.0, fps)
    return {
        "id": f"{cue.get('id', 'graphic')}-entry-sfx",
        "graphic_id": str(cue.get("id", "")),
        "asset_path": str(asset.resolve()),
        "asset_name": asset.name,
        "role": "hafez-layered-motion",
        "recipe": recipe,
        "layers": list(details.get("layers", [])),
        "source_mode": "licensed-local-derived",
        "generated_audio": False,
        "start": round(start, 6),
        "start_frame": start_frame,
        "duration": float(details.get("duration", TEXT_ANIMATION_SFX.duration)),
        "sample_rate": int(MOTION_STYLE["audio"]["sampleRate"]),
        "channels": int(MOTION_STYLE["audio"]["channels"]),
        "transient_offset_ms": int(details.get("transient_offset_ms", 0)),
        "settle_offset_ms": int(details.get("settle_offset_ms", 0)),
        "true_peak_ceiling_dbfs": float(MOTION_STYLE["audio"]["truePeakCeilingDbfs"]),
        "audio_track": TEXT_ANIMATION_SFX.audio_track,
        "sync": "mogrt-first-entry-frame",
        "ducking_target": "background-music-only",
        "voice_untouched": True,
    }


def _expand_face_box(box: tuple[float, float, float, float] | None) -> tuple[float, float, float, float]:
    if box is None:
        # Conservative central presenter zone when a sparse sample misses.
        return (0.36, 0.18, 0.28, 0.48)
    x, y, w, h = box
    margin_x = max(0.05, w * 0.45)
    margin_top = max(0.06, h * 0.35)
    margin_bottom = max(0.10, h * 0.85)  # reserve mouth and upper-chest gestures
    left = max(0.02, x - margin_x)
    top = max(0.04, y - margin_top)
    right = min(0.98, x + w + margin_x)
    bottom = min(0.94, y + h + margin_bottom)
    return (left, top, right - left, bottom - top)


def _source_frame_at(clips: list[list[int] | tuple[int, ...]], timeline_seconds: float, fps: float) -> int:
    timeline_frame = int(round(timeline_seconds * fps))
    for raw in clips:
        tl_start, tl_end, media_in = map(int, raw[:3])
        if tl_start <= timeline_frame < tl_end:
            return media_in + timeline_frame - tl_start
    return max(0, timeline_frame)


def _source_frames_for_interval(
    clips: list[list[int] | tuple[int, ...]],
    start: float,
    end: float,
    fps: float,
    *,
    maximum_samples: int = 11,
) -> list[int]:
    """Sample the complete graphic lifetime, including both temporal edges."""
    safe_end = max(start, end)
    duration = safe_end - start
    count = max(3, min(maximum_samples, int(math.ceil(duration / 0.45)) + 1))
    if duration <= 0.001:
        timeline_samples = [start]
    else:
        timeline_samples = [start + duration * index / (count - 1) for index in range(count)]
    return sorted({_source_frame_at(clips, value, fps) for value in timeline_samples})


def _visible_source_frames(clips, start, end, fps):
    """All source frames used by a frame-quantized MOGRT, end exclusive."""
    frames = set()
    first, last = int(round(start * fps)), int(round(end * fps))
    for clip in clips:
        if len(clip) >= 5 and not clip[4]:
            continue
        a, b, source = map(int, clip[:3])
        source_end = int(clip[3]) if len(clip) >= 4 else source + b - a
        if max(first, a) < min(last, b) and source_end - source != b - a:
            frames.add(-1)  # Unsupported retime: force incomplete evidence, never guess.
        for tick in range(max(first, a), min(last, b)):
            value = source + tick - a
            if value < source_end:
                frames.add(value)
    return sorted(frames)


def _timeline_coverage_complete(tracks, start, end, fps):
    expected = set(range(int(round(start * fps)), int(round(end * fps))))
    actual = set()
    for track in tracks:
        for clip in track:
            if len(clip) >= 5 and not clip[4]:
                continue
            actual.update(range(int(clip[0]), int(clip[1])))
    return bool(expected) and expected.issubset(actual)


def _fit_node_text(value: str, max_words: int = 7) -> str:
    """Create an editable two-line label that cannot escape a flow node."""
    words = _normalize_statement(value).rstrip(".!؟?").split()[:max_words]
    if not words:
        return ""
    if len(words) <= 3:
        return " ".join(words)
    split = int(math.ceil(len(words) / 2))
    return " ".join(words[:split]) + "\r" + " ".join(words[split:])


def _semantic_flow_nodes(
    segments: list[dict[str, Any]],
    selected_index: int,
    proposed_nodes: Iterable[Any] = (),
) -> list[str]:
    """Turn a spoken process into short, useful, editable flowchart nodes.

    LLMs occasionally split a Persian sentence at arbitrary token boundaries,
    which produces boxes such as «رو انجام دادم». Prefer explicit concepts
    found in the nearby transcript and only keep proposed nodes when they are
    independently understandable.
    """
    window = " ".join(
        _normalize_statement(item.get("text", ""))
        for item in segments[max(0, selected_index - 3) : selected_index + 9]
    ).casefold()

    # A recurring automation pipeline deserves editorial labels, not raw ASR
    # fragments. Every label is emitted only when its concept occurs locally.
    has_tradingview = any(value in window for value in ("تریدینگ‌ویو", "تریدینگ ویو", "tradingview"))
    has_webhook = any(value in window for value in ("وبهوک", "وب‌هوک", "webhook"))
    has_hermes = any(value in window for value in ("هرمس", "هوش‌مصنوعی", "هوش مصنوعی", "مدل لوکال", "مودل لوکال"))
    has_python = any(value in window for value in ("پایتون", "python"))
    has_metatrader = any(value in window for value in ("متاتریدر", "metatrader"))
    has_telegram = any(value in window for value in ("تلگرام", "telegram"))
    if has_tradingview and has_hermes and has_metatrader:
        nodes = ["سیگنال در تریدینگ‌ویو"]
        if has_webhook:
            nodes.append("ارسال با وب‌هوک")
        nodes.append("تصمیم‌گیری هرمس لوکال")
        if has_python and has_metatrader:
            nodes.append("اجرای پایتون در متاتریدر")
        else:
            nodes.append("اجرای معامله در متاتریدر")
        if has_telegram and len(nodes) < 4:
            nodes.append("گزارش نتیجه در تلگرام")
        return [_fit_node_text(node) for node in nodes[:4]]

    concepts = (
        (("ورودی", "داده", "اطلاعات"), "دریافت ورودی"),
        (("تحلیل", "بررسی"), "تحلیل داده"),
        (("سیگنال", "هشدار", "آلارم"), "ساخت سیگنال"),
        (("پایتون", "کد", "اسکریپت"), "اجرای کد"),
        (("معامله", "سفارش"), "اجرای معامله"),
        (("نتیجه", "گزارش", "تلگرام"), "نمایش نتیجه"),
    )
    inferred = [label for aliases, label in concepts if any(alias in window for alias in aliases)]
    if len(inferred) >= 3:
        return [_fit_node_text(node) for node in inferred[:4]]

    understandable: list[str] = []
    for raw in proposed_nodes:
        node = _normalize_statement(str(raw)).rstrip(".!؟?")
        words = node.split()
        if not 1 <= len(words) <= 7:
            continue
        if words[-1].casefold() in INCOMPLETE_ENDINGS:
            continue
        if any(node.startswith(prefix + " ") for prefix in ("که", "و", "رو", "یا", "چون")):
            continue
        understandable.append(_fit_node_text(node))
    return understandable[:4]


def _flowchart_headline(segments: list[dict[str, Any]], selected_index: int, fallback: str) -> str:
    """Prefer the speaker's nearby process question as the flowchart title."""
    nearby = segments[max(0, selected_index - 4) : selected_index + 3]
    for item in nearby:
        value = _normalize_statement(item.get("text", ""))
        normalized = value.casefold()
        if any(cue in normalized for cue in ("workflow", "فلوچارت", "چیکار کردم", "چطور", "مراحل")):
            words = value.split()
            if 3 <= len(words) <= 14:
                return value if value.endswith(("؟", "?", "!", ".")) else value + "؟"
    return fallback


def _native_copy_index(text: str) -> tuple[str, list[int]]:
    """Normalized comparison text with offsets back into the untouched source."""
    characters: list[str] = []
    offsets: list[int] = []
    for index, character in enumerate(text):
        if character == "ـ" or "\u064b" <= character <= "\u065f" or character == "\u0670":
            continue
        normalized = {"ي": "ی", "ك": "ک"}.get(character, character).casefold()
        for character in normalized:
            if not character.isalnum():
                if not characters or characters[-1] == " ":
                    continue
                character = " "
            characters.append(character)
            offsets.append(index)
    if characters and characters[-1] == " ":
        characters.pop()
        offsets.pop()
    return "".join(characters), offsets


def _native_glass_concise_copy(item: Mapping[str, Any], controls: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Choose a glossary label, never infer a noun or rewrite an assertion."""
    unchanged = dict(controls)
    if item.get("review_blocked") or item.get("needs_manual_copy"):
        return unchanged, None
    body = str(controls.get("Body", ""))
    provenance = item.get("copy_provenance", {})
    if not isinstance(provenance, Mapping) or not is_complete_statement(body):
        return unchanged, None
    grounding = provenance.get("grounding", {})
    if isinstance(grounding, Mapping) and grounding.get("supported") is False:
        return unchanged, None
    source = str(provenance.get("source_text", ""))
    body_normal, _ = _native_copy_index(body)
    headline_normal, _ = _native_copy_index(str(item.get("headline_fa", "")))
    source_normal, source_offsets = _native_copy_index(source)
    if not source or not body_normal or headline_normal != body_normal:
        return unchanged, None
    # Reject a repeated/ambiguous anchor instead of choosing whichever source
    # occurrence is convenient. Punctuation normalization does not change text.
    anchors = list(re.finditer(r"(?<!\S)" + re.escape(body_normal) + r"(?!\S)", source_normal))
    if len(anchors) != 1:
        return unchanged, None
    anchor = anchors[0]
    clause_start = source_offsets[anchor.start()]
    clause_end = source_offsets[anchor.end() - 1] + 1
    # Include an introductory qualification in the same source clause; a
    # proposed substring must not erase "perhaps" or "someone said".
    prefix = re.split(r"[.!؟?؛;]", source[:clause_start])[-1]
    context, _ = _native_copy_index(prefix + " " + body)
    tokens = context.split()
    excluded = {
        "نه", "نیست", "نیستن", "نیستند", "نبود", "نبوده", "نباشد", "نباشه",
        "نداره", "ندارد", "ندارند", "نداشت", "نداشته", "نیستم", "نیستی", "نبودم",
        "بدون", "هرگز", "هیچ", "اگر", "اگه", "وقتی",
        "چنانچه", "مگر", "شاید", "احتمالا", "احتمالی", "ممکن", "گویا", "ظاهرا",
        "انگار", "گمان", "حدس", "شنیدم", "شنیده", "گفت", "گفتند", "گفته", "ادعا", "بعضی", "برخی",
        "دیگران", "اونا", "آنها", "فلانی",
    }
    if (re.search(r"[؟?]", prefix + body) or any(token in excluded or token.startswith(("نمی", "نخواه")) for token in tokens)
            or any(phrase in context for phrase in ("به نظرم", "فکر می کنم", "فکر میکنم", "می گفت", "میگفت"))):
        return unchanged, None
    matches = []
    for persian, english in NATIVE_GLASS_TERM_LABELS.items():
        term_normal, _ = _native_copy_index(persian)
        for match in re.finditer(r"(?<!\S)" + re.escape(term_normal) + r"(?!\S)", body_normal):
            matches.append((persian, english, term_normal, match))
    if len(matches) != 1:
        return unchanged, None
    persian, english, term_normal, match = matches[0]
    term_start = source_offsets[anchor.start() + match.start()]
    term_end = source_offsets[anchor.start() + match.end() - 1] + 1
    while term_end < len(source) and ("\u064b" <= source[term_end] <= "\u065f" or source[term_end] == "\u0670"):
        term_end += 1
    # A half-space is permitted inside a glossary term, not as a false word
    # boundary for attached prefixes/suffixes such as "کامیونیتی‌ها".
    if ((term_start and source[term_start - 1] == "\u200c")
            or (term_end < len(source) and source[term_end] == "\u200c")):
        return unchanged, None
    exact_term = source[term_start:term_end]
    definition = bool(re.fullmatch(r"به .+ (?:می گن|میگن|می گویند|میگویند) " + re.escape(term_normal), body_normal))
    candidate = {**unchanged, "Title": english}
    if definition:
        candidate["Body"] = exact_term
    return candidate, {
        "method": "curated-domain-term-v1", "applied": False,
        "display_kind": "term-label" if definition else "term-topic-with-complete-source-clause",
        "glossary_term": persian, "english_title_source": "local-curated-term-glossary",
        "source_text": source, "complete_clause": body,
        "source_clause_span": [clause_start, clause_end], "source_term_span": [term_start, term_end],
        "exact_source_term": exact_term, "source_segment_ids": list(item.get("copy_segment_ids", [])),
        "original_controls": {"Title": unchanged.get("Title", ""), "Body": body},
        "candidate_controls": {"Title": candidate["Title"], "Body": candidate["Body"]},
    }


def _native_glass_editorial_copy(item: Mapping[str, Any], controls: Mapping[str, Any]):
    """An explicit topic label is a noun, not a shortened speaker assertion.

    Reuse every complete-clause, unique-anchor, glossary, negation and
    uncertainty check. No model English, invented words, numeric claims,
    approximate matches or incomplete sentences can qualify through this path.
    The original assertion and exact source span remain in the evidence.
    """
    candidate, evidence = _native_glass_concise_copy(item, controls)
    contract = item.get("native_runtime_contract", {})
    if (isinstance(contract, Mapping) and contract.get("allowExactTopicLabels") is True
            and evidence and evidence.get("display_kind") == "term-topic-with-complete-source-clause"):
        candidate["Body"] = evidence["exact_source_term"]
        evidence = {**evidence, "method": "curated-exact-topic-label-v1", "display_kind": "topic-label",
                    "assertion_displayed": False,
                    "candidate_controls": {"Title": candidate["Title"], "Body": candidate["Body"]}}
    return candidate, evidence


def guard_automatic_graphic_copy(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fail closed on machine sentences; a measured fit is not lexical QA.

    Automatic jobs currently have no audio-reviewed copy approval ledger.
    Only the narrow, independently curated glossary label is eligible here;
    it must be re-derived from the source clause and match the live controls.
    This never rewrites bad ASR into a plausible but invented assertion.
    """
    result = []
    for original in cues:
        item = dict(original)
        result.append(item)
        if item.get("review_blocked"):
            continue
        selection = item.get("native_copy_selection")
        allowed = False
        if isinstance(selection, Mapping) and selection.get("applied") is True:
            proposed = selection.get("original_controls", {})
            if isinstance(proposed, Mapping):
                expected, evidence = _native_glass_editorial_copy(item, proposed)
                actual = item.get("controls", {})
                allowed = bool(
                    evidence and evidence.get("display_kind") in {"term-label", "topic-label"}
                    and selection.get("display_kind") == evidence.get("display_kind")
                    and isinstance(actual, Mapping)
                    and all(_native_copy_index(str(actual.get(slot, "")))[0]
                            == _native_copy_index(str(expected.get(slot, "")))[0]
                            for slot in ("Title", "Body"))
                    and len(item.get("template_layers", [])) == 1
                    and all(_native_copy_index(str(item["template_layers"][0].get("controls", {}).get(slot, "")))[0]
                            == _native_copy_index(str(expected.get(slot, "")))[0]
                            for slot in ("Title", "Body"))
                )
        item["automatic_copy_gate"] = {
            "policy": "curated-label-until-audio-reviewed-copy-v1",
            "status": "curated-source-term" if allowed else "blocked-unverified-machine-copy",
            "audio_verified": False,
        }
        if not allowed:
            item["review_blocked"] = True
            item["review_blocked_reason"] = (
                "Automatic text withheld: an ASR sentence is not audio-verified copy. "
                "Readable geometry and a complete verb do not establish correct words. "
                "Review the original speech before inserting this editable draft."
            )
            item["qa_flags"] = list(dict.fromkeys(item.get("qa_flags", []) + ["UNVERIFIED_MACHINE_GRAPHIC_COPY"]))
            item.pop("sfx_cue", None)
            item["sfx"] = "none-review-blocked"
    return result


def _native_abar_font_path(postscript_name: str) -> Path:
    """Resolve the exact native weight, never the preview renderer's fallback."""
    if not re.fullmatch(r"AbarHighFaNum-(Black|ExtraBold|Bold|SemiBold|Regular)", postscript_name):
        raise ValueError("Native Glass typography requires an exact ABAR High FaNum weight")
    roots = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Microsoft/Windows/Fonts",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    )
    for root in roots:
        for extension in (".ttf", ".otf"):
            candidate = root / (postscript_name + extension)
            if candidate.is_file():
                family, style = ImageFont.truetype(str(candidate), 16).getname()
                normalized = lambda value: re.sub(r"[\s_-]+", "", value).casefold()
                if normalized(family) != "abarhighfanum" or normalized(style) != normalized(postscript_name.split("-", 1)[1]):
                    raise ValueError("Installed native font metadata does not match its ABAR filename")
                return candidate
    raise FileNotFoundError("Required native font is missing: " + postscript_name)


def _native_glass_candidates(text: str, font_path: Path, *, maximum_size: int,
                             minimum_size: int, max_lines: int) -> list[dict[str, Any]]:
    """Measure all words using the selected native font; overflow never truncates."""
    if not text.strip() or "…" in text or "..." in text:
        return []
    # Review 8 has a 720x380 plate, 28px inset and 30px horizontal entrance
    # travel. Its live text centers are authored at y=-92 (Title), y=42 (Body).
    max_width = 720 - 2 * (28 + 30)
    candidates = []
    for size in range(maximum_size, minimum_size - 1, -1):
        font = ImageFont.truetype(str(font_path), size)
        def bbox(value: str) -> tuple[int, int, int, int]:
            if re.search(r"[\u0600-\u06ff]", value):
                # Missing shaping support must fail closed, not measure broken
                # unjoined glyphs and declare a false native fit.
                import arabic_reshaper
                from bidi.algorithm import get_display
                value = get_display(arabic_reshaper.reshape(value))
            return font.getbbox(value)
        lines: list[str] = []
        overflow = False
        for paragraph in text.replace("\r", "\n").split("\n"):
            current = ""
            for word in paragraph.split():
                word_box = bbox(word)
                if word_box[2] - word_box[0] > max_width:
                    overflow = True
                    break
                proposal = (current + " " + word).strip()
                proposal_box = bbox(proposal)
                if current and proposal_box[2] - proposal_box[0] > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = proposal
            if overflow:
                break
            if current:
                lines.append(current)
        if overflow or not lines or len(lines) > max_lines:
            continue
        if " ".join(lines).split() != text.replace("\r", "\n").split():
            raise ValueError("Native typography word-preservation check failed")
        boxes = [bbox(line) for line in lines]
        leading = min(100, max(round(size * 1.10), max(box[3] - box[1] for box in boxes) + 2))
        if len(lines) > 1 and leading < max(box[3] - box[1] for box in boxes) + 2:
            continue
        measured_height = max(box[3] + i * leading for i, box in enumerate(boxes)) - min(
            box[1] + i * leading for i, box in enumerate(boxes))
        candidates.append({"size": size, "leading": leading, "lines": lines,
                           "width": max(box[2] - box[0] for box in boxes),
                           "height": measured_height})
    return candidates


def _apply_native_glass_typography(item: dict[str, Any], *, fps: float, height: int) -> None:
    """Opt-in post-placement fit for a hash-bound, native-QA-approved Review 8."""
    contract = item.get("native_runtime_contract", {})
    typography = contract.get("typography", {}) if isinstance(contract, Mapping) else {}
    if (item.get("element_id") != "hermes-glass-insight" or not isinstance(typography, Mapping)
            or typography.get("profile") != NATIVE_GLASS_PROFILE or item.get("review_blocked")):
        return
    try:
        if (contract.get("status") != "native-qa-approved" or contract.get("responsiveTiming") is not True
                or contract.get("durationControl") != "Duration Seconds"):
            raise ValueError("Native Glass runtime contract has not passed QA")
        template = Path(str(item.get("template_path", "")))
        asset_hash = str(contract.get("assetSha256", "")).lower()
        if (template.name != "Hafez Hermes Glass Insight Review 8.mogrt"
                or not re.fullmatch(r"[0-9a-f]{64}", asset_hash)
                or hashlib.sha256(template.read_bytes()).hexdigest() != asset_hash):
            raise ValueError("Native Glass asset identity differs from the approved Review 8")
        layers = item.get("template_layers", [])
        if len(layers) != 1 or layers[0].get("role") != "catalog-curated-element":
            raise ValueError("Native Glass profile requires one curated Title/Body layer")
        if Path(str(layers[0].get("template_path", ""))).resolve() != template.resolve():
            raise ValueError("Native Glass layer points to a different asset")
        layout = item.get("layout", {})
        scale = float(layout.get("scale", 0)) / 100
        if layout.get("collision_free") is not True or not math.isfinite(scale) or not 0 < scale <= 1:
            raise ValueError("No safe native Glass placement is available")
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Invalid native Glass frame rate")
        # Stay inside the already-tracked interval; do not extend into an
        # unexamined frame when snapping the native container and entry SFX.
        start_frame = math.ceil(float(item["start"]) * fps - 1e-7)
        end_frame = math.floor(float(item["end"]) * fps + 1e-7)
        duration = (end_frame - start_frame) / fps
        if not 1.6 <= duration <= 30:
            raise ValueError("Native Glass duration is outside the authored responsive range")
        controls = dict(layers[0].get("controls", {}))
        controls, copy_selection = _native_glass_editorial_copy(item, controls)
        if copy_selection:
            item["native_copy_selection"] = copy_selection
        fonts = typography.get("fonts", {"Title": "AbarHighFaNum-Black", "Body": "AbarHighFaNum-Black"})
        maximum = typography.get("maximumFontSize", {"Title": 84, "Body": 100})
        minimum = typography.get("minimumScreenPx1080", {"Title": 28, "Body": 30})
        choices = {}
        font_paths = {}
        for slot in ("Title", "Body"):
            max_size, min_screen = float(maximum[slot]), float(minimum[slot])
            if not (math.isfinite(max_size) and 1 <= max_size <= 100 and math.isfinite(min_screen) and 28 <= min_screen <= 100):
                raise ValueError("Invalid native typography size limits")
            font_paths[slot] = _native_abar_font_path(str(fonts[slot]))
            choices[slot] = _native_glass_candidates(
                str(controls.get(slot, "")), font_paths[slot], maximum_size=int(max_size),
                minimum_size=math.ceil(min_screen / scale), max_lines=2)
        fits = []
        for title in choices["Title"]:
            for body in choices["Body"]:
                title_top, title_bottom = -92 - title["height"] / 2, -92 + title["height"] / 2
                body_top, body_bottom = 42 - body["height"] / 2, 42 + body["height"] / 2
                if title_top < -162 or body_bottom > 162 or title_bottom + 12 > body_top:
                    continue
                score = title["size"] / float(maximum["Title"]) + body["size"] / float(maximum["Body"])
                fits.append((score, title, body))
        if not fits:
            raise ValueError("Complete native copy cannot fit without truncation, overlap or unreadable text")
        _, title, body = max(fits, key=lambda fit: (fit[0], fit[1]["size"], fit[2]["size"]))
        fitted = {"Title": title, "Body": body}
        sizes = {slot: values["size"] for slot, values in fitted.items()}
        required = ["Duration Seconds", "Layout Position", "Layout Scale"]
        controls["Duration Seconds"] = duration
        for slot, values in fitted.items():
            controls[slot] = "\r".join(values["lines"])
            controls[slot + " · Line Spacing"] = values["leading"]
            controls[slot + " · Tracking"] = 0
            color = BRAND_PRIMARY_SOFT if slot == "Title" else BRAND_TEXT
            controls[slot + " · Text Color"] = [value / 255 for value in color] + [1.0]
            required.extend(slot + suffix for suffix in (" · Line Spacing", " · Tracking", " · Text Color"))
        # The profile is tied to the audited Review 8 native component. Generic
        # legacy palette controls are not real parameters of this template.
        discarded_controls = sorted(set(controls) - NATIVE_GLASS_CONTROLS)
        controls = {key: value for key, value in controls.items() if key in NATIVE_GLASS_CONTROLS}
        item.update(start=start_frame / fps, end=end_frame / fps, duration=duration,
                    text_sizes=sizes, text_fonts=dict(fonts), controls=controls,
                    required_controls=list(dict.fromkeys(item.get("required_controls", []) + required)))
        item["template_layers"] = [{**layers[0], "controls": dict(controls), "text_sizes": dict(sizes),
                                    "text_fonts": dict(fonts), "text_controls": ["Title", "Body"],
                                    "required_controls": list(dict.fromkeys(layers[0].get("required_controls", []) + required))}]
        item["native_typography_fit"] = {
            "profile": NATIVE_GLASS_PROFILE, "status": "measured-fit-native-render-review-required",
            "asset_sha256": asset_hash, "selected_display_words_preserved": True,
            "discarded_legacy_controls": discarded_controls,
            "source_words_preserved": not bool(copy_selection and copy_selection["display_kind"] == "term-label"),
            "source_clause_preserved_in_metadata": bool(copy_selection),
            "plate_padding": 28, "horizontal_motion_margin": 30, "minimum_slot_gap": 12,
            "start_frame": start_frame, "end_frame": end_frame,
            "slots": {slot: {**values, "font_path": str(font_paths[slot]),
                              "screen_px_1080": round(values["size"] * scale, 3),
                              "screen_px": round(values["size"] * scale * height / 1080, 3)}
                      for slot, values in fitted.items()},
        }
        if isinstance(layout.get("template_fit"), dict):
            item["layout"] = {**layout, "template_fit": {**layout["template_fit"], "profile": NATIVE_GLASS_PROFILE}}
        if copy_selection:
            item["native_copy_selection"] = {**copy_selection, "applied": True}
        if isinstance(item.get("sfx_cue"), dict):
            item["sfx_cue"] = {**item["sfx_cue"], "start": round(start_frame / fps, 6), "start_frame": start_frame}
    except (ValueError, TypeError, KeyError, OSError, ImportError, OverflowError) as error:
        item["review_blocked"] = True
        item["review_blocked_reason"] = "Native typography review required: " + str(error)
        item["qa_flags"] = list(dict.fromkeys(item.get("qa_flags", []) + ["NATIVE_TYPOGRAPHY_FIT_FAILED"]))
        item["native_typography_fit"] = {"profile": NATIVE_GLASS_PROFILE, "status": "blocked", "reason": str(error)}
        item.pop("sfx_cue", None)
        item["sfx"] = "none-review-blocked"


def apply_face_safe_layout(
    cues: list[dict[str, Any]],
    *,
    video_path: str,
    clips: list[list[int] | tuple[int, ...]],
    fps: float,
    width: int,
    height: int,
    secondary_video_path: str | None = None,
    secondary_clips: list[list[int] | tuple[int, ...]] | None = None,
    motion_events: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Attach collision-free layout using the union of the full cue lifetime."""
    # Both visible camera angles must participate; a safe CAM1 placement is
    # not evidence of a safe CAM2 placement after a cut.
    if secondary_video_path and secondary_clips is not None:
        def visible_groups(track):
            return [_visible_source_frames(track, float(c["start"]), float(c["end"]), fps) for c in cues]
        primary_groups = visible_groups(clips)
        secondary_groups = visible_groups(secondary_clips)
        first, backend1 = detect_subject_box_unions(video_path, primary_groups, face_model_path())
        second, backend2 = detect_subject_box_unions(secondary_video_path, secondary_groups, face_model_path())
        tracked_intervals = []
        for a, b in zip(first, second):
            active = [value for value in (a, b) if value["sample_count"]]
            count = sum(value["sample_count"] for value in active)
            found = sum(value["detected_count"] for value in active)
            subjects = [value.get("subject_union") or (0.30, 0.08, 0.40, 0.84) for value in active]
            tracked_intervals.append({
                "sample_frames": a["sample_frames"], "sample_count": count,
                "detected_count": found, "coverage": found / max(1, count),
                "face_union": _union_normalized_boxes([value["face_union"] for value in active if value.get("face_union")]),
                "subject_union": _union_normalized_boxes(subjects),
                "body_complete": bool(active) and all(v.get("body_complete") is True for v in active),
                "body_tracking_method": "pphumanseg-independent-person-union",
                "cameras": {"cam1": a, "cam2": b},
            })
        backend = f"active-cameras:{backend1}+{backend2}"
    else:
        frame_groups = [
            _visible_source_frames(clips, float(cue["start"]), float(cue["end"]), fps)
            for cue in cues
        ]
        tracked_intervals, backend = detect_subject_box_unions(video_path, frame_groups, face_model_path())
    glow = max(0.0, min(1.0, float(os.environ.get("HERMES_GLOW_INTENSITY", str(BRAND_TOKENS["glow"]["intensity"])))))
    brand_controls = mogrt_control_values(BRAND_TOKENS, glow)
    material = MOTION_STYLE["material"]
    brand_controls.update(
        {
            "Glass Opacity": round(float(material["surfaceOpacity"]) * 100.0, 1),
            "Inner Light": round(float(material["innerLightOpacity"]) * 100.0, 1),
            "Background Dim": round(float(material["backgroundDimOpacity"]) * 100.0, 1),
            "Ambient Glow": round(float(material["ambientGlowOpacity"]) * 100.0, 1),
        }
    )
    placed: list[dict[str, Any]] = []
    region_usage = {name: 0 for name in REGION_SPECS}
    recent_regions: list[str] = []
    for index, cue in enumerate(cues):
        item = dict(cue)
        tracking = tracked_intervals[index]
        tracking = {**tracking, "body_complete": tracking.get("body_complete") is True and
                    _timeline_coverage_complete([clips, secondary_clips or []], float(cue["start"]), float(cue["end"]), fps)}
        face = tracking.get("face_union")
        subject = tracking.get("subject_union") or (0.30, 0.08, 0.40, 0.84)
        kind = str(item.get("kind", "statement"))
        fullscreen_takeover = (str(item.get("template", "")) == TEXT_ANIMATION_TITLE.template_name
                               or item.get("element_id") in {"hermes-title-hero-2", "hermes-title-hero-3"})
        word_count = len(str(item.get("text", "")).split())
        native_glass = (item.get("element_id") == "hermes-glass-insight" and
                        item.get("native_runtime_contract", {}).get("typography", {}).get("profile") == NATIVE_GLASS_PROFILE)
        # A native minimum is physical font size; generic MIN_LAYOUT_SCALE is
        # a ratio relative to a different, arbitrary region shape.
        minimum_scale = 28 / 84 if native_glass else MIN_LAYOUT_SCALE
        if native_glass:
            candidates = ("top-banner", "top-left", "top-right", "side-left", "side-right", "bottom-dock")
        elif fullscreen_takeover:
            candidates = ("fullscreen-takeover",)
        elif kind == "flowchart":
            candidates = ("side-left", "side-right")
        elif kind in {"hook", "chapter", "compare"}:
            candidates = ("bottom-dock", "top-banner", "top-left", "top-right")
        elif kind in {"number", "hud"}:
            candidates = ("top-right", "top-left", "side-right", "side-left")
        elif word_count > 10:
            candidates = ("bottom-dock", "top-banner", "top-left", "top-right")
        else:
            candidates = ("top-left", "top-right", "bottom-dock", "side-left", "side-right")
        scored: list[dict[str, Any]] = []
        for region in candidates:
            if region == "fullscreen-takeover":
                # The source image remains visible at low luminance under the
                # Hafez canvas, while the centered title card stays title-safe.
                rect = (0.1979, 0.30095, 0.6042, 0.3981)
                fit_scale, contained = 1.0, True
            elif native_glass:
                rect, fit_scale, contained = _fit_native_glass_region(region, subject)
            else:
                rect, fit_scale, contained = _fit_region_outside_subject(region, subject)
            safe_overlap = _intersection_ratio(rect, subject)
            actual_overlap = _intersection_ratio(rect, face) if face else 0.0
            scored.append(
                {
                    "face_overlap": actual_overlap,
                    "subject_overlap": safe_overlap,
                    "region": region,
                    "rect": rect,
                    "fit_scale": fit_scale,
                    "safe_area_contained": contained,
                }
            )

        # First protect the presenter. Among equally safe choices, rotate
        # placements so a long talking-head video never feels repetitive.
        collision_free = [
            entry
            for entry in scored
            if entry["face_overlap"] <= MAX_SAFE_OVERLAP
            and entry["subject_overlap"] <= MAX_SAFE_OVERLAP
            and entry["safe_area_contained"]
            and entry["fit_scale"] >= minimum_scale
        ]
        usable = collision_free or sorted(
            scored,
            key=lambda entry: (
                entry["face_overlap"],
                entry["subject_overlap"],
                -entry["fit_scale"],
            ),
        )[:2]
        chosen_layout = min(
            usable,
            key=lambda entry: (
                -entry["fit_scale"] if native_glass else 0,
                region_usage.get(entry["region"], 0) * 0.42
                + (1.6 if recent_regions and recent_regions[-1] == entry["region"] else 0.0)
                + (0.55 if len(recent_regions) > 1 and recent_regions[-2] == entry["region"] else 0.0)
                + entry["subject_overlap"] * 100.0
                + (1.0 - entry["fit_scale"]) * 2.5,
                candidates.index(entry["region"]),
            ),
        )
        actual_face_overlap = float(chosen_layout["face_overlap"])
        safe_overlap = float(chosen_layout["subject_overlap"])
        region = str(chosen_layout["region"])
        rect_x, rect_y, rect_w, rect_h = chosen_layout["rect"]
        fit_scale = float(chosen_layout["fit_scale"])
        centre_x, centre_y = rect_x + rect_w / 2.0, rect_y + rect_h / 2.0
        english_y = rect_y + rect_h * 0.38
        persian_y = rect_y + rect_h * 0.73
        nodes = [_fit_node_text(str(node)) for node in item.get("nodes", []) if str(node).strip()][:4]
        if nodes:
            item["nodes"] = nodes
        max_lines = 2 if kind in {"flowchart", "number", "hud"} else 3
        layout = {
            "region": region,
            "x": round(centre_x * width, 1),
            "y": round(centre_y * height, 1),
            "english_position": [round(centre_x * width, 1), round(english_y * height, 1)],
            "persian_position": [round(centre_x * width, 1), round(persian_y * height, 1)],
            "max_width": round(rect_w * width, 1),
            "max_height": round(rect_h * height, 1),
            "scale": round(min(100.0 if region in {"bottom-dock", "top-banner", "fullscreen-takeover"} else 88.0, fit_scale * 100.0), 1),
            "max_lines": max_lines,
            "safe_area_bbox": list(TITLE_SAFE_AREA),
            "region_bbox": [round(value, 4) for value in (rect_x, rect_y, rect_w, rect_h)],
            "safe_area_contained": bool(chosen_layout["safe_area_contained"]),
            "tracking_mode": "every-visible-source-frame-union",
            "tracking_sample_frames": list(tracking.get("sample_frames", [])),
            "tracking_sample_count": int(tracking.get("sample_count", 0)),
            "tracking_detected_count": int(tracking.get("detected_count", 0)),
            "tracking_coverage": float(tracking.get("coverage", 0.0)),
            "tracking_cameras": tracking.get("cameras", {}),
            "body_tracking_method": tracking.get("body_tracking_method", "unverified"),
            "body_tracking_complete": tracking.get("body_complete") is True,
            "tracking_frame_evidence": tracking.get("frame_evidence", []),
            "face_union_bbox": [round(value, 4) for value in face] if face else None,
            "subject_union_bbox": [round(value, 4) for value in subject],
            "face_bbox": [round(value, 4) for value in face] if face else None,
            "safe_face_bbox": [round(value, 4) for value in subject],
            "face_overlap_ratio": round(actual_face_overlap, 4),
            "safe_margin_overlap_ratio": round(safe_overlap, 4),
            "overlap_ratio": round(safe_overlap, 4),
            "collision_free": (
                fullscreen_takeover
                or (
                    actual_face_overlap <= MAX_SAFE_OVERLAP
                    and safe_overlap <= MAX_SAFE_OVERLAP
                    and bool(chosen_layout["safe_area_contained"])
                    and fit_scale >= minimum_scale
                )
            ),
            "collision_policy": (
                "intentional-fullframe-takeover" if fullscreen_takeover else "avoid-full-subject-union"
            ),
            "source_visibility": (
                round(1.0 - float(material["backgroundDimOpacity"]), 3) if fullscreen_takeover else 1.0
            ),
        }
        if str(item.get("template", "")) == TEXT_ANIMATION_TITLE.template_name:
            base_width, base_height = MOTION_STYLE["families"]["fullscreen-glass"].get("baseSize", [1120, 430])
            physical_scale = min(
                layout["scale"],
                rect_w * width / max(1.0, float(base_width)) * 100.0,
                rect_h * height / max(1.0, float(base_height)) * 100.0,
            )
            layout["scale"] = round(max(1.0, physical_scale), 1)
        if item.get("element_id") == "hermes-glass-insight":
            # Approved AE Review 7 plate, measured in its 1920x1080 comp.
            # A generic card's fit ratio is not the physical size of this MOGRT.
            authored_width = rect_w * TEXT_ANIMATION_TITLE.coordinate_width
            authored_height = rect_h * TEXT_ANIMATION_TITLE.coordinate_height
            physical_scale = min(
                layout["scale"],
                max(0.0, authored_width - 24.0) / 720.0 * 100.0,
                max(0.0, authored_height - 24.0) / 380.0 * 100.0,
            )
            layout["scale"] = math.floor(max(0.0, physical_scale) * 10.0) / 10.0
            layout["template_fit"] = {
                "profile": "approved-glass-review-7",
                "plate_size": [720, 380],
                "halo_margin": 24,
                "coordinate_space": [1920, 1080],
            }
            if layout["scale"] < 1.0:
                layout["collision_free"] = False
        layout["mogrt_coordinate_space"] = [
            TEXT_ANIMATION_TITLE.coordinate_width,
            TEXT_ANIMATION_TITLE.coordinate_height,
        ]
        layout["mogrt_english_position"] = [
            round(layout["english_position"][0] / max(1, width) * TEXT_ANIMATION_TITLE.coordinate_width, 1),
            round(layout["english_position"][1] / max(1, height) * TEXT_ANIMATION_TITLE.coordinate_height, 1),
        ]
        layout["mogrt_layout_position"] = [
            round(layout["x"] / max(1, width) * TEXT_ANIMATION_TITLE.coordinate_width, 1),
            round(layout["y"] / max(1, height) * TEXT_ANIMATION_TITLE.coordinate_height, 1),
        ]
        item["placement"] = region
        item["layout"] = layout
        controls = dict(item.get("controls", {}))
        controls.update(
            {
                "FA Headline": item.get("headline_fa", item.get("text", "")),
                "Layout Position": [layout["x"], layout["y"]],
                "Layout Scale": layout["scale"],
                "Max Text Width": layout["max_width"],
                "Glow Intensity": round(glow * 100.0, 1),
            }
        )
        controls.update(brand_controls)
        if str(item.get("template", "")) == TEXT_ANIMATION_TITLE.template_name:
            controls.update(
                {
                    TEXT_ANIMATION_TITLE.position_control: layout["mogrt_layout_position"],
                    TEXT_ANIMATION_TITLE.persian_control: item.get("headline_fa", item.get("text", "")),
                    TEXT_ANIMATION_TITLE.scale_control: layout["scale"],
                }
            )
        controls.update({f"Node {node_index + 1}": node for node_index, node in enumerate(nodes)})
        item["controls"] = controls
        layers: list[dict[str, Any]] = []
        for raw_layer in item.get("template_layers", []):
            layer = dict(raw_layer)
            layer_controls = dict(layer.get("controls", {}))
            if layer.get("role") == "bilingual-hero-title":
                layer_controls.update(
                    {
                        TEXT_ANIMATION_TITLE.english_control: item.get("headline_en", ""),
                        TEXT_ANIMATION_TITLE.persian_control: item.get("headline_fa", item.get("text", "")),
                        TEXT_ANIMATION_TITLE.position_control: layout["mogrt_layout_position"],
                        TEXT_ANIMATION_TITLE.scale_control: layout["scale"],
                        "Max Text Width": layout["max_width"],
                        "Glow Intensity": round(glow * 100.0, 1),
                    }
                )
            elif layer.get("role") == "english-display-title":
                layer_controls.update(
                    {
                        TEXT_ANIMATION_TITLE.position_control: layout["mogrt_english_position"],
                        TEXT_ANIMATION_TITLE.scale_control: layout["scale"],
                    }
                )
            elif layer.get("role") == "catalog-curated-element":
                layer_controls.update({
                    "Layout Position": layout["mogrt_layout_position"],
                    "Layout Scale": layout["scale"],
                    "Show Background": 1 if fullscreen_takeover else 0,
                })
            else:
                layer_controls.update(
                    {
                        "FA Headline": item.get("headline_fa", item.get("text", "")),
                        "Layout Position": layout["persian_position"],
                        "Layout Scale": round(min(72.0, layout["scale"] * 0.78), 1),
                        "Max Text Width": layout["max_width"],
                        "Glow Intensity": round(glow * 100.0, 1),
                    }
                )
            layer_controls.update(brand_controls)
            if item.get("element_id") == "hermes-title-hero-3":
                layer_controls["Glow Radius"] = 200
                layer_controls["Glow Intensity"] = round(20 * glow / 0.82, 2)
            layer["controls"] = layer_controls
            layers.append(layer)
        if layers:
            item["template_layers"] = layers
        _apply_native_glass_typography(item, fps=fps, height=height)
        transformed = any(_unverified_motion_overlap(track, float(cue["start"]), float(cue["end"]), fps, motion_events or [])
                          for track in (clips, secondary_clips or []))
        item["layout"]["transform_status"] = "uncalibrated-fcpcurve-overlap" if transformed else "identity-during-cue"
        spatial_reason = ("Independent per-frame body tracking incomplete." if tracking.get("body_complete") is not True
                          else "Native camera transform requires spatial calibration." if transformed
                          else "No safe, readable template placement." if not fullscreen_takeover and not layout["collision_free"] else "")
        if spatial_reason:
            item["review_blocked"] = True
            item["review_blocked_reason"] = (item.get("review_blocked_reason", "") + " " + spatial_reason).strip()
            flag = "BODY_TRACKING_REVIEW_REQUIRED" if tracking.get("body_complete") is not True else "CAMERA_TRANSFORM_REVIEW_REQUIRED" if transformed else "SAFE_PLACEMENT_REVIEW_REQUIRED"
            item["qa_flags"] = list(dict.fromkeys(item.get("qa_flags", []) + [flag]))
            item["layout"]["collision_free"] = False
            item.pop("sfx_cue", None)
            item["sfx"] = "none-review-blocked"
        item["brand"] = {
            "id": BRAND_TOKENS["id"],
            "palette": dict(BRAND_TOKENS["palette"]),
            "radius": dict(BRAND_TOKENS["radius"]),
            "glow": dict(BRAND_TOKENS["glow"]),
        }
        placed.append(item)
        region_usage[region] = region_usage.get(region, 0) + 1
        recent_regions.append(region)
    return placed, backend


def _english_kicker(text: str, marker: dict[str, Any]) -> str:
    explicit = str(
        marker.get("title_en", "")
        or marker.get("headline_en", "")
        or marker.get("kicker_en", "")
    ).strip().upper()
    if 2 <= len(explicit.split()) <= 6 and re.fullmatch(r"[A-Z0-9 &+\-./]+", explicit):
        return explicit
    normalized = text.casefold()
    for cues, label in SAFE_ENGLISH_KICKERS:
        if any(cue in normalized for cue in cues):
            return label
    return "KEY INSIGHT"


def _template_for(kind: str) -> tuple[str, Path]:
    if kind in TEXT_ANIMATION_TITLE.allowed_kinds:
        text_animation = resolve_text_animation_title()
        if text_animation:
            return TEXT_ANIMATION_TITLE.template_name, text_animation
    custom_name = CUSTOM_TEMPLATE_MAP.get(kind, CUSTOM_TEMPLATE_MAP["statement"])
    custom_path = MOTION_PACK_ROOT / custom_name
    if custom_path.exists():
        return custom_name, custom_path
    fallback_kind = kind if kind in TEMPLATE_MAP else "keyword"
    fallback_name = TEMPLATE_MAP[fallback_kind]
    return fallback_name, TEMPLATE_ROOT / fallback_name


def _catalog_runtime_controls(element: Mapping[str, Any], duration: float) -> dict[str, float]:
    """Opt in only after the actual responsive MOGRT passes native QA.

    The old Glass Review 7 does not expose this control. A template name alone
    must never authorize writing a property that its installed asset lacks.
    """
    contract = element.get("runtimeContract", {})
    if (element.get("id") != "hermes-glass-insight"
            or not isinstance(contract, Mapping)
            or contract.get("status") != "native-qa-approved"
            or contract.get("responsiveTiming") is not True
            or contract.get("durationControl") != "Duration Seconds"
            or not math.isfinite(duration) or duration <= 0):
        return {}
    return {"Duration Seconds": round(duration, 6)}


def _catalog_review_failure(element: Mapping[str, Any] | None) -> str:
    """Release only an explicitly native-approved template; retain other drafts.

    A missing legacy contract, unknown status, or uncatalogued fallback is not
    evidence of native QA. Do not infer approval from a filename or availability.
    """
    contract = element.get("runtimeContract", {}) if isinstance(element, Mapping) else {}
    if isinstance(contract, Mapping) and contract.get("status") == "native-qa-approved":
        return ""
    if isinstance(contract, Mapping) and contract.get("status") == "native-qa-failed":
        return str(contract.get("reason") or "The authored template failed native visual QA; review is required before insertion.")
    return "No native QA approval is recorded for this template. Editable draft only; native QA is required before automatic insertion."


def _catalog_control_values(
    element: Mapping[str, Any],
    *,
    persian_text: str,
    english_title: str,
    nodes: Iterable[str] = (),
    short_title_fa: str = "",
) -> dict[str, str]:
    """Populate only facts we can prove; unknown editable values stay as …."""
    node_values = [str(value).strip() for value in nodes if str(value).strip()]
    number_match = re.search(r"(?:[0-9۰-۹]+(?:[.,٫][0-9۰-۹]+)?\s*(?:%|درصد)?)", persian_text)
    number_value = number_match.group(0) if number_match else "…"
    authored_defaults = element.get("defaultText", {})
    if not isinstance(authored_defaults, Mapping):
        authored_defaults = {}
    controls: dict[str, str] = {}
    for slot in element.get("textSlots", []):
        normalized = str(slot).casefold()
        node_match = re.fullmatch(r"node\s+(\d+)", normalized)
        option_match = re.fullmatch(r"option\s+(\d+)", normalized)
        if node_match:
            index = int(node_match.group(1)) - 1
            controls[str(slot)] = node_values[index] if index < len(node_values) else "…"
        elif option_match:
            index = int(option_match.group(1)) - 1
            controls[str(slot)] = node_values[index] if index < len(node_values) else "…"
        elif any(key in normalized for key in ("value", "price", "percentage", "rate", "total")):
            controls[str(slot)] = number_value
        elif normalized in {"cta text", "channel name", "channel subtitle"}:
            value = authored_defaults.get(str(slot))
            controls[str(slot)] = value.strip() if isinstance(value, str) and value.strip() else (
                "سابسکرایب کن" if normalized == "cta text" else "…"
            )
        elif (normalized == "title" and 1 <= len(short_title_fa.split()) <= 5
              and contains_exact_phrase(persian_text, short_title_fa)):
            controls[str(slot)] = short_title_fa
        elif normalized == "title" and "Body" in element.get("textSlots", []):
            controls[str(slot)] = english_title or "…"
        elif any(key in normalized for key in ("body", "quote", "description", "primary text", "title")):
            controls[str(slot)] = persian_text
        elif any(key in normalized for key in ("label", "period", "greeting")):
            controls[str(slot)] = english_title or "…"
        else:
            controls[str(slot)] = "…"
    return controls


def _catalog_subscribe_cue(
    segments: list[dict[str, Any]],
    duration: float,
    catalog: Mapping[str, Any],
    *, word_context: dict[str, Any] | None = None, fps: float = 30.0,
) -> dict[str, Any] | None:
    matches = exact_subscribe_segments(segments, catalog)
    if not matches:
        return None
    match = matches[0]
    timing = exact_trigger_timing(segments, match["matched_phrase"], word_context,
                                  fps=fps, timeline_duration=duration)
    if timing["selected"]:
        match = {**match, **timing["selected"]}
    element, selection_trace = select_editorial_element(
        {"kind": "cta", "semantic_role": "subscribe", "element_id": SUBSCRIBE_ELEMENT_ID},
        match["matched_phrase"],
        catalog=catalog,
    )
    if not element:
        return None
    template_path = resolve_catalog_mogrt(element)
    start = max(0.0, float(match["start"]))
    preferred_duration = 4.2
    cue_duration = max(0.0, min(preferred_duration, duration - start))
    if timing["selected"]:
        cue_duration = timing["selected"]["end"] - start
    controls = _catalog_control_values(
        element,
        persian_text=str(match["matched_phrase"]),
        english_title="SUBSCRIBE",
    )
    qa_flags = [] if template_path.is_file() else ["MISSING_CATALOG_MOGRT"]
    native_failure = _catalog_review_failure(element)
    if native_failure:
        qa_flags.append("NATIVE_TEMPLATE_QA_FAILED")
    timing_failure = "" if timing["selected"] else "Exact spoken CTA timing requires source-word review; segment-start placement is disabled."
    if timing_failure:
        qa_flags.append("EXACT_TRIGGER_TIMING_REVIEW_REQUIRED")
    missing_authored_text = any(value == "…" for value in controls.values())
    if missing_authored_text:
        qa_flags.append("NEEDS_COPY_REVIEW")
    copy_failure = "Authored channel text is not available; do not invent the channel identity." if missing_authored_text else ""
    return {
        "id": "graphic-subscribe-001",
        "segment_id": int(match["segment_id"]),
        "start": round(start, 3),
        "end": round(start + cue_duration, 3),
        "duration": round(cue_duration, 3),
        "text": str(match["matched_phrase"]),
        "headline_fa": str(match["matched_phrase"]),
        "headline_en": "SUBSCRIBE",
        "kicker_en": "SUBSCRIBE",
        "kind": "cta",
        "semantic_role": "subscribe",
        "element_id": element["id"],
        "element_label_fa": element.get("labelFa", ""),
        "template": element["mogrtName"],
        "template_path": str(template_path),
        "template_family": element["familyId"],
        "asset_mode": "catalog-curated",
        "template_layers": [{
            "role": "catalog-curated-element",
            "track": 3,
            "template": element["mogrtName"],
            "template_path": str(template_path),
            "font_family": "Abar High FaNum",
            "font_family_editable": True,
            "font_size_editable": True,
            "text_controls": list(element.get("textSlots", [])),
            "controls": controls,
        }],
        "font_family": "Abar High FaNum",
        "font_role": "title",
        "font_weight": 800,
        "title_font_family": "Abar High FaNum",
        "title_font_weight": 800,
        "body_font_family": "Abar High FaNum",
        "body_font_weight": 400,
        "sfx_recipe": str(element.get("sfxRecipe", "insight-air")),
        "transition": "hafez-ui-entry",
        "typography_motion": "hafez-ui-entry",
        "priority": "high",
        "placement": "bottom-dock",
        "required_by_trigger": True,
        "exact_trigger": str(match["matched_phrase"]),
        "trigger_timing": timing,
        "selection_trace": selection_trace,
        "palette_bindings": dict(element.get("paletteBindings", {})),
        "controls": controls,
        "qa_flags": qa_flags,
        "needs_manual_copy": missing_authored_text,
        "review_blocked": bool(native_failure or copy_failure or timing_failure),
        "review_blocked_reason": " ".join(value for value in (native_failure, copy_failure) if value) or timing_failure,
    }


def build_graphic_cues(
    segments: list[dict[str, Any]],
    duration: float,
    markers: Iterable[dict[str, Any]] = (),
    *,
    fps: float = 30.0,
    family_history: Iterable[str] | None = None,
    word_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Plan only semantically justified, source-grounded on-screen cues."""
    if not segments or duration <= 0:
        return []
    editorial_catalog = load_editorial_catalog()
    history = list(family_history) if family_history is not None else load_template_family_history()
    density = os.environ.get("HERMES_GRAPHIC_DENSITY", "balanced").casefold()
    cadence = {"balanced": 42.0, "dense": 30.0, "max": 22.0}.get(density, 42.0)
    spacing = {"balanced": 16.0, "dense": 12.0, "max": 9.0}.get(density, 16.0)
    importance_floor = {"balanced": 0.9, "dense": 0.65, "max": 0.45}.get(density, 0.9)
    target_count = max(1, min(24, int(round(duration / cadence))))
    chosen: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    marker_by_segment: dict[int, dict[str, Any]] = {}
    for item in markers:
        if not isinstance(item, dict) or not str(item.get("segment_id", "")).lstrip("-").isdigit():
            continue
        if str(item.get("type", "GRAPHIC")).upper() not in {"GRAPHIC", "TEXT", "TITLE", "CHAPTER", "HOOK", "FLOWCHART", "COMPARE"}:
            continue
        segment_id = int(item["segment_id"])
        old = marker_by_segment.get(segment_id, {})
        if any(item.get(key) for key in ("headline_fa", "overlay_text", "nodes", "visual_kind")) or not old:
            marker_by_segment[segment_id] = item
    for index in range(target_count):
        target = min(duration - 0.1, (index + 0.35) * duration / target_count)
        candidates = [
            item
            for item in segments
            if int(item["id"]) not in used_ids
            and all(abs(float(item["start"]) - float(old["start"])) >= spacing
                    for old in chosen if not old.get("review_blocked"))
            and abs(float(item["start"]) - target) <= max(22.0, duration / target_count)
            and (
                int(item["id"]) in marker_by_segment
                or (not marker_by_segment and _semantic_importance(item) >= importance_floor)
            )
        ]
        if not candidates:
            continue
        # Editorial markers that request a specific visual (especially a real
        # flowchart or comparison) must win over generic cadence candidates.
        # Otherwise a valid AI direction can be skipped simply because a nearby
        # sentence happened to score slightly higher on lexical importance.
        segment = max(
            candidates,
            key=lambda item: _importance(item, target)
            + (100.0 if int(item["id"]) in marker_by_segment else 0.0),
        )
        selected_index = segments.index(segment)
        marker = marker_by_segment.get(int(segment["id"]), {})
        copy_decision = _complete_statement_decision(segments, selected_index, marker)
        if not copy_decision:
            continue
        requested_segment_id = int(segment["id"])
        if copy_decision.get("source") == "later-corrected-take":
            anchor_id = copy_decision.get("anchor_segment_id")
            anchor = next((item for item in segments if int(item["id"]) == anchor_id), None)
            if anchor is None:
                continue
            # These segments have already been remapped to the Tight timeline.
            # Read the anchor from that same collection, never the raw ASR time.
            if int(anchor["id"]) in used_ids or any(
                abs(float(anchor["start"]) - float(old["start"])) < spacing
                for old in chosen if not old.get("review_blocked")
            ):
                used_ids.add(requested_segment_id)
                continue
            segment = anchor
            selected_index = segments.index(segment)
        text = str(copy_decision["text"])
        segment_id = int(segment["id"])
        has_number = bool(re.search(r"[0-9۰-۹]", text))
        requested_kind = str(marker.get("visual_kind", marker.get("template_hint", ""))).casefold()
        has_nodes = isinstance(marker.get("nodes"), list) and len(marker.get("nodes", [])) >= 3
        allowed_kinds = {"statement", "kinetic", "hud", "number", "flowchart", "compare", "chapter"}
        explicit_kind = next((value for value in allowed_kinds if value in requested_kind), "")
        if has_nodes:
            kind = "flowchart"
        elif explicit_kind:
            kind = explicit_kind
        elif any(word in requested_kind for word in ("compare", "versus", "vs")):
            kind = "compare"
        elif index == 0:
            kind = "hook"
        elif str(marker.get("type", "")).upper() == "CHAPTER":
            kind = "chapter"
        elif has_number:
            kind = "number"
        else:
            kind = ("statement", "kinetic", "statement", "hud", "keyword", "typewriter")[index % 6]
        if kind == "flowchart":
            text = _flowchart_headline(segments, selected_index, text)
        template_name, template_path = _template_for(kind)
        start = float(marker["start"]) if (marker.get("copy_time_binding") == "unique-original-word-quote"
            and int(marker.get("segment_id", -1)) == segment_id) else float(segment["start"])
        cue_duration = (
            TEXT_ANIMATION_TITLE.default_duration
            if template_name == TEXT_ANIMATION_TITLE.template_name
            else 5.3 if kind in {"flowchart", "compare"}
            else 4.2 if kind in {"hook", "chapter"}
            else 3.1 + (index % 3) * 0.35
        )
        nodes = (
            _semantic_flow_nodes(segments, selected_index, marker.get("nodes", []))
            if kind == "flowchart"
            else [str(node).strip() for node in marker.get("nodes", []) if str(node).strip()][:4]
        )
        selection_input = {
            "kind": kind,
            "visual_kind": kind,
            "semantic_role": str(marker.get("semantic_role", "editorial-beat")),
            "element_id": str(marker.get("element_id", "")),
            "nodes": nodes,
            "options": marker.get("options", []),
            "option_count": marker.get("option_count", 0),
        }
        selected_element, selection_trace = select_editorial_element(
            selection_input,
            text,
            catalog=editorial_catalog,
            family_history=history,
        )
        explicit_text_animation_override = bool(os.environ.get("HERMES_TEXT_ANIMATION_ROOT", "").strip()) and (
            template_name == TEXT_ANIMATION_TITLE.template_name
        )
        if explicit_text_animation_override and not str(marker.get("element_id", "")).strip():
            selected_element = None
            selection_trace = {
                **selection_trace,
                "selected_id": "external-text-animation-title",
                "score": 100.0,
                "reasons": ["explicit-text-animation-root"],
            }
        catalog_template_path: Path | None = None
        if selected_element:
            catalog_template_path = resolve_catalog_mogrt(selected_element)
            template_name = str(selected_element["mogrtName"])
            template_path = catalog_template_path
            duration_range = selected_element.get("durationSeconds", [cue_duration, cue_duration])
            if isinstance(duration_range, list) and len(duration_range) == 2:
                cue_duration = min(float(duration_range[1]), max(float(duration_range[0]), cue_duration))
        font_role = _cue_font_role(kind)
        english_title = _english_kicker(text, marker)
        semantic_subtitle = str(marker.get("semantic_subtitle_fa", "")).strip()
        semantic_grounding = copy_grounding(
            semantic_subtitle,
            (copy_decision.get("source_text", text),),
        )
        allow_semantic_subtitle = (
            os.environ.get("HERMES_COPY_MODE", "source-faithful").casefold() == "grounded-summary"
            and is_complete_statement(semantic_subtitle)
            and semantic_grounding["supported"]
        )
        if allow_semantic_subtitle:
            display_persian = semantic_subtitle
            if display_persian[-1] not in ".!؟?":
                display_persian += "."
        else:
            display_persian = text
        typography = bilingual_typography_contract(
            english_title=english_title,
            persian_statement=display_persian,
            persian_font_family=_font_family("body"),
        )
        is_text_animation = template_name == TEXT_ANIMATION_TITLE.template_name
        template_layers = [
            {
                "role": "bilingual-hero-title" if is_text_animation else "single-graphic",
                "track": 3,
                "template": template_name,
                "template_path": str(template_path),
                "font_family": "User selectable (Arial Bold default)" if is_text_animation else _font_family(font_role),
                "intended_font_family": "Relaxe" if is_text_animation else _font_family(font_role),
                "font_compatibility_status": (
                    "native-premiere-font-picker-enabled" if is_text_animation else "native"
                ),
                "font_family_editable": bool(is_text_animation),
                "font_size_editable": bool(is_text_animation),
                "controls": (
                    {
                        TEXT_ANIMATION_TITLE.english_control: english_title,
                        TEXT_ANIMATION_TITLE.persian_control: display_persian,
                    }
                    if is_text_animation
                    else {
                        "FA Headline": display_persian,
                        "EN Kicker": english_title,
                        **{f"Node {node_index + 1}": node for node_index, node in enumerate(nodes)},
                    }
                ),
            }
        ]
        if selected_element:
            catalog_controls = _catalog_control_values(
                selected_element,
                persian_text=display_persian,
                english_title=english_title,
                nodes=nodes,
                short_title_fa=str(marker.get("short_title_fa", "")).strip(),
            )
            catalog_controls.update(_catalog_runtime_controls(
                selected_element, max(0.0, min(cue_duration, duration - start))
            ))
            template_layers = [
                {
                    "role": "catalog-curated-element",
                    "track": 3,
                    "template": template_name,
                    "template_path": str(template_path),
                    "font_family": "Abar High FaNum",
                    "intended_font_family": "Abar High FaNum",
                    "font_compatibility_status": "native-premiere-font-picker-enabled",
                    "font_family_editable": True,
                    "font_size_editable": True,
                    "font_roles": dict(selected_element.get("fontRoles", {})),
                    "text_controls": list(selected_element.get("textSlots", [])),
                    "controls": catalog_controls,
                }
            ]
        chosen.append(
            {
                "id": f"graphic-{index + 1:03d}",
                "segment_id": segment_id,
                "start": round(start, 3),
                "end": round(min(duration, start + cue_duration), 3),
                "duration": round(min(cue_duration, duration - start), 3),
                "text": text,
                "headline_fa": display_persian,
                "semantic_subtitle_source": "grounded-marker" if display_persian != text else "speaker-copy",
                "copy_source": str(copy_decision.get("source", "unknown")),
                "copy_segment_ids": list(copy_decision.get("segment_ids", [segment_id])),
                "requested_segment_id": requested_segment_id,
                "copy_provenance": {
                    "source_text": str(copy_decision.get("source_text", text)),
                    "display_text": display_persian,
                    "mode": str(copy_decision.get("source", "unknown")),
                    "grounding": dict(copy_decision.get("grounding", {})),
                },
                "needs_manual_copy": bool(copy_decision.get("needs_manual_copy", False)),
                "review_blocked": bool(copy_decision.get("needs_manual_copy", False) or _catalog_review_failure(selected_element)),
                "review_blocked_reason": (
                    "No reliable complete source clause. Editable draft only; source-audio review required before insertion."
                    if copy_decision.get("needs_manual_copy") else _catalog_review_failure(selected_element)
                ),
                "qa_flags": (
                    (["NEEDS_COPY_REVIEW"] if copy_decision.get("needs_manual_copy") else [])
                    + (["MISSING_CATALOG_MOGRT"] if selected_element and not catalog_template_path.is_file() else [])
                    + (["NATIVE_TEMPLATE_QA_FAILED"] if _catalog_review_failure(selected_element) else [])
                ),
                "kicker_en": english_title,
                "headline_en": english_title,
                "nodes": nodes,
                "kind": kind,
                "template": template_name,
                "template_path": str(template_path),
                "template_family": (
                    str(selected_element["familyId"])
                    if selected_element
                    else str(family_for_kind(kind, MOTION_STYLE).get("familyId", "hafez-insight-card"))
                ),
                "asset_mode": "catalog-curated" if selected_element else (TEXT_ANIMATION_TITLE.asset_mode if is_text_animation else "bundled"),
                "template_rule": template_rule_payload() if is_text_animation else None,
                "template_layers": template_layers,
                "element_id": str(selected_element.get("id", "")) if selected_element else "",
                "element_label_fa": str(selected_element.get("labelFa", "")) if selected_element else "",
                "element_mogrt_available": bool(catalog_template_path and catalog_template_path.is_file()),
                "selection_trace": selection_trace,
                "palette_bindings": dict(selected_element.get("paletteBindings", {})) if selected_element else {},
                "sfx_recipe": str(selected_element.get("sfxRecipe", "")) if selected_element else "",
                "bilingual_typography": typography,
                "font_family": "Abar High FaNum" if selected_element else _font_family(font_role),
                "font_role": font_role,
                "font_weight": _font_weight(font_role),
                "typography_motion": _typography_motion(kind),
                "semantic_role": str(marker.get("semantic_role", "editorial-beat")),
                "editorial_reason": str(marker.get("comment", "")).strip(),
                "transition": str(marker.get("transition", _typography_motion(kind))),
                "sfx": str(marker.get("sfx", "none")),
                "title_font_family": _font_family("title"),
                "title_font_weight": _font_weight("title"),
                "body_font_family": _font_family("body"),
                "body_font_weight": _font_weight("body"),
                "track": 3,
                "priority": "high" if kind in {"hook", "number", "chapter"} else "normal",
                "placement": "center" if kind in {"hook", "chapter", "flowchart", "compare"} else ("left" if index % 2 == 0 else "right"),
                "controls": (
                    catalog_controls
                    if selected_element
                    else {
                        "FA Headline": text,
                        "EN Kicker": english_title,
                        **(
                            {
                                TEXT_ANIMATION_TITLE.english_control: english_title,
                                TEXT_ANIMATION_TITLE.persian_control: display_persian,
                            }
                            if is_text_animation
                            else {}
                        ),
                        **{f"Node {node_index + 1}": node for node_index, node in enumerate(nodes)},
                    }
                ),
            }
        )
        contract = selected_element.get("runtimeContract", {}) if selected_element else {}
        if (isinstance(contract, Mapping) and isinstance(contract.get("typography"), Mapping)
                and contract["typography"].get("profile") == NATIVE_GLASS_PROFILE):
            chosen[-1]["native_runtime_contract"] = dict(contract)
        used_ids.add(segment_id)
        used_ids.add(requested_segment_id)
    subscribe_cue = _catalog_subscribe_cue(segments, duration, editorial_catalog, word_context=word_context, fps=fps)
    if subscribe_cue:
        subscribe_start = float(subscribe_cue["start"])
        chosen = [cue for cue in chosen if abs(float(cue["start"]) - subscribe_start) >= 2.0]
        chosen.append(subscribe_cue)
    ordered = sorted(chosen, key=lambda item: float(item["start"]))
    active, family_identity = select_template_families(
        [item for item in ordered if not item.get("review_blocked")], history, limit=4
    )
    # Drafts remain editable in the plan but cannot claim a visual family slot
    # or displace a verified graphic from the active identity.
    curated = sorted(active + [item for item in ordered if item.get("review_blocked")],
                     key=lambda item: float(item["start"]))
    for item in curated:
        item["family_identity"] = family_identity
        if item.get("review_blocked"):
            item["sfx"] = "none-review-blocked"
            item.pop("sfx_cue", None)
            continue
        sfx_cue = build_sfx_cue(item, fps)
        if sfx_cue:
            item["sfx"] = sfx_cue["role"]
            item["sfx_cue"] = sfx_cue
        else:
            item["sfx"] = "missing-curated-local-sfx"
            flags = list(item.get("qa_flags", []))
            if "MISSING_ENTRY_SFX" not in flags:
                flags.append("MISSING_ENTRY_SFX")
            item["qa_flags"] = flags
    return curated


def _wrap_words(text: str, maximum: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        proposal = " ".join(current + [word])
        if current and len(proposal) > maximum:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def _english_font(size: int) -> ImageFont.FreeTypeFont:
    relaxe = resolve_relaxe_font()
    if relaxe:
        return ImageFont.truetype(str(relaxe), size)
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("segoeuib.ttf", "arialbd.ttf", "segoeui.ttf"):
        candidate = windows / name
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _gradient_panel(size: tuple[int, int], accent: tuple[int, int, int]) -> Image.Image:
    width, height = size
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = panel.load()
    for y in range(height):
        for x in range(width):
            edge = min(x, y, width - 1 - x, height - 1 - y)
            alpha = int(198 + 28 * max(0.0, min(1.0, edge / 55.0)))
            mix = x / max(1, width - 1)
            pixels[x, y] = (
                min(255, int(BRAND_SURFACE[0] + accent[0] * 0.035 * mix)),
                min(255, int(BRAND_SURFACE[1] + accent[1] * 0.055 * mix)),
                min(255, int(BRAND_SURFACE[2] + accent[2] * 0.035 * mix)),
                alpha,
            )
    return panel


def _wrap_pixels(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    """RTL-agnostic logical wrapping measured with the final Persian font."""
    paragraphs = str(text).replace("\r", "\n").split("\n")
    lines: list[str] = []
    for paragraph in paragraphs:
        current: list[str] = []
        for word in paragraph.split():
            proposal = " ".join(current + [word])
            shaped = _shape_rtl(proposal)
            box = draw.textbbox((0, 0), shaped, font=font)
            if current and box[2] - box[0] > max_width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
    return lines[:max_lines]


def _fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    weight: int,
    start_size: int,
    minimum_size: int,
    max_width: int,
    max_height: int,
    max_lines: int,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """Fit editable copy to a known MOGRT box; never overflow or clip."""
    for size in range(start_size, minimum_size - 1, -2):
        font = _load_font(font_path, size, weight)
        lines = _wrap_pixels(draw, text, font, max_width, max_lines)
        line_height = int(size * 1.30)
        logical_word_count = sum(len(line.split()) for line in lines)
        if lines and line_height * len(lines) <= max_height and logical_word_count >= len(str(text).replace("\r", " ").split()):
            return font, lines, line_height
    font = _load_font(font_path, minimum_size, weight)
    lines = _wrap_pixels(draw, text, font, max_width, max_lines)
    return font, lines, int(minimum_size * 1.30)


def _render_flowchart_asset(
    canvas: Image.Image,
    cue: dict[str, Any],
    width: int,
    height: int,
    title_font_path: Path,
    body_font_path: Path,
) -> None:
    draw = ImageDraw.Draw(canvas)
    accent = BRAND_PRIMARY + (255,)
    layout = dict(cue.get("layout") or {})
    region = str(layout.get("region", cue.get("placement", "side-left")))
    centre_x = int(layout.get("x", width * (0.20 if "left" in region else 0.80)))
    max_width = int(layout.get("max_width", width * 0.30))
    max_height = int(layout.get("max_height", height * 0.50))
    en_font = _english_font(max(15, int(height * 0.021)))
    title_font, title_lines, title_line_height = _fit_lines(
        draw,
        str(cue.get("headline_fa", cue.get("text", ""))),
        title_font_path,
        _font_weight("title"),
        max(34, int(height * 0.052)),
        max(24, int(height * 0.033)),
        max_width - 36,
        max(48, int(height * 0.11)),
        2,
    )
    kicker = str(cue.get("kicker_en", "AUTOMATION FLOW"))
    header_y = max(70, int(height * 0.13))
    draw.text((centre_x, header_y), kicker, anchor="mm", font=en_font, fill=accent)
    for line_index, logical in enumerate(title_lines):
        draw.text(
            (centre_x, header_y + int(height * 0.055) + line_index * title_line_height),
            _shape_rtl(logical),
            anchor="mm",
            font=title_font,
            fill=BRAND_TEXT + (255,),
        )
    nodes = list(cue.get("nodes") or [])[:4]
    if len(nodes) < 3:
        nodes = ["دریافت داده", "تحلیل الگوریتم", "تولید سیگنال", "اجرای تصمیم"]
    node_width = max(240, min(max_width, int(width * 0.30)))
    gap = max(12, int(height * 0.017))
    node_height = max(74, int((max_height - gap * (len(nodes) - 1)) / len(nodes)))
    start_x = int(centre_x - node_width / 2)
    y = max(int(height * 0.30), int(layout.get("y", height * 0.55) - max_height / 2))
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for index, node in enumerate(nodes):
        node_y = y + index * (node_height + gap)
        gd.rounded_rectangle((start_x, node_y, start_x + node_width, node_y + node_height), BRAND_CARD_RADIUS, outline=BRAND_PRIMARY + (210,), width=7)
        if index < len(nodes) - 1:
            gd.line((centre_x, node_y + node_height, centre_x, node_y + node_height + gap), fill=BRAND_PRIMARY_SOFT + (220,), width=8)
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(BRAND_GLOW_RADIUS)))
    draw = ImageDraw.Draw(canvas)
    for index, node in enumerate(nodes):
        node_y = y + index * (node_height + gap)
        panel = _gradient_panel((node_width, node_height), accent[:3])
        mask = Image.new("L", panel.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, node_width - 1, node_height - 1), BRAND_CARD_RADIUS, fill=255)
        canvas.paste(panel, (start_x, node_y), mask)
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((start_x, node_y, start_x + node_width, node_y + node_height), BRAND_CARD_RADIUS, outline=accent, width=3)
        draw.text((start_x + 22, node_y + 14), f"0{index + 1}", font=en_font, fill=accent)
        node_font, node_lines, node_line_height = _fit_lines(
            draw, str(node), body_font_path, _font_weight("body"),
            max(25, int(height * 0.031)), max(19, int(height * 0.024)),
            node_width - 100, node_height - 24, 2,
        )
        centre_y = node_y + node_height // 2 - (len(node_lines) - 1) * node_line_height // 2
        for line_index, logical in enumerate(node_lines):
            draw.text((centre_x + 18, centre_y + line_index * node_line_height), _shape_rtl(logical), anchor="mm", font=node_font, fill=BRAND_TEXT + (255,))
        if index < len(nodes) - 1:
            connector_end = node_y + node_height + gap
            draw.line((centre_x, node_y + node_height, centre_x, connector_end - 8), fill=BRAND_PRIMARY_SOFT + (255,), width=4)
            draw.polygon([(centre_x - 7, connector_end - 9), (centre_x, connector_end), (centre_x + 7, connector_end - 9)], fill=BRAND_PRIMARY_SOFT + (255,))


def render_graphic_assets(
    cues: list[dict[str, Any]],
    output_dir: str | Path,
    width: int,
    height: int,
) -> list[dict[str, Any]]:
    """Render optional preview-only PNGs without making them timeline assets."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    title_font_path = _font_path("title")
    body_font_path = _font_path("body")
    rendered: list[dict[str, Any]] = []
    for index, cue in enumerate(cues, 1):
        kind = str(cue.get("kind", "keyword"))
        # A rejected native placement is not a drawable preview rectangle. Keep
        # its editable review data, but never let an optional PNG abort the edit
        # or make a blocked proposal appear approved.
        preview_skip = "skipped-review-blocked" if cue.get("review_blocked") is True else ""
        layout = dict(cue.get("layout") or {})
        if not preview_skip:
            try:
                bounds = (("max_width", 180, width), ("max_height", 100, height),
                          ("x", 0, width), ("y", 0, height))
                for key, minimum, maximum in bounds:
                    if key in layout:
                        value = float(layout[key])
                        if not math.isfinite(value) or not minimum <= value <= maximum:
                            preview_skip = "skipped-invalid-geometry"
                            break
            except (TypeError, ValueError, OverflowError):
                preview_skip = "skipped-invalid-geometry"
        if preview_skip:
            item = dict(cue)
            item.pop("asset_path", None)
            item["preview_status"] = preview_skip
            rendered.append(item)
            continue
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if kind == "flowchart":
            _render_flowchart_asset(canvas, cue, width, height, title_font_path, body_font_path)
            asset_path = directory / f"hafez-{index:03d}-{kind}.png"
            canvas.save(asset_path)
            item = dict(cue)
            item["asset_path"] = str(asset_path)
            item["font_path"] = str(body_font_path)
            item["title_font_path"] = str(title_font_path)
            item["body_font_path"] = str(body_font_path)
            rendered.append(item)
            continue
        layout = dict(cue.get("layout") or {})
        font_size = 78 if kind in {"hook", "chapter"} else 70 if kind == "number" else 54
        font_role = str(cue.get("font_role", _cue_font_role(kind)))
        font_path = title_font_path if font_role == "title" else body_font_path
        max_width = int(layout.get("max_width", width * (0.68 if cue.get("placement") in {"center", "bottom-dock", "top-banner"} else 0.34)))
        max_height = int(layout.get("max_height", height * 0.25))
        padding_x, padding_y = int(font_size * 0.55), int(font_size * 0.36)
        font, logical_lines, line_height = _fit_lines(
            ImageDraw.Draw(canvas),
            str(cue.get("text", "")),
            font_path,
            int(cue.get("font_weight", _font_weight(font_role))),
            font_size,
            30,
            max(180, max_width - padding_x * 2),
            max(70, max_height - padding_y * 2 - 38),
            int(layout.get("max_lines", 3)),
        )
        visual_lines = [_shape_rtl(line) for line in logical_lines]
        draw = ImageDraw.Draw(canvas)
        bboxes = [draw.textbbox((0, 0), line, font=font) for line in visual_lines]
        text_width = max((box[2] - box[0] for box in bboxes), default=600)
        text_height = line_height * max(1, len(visual_lines))
        box_width = min(max_width, text_width + padding_x * 2)
        box_height = min(max_height, text_height + padding_y * 2 + 40)
        placement = str(cue.get("placement", "right"))
        centre_x = int(layout.get("x", width / 2))
        centre_y = int(layout.get("y", height * 0.78))
        x = max(40, min(width - box_width - 40, centre_x - box_width // 2))
        y = max(36, min(height - box_height - 48, centre_y - box_height // 2))
        accent_rgb = BRAND_NEGATIVE if str(cue.get("sentiment", "")).lower() in {"negative", "warning", "error"} else BRAND_PRIMARY
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.rounded_rectangle((x, y, x + box_width, y + box_height), BRAND_CARD_RADIUS, outline=accent_rgb + (225,), width=8)
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(BRAND_GLOW_RADIUS)))
        panel = _gradient_panel((box_width, box_height), accent_rgb)
        mask = Image.new("L", (box_width, box_height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, box_width - 1, box_height - 1), BRAND_CARD_RADIUS, fill=255)
        canvas.paste(panel, (x, y), mask)
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((x, y, x + box_width, y + box_height), BRAND_CARD_RADIUS, outline=accent_rgb + (235,), width=3)
        draw.rounded_rectangle(
            (x + box_width - 14, y + 20, x + box_width - 5, y + box_height - 20),
            radius=5,
            fill=accent_rgb + (255,),
        )
        kicker = str(cue.get("kicker_en", "KEY INSIGHT"))
        en_font = _english_font(max(18, int(font_size * .34)))
        draw.text((x + box_width - padding_x, y + 18), kicker, anchor="ra", font=en_font, fill=accent_rgb + (255,))
        for line_index, line in enumerate(visual_lines):
            bbox = bboxes[line_index]
            line_width = bbox[2] - bbox[0]
            tx = x + (box_width - line_width) // 2
            ty = y + padding_y + 24 + line_index * line_height
            draw.text(
                (tx + 3, ty + 4), line, font=font, fill=(0, 0, 0, 210), stroke_width=1
            )
            draw.text(
                (tx, ty), line, font=font, fill=BRAND_TEXT + (255,), stroke_width=1,
                stroke_fill=BRAND_SURFACE + (230,),
            )
        asset_path = directory / f"hafez-{index:03d}-{kind}.png"
        canvas.save(asset_path)
        item = dict(cue)
        item["asset_path"] = str(asset_path)
        item["font_path"] = str(font_path)
        item["title_font_path"] = str(title_font_path)
        item["body_font_path"] = str(body_font_path)
        rendered.append(item)
    return rendered


def build_action_markers(
    events: list[dict[str, Any]],
    camera_schedule: list[dict[str, Any]],
    graphics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build concise, genuinely executable timeline markers."""
    markers: list[dict[str, Any]] = []
    for event in events:
        scale = float(event.get("scale", 112.0))
        markers.append(
            {
                "segment_id": int(event.get("segment_id", -1)),
                "type": "PUNCH",
                "start": float(event["start"]),
                "end": float(event["end"]),
                "confidence": float(event.get("score", 0.85)),
                "comment": (
                    f"PUNCH | Scale {scale:.0f}% | ورود نرم 8f | حفظ مرکز صورت | "
                    f"خروج نرم 8f | دلیل: {event.get('kind', 'emphasis')}"
                ),
            }
        )
    for index, shot in enumerate(camera_schedule):
        if index == 0:
            continue
        camera = str(shot["camera"]).upper()
        markers.append(
            {
                "segment_id": -1,
                "type": camera,
                "start": float(shot["start"]),
                "end": min(float(shot["end"]), float(shot["start"]) + 2.0),
                "confidence": 1.0,
                "comment": (
                    f"{camera} ACTIVE | دوربین دیگر Disabled | Hard Cut روی شروع جمله | "
                    f"تا {shot['end']:.1f}s | {shot.get('reason', '')}"
                )[:500],
            }
        )
    for cue in graphics:
        blocked = bool(cue.get("review_blocked"))
        markers.append(
            {
                "segment_id": int(cue.get("segment_id", -1)),
                "type": "CHECK" if blocked else "TEXT",
                "start": float(cue["start"]),
                "end": float(cue["end"]),
                "confidence": 1.0,
                "comment": (
                    f"{'REVIEW BLOCKED' if blocked else 'TEXT'} | «{cue['text']}» | {cue['duration']:.1f}s | "
                    f"Template: {cue['template']} | Font: {cue['font_family']} | "
                    f"Type Motion: {cue.get('typography_motion', 'adaptive-2026')} | ورود/خروج داخل MOGRT"
                )[:500],
            }
        )
    return sorted(markers, key=lambda item: (float(item["start"]), str(item["type"])))


def write_professional_plan(
    path: str | Path,
    *,
    sequence_name: str,
    fps: float,
    camera_schedule: list[dict[str, Any]],
    events: list[dict[str, Any]],
    graphics: list[dict[str, Any]],
    history_path: str | Path | None = None,
) -> None:
    selected_families = list(dict.fromkeys(str(item.get("template_family", "")) for item in graphics
                                         if item.get("template_family") and not item.get("review_blocked")))[:4]
    saved_history = save_template_family_history(selected_families, history_path) if history_path else None
    if history_path:
        save_template_family_history(selected_families)
    sfx_cues = [dict(item["sfx_cue"]) for item in graphics
               if not item.get("review_blocked") and isinstance(item.get("sfx_cue"), dict)]
    payload = {
        "protocol": "hermes-professional-edit-v2",
        "sequence": sequence_name,
        "fps": fps,
        "video_tracks": {
            "cam1": 0,
            "cam2": 1,
            "png_guide": 2,
            "mogrt": 3,
            "mogrt_persian": 4,
        },
        "audio_tracks": {
            "camera_1": 0,
            "camera_2": 1,
            "voice_master": 2,
            "sfx": 3,
        },
        "camera_schedule": camera_schedule,
        "punch_ins": events,
        "graphics": graphics,
        "editorial_catalog": catalog_plan_payload(),
        "sfx_cues": sfx_cues,
        "audio_policy": {
            "dialogue_role": "camera1-original" if os.environ.get("HERMES_PRESERVE_CAMERA1_AUDIO", "1") == "1" else "voice-master",
            "voice_untouched_by_ducking": True,
            "ducking_target": "background-music-only",
            "background_music_present": False,
            "ducking_applied": False,
            "motion_sfx_protocol": "hafez-curated-sfx-v1",
            "motion_sfx_sample_rate": int(MOTION_STYLE["audio"]["sampleRate"]),
            "motion_sfx_true_peak_ceiling_dbfs": float(MOTION_STYLE["audio"]["truePeakCeilingDbfs"]),
        },
        "template_root": str(TEMPLATE_ROOT),
        "brand_tokens": {
            "id": BRAND_TOKENS["id"],
            "palette": dict(BRAND_TOKENS["palette"]),
            "radius": dict(BRAND_TOKENS["radius"]),
            "glow": dict(BRAND_TOKENS["glow"]),
            "rules": dict(BRAND_TOKENS["rules"]),
        },
        "motion_style": {
            "id": MOTION_STYLE["id"],
            "material": dict(MOTION_STYLE["material"]),
            "motion": dict(MOTION_STYLE["motion"]),
            "typography": dict(MOTION_STYLE["typography"]),
            "families": dict(MOTION_STYLE["families"]),
            "visual_limits": dict(MOTION_STYLE["visualLimits"]),
            "provenance": dict(MOTION_STYLE.get("provenance", {})),
        },
        "font_family": _font_family("body"),
        "motion_finisher": {
            "required": True,
            "editable_mogrt_only": True,
            "mute_png_guide_after_success": False,
            "png_guide_present": False,
            "premiere_import_report_required": True,
            "reject_face_collisions": True,
            "reject_text_overflow": True,
            "glow_intensity": float(os.environ.get("HERMES_GLOW_INTENSITY", str(BRAND_TOKENS["glow"]["intensity"]))),
            "copy_mode": os.environ.get("HERMES_COPY_MODE", "source-faithful"),
            "entry_curve": list(MOTION_STYLE["motion"]["entryCurve"]),
            "exit_curve": list(MOTION_STYLE["motion"]["exitCurve"]),
            "linear_allowed": False,
            "maximum_overshoot_percent": float(MOTION_STYLE["motion"]["maximumOvershootPercent"]),
        },
        "curation": {
            "mode": "rule-based",
            "model_role": "proposal-only",
            "invalid_copy_policy": "review-blocked-editable-draft-no-render-no-sfx",
            "ellipsis_allowed": "standalone-placeholder-only",
            "template_family_limit": 4,
            "prefer_history": True,
            "selected_template_families": selected_families,
            "history_path": str(saved_history or ""),
            "spatial_qa": "multi-frame-union",
            "visual_critic": "final-validation-only",
        },
        "typography": {
            "system": "Hafez Adaptive Type 2026",
            "principles": [
                "variable-weight",
                "adaptive-tracking",
                "editorial-scale",
                "tactile-detail",
                "purposeful-kinetic-type",
            ],
            "title": {
                "family": _font_family("title"),
                "path": str(_font_path("title")),
                "weight": _font_weight("title"),
                "usage": "chapter, hook, metric, kinetic, compare",
            },
            "english_display": {
                "family": "Relaxe",
                "path": str(resolve_relaxe_font() or ""),
                "adobe_host_default": "Arial Bold",
                "relaxe_override_required": True,
                "compatibility_status": "blocked-by-adobe-2026-font-crash",
                "usage": "large editable English title in text-animation-title",
            },
            "body": {
                "family": _font_family("body"),
                "path": str(_font_path("body")),
                "weight": _font_weight("body"),
                "usage": "statement, support text, flowchart nodes",
            },
            "premiere_note": "PNGهای XML فقط راهنمای دیداری‌اند؛ Hafez Finisher آن‌ها را پس از جایگذاری کامل MOGRTها Mute می‌کند.",
        },
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")
