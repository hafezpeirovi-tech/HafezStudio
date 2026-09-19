"""Pure, source-faithful word mapping and conservative cut-boundary review.

No function in this module changes keeps, media, caches or text. Nonzero gaps
are never restored here. Explicit audio-reviewed evidence is a separate caller
input, not a boolean an ASR response can award itself.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def collect_source_words(segments: Sequence[Mapping[str, Any]], evidence_id: str) -> list[dict[str, Any]]:
    """Keep unclipped acoustic times; interpolation is explicitly not word ASR."""
    result = []
    for si, segment in enumerate(segments):
        for wi, word in enumerate(segment.get("words", [])):
            start, end = _finite(word.get("start")), _finite(word.get("end"))
            text = str(word.get("word") or "").strip()
            if start is None or end is None or start < 0 or end <= start or not text:
                continue
            result.append({
                "word_id": f"{evidence_id}:{si}:{wi}", "evidence_id": evidence_id,
                "text": text, "acoustic_start": start, "acoustic_end": end,
                "confidence": _finite(word.get("probability")),
                "timing_origin": word.get("timing_origin", "unknown"),
                "source_segment_index": si, "source_word_index": wi,
            })
    return result


def map_source_words(words: Sequence[Mapping[str, Any]], mapping: Sequence[Mapping[str, float]]) -> list[dict[str, Any]]:
    """Map each word once, joining only exact source AND timeline continuity.

    For nonzero gaps or source reordering, retain the previous largest-overlap
    choice and report partial coverage. Do not expand over a removed interval.
    """
    result = []
    for word in words:
        start, end = _finite(word.get("acoustic_start")), _finite(word.get("acoustic_end"))
        if start is None or end is None or end <= start:
            continue
        fragments = []
        for item in mapping:
            a, b = float(item["orig_start_ms"])/1000, float(item["orig_end_ms"])/1000
            left, right = max(start, a), min(end, b)
            if right <= left:
                continue
            timeline = float(item["tl_start_ms"])/1000
            fragments.append({"source_start": left, "source_end": right,
                              "start": timeline+left-a, "end": timeline+right-a})
        runs: list[list[dict[str, float]]] = []
        for fragment in fragments:
            previous = runs[-1][-1] if runs else None
            if (previous and abs(previous["source_end"]-fragment["source_start"]) <= 1e-9
                    and abs(previous["end"]-fragment["start"]) <= 1e-9):
                runs[-1].append(fragment)
            else:
                runs.append([fragment])
        if not runs:
            continue
        selected = max(runs, key=lambda run: sum(f["source_end"]-f["source_start"] for f in run))
        coverage = sum(f["source_end"]-f["source_start"] for f in selected)/(end-start)
        result.append({
            "text": word["text"], "start": round(selected[0]["start"], 4),
            "end": round(selected[-1]["end"], 4),
            "source_start": round(selected[0]["source_start"], 4),
            "source_end": round(selected[-1]["source_end"], 4),
            "confidence": word.get("confidence"),
            "acoustic_start": start, "acoustic_end": end,
            "source_word_id": word.get("word_id"), "source_evidence_id": word.get("evidence_id"),
            "timing_origin": word.get("timing_origin", "unknown"),
            "source_fragments": selected,
            "source_coverage": round(min(1.0, coverage), 8),
            "word_boundary_review_required": coverage < 1.0-1e-8 or len(runs) > 1,
            "mapping_policy": "exact-contiguous-fragments-only",
        })
    return result


def _verified_word(word: Mapping[str, Any], proof: Mapping[str, Any], media: Mapping[str, Any]) -> bool:
    """Only a separately supplied, source-content-bound audio review qualifies.

    Ordinary/targeted ASR confidence and weak path/stat identities are never
    promoted to verified evidence. Corroboration without audio review remains
    report-only in this first implementation.
    """
    digest = str(media.get("sha256", ""))
    return (
        bool(re.fullmatch(r"[a-fA-F0-9]{64}", digest))
        and proof.get("source_sha256") == digest
        and proof.get("verification_kind") == "audio-reviewed"
        and bool(str(proof.get("verification_id", "")).strip())
        and proof.get("text") == word.get("text")
        and _finite(proof.get("acoustic_start")) == _finite(word.get("acoustic_start"))
        and _finite(proof.get("acoustic_end")) == _finite(word.get("acoustic_end"))
    )


def assess_word_boundary_gaps(
    keeps: Sequence[Sequence[int]], words: Sequence[Mapping[str, Any]], *, fps: float,
    media_identity: Mapping[str, Any] | None = None, gap_origin: str = "unknown",
    protected_removals: Sequence[Mapping[str, Any]] = (),
    verified_words: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Review [timeline-in, timeline-out, source-in, source-out] frame keeps.

    Return decisions only. Protected source-frame removals win regardless of
    reason/size. Unknown origin, old clipped-only words and ordinary ASR fail
    closed. Outer take boundaries are deliberately not restoration candidates.
    """
    rate = _finite(fps)
    if rate is None or rate <= 0:
        raise ValueError("A finite positive frame rate is required")
    for keep in keeps:
        if (len(keep) != 4 or any(isinstance(v, bool) or not isinstance(v, int) for v in keep)
                or min(keep) < 0 or keep[1] <= keep[0] or keep[3] <= keep[2]
                or keep[1]-keep[0] != keep[3]-keep[2]):
            raise ValueError("Keeps must contain nonnegative, equal-duration integer frame intervals")
    protected = []
    for item in protected_removals:
        a, b = item.get("start_frame"), item.get("end_frame")
        if (isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int)
                or not isinstance(b, int) or a < 0 or b <= a):
            raise ValueError("Invalid protected removal; refusing boundary assessment")
        protected.append((a, b))
    ordered = all(left[1] <= right[0] and left[3] <= right[2]
                  for left, right in zip(keeps, keeps[1:]))
    decisions = []
    invalid_words = []
    for word in words:
        a, b = _finite(word.get("acoustic_start")), _finite(word.get("acoustic_end"))
        if a is None or b is None or a < 0 or b <= a:
            invalid_words.append({"word_id": word.get("word_id"), "reason": "missing-or-invalid-raw-acoustic-evidence"})
    for index, (left, right) in enumerate(zip(keeps, keeps[1:])):
        gap_start, gap_end = left[3], right[2]
        if gap_end <= gap_start:
            continue
        for word in words:
            a, b = _finite(word.get("acoustic_start")), _finite(word.get("acoustic_end"))
            if a is None or b is None or not (a < gap_start/rate < gap_end/rate < b):
                continue
            duration = b-a
            coverage = (max(0.0, min(b, left[3]/rate)-max(a, left[2]/rate))
                        + max(0.0, min(b, right[3]/rate)-max(a, right[2]/rate)))/duration
            reasons = []
            if not ordered:
                reasons.append("source-or-timeline-order-invalid")
            if left[1] != right[0]:
                reasons.append("timeline-not-contiguous")
            if gap_origin != "vad_silence":
                reasons.append("unknown-or-intentional-gap-origin")
            if any(gap_start < end and gap_end > start for start, end in protected):
                reasons.append("protected-removal")
            if gap_end-gap_start > 5 or (gap_end-gap_start)/rate > 0.180+1e-9:
                reasons.append("gap-exceeds-frame-or-duration-limit")
            if duration > 1.2 or duration < 0.06 or coverage < 0.70:
                reasons.append("implausible-word-duration-or-insufficient-coverage")
            confidence = _finite(word.get("confidence"))
            if confidence is None or confidence < 0.90 or confidence > 1:
                reasons.append("low-or-invalid-asr-confidence")
            if word.get("timing_origin") != "asr-word-timestamps":
                reasons.append("not-original-word-timestamps")
            proof = (verified_words or {}).get(str(word.get("word_id", "")), {})
            if not _verified_word(word, proof, media_identity or {}):
                reasons.append("source-audio-verification-required")
            decisions.append({
                "word_id": word.get("word_id"), "text": word.get("text"),
                "gap_source_frames": [gap_start, gap_end], "left_keep_index": index,
                "gap_frames": gap_end-gap_start, "gap_seconds": (gap_end-gap_start)/rate,
                "retained_source_coverage": round(coverage, 8),
                "eligible_for_verified_restoration": not reasons,
                "status": "verified-candidate-not-applied" if not reasons else "review-required",
                "reasons": reasons, "applied": False,
            })
    return {"protocol": "hafez-word-boundary-review-v1", "mode": "report-only",
            "restored_frames": 0, "cuts_changed": False,
            "source_and_timeline_order_valid": ordered,
            "decisions": decisions, "invalid_word_evidence": invalid_words,
            "eligible_candidates": sum(d["eligible_for_verified_restoration"] for d in decisions),
            "review_required": len(invalid_words)+sum(bool(d["reasons"]) for d in decisions),
            "publication_ready": False}
