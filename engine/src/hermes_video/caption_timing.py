"""Draft captions timed to retained ASR words, never character interpolation.

Only fresh content-bound words already selected in prepare are eligible.
Partial ASR/cut words remain explicitly unverified; this does not repair cuts,
certify speech, add words, or override the separate audio-review gate.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

from caption_layout import build_source_word_cues


def build_timeline_word_cues(context: dict[str, Any]):
    numerator, denominator = context["fps"]
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in (numerator, denominator)):
        raise ValueError("An exact frame clock is required")
    rate = Fraction(numerator, denominator)
    keeps = context["keeps"]
    last_end = 0
    for keep in keeps:
        frames = [keep[k] for k in ("start_frame", "end_frame", "source_in_frame", "source_out_frame")]
        if (any(isinstance(x, bool) or not isinstance(x, int) for x in frames)
                or min(frames) < 0 or frames[0] < last_end or frames[1] <= frames[0]
                or frames[1]-frames[0] != frames[3]-frames[2]
                or keep["media_sha256"] != context["media_sha256"]):
            raise ValueError("Invalid final A1 keeps")
        last_end = frames[1]
    result, reviews, removed = [], [], []
    seen = set()
    for word in context["words"]:
        wid = word.get("source_word_id")
        if (not isinstance(wid, str) or not wid or wid in seen
                or word.get("source_evidence_id") != context["evidence_id"]
                or word.get("media_sha256") != context["media_sha256"]
                or word.get("timing_origin") != "asr-word-timestamps"):
            raise ValueError("Ambiguous source-word provenance")
        seen.add(wid)
        # source_start/end are the already-selected prepare fragment, not the
        # original uncut acoustic range: never restore a removed word tail.
        a, b = (Fraction(str(word[k])) for k in ("source_start", "source_end"))
        acoustic_a, acoustic_b = (Fraction(str(word[k])) for k in ("acoustic_start", "acoustic_end"))
        epsilon = Fraction(1, 10_000_000)  # binary float serialization only
        if (not str(word.get("text", "")).strip() or a < 0 or b <= a
                or a + epsilon < acoustic_a or b - epsilon > acoustic_b):
            raise ValueError("Invalid selected source-word bounds")
        a, b = max(a, acoustic_a), min(b, acoustic_b)  # narrow, never extend
        spans = []
        for ki, keep in enumerate(keeps):
            left = max(a, Fraction(keep["source_in_frame"], 1)/rate)
            right = min(b, Fraction(keep["source_out_frame"], 1)/rate)
            if left < right:
                offset = Fraction(keep["start_frame"]-keep["source_in_frame"], 1)/rate
                spans.append((right-left, left+offset, right+offset, left, right, ki))
        if not spans:
            removed.append(wid)
            continue
        # Same conservative largest retained fragment as prepare. No joining
        # across deleted speech, no lexical restoration from original segments.
        _, start, end, sa, sb, ki = max(spans, key=lambda item: item[0])
        reasons = []
        if len(spans) != 1 or sa != a or sb != b or word.get("word_boundary_review_required"):
            reasons.append("partial-machine-word-after-cut")
        if float(word["acoustic_end"])-float(word["acoustic_start"]) > 2.5:
            reasons.append("implausible-asr-word-duration")
        if reasons:
            reviews.append({"word_id": wid, "start": float(start), "end": float(end), "reasons": reasons})
        result.append({**word, "start": float(start), "end": float(end), "source_start": float(sa),
                       "source_end": float(sb), "final_keep_index": ki,
                       "caption_boundary_before": bool(word.get("caption_boundary_before")),
                       "caption_boundary_after": bool(word.get("caption_boundary_after"))})
    result.sort(key=lambda word: word["start"])
    for left, right in zip(result, result[1:]):
        if left["end"] > right["start"] + .001:
            raise ValueError("Overlapping ASR words need fresh recognition")
        if (left["final_keep_index"] != right["final_keep_index"]
                and abs(right["source_start"]-left["source_end"]) > .8):
            left["caption_boundary_after"] = right["caption_boundary_before"] = True
    cues = build_source_word_cues(result)
    return cues, {"status": "draft-source-word-timed-not-audio-verified", "applied": True,
                  "retained_word_count": len(result), "removed_word_ids": removed,
                  "word_review": reviews, "review": [
                      {"cue_index": i, "start": c["start"], "reasons": c["layout_review"]}
                      for i, c in enumerate(cues) if c.get("layout_review")],
                  "audio_or_cuts_changed": False, "publication_ready": False}
