"""Deterministic delivery QA for a Hafez Studio edit manifest.

The report checks the imported Premiere contract, graphic assets, subtitle
timing, audio-master provenance and the editorial density plan.  It performs
no media rendering and is safe to run after every local or Telegram job.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from PIL import Image


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def _seconds(value: str) -> float:
    hours, minutes, tail = value.split(":")
    seconds, millis = tail.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def _srt_metrics(path: Path, failures: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig").strip()
    pattern = re.compile(
        r"(?m)^(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
        re.DOTALL,
    )
    cues = pattern.findall(text)
    _check(bool(cues), f"SRT is empty or invalid: {path.name}", failures)
    previous_end = -1.0
    overlaps = 0
    invalid = 0
    for _index, raw_start, raw_end, caption in cues:
        start, end = _seconds(raw_start), _seconds(raw_end)
        invalid += int(end <= start or not caption.strip())
        overlaps += int(start < previous_end - 0.002)
        previous_end = max(previous_end, end)
    _check(invalid == 0, f"Invalid SRT cues: {path.name}", failures)
    _check(overlaps == 0, f"Overlapping SRT cues: {path.name}", failures)
    return {
        "path": str(path),
        "cues": len(cues),
        "invalid": invalid,
        "overlaps": overlaps,
        "last_end": round(previous_end, 3),
    }


def run(manifest_path: Path) -> dict[str, Any]:
    failures: list[str] = []
    manifest = _read_json(manifest_path)
    outputs = manifest["outputs"]
    plan_path = Path(outputs["professional_plan"])
    xml_path = Path(outputs["xml"])
    plan = _read_json(plan_path)
    root = ET.parse(xml_path).getroot()

    cam1 = manifest["cam1_metadata"]
    expected_width, expected_height = int(cam1["width"]), int(cam1["height"])
    sequences = {sequence.findtext("name", ""): sequence for sequence in root.findall(".//sequence")}
    required_sequences = {"01 - Hafez Safe Cut", "02 - Hafez Tight Cut", "03 - Hafez Director Cut"}
    _check(required_sequences.issubset(sequences), "Three delivery sequences are not present", failures)
    director = sequences.get("03 - Hafez Director Cut")
    if director is None:
        return {"status": "failed", "failures": failures}

    width = int(director.findtext("./media/video/format/samplecharacteristics/width", "0"))
    height = int(director.findtext("./media/video/format/samplecharacteristics/height", "0"))
    _check((width, height) == (expected_width, expected_height), "Sequence does not inherit camera-1 dimensions", failures)

    video_tracks = director.findall("./media/video/track")
    audio_tracks = director.findall("./media/audio/track")
    _check(len(video_tracks) == 3, "Director Cut must contain V1/V2/V3", failures)
    _check(len(audio_tracks) == 3, "Director Cut must contain two disabled source tracks and one master", failures)

    camera_pairs = 0
    camera_inverse_failures = 0
    if len(video_tracks) >= 2:
        first_clips = video_tracks[0].findall("clipitem")
        second_clips = video_tracks[1].findall("clipitem")
        camera_pairs = min(len(first_clips), len(second_clips))
        _check(len(first_clips) == len(second_clips) and camera_pairs > 0, "Camera track clip counts differ", failures)
        for first, second in zip(first_clips, second_clips):
            same_range = (first.findtext("start"), first.findtext("end")) == (second.findtext("start"), second.findtext("end"))
            first_on = first.findtext("enabled", "FALSE").upper() == "TRUE"
            second_on = second.findtext("enabled", "FALSE").upper() == "TRUE"
            if not same_range or first_on == second_on:
                camera_inverse_failures += 1
        _check(camera_inverse_failures == 0, "Camera enablement is not mutually exclusive", failures)

    audio_enablement: list[tuple[int, int]] = []
    for track in audio_tracks:
        clips = track.findall("clipitem")
        enabled = sum(clip.findtext("enabled", "FALSE").upper() == "TRUE" for clip in clips)
        audio_enablement.append((enabled, len(clips) - enabled))
    _check(len(audio_enablement) >= 3 and audio_enablement[0][0] == 0 and audio_enablement[1][0] == 0, "Source camera audio is not disabled", failures)
    _check(len(audio_enablement) >= 3 and audio_enablement[2][0] == 1, "Processed camera-1 master is not enabled", failures)

    url_text = "\n".join(element.text or "" for element in root.findall(".//pathurl"))
    _check("C2953.MP4" in urllib.parse.unquote(url_text), "Camera 1 source link missing", failures)
    _check("C0126.MP4" in urllib.parse.unquote(url_text), "Camera 2 source link missing", failures)

    graphics = list(plan.get("graphics", []))
    graphic_clips = video_tracks[2].findall("clipitem") if len(video_tracks) >= 3 else []
    _check(len(graphics) == len(graphic_clips) and len(graphics) >= 24, "Professional graphics are missing from V3", failures)
    long_headlines = [item.get("id") for item in graphics if len(str(item.get("headline_fa", ""))) > 110]
    incomplete_headlines = [
        item.get("id")
        for item in graphics
        if not str(item.get("headline_fa", "")).strip().endswith((".", "!", "؟", "?"))
    ]
    _check(not long_headlines, "One or more graphic headlines exceed 110 characters", failures)
    _check(not incomplete_headlines, "One or more graphic headlines are incomplete", failures)

    overlap_count = 0
    ordered_graphics = sorted(graphics, key=lambda item: float(item["start"]))
    for previous, current in zip(ordered_graphics, ordered_graphics[1:]):
        overlap_count += int(float(current["start"]) < float(previous["end"]) - 0.002)
    _check(overlap_count == 0, "Graphic cues overlap each other", failures)

    missing_assets: list[str] = []
    invalid_assets: list[str] = []
    for item in graphics:
        asset = Path(str(item.get("asset_path", "")))
        if not asset.exists():
            missing_assets.append(str(asset))
            continue
        with Image.open(asset) as image:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            if rgba.size != (expected_width, expected_height) or alpha.getbbox() is None or alpha.getextrema()[0] == 255:
                invalid_assets.append(str(asset))
    _check(not missing_assets and not invalid_assets, "Graphic PNG assets are missing, opaque, empty or wrong-sized", failures)

    motion_failures = 0
    for clip in graphic_clips:
        effects = {flt.findtext("./effect/name", ""): flt for flt in clip.findall("filter")}
        basic = effects.get("Basic Motion")
        opacity = effects.get("Opacity")
        parameters = {
            parameter.findtext("parameterid", ""): len(parameter.findall("keyframe"))
            for parameter in (basic.findall("./effect/parameter") if basic is not None else [])
        }
        opacity_parameters = {
            parameter.findtext("parameterid", ""): len(parameter.findall("keyframe"))
            for parameter in (opacity.findall("./effect/parameter") if opacity is not None else [])
        }
        if parameters.get("scale", 0) < 3 or parameters.get("center", 0) < 2 or parameters.get("anchorpoint", 0) < 2 or opacity_parameters.get("opacity", 0) < 3:
            motion_failures += 1
    _check(motion_failures == 0, "One or more V3 graphics lack real Motion/Opacity keyframes", failures)

    srt = {
        "safe": _srt_metrics(Path(outputs["safe_srt"]), failures),
        "tight": _srt_metrics(Path(outputs["tight_srt"]), failures),
    }

    youtube_path = Path(outputs["youtube"])
    youtube_text = youtube_path.read_text(encoding="utf-8-sig").strip()
    placeholders = ("عنوان پیشنهادی توسط AI تولید نشد", "تولید نشد", "TODO", "<!--")
    _check(len(youtube_text) >= 500 and not any(value in youtube_text for value in placeholders), "YouTube package is empty or contains placeholders", failures)

    audit = _read_json(Path(outputs["audit"]))
    tight_audio = audit.get("audio", {}).get("tight", {})
    audio_ok = (
        tight_audio.get("source_role") == "camera1_external_microphone"
        and int(tight_audio.get("sample_rate", 0)) == 48000
        and int(tight_audio.get("channels", 0)) == 1
        and int(tight_audio.get("depth", 0)) == 24
        and abs(float(tight_audio.get("target_lufs", 0)) + 14.0) < 0.01
        and abs(float(tight_audio.get("target_true_peak_db", 0)) + 1.0) < 0.01
        and Path(str(tight_audio.get("output_path", ""))).exists()
    )
    _check(audio_ok, "Audio master is not the 48 kHz/24-bit camera-1 external mic master", failures)

    kinds: dict[str, int] = {}
    for graphic in graphics:
        kind = str(graphic.get("kind", "unknown"))
        kinds[kind] = kinds.get(kind, 0) + 1

    report = {
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "manifest": str(manifest_path),
        "xml": str(xml_path),
        "sequence": {
            "name": "03 - Hafez Director Cut",
            "dimensions": [width, height],
            "video_tracks": len(video_tracks),
            "audio_tracks": len(audio_tracks),
            "camera_clip_pairs": camera_pairs,
            "camera_inverse_failures": camera_inverse_failures,
            "audio_enablement": audio_enablement,
        },
        "editorial": {
            "camera_shots": len(plan.get("camera_schedule", [])),
            "camera_switches": max(0, len(plan.get("camera_schedule", [])) - 1),
            "punch_ins": len(plan.get("punch_ins", [])),
            "graphics": len(graphics),
            "graphic_kinds": kinds,
            "graphic_overlaps": overlap_count,
            "maximum_headline_characters": max((len(str(item.get("headline_fa", ""))) for item in graphics), default=0),
            "motion_failures": motion_failures,
        },
        "subtitles": srt,
        "audio": {
            "source_role": tight_audio.get("source_role"),
            "profile": tight_audio.get("voice_profile"),
            "target_lufs": tight_audio.get("target_lufs"),
            "target_true_peak_db": tight_audio.get("target_true_peak_db"),
            "sample_rate": tight_audio.get("sample_rate"),
            "channels": tight_audio.get("channels"),
            "depth": tight_audio.get("depth"),
        },
        "rough_cut": {
            "safe_removed_seconds": audit.get("variants", {}).get("safe", {}).get("removed_seconds"),
            "tight_removed_seconds": audit.get("variants", {}).get("tight", {}).get("removed_seconds"),
            "validated_edits": len(audit.get("edits", [])),
        },
        "youtube_package_characters": len(youtube_text),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.manifest.resolve())
    output = args.output or args.manifest.with_name(args.manifest.stem.replace(".edit", "") + ".quality-report.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"QUALITY_REPORT {output}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
