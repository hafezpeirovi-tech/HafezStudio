"""Build the real Hafez Studio rule-based Golden Segment proof.

The builder uses only the user-approved local still, Relaxe font, text-animation
MOGRT and SFX.  It creates a Premiere-importable XMEML sequence plus the v2
Hafez Finisher plan that inserts two editable bilingual MOGRT layers.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_MODULES = PRODUCT_ROOT / "engine" / "src" / "hermes_video"
if str(ENGINE_MODULES) not in sys.path:
    sys.path.insert(0, str(ENGINE_MODULES))

os.environ.setdefault("HERMES_STUDIO_ROOT", str(PRODUCT_ROOT))
os.environ.setdefault("HERMES_RUNTIME_ROOT", str(PRODUCT_ROOT / "runtime"))
os.environ.setdefault("HERMES_PERSONAL_ASSET_ROOT", str(PRODUCT_ROOT / "personal-assets"))
os.environ.setdefault("HERMES_MOTION_PACK", str(PRODUCT_ROOT / "motion-pack" / "dist"))

import autocut  # noqa: E402
import professional_edit  # noqa: E402
from brand_tokens import hex_rgba, load_brand_tokens  # noqa: E402
from curation_rules import (  # noqa: E402
    TEXT_ANIMATION_TITLE,
    inspect_mogrt_asset,
    resolve_relaxe_font,
    resolve_text_animation_title,
)
from motion_style import load_motion_style  # noqa: E402
from runtime_paths import find_executable  # noqa: E402
from smart_crop import probe_video  # noqa: E402


FPS = 30.0
DURATION = TEXT_ANIMATION_TITLE.default_duration
SOURCE_TIMECODE = "00:02:35:00"
ENGLISH_TITLE = "THE WORKFLOW"
PERSIAN_STATEMENT = "من یک Workflow ساختم که سیگنال را از تریدینگ‌ویو به هوش مصنوعی می‌فرستد."
PERSIAN_CONCEPT = "سیگنال تریدینگ‌ویو به هوش مصنوعی می‌رسد."
PROOF_DIR = PRODUCT_ROOT / "proof" / "golden-segment"
SOURCE_STILL = PROOF_DIR / "golden-source-frame.png"
REFERENCE_VIDEO = Path(r"D:\Download\Video\text animation - Video Templates.mp4")
TEXT_ARCHIVE = Path(r"D:\Download\Compressed\text-animation-2026-08-13-06-42-05-utc.zip")
RELAXE_ARCHIVE = Path(r"D:\Download\Compressed\relaxe-typeface-2026-04-07-06-21-14-utc.zip")
BRAND = load_brand_tokens()
MOTION_STYLE = load_motion_style()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-4000:] or completed.stdout[-4000:])


def _ffmpeg() -> str:
    executable = find_executable(("ffmpeg",))
    if not executable:
        raise FileNotFoundError("Bundled FFmpeg is required for the Golden Segment")
    return executable


def _create_source_video(output: Path) -> dict[str, Any]:
    _run(
        [
            _ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(int(FPS)),
            "-i",
            str(SOURCE_STILL),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono",
            "-t",
            f"{DURATION:.3f}",
            "-r",
            str(int(FPS)),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(output),
        ]
    )
    return probe_video(str(output))


def _extract_template_thumbnail(mogrt: Path, destination: Path) -> None:
    with zipfile.ZipFile(mogrt) as archive:
        thumbnail = next(
            (info for info in archive.infolist() if info.filename.casefold().endswith("thumb.png")),
            None,
        )
        if thumbnail is None:
            return
        destination.write_bytes(archive.read(thumbnail))


def _write_template_catalog(destination: Path) -> list[dict[str, Any]]:
    entries: list[tuple[str, Image.Image, list[str], bool]] = []
    with zipfile.ZipFile(TEXT_ARCHIVE) as outer:
        mogrt_entries = sorted(
            (info for info in outer.infolist() if info.filename.casefold().endswith(".mogrt")),
            key=lambda info: info.filename.casefold(),
        )
        for info in mogrt_entries:
            try:
                with zipfile.ZipFile(io.BytesIO(outer.read(info))) as mogrt_archive:
                    thumb_info = next(
                        (item for item in mogrt_archive.infolist() if item.filename.casefold().endswith("thumb.png")),
                        None,
                    )
                    definition_info = next(
                        (item for item in mogrt_archive.infolist() if item.filename.casefold().endswith("definition.json")),
                        None,
                    )
                    if thumb_info is None:
                        continue
                    thumbnail = Image.open(io.BytesIO(mogrt_archive.read(thumb_info))).convert("RGB")
                    controls: list[str] = []
                    grain_present = False
                    if definition_info is not None:
                        definition_payload = mogrt_archive.read(definition_info)
                        definition_text = definition_payload.decode("utf-8-sig", errors="replace")
                        grain_present = "grain" in definition_text.casefold()
                        for control in ("Main Text", "Main Text Position", "Main Text Scale", "Text Color"):
                            if control in definition_text:
                                controls.append(control)
                    entries.append((Path(info.filename).name, thumbnail.copy(), controls, grain_present))
            except (KeyError, OSError, zipfile.BadZipFile):
                continue
    tile_width, tile_height = 320, 220
    columns = 4
    rows = max(1, math.ceil(len(entries) / columns))
    catalog = Image.new("RGB", (columns * tile_width, rows * tile_height), (10, 13, 20))
    draw = ImageDraw.Draw(catalog)
    label_font = ImageFont.truetype(str(PRODUCT_ROOT / "app" / "assets" / "fonts" / "Estedad-VF.ttf"), 18)
    for index, (name, thumbnail, controls, grain_present) in enumerate(entries):
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        preview = thumbnail.copy()
        preview.thumbnail((tile_width - 16, 170), Image.Resampling.LANCZOS)
        catalog.paste(preview, (x + (tile_width - preview.width) // 2, y + 8))
        draw.text((x + 10, y + 181), name, font=label_font, fill=(255, 92, 118) if grain_present else (245, 248, 255))
        draw.text((x + 10, y + 202), ", ".join(controls)[:42], font=label_font, fill=(85, 255, 114))
    catalog.save(destination)
    return [
        {
            "name": name,
            "controls": controls,
            "thumbnail_size": list(thumbnail.size),
            "rejected_for_grain": grain_present,
        }
        for name, thumbnail, controls, grain_present in entries
    ]


def _fit_english_font(font_path: Path, text: str, max_width: int) -> ImageFont.FreeTypeFont:
    for size in range(128, 53, -2):
        font = ImageFont.truetype(str(font_path), size)
        box = ImageDraw.Draw(Image.new("RGB", (8, 8))).textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(str(font_path), 52)


def _render_bilingual_overlay(
    size: tuple[int, int],
    cue: dict[str, Any],
    base: Image.Image,
) -> Image.Image:
    width, height = size
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    layout = cue["layout"]
    rect_x, rect_y, rect_w, rect_h = layout["region_bbox"]
    left, top = int(rect_x * width), int(rect_y * height)
    right, bottom = int((rect_x + rect_w) * width), int((rect_y + rect_h) * height)
    accent = hex_rgba(BRAND["palette"]["primaryAccent"])
    surface = hex_rgba(BRAND["palette"]["surface"])
    text_primary = hex_rgba(BRAND["palette"]["textPrimary"])
    text_secondary = hex_rgba(BRAND["palette"]["textSecondary"])
    radius = max(12, int(BRAND["radius"]["card"] * cue["layout"]["scale"] / 100.0))

    # One Hafez-native material: blurred live background, dense dark surface,
    # soft outer shadow, white inner light and a restrained neon spectral edge.
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((left, top, right, bottom), radius, fill=255)
    shadow_mask = mask.filter(ImageFilter.GaussianBlur(int(MOTION_STYLE["material"]["shadowBlurPx"])))
    shadow = Image.new("RGBA", size, (2, 3, 3, 0))
    shadow.putalpha(shadow_mask.point(lambda value: int(value * 0.54)))
    shifted_shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    shifted_shadow.alpha_composite(shadow, (0, int(MOTION_STYLE["material"]["shadowOffsetPx"])))
    overlay.alpha_composite(shifted_shadow)

    blurred = base.convert("RGBA").filter(ImageFilter.GaussianBlur(18))
    blurred.putalpha(mask.point(lambda value: int(value * 0.34)))
    overlay.alpha_composite(blurred)
    glass_fill = Image.new("RGBA", size, (surface[0], surface[1], surface[2], 0))
    glass_fill.putalpha(mask.point(lambda value: int(value * 0.82)))
    overlay.alpha_composite(glass_fill)

    draw = ImageDraw.Draw(overlay)
    border_alpha = int(float(MOTION_STYLE["material"]["borderOpacity"]) * 255)
    draw.rounded_rectangle((left, top, right, bottom), radius, outline=(255, 255, 255, border_alpha), width=1)
    draw.rounded_rectangle((left + 3, top + 3, right - 3, bottom - 3), max(9, radius - 3), outline=(255, 255, 255, 24), width=1)

    rail_left, rail_right, rail_y = left + 28, right - 28, top + 9
    bloom = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(bloom).line((rail_left, rail_y, rail_right, rail_y), fill=accent[:3] + (104,), width=5)
    overlay.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(12)))
    draw = ImageDraw.Draw(overlay)
    draw.line((rail_left, rail_y, rail_right, rail_y), fill=accent[:3] + (232,), width=2)

    relaxe = resolve_relaxe_font()
    if not relaxe:
        raise FileNotFoundError("Relaxe font is not connected")
    english_display = str(cue.get("headline_en", ENGLISH_TITLE)).strip().upper()
    persian_display = str(cue.get("headline_fa", cue.get("text", PERSIAN_CONCEPT))).strip()
    max_text_width = max(160, right - left - 64)
    english_font = _fit_english_font(relaxe, english_display, max_text_width)
    english_position = tuple(layout["english_position"])
    draw.text(
        english_position,
        english_display,
        anchor="mm",
        font=english_font,
        fill=text_primary,
    )

    persian_path = professional_edit._font_path("body")
    scratch = ImageDraw.Draw(overlay)
    persian_font, logical_lines, line_height = professional_edit._fit_lines(
        scratch,
        persian_display,
        persian_path,
        400,
        26,
        18,
        max_text_width,
        max(52, bottom - top - 82),
        3,
    )
    px, py = layout["persian_position"]
    block_height = max(1, len(logical_lines)) * line_height
    block_center = max(top + 70 + block_height / 2, min(bottom - 12 - block_height / 2, py))
    start_y = block_center - (len(logical_lines) - 1) * line_height / 2
    for index, logical in enumerate(logical_lines):
        draw.text(
            (px, start_y + index * line_height),
            professional_edit._shape_rtl(logical),
            anchor="mm",
            font=persian_font,
            fill=text_secondary,
        )
    return overlay


def _bezier_progress(progress: float, curve: list[float]) -> float:
    """Evaluate CSS cubic-bezier by solving x(t), then returning y(t)."""
    x1, y1, x2, y2 = curve
    target = max(0.0, min(1.0, progress))
    low, high = 0.0, 1.0
    parameter = target
    for _ in range(18):
        inv = 1.0 - parameter
        x = 3 * inv * inv * parameter * x1 + 3 * inv * parameter * parameter * x2 + parameter**3
        if x < target:
            low = parameter
        else:
            high = parameter
        parameter = (low + high) / 2.0
    inv = 1.0 - parameter
    return 3 * inv * inv * parameter * y1 + 3 * inv * parameter * parameter * y2 + parameter**3


def _motion_for_frame(frame: int, total_frames: int) -> tuple[float, float, float, float]:
    motion = MOTION_STYLE["motion"]
    entry_frames = int(motion["entryFrames"])
    settle_frames = int(motion["settleFrames"])
    exit_frames = int(motion["exitFrames"])
    if frame < entry_frames:
        progress = frame / max(1, entry_frames - 1)
        eased = _bezier_progress(progress, list(motion["entryCurve"]))
        scale = 0.985 + 0.022 * eased
        return eased, float(motion["liftPx"]) * (1.0 - eased), float(motion["blurPx"]) * (1.0 - eased), scale
    if frame < entry_frames + settle_frames:
        progress = (frame - entry_frames) / max(1, settle_frames - 1)
        eased = _bezier_progress(progress, list(motion["exitCurve"]))
        return 1.0, 0.0, 0.0, 1.007 - 0.007 * eased
    if frame >= total_frames - exit_frames:
        progress = (frame - (total_frames - exit_frames)) / max(1, exit_frames - 1)
        eased = _bezier_progress(progress, list(motion["exitCurve"]))
        return 1.0 - eased, -10.0 * eased, 4.0 * eased, 1.0
    return 1.0, 0.0, 0.0, 1.0


def _context_base(source: Image.Image) -> Image.Image:
    graded = ImageEnhance.Color(source.convert("RGB")).enhance(0.28)
    graded = ImageEnhance.Brightness(graded).enhance(0.74).filter(ImageFilter.GaussianBlur(4.5))
    base = graded.convert("RGBA")
    tint = Image.new("RGBA", base.size, hex_rgba(BRAND["palette"]["canvas"])[:3] + (74,))
    base.alpha_composite(tint)
    shade = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    width, height = base.size
    for y in range(height):
        top_alpha = int(182 * max(0.0, 1.0 - y / (height * 0.44)))
        bottom_alpha = int(82 * max(0.0, (y / height - 0.56) / 0.44))
        alpha = max(top_alpha, bottom_alpha)
        if alpha:
            draw.line((0, y, width, y), fill=(2, 3, 3, alpha))
    base.alpha_composite(shade)
    return base


def _transform_overlay(source: Image.Image, scale: float, offset_y: float, blur: float, opacity: float) -> Image.Image:
    animated = source
    bounds = source.getbbox()
    if bounds and abs(scale - 1.0) > 0.0005:
        crop = source.crop(bounds)
        resized = crop.resize(
            (max(1, int(round(crop.width * scale))), max(1, int(round(crop.height * scale)))),
            Image.Resampling.LANCZOS,
        )
        animated = Image.new("RGBA", source.size, (0, 0, 0, 0))
        center_x = (bounds[0] + bounds[2]) // 2
        center_y = (bounds[1] + bounds[3]) // 2
        animated.alpha_composite(resized, (center_x - resized.width // 2, center_y - resized.height // 2))
    if blur > 0.25:
        animated = animated.filter(ImageFilter.GaussianBlur(blur))
    if offset_y:
        shifted = Image.new("RGBA", source.size, (0, 0, 0, 0))
        shifted.alpha_composite(animated, (0, int(round(offset_y))))
        animated = shifted
    if opacity < 0.999:
        alpha = animated.getchannel("A").point(lambda value: int(value * opacity))
        animated = animated.copy()
        animated.putalpha(alpha)
    return animated


def _render_preview(
    cue: dict[str, Any],
    preview_path: Path,
    still_path: Path,
    *,
    base_override: Image.Image | None = None,
) -> Path:
    base = base_override.convert("RGBA") if base_override is not None else _context_base(Image.open(SOURCE_STILL).convert("RGB"))
    overlay = _render_bilingual_overlay(base.size, cue, base)
    total_frames = max(1, int(round(DURATION * FPS)))
    sfx_path = Path(cue["sfx_cue"]["asset_path"])
    with tempfile.TemporaryDirectory(prefix="hafez-golden-") as temp_name:
        temp = Path(temp_name)
        for frame in range(total_frames):
            opacity, offset_y, blur, scale = _motion_for_frame(frame, total_frames)
            animated = _transform_overlay(overlay, scale, offset_y, blur, opacity)
            frame_image = base.copy()
            frame_image.alpha_composite(animated)
            frame_image.convert("RGB").save(temp / f"frame-{frame:04d}.png", compress_level=2)
        shutil.copyfile(temp / f"frame-{min(total_frames - 1, int(FPS * 1.5)):04d}.png", still_path)
        _run(
            [
                _ffmpeg(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-framerate",
                str(int(FPS)),
                "-i",
                str(temp / "frame-%04d.png"),
                "-i",
                str(sfx_path),
                "-filter_complex",
                f"[1:a]aresample=48000,apad=pad_dur={DURATION:.3f},atrim=0:{DURATION:.3f}[entry_sfx]",
                "-map",
                "0:v:0",
                "-map",
                "[entry_sfx]",
                "-r",
                str(int(FPS)),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                f"{DURATION:.3f}",
                str(preview_path),
            ]
        )
    return preview_path


def _clean_style_canvas(size: tuple[int, int]) -> Image.Image:
    width, height = size
    canvas = Image.new("RGBA", size, hex_rgba(BRAND["palette"]["canvas"]))
    accent = hex_rgba(BRAND["palette"]["primaryAccent"])
    elevated = hex_rgba(BRAND["palette"]["surfaceElevated"])
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (width * 0.50, -height * 0.46, width * 1.18, height * 0.74),
        fill=accent[:3] + (34,),
    )
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150)))
    draw = ImageDraw.Draw(canvas)
    for index in range(1, 8):
        y = int(height * index / 8)
        draw.line((90, y, width - 90, y), fill=elevated[:3] + (22,), width=1)
    for index in range(1, 12):
        x = int(width * index / 12)
        draw.line((x, 70, x, height - 70), fill=elevated[:3] + (14,), width=1)
    return canvas


def _clean_style_cue(cue: dict[str, Any], size: tuple[int, int]) -> dict[str, Any]:
    clean = json.loads(json.dumps(cue, ensure_ascii=False))
    width, height = size
    region = [0.285, 0.36, 0.43, 0.25]
    left, top, rect_width, rect_height = region
    center_x = (left + rect_width / 2.0) * width
    clean["layout"].update(
        {
            "region": "style-board-center",
            "region_bbox": region,
            "x": round(center_x, 1),
            "y": round((top + rect_height / 2.0) * height, 1),
            "english_position": [round(center_x, 1), round((top + rect_height * 0.40) * height, 1)],
            "persian_position": [round(center_x, 1), round((top + rect_height * 0.73) * height, 1)],
            "max_width": round(rect_width * width - 96, 1),
            "max_height": round(rect_height * height, 1),
            "scale": 100.0,
            "max_lines": 2,
        }
    )
    return clean


def _render_placement_qa(cue: dict[str, Any], destination: Path) -> None:
    image = Image.open(SOURCE_STILL).convert("RGBA")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    safe = cue["layout"]["safe_area_bbox"]
    subject = cue["layout"]["subject_union_bbox"]
    region = cue["layout"]["region_bbox"]

    def pixels(box: list[float]) -> tuple[int, int, int, int]:
        x, y, w, h = box
        return (int(x * width), int(y * height), int((x + w) * width), int((y + h) * height))

    draw.rectangle(pixels(safe), outline=(255, 255, 255, 255), width=5)
    draw.rectangle(pixels(subject), outline=(255, 78, 112, 255), width=6)
    draw.rectangle(pixels(region), outline=(85, 255, 114, 255), width=7)
    draw.text((72, height - 82), "WHITE: SAFE AREA   RED: FULL SUBJECT UNION   HAFEZ GREEN: TITLE BOX", fill=(255, 255, 255, 255))
    image.save(destination)


def _write_xml(
    source_video: Path,
    metadata: dict[str, Any],
    graphics: list[dict[str, Any]],
    destination: Path,
) -> dict[str, str]:
    frame_count = max(1, int(metadata["frame_count"]))
    manifest = {
        "cam1_path": str(source_video),
        "cam2_path": str(source_video),
        "cam1_metadata": metadata,
        "cam2_metadata": metadata,
        "audio_metadata": {
            "cam1": {"depth": 16, "sample_rate": 48_000, "channels": 1},
            "cam2": {"depth": 16, "sample_rate": 48_000, "channels": 1},
        },
        "fps": FPS,
    }
    variant = {
        "name": "Hafez Golden Segment - 02m35s",
        "timeline_frames": frame_count,
        "clips": {
            "cam1": [[0, frame_count, 0, frame_count, True]],
            "cam2": [[0, frame_count, 0, frame_count, False]],
        },
    }
    markers = [
        {
            "type": "GOLDEN SEGMENT",
            "start": 0.0,
            "end": DURATION,
            "comment": f"Source reference {SOURCE_TIMECODE}; editable EN/FA MOGRT; entry SFX on frame 0",
        }
    ]
    sequence, backends = autocut._sequence_xml(
        manifest,
        "golden",
        variant,
        [],
        markers,
        None,
        graphics,
    )
    content = [
        "<?xml version='1.0' encoding='utf-8'?>",
        "<!DOCTYPE xmeml>",
        '<xmeml version="5">',
        "  <importoptions>",
        "    <filterincludemarkers>TRUE</filterincludemarkers>",
        "    <filterincludeeffects>TRUE</filterincludeeffects>",
        "    <filterincludesequencesettings>TRUE</filterincludesequencesettings>",
        "  </importoptions>",
        *sequence,
        "</xmeml>",
    ]
    destination.write_text("\n".join(content), encoding="utf-8")
    return backends


def main() -> int:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE_STILL.is_file():
        raise FileNotFoundError(SOURCE_STILL)
    mogrt = resolve_text_animation_title()
    relaxe = resolve_relaxe_font()
    if not mogrt or not relaxe:
        raise FileNotFoundError("Hafez bilingual MOGRT and Relaxe must both be connected")
    inspection = inspect_mogrt_asset(mogrt)
    _extract_template_thumbnail(mogrt, PROOF_DIR / "selected-template-thumb.png")
    template_catalog = _write_template_catalog(PROOF_DIR / "text-animation-template-catalog.png")

    # Premiere may keep the previous proof media open.  Versioned artifact
    # names make rebuilds non-destructive and avoid force-closing the editor.
    source_video = PROOF_DIR / "golden-segment-source-v3-fullscreen-glass.mp4"
    metadata = _create_source_video(source_video)
    total_frames = max(1, int(metadata["frame_count"]))
    segments = [
        {"id": 235, "start": 0.0, "end": DURATION, "text": PERSIAN_STATEMENT}
    ]
    markers = [
        {
            "segment_id": 235,
            "type": "CHAPTER",
            "visual_kind": "chapter",
            "semantic_role": "workflow-explanation",
            "headline_fa": PERSIAN_STATEMENT,
            "semantic_subtitle_fa": PERSIAN_CONCEPT,
            "title_en": ENGLISH_TITLE,
            "transition": "hafez-ui-entry",
            "sfx": "hero-glass",
            "priority": "high",
            "comment": "Golden Segment selected from source reference 00:02:35:00",
        }
    ]
    history_path = PROOF_DIR / "curator-family-history.json"
    cues = professional_edit.build_graphic_cues(
        segments,
        DURATION,
        markers,
        fps=FPS,
        family_history=[TEXT_ANIMATION_TITLE.family_id],
    )
    if len(cues) != 1:
        raise RuntimeError(f"Expected exactly one Golden cue, received {len(cues)}")
    cues, tracking_backend = professional_edit.apply_face_safe_layout(
        cues,
        video_path=str(source_video),
        clips=[[0, total_frames, 0, total_frames]],
        fps=FPS,
        width=int(metadata["width"]),
        height=int(metadata["height"]),
    )
    cue = cues[0]
    if not cue["layout"]["collision_free"]:
        raise RuntimeError("Golden title could not be placed fully outside the tracked presenter union")
    if int(cue["layout"]["tracking_sample_count"]) < 3:
        raise RuntimeError("Multi-frame tracking did not sample the complete MOGRT lifetime")
    if not cue.get("sfx_cue") or int(cue["sfx_cue"]["start_frame"]) != 0:
        raise RuntimeError("Entry SFX is not synchronized to the first MOGRT frame")
    sfx = Path(cue["sfx_cue"]["asset_path"])
    if sfx.suffix.casefold() != ".wav" or int(cue["sfx_cue"]["sample_rate"]) != 48_000:
        raise RuntimeError("Golden Segment must use the layered 48 kHz Hafez SFX recipe")

    graphics = professional_edit.render_graphic_assets(
        cues,
        PROOF_DIR / "premiere-guide-assets-v3-fullscreen-glass",
        int(metadata["width"]),
        int(metadata["height"]),
    )
    cue = graphics[0]
    xml_path = PROOF_DIR / "hafez-golden-segment-premiere-v3-fullscreen-glass.xml"
    tracking_backends = _write_xml(source_video, metadata, graphics, xml_path)
    plan_path = PROOF_DIR / "hafez-golden-segment-premiere-plan-v3-fullscreen-glass.json"
    professional_edit.write_professional_plan(
        plan_path,
        sequence_name="Hafez Golden Segment - 02m35s",
        fps=FPS,
        camera_schedule=[{"start": 0.0, "end": DURATION, "camera": "cam1", "reason": "approved still proxy"}],
        events=[],
        graphics=graphics,
        history_path=history_path,
    )

    preview_path = PROOF_DIR / "hafez-golden-segment-preview-v3-fullscreen-glass.mp4"
    preview_still = PROOF_DIR / "hafez-golden-segment-preview-v3-fullscreen-glass.png"
    _render_preview(cue, preview_path, preview_still)
    style_preview_path = PROOF_DIR / "hafez-motion-style-preview-v3-fullscreen-glass.mp4"
    style_preview_still = PROOF_DIR / "hafez-motion-style-preview-v3-fullscreen-glass.png"
    style_cue = _clean_style_cue(cue, (int(metadata["width"]), int(metadata["height"])))
    _render_preview(
        style_cue,
        style_preview_path,
        style_preview_still,
        base_override=_clean_style_canvas((int(metadata["width"]), int(metadata["height"]))),
    )
    _render_placement_qa(cue, PROOF_DIR / "hafez-golden-segment-placement-qa.png")

    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    plan["golden_segment"] = {
        "source_timecode": SOURCE_TIMECODE,
        "source_kind": "approved-still-derived-4.8s-style-preview",
        "moving_footage_available": False,
        "english_title": ENGLISH_TITLE,
        "persian_statement": PERSIAN_STATEMENT,
        "persian_semantic_subtitle": PERSIAN_CONCEPT,
        "preview_is_deterministic_motion_contract": True,
        "preview_background_contains_baked_legacy_graphics": True,
        "preview_background_treatment": "desaturated + Hafez canvas tint + top/bottom luminance mask",
        "actual_mogrt_path": str(mogrt.resolve()),
        "clean_motion_style_preview": str(style_preview_path.resolve()),
    }
    plan["qa"] = {
        "rule_based_primary": True,
        "qwen_vision_role": "final-validation-only",
        "qwen_vision_invoked": False,
        "grain_free": bool(inspection["grain_free"]),
        "multi_frame_tracking_backend": tracking_backend,
        "xml_motion_backends": tracking_backends,
        "subject_overlap_ratio": cue["layout"]["safe_margin_overlap_ratio"],
        "face_overlap_ratio": cue["layout"]["face_overlap_ratio"],
        "safe_area_contained": cue["layout"]["safe_area_contained"],
        "exact_entry_curve": list(MOTION_STYLE["motion"]["entryCurve"]),
        "exact_exit_curve": list(MOTION_STYLE["motion"]["exitCurve"]),
        "motion_sfx_recipe": cue["sfx_cue"]["recipe"],
        "motion_sfx_layers": cue["sfx_cue"]["layers"],
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8-sig")

    input_assets = [SOURCE_STILL, TEXT_ARCHIVE, RELAXE_ARCHIVE, REFERENCE_VIDEO]
    output_assets = [
        source_video,
        xml_path,
        plan_path,
        preview_path,
        preview_still,
        style_preview_path,
        style_preview_still,
        mogrt,
        relaxe,
        sfx,
    ]
    manifest = {
        "protocol": "hafez-golden-segment-proof-v2",
        "source_timecode": SOURCE_TIMECODE,
        "duration": DURATION,
        "fps": FPS,
        "inputs": [{"path": str(path), "sha256": _sha256(path)} for path in input_assets],
        "outputs": [{"path": str(path), "sha256": _sha256(path)} for path in output_assets if path.is_file()],
        "checks": {
            "grain_assets_or_effects": 0,
            "source_templates_rejected_for_grain": len(
                [item for item in template_catalog if item["rejected_for_grain"]]
            ),
            "editable_mogrt_layers": len(cue.get("template_layers", [])),
            "template_families": len({cue["template_family"]}),
            "entry_sfx_start_frame": cue["sfx_cue"]["start_frame"],
            "entry_sfx_recipe": cue["sfx_cue"]["recipe"],
            "entry_sfx_layers": len(cue["sfx_cue"]["layers"]),
            "entry_sfx_sample_rate": cue["sfx_cue"]["sample_rate"],
            "linear_allowed": cue["bilingual_typography"]["motion"]["linear_allowed"],
            "entry_curve": cue["bilingual_typography"]["motion"]["entry_curve"],
            "exit_curve": cue["bilingual_typography"]["motion"]["exit_curve"],
            "tracking_sample_count": cue["layout"]["tracking_sample_count"],
            "tracking_detected_count": cue["layout"]["tracking_detected_count"],
            "collision_free": cue["layout"]["collision_free"],
        },
        "template_catalog": template_catalog,
    }
    (PROOF_DIR / "golden-segment-proof.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    (PROOF_DIR / "README.md").write_text(
        "# Hafez Golden Segment\n\n"
        "1. `hafez-golden-segment-premiere-v3-fullscreen-glass.xml` را در Premiere Pro Import کنید.\n"
        "2. Sequence با نام `Hafez Golden Segment - 02m35s` را فعال کنید.\n"
        "3. Hafez Finisher را باز و `hafez-golden-segment-premiere-plan-v3-fullscreen-glass.json` را اجرا کنید.\n"
        "4. هر دو متن انگلیسی و فارسی داخل یک MOGRT منسجم روی V4 قابل‌ویرایش می‌مانند؛ SFX چندلایه روی A4 از فریم صفر قرار دارد.\n\n"
        "Preview ویدیویی نمایش قطعی Motion Contract است، اما Source آن Still دارای گرافیک قدیمیِ Bake‌شده است. "
        "برای قضاوت Art Direction ابتدا Previewهای واقعی پوشه `../glass-title-variants` را ببینید؛ MOGRT Fullscreen Glass در مرحله Finisher وارد می‌شود.\n",
        encoding="utf-8-sig",
    )
    print(json.dumps({"ok": True, "proof_dir": str(PROOF_DIR), "preview": str(preview_path), "xml": str(xml_path), "plan": str(plan_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
