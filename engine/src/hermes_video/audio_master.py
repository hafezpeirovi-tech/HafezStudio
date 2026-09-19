"""Create timeline-matched studio voice masters without rendering video."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pydub import AudioSegment
from runtime_paths import find_executable


TARGET_SAMPLE_RATE = 48_000
TARGET_LUFS = -14.0
TARGET_LRA = 7.0
TARGET_TRUE_PEAK = -1.0
BOUNDARY_FADE_MS = 4
VOICE_PROFILE = "broadcast-warm-male-v2"


def find_ffmpeg() -> str:
    portable = find_executable(("ffmpeg",))
    if portable:
        return portable
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    patterns = (
        "Microsoft/WinGet/Packages/Gyan.FFmpeg_*/ffmpeg-*/bin/ffmpeg.exe",
        "Programs/ffmpeg/bin/ffmpeg.exe",
    )
    for pattern in patterns:
        matches = sorted(local.glob(pattern), reverse=True)
        if matches:
            return str(matches[0])
    raise FileNotFoundError("FFmpeg پیدا نشد؛ نصب WinGet موجود در سیستم قابل شناسایی نبود.")


def configure_pydub_runtime() -> str:
    """Make bundled FFmpeg/FFprobe visible to both pydub and its media probe."""
    ffmpeg = find_ffmpeg()
    tools_dir = str(Path(ffmpeg).parent)
    current_path = os.environ.get("PATH", "")
    path_entries = [value for value in current_path.split(os.pathsep) if value]
    if tools_dir.casefold() not in {value.casefold() for value in path_entries}:
        os.environ["PATH"] = tools_dir + os.pathsep + current_path
    AudioSegment.converter = ffmpeg
    ffprobe = find_executable(("ffprobe",))
    if ffprobe:
        AudioSegment.ffprobe = ffprobe
    return ffmpeg


def _estimate_noise_floor(audio: AudioSegment) -> float:
    """Estimate a conservative floor from short windows; avoid hard gating."""
    levels: list[float] = []
    window_ms = 120
    step_ms = 240
    for start in range(0, len(audio), step_ms):
        chunk = audio[start : start + window_ms]
        if len(chunk) and math.isfinite(chunk.dBFS):
            levels.append(float(chunk.dBFS))
    if not levels:
        return -50.0
    levels.sort()
    percentile = levels[min(len(levels) - 1, max(0, int(len(levels) * 0.18)))]
    return round(min(-38.0, max(-64.0, percentile + 2.0)), 1)


def assemble_timeline_audio(
    source_path: str,
    clips: list[list[int]],
    fps: float,
) -> tuple[AudioSegment, dict[str, Any]]:
    configure_pydub_runtime()
    source = AudioSegment.from_file(source_path).set_channels(1).set_frame_rate(TARGET_SAMPLE_RATE)
    chunks: list[AudioSegment] = []
    for raw_clip in clips:
        timeline_start, timeline_end, media_in, media_out = map(int, raw_clip)
        expected_ms = max(1, int(round((timeline_end - timeline_start) / fps * 1000.0)))
        source_start_ms = max(0, int(round(media_in / fps * 1000.0)))
        source_end_ms = max(source_start_ms + 1, int(round(media_out / fps * 1000.0)))
        chunk = source[source_start_ms:source_end_ms]
        if len(chunk) > expected_ms:
            chunk = chunk[:expected_ms]
        elif len(chunk) < expected_ms:
            chunk += AudioSegment.silent(expected_ms - len(chunk), frame_rate=TARGET_SAMPLE_RATE)
        fade = min(BOUNDARY_FADE_MS, max(0, len(chunk) // 5))
        if fade:
            chunk = chunk.fade_in(fade).fade_out(fade)
        chunks.append(chunk)

    if chunks:
        raw = b"".join(chunk.raw_data for chunk in chunks)
        timeline = AudioSegment(
            data=raw,
            sample_width=chunks[0].sample_width,
            frame_rate=chunks[0].frame_rate,
            channels=chunks[0].channels,
        )
    else:
        timeline = AudioSegment.silent(100, frame_rate=TARGET_SAMPLE_RATE).set_channels(1)

    expected_total_ms = max(
        1,
        int(round(max((int(clip[1]) for clip in clips), default=0) / fps * 1000.0)),
    )
    if len(timeline) > expected_total_ms:
        timeline = timeline[:expected_total_ms]
    elif len(timeline) < expected_total_ms:
        timeline += AudioSegment.silent(expected_total_ms - len(timeline), frame_rate=TARGET_SAMPLE_RATE)

    report = {
        "source_duration_ms": len(source),
        "timeline_duration_ms": len(timeline),
        "input_dbfs": round(float(timeline.dBFS), 2) if math.isfinite(timeline.dBFS) else None,
        "input_peak_dbfs": round(float(timeline.max_dBFS), 2) if math.isfinite(timeline.max_dBFS) else None,
        "noise_floor_dbfs": _estimate_noise_floor(timeline),
        "clip_count": len(clips),
    }
    return timeline, report


def _base_filter(report: dict[str, Any]) -> str:
    """Build a clear, studio-forward male dialogue chain.

    This profile deliberately adds more audible body and articulation than v1,
    but avoids pitch shifting so the speaker keeps his natural identity.
    """
    noise_floor = float(report.get("noise_floor_dbfs", -50.0))
    filters: list[str] = []
    if float(report.get("input_peak_dbfs") or -99.0) >= -0.20:
        filters.append("adeclip=t=12")
        report["declip"] = True
    else:
        report["declip"] = False
    filters.extend(
        [
            "highpass=f=65:p=2",
            f"afftdn=nr=12:nf={noise_floor}:tn=1:ad=0.72:gs=10",
            "lowshelf=f=125:g=2.4:w=0.85",
            "equalizer=f=275:t=q:w=1.05:g=-2.8",
            "equalizer=f=720:t=q:w=1.20:g=-0.8",
            "equalizer=f=3000:t=q:w=1.00:g=1.9",
            "equalizer=f=6200:t=q:w=1.25:g=0.9",
            "deesser=i=0.30:m=0.45:f=0.55",
            "acompressor=threshold=0.115:ratio=3.2:attack=10:release=115:makeup=1.32:knee=4:mix=1",
            "aexciter=amount=0.52:drive=3.0:blend=0.09:freq=3500:ceil=15500",
            "asoftclip=type=tanh:threshold=0.90:output=0.97:param=1.28:oversample=4",
        ]
    )
    report["voice_profile"] = VOICE_PROFILE
    report["source_role"] = "camera1_external_microphone"
    return ",".join(filters)


def _extract_loudnorm_json(stderr: str) -> dict[str, Any] | None:
    blocks = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.DOTALL)
    for block in reversed(blocks):
        try:
            value = json.loads(block)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _thread_args() -> list[str]:
    value = os.environ.get("HERMES_FFMPEG_THREADS", "0")
    return ["-threads", value if value.isdigit() else "0"]


def build_voice_master(
    source_path: str,
    clips: list[list[int]],
    fps: float,
    output_path: str,
) -> dict[str, Any]:
    """Render audio only, preserving exact edited timeline duration."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    premaster = output.with_suffix(".premaster.wav")
    timeline, report = assemble_timeline_audio(source_path, clips, fps)
    timeline.export(premaster, format="wav", codec="pcm_s24le", parameters=["-ar", str(TARGET_SAMPLE_RATE), "-ac", "1"])

    ffmpeg = find_ffmpeg()
    base = _base_filter(report)
    measurement_filter = (
        base
        + f",loudnorm=I={TARGET_LUFS}:LRA={TARGET_LRA}:TP={TARGET_TRUE_PEAK}:dual_mono=true:print_format=json"
    )
    measure = _run([ffmpeg, "-hide_banner", "-nostdin", *_thread_args(), "-i", str(premaster), "-af", measurement_filter, "-f", "null", "-"])
    stats = _extract_loudnorm_json(measure.stderr)

    if stats:
        loudness = (
            f"loudnorm=I={TARGET_LUFS}:LRA={TARGET_LRA}:TP={TARGET_TRUE_PEAK}"
            f":measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}"
            f":measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}"
            f":offset={stats['target_offset']}:linear=true:dual_mono=true"
        )
        report["loudnorm_passes"] = 2
        report["loudness_measurement"] = stats
    else:
        loudness = f"loudnorm=I={TARGET_LUFS}:LRA={TARGET_LRA}:TP={TARGET_TRUE_PEAK}:dual_mono=true"
        report["loudnorm_passes"] = 1
        report["measurement_warning"] = measure.stderr[-1200:]

    final_filter = base + "," + loudness
    render = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            *_thread_args(),
            "-i",
            str(premaster),
            "-af",
            final_filter,
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-ac",
            "1",
            "-c:a",
            "pcm_s24le",
            str(output),
        ]
    )
    if render.returncode != 0 or not output.exists():
        shutil.copyfile(premaster, output)
        report["processing_backend"] = "premaster-fallback"
        report["processing_error"] = render.stderr[-2000:]
    else:
        report["processing_backend"] = f"ffmpeg-{VOICE_PROFILE}"
    premaster.unlink(missing_ok=True)
    report.update(
        {
            "output_path": str(output),
            "sample_rate": TARGET_SAMPLE_RATE,
            "channels": 1,
            "depth": 24,
            "target_lufs": TARGET_LUFS,
            "target_true_peak_db": TARGET_TRUE_PEAK,
        }
    )
    return report
