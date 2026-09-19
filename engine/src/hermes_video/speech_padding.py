"""Conservative INITIAL silence planning, before ASR or editorial removals.

This is not word verification/restoration. It accepts detector ranges only, not
existing edited keeps, and never changes media. Overlapping handles are unioned
before frame mapping so a quieter onset does not cause duplicated speech.
"""
from __future__ import annotations

import math


POLICY = {"id": "glass-conservative-silence-v1", "head_ms": 600, "tail_ms": 350,
          "merge_overlaps": True, "frame_exact_mapping": True,
          "authority": "initial-silence-planning-not-audio-verification"}


def build_padded_timeline(ranges, offset_ms, fps, duration_ms, *, head_ms=600, tail_ms=350):
    """Return two-camera clips, source mapping and duration on one frame clock.

Cam2 retains the established fixed-offset / zero-clamp convention. Source
handles round outward; the mapping describes those actual frames, not the
pre-rounding milliseconds. Input ranges must be ordered and within the media.
    """
    values = (offset_ms, fps, duration_ms, head_ms, tail_ms)
    if not all(math.isfinite(float(v)) for v in values) or fps <= 0 or duration_ms < 0:
        raise ValueError("Invalid timing parameters")
    if head_ms < 0 or tail_ms < 0:
        raise ValueError("Negative silence handle")
    media_limit = math.floor(duration_ms * fps / 1000 + 1e-9)
    merged = []
    previous_start = -1
    for start, end in ranges:
        if not all(math.isfinite(float(v)) for v in (start, end)):
            raise ValueError("Non-finite silence range")
        if not 0 <= start < end <= duration_ms or start < previous_start:
            raise ValueError("Unordered or out-of-media silence range")
        previous_start = start
        a = max(0, math.floor((start-head_ms) * fps / 1000 + 1e-9))
        b = min(media_limit, math.ceil((end+tail_ms) * fps / 1000 - 1e-9))
        if b <= a:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    clips = {"cam1": [], "cam2": []}
    mapping = []
    cursor = 0
    offset_frames = round(offset_ms * fps / 1000)
    for a, b in merged:
        duration = b-a
        second = max(0, a-offset_frames)
        clips["cam1"].append((cursor, cursor+duration, a, b))
        clips["cam2"].append((cursor, cursor+duration, second, second+duration))
        mapping.append({"orig_start_ms": a/fps*1000, "orig_end_ms": b/fps*1000,
                        "tl_start_ms": cursor/fps*1000, "tl_end_ms": (cursor+duration)/fps*1000})
        cursor += duration
    return clips, mapping, cursor
