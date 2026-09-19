"""Offline, deterministic Hafez motion sound design.

No sound is generated and nothing is downloaded.  The two licensed local
text-animation effects are trimmed, filtered and layered into short 48 kHz
recipes whose transient starts on the first MOGRT frame.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from motion_style import load_motion_style
from runtime_paths import find_executable, studio_root


SOURCE_ROOT = studio_root() / "personal-assets" / "Text Animation" / "Sound Effects"
DEFAULT_OUTPUT_ROOT = studio_root() / "personal-assets" / "Hafez Motion SFX"
SOURCE_FILES = ("Sound Effect_1.mp3", "Sound Effect_2.mp3")


def sound_kit_root() -> Path:
    override = os.environ.get("HERMES_HAFEZ_SFX_ROOT", "").strip()
    return Path(override).expanduser() if override else DEFAULT_OUTPUT_ROOT


def _ffmpeg() -> str:
    executable = find_executable(("ffmpeg",))
    if not executable:
        raise FileNotFoundError("Bundled FFmpeg is required to build the Hafez motion SFX kit")
    return executable


def _sources() -> tuple[Path, Path]:
    paths = tuple(SOURCE_ROOT / name for name in SOURCE_FILES)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing curated local SFX source: " + ", ".join(missing))
    return paths  # type: ignore[return-value]


def _filters(recipe: str, duration: float) -> str:
    # Input 0 supplies the soft body and tail; input 1 supplies the crisp edge.
    # Every layer starts from a real licensed source sample and remains subtle
    # enough to sit below dialogue without ducking the speaker.
    variants = {
        "hero-glass": ((
            "[0:a]atrim=0.105:0.500,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=85,lowpass=f=1300,volume=0.42,afade=t=out:st=0.28:d=0.11[body];"
            "[1:a]atrim=0.045:0.250,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=1650,lowpass=f=9000,volume=0.28,afade=t=out:st=0.12:d=0.08[edge];"
            "[0:a]atrim=0.705:1.210,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=2600,lowpass=f=11000,volume=0.16,aecho=0.8:0.35:38|82:0.24|0.10,"
            "adelay=245|245,afade=t=out:st=0.52:d=0.18[settle]"
        ), "[body][edge][settle]", 3),
        "insight-air": ((
            "[0:a]atrim=0.105:0.455,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=420,lowpass=f=6200,volume=0.26,afade=t=out:st=0.24:d=0.10[body];"
            "[1:a]atrim=0.365:0.780,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=2850,lowpass=f=10500,volume=0.13,aecho=0.8:0.3:34|70:0.20|0.08,"
            "adelay=210|210,afade=t=out:st=0.40:d=0.15[settle]"
        ), "[body][settle]", 2),
        "process-ticks": ((
            "[1:a]atrim=0.045:0.210,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=1900,lowpass=f=8800,volume=0.24,afade=t=out:st=0.10:d=0.06[body];"
            "[0:a]atrim=0.305:0.620,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=500,lowpass=f=4200,volume=0.17,adelay=180|180,afade=t=out:st=0.28:d=0.10[pulse];"
            "[1:a]atrim=0.650:1.040,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=2800,lowpass=f=9800,volume=0.11,aecho=0.8:0.25:32|68:0.18|0.07,"
            "adelay=350|350,afade=t=out:st=0.30:d=0.10[settle]"
        ), "[body][pulse][settle]", 3),
        "metric-lock": ((
            "[0:a]atrim=0.105:0.405,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=90,lowpass=f=1050,volume=0.34,afade=t=out:st=0.20:d=0.09[body];"
            "[1:a]atrim=0.045:0.205,asetpts=PTS-STARTPTS,aresample=48000,"
            "highpass=f=2200,lowpass=f=9500,volume=0.24,adelay=35|35,afade=t=out:st=0.09:d=0.06[settle]"
        ), "[body][settle]", 2),
    }
    layers, inputs, input_count = variants[recipe]
    return (
        layers
        + f";{inputs}amix=inputs={input_count}:normalize=0,apad=whole_dur={duration:.3f},atrim=0:{duration:.3f},"
        "afade=t=out:st="
        + f"{max(0.1, duration - 0.16):.3f}:d=0.16,"
        "alimiter=limit=0.1585:attack=2:release=55:level=1,pan=stereo|c0=c0|c1=c1[out]"
    )


def build_sound_kit(*, force: bool = False) -> dict[str, Any]:
    style = load_motion_style()
    output_root = sound_kit_root()
    output_root.mkdir(parents=True, exist_ok=True)
    first, second = _sources()
    built: dict[str, Any] = {}
    for recipe, spec in style["audio"]["recipes"].items():
        destination = output_root / f"hafez-{recipe}.wav"
        if force or not destination.is_file():
            command = [
                _ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(first), "-i", str(second),
                "-filter_complex", _filters(recipe, float(spec["duration"])),
                "-map", "[out]", "-ar", str(style["audio"]["sampleRate"]),
                "-ac", str(style["audio"]["channels"]), "-c:a", str(style["audio"]["format"]),
                str(destination),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr[-3000:] or completed.stdout[-3000:])
        built[recipe] = {
            "path": str(destination.resolve()),
            "duration": float(spec["duration"]),
            "layers": list(spec["layers"]),
            "transient_offset_ms": int(spec["transientOffsetMs"]),
            "settle_offset_ms": int(spec["settleOffsetMs"]),
        }
    manifest = {
        "protocol": "hafez-curated-sfx-v1",
        "source_mode": "licensed-local-derived",
        "generated_audio": False,
        "sample_rate": int(style["audio"]["sampleRate"]),
        "channels": int(style["audio"]["channels"]),
        "true_peak_ceiling_dbfs": float(style["audio"]["truePeakCeilingDbfs"]),
        "voice_untouched": bool(style["audio"]["voiceUntouched"]),
        "ducking_target": str(style["audio"]["duckingTarget"]),
        "sources": [str(first.resolve()), str(second.resolve())],
        "recipes": built,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )
    return manifest


def recipe_asset(recipe: str) -> tuple[Path, dict[str, Any]]:
    manifest = build_sound_kit()
    details = dict(manifest["recipes"].get(recipe) or manifest["recipes"]["insight-air"])
    return Path(details["path"]), details
