"""Conservative, pure orphan-caption merges; not integrated into finalize yet.

The caller supplies ONLY already-selected cue word IDs. No transcript search,
copy correction, word restoration, media read, ASR, or keep/audio edit occurs.

Contract:
* cues: id, start/end (final timeline seconds), text, source_word_ids in order.
* words: source_word_id/source_evidence_id, media_sha256, literal text,
  start/end (final timeline), unclipped acoustic_start/acoustic_end (source),
  confidence, timing_origin='asr-word-timestamps', source_coverage=1,
  word_boundary_review_required=False.
* keeps: id, media_sha256, start_frame/end_frame, source_in_frame/source_out_frame;
  finite integer, positive, ordered, non-overlapping, 1x final A1 clips.
* fps: exact positive integer (numerator, denominator), not a float.

media_sha256 is a caller-verified content fingerprint, not computed here. This
helper checks binding/format, not whether a caller actually hashed the media.
ASR timing remains machine evidence, never publication/audio verification.
Legacy or ambiguous ownership and explicit protected boundaries fail closed.
"""
from __future__ import annotations

import copy
import math
import re
from collections import Counter
from fractions import Fraction
from typing import Any, Mapping, Sequence

from caption_layout import wrap_caption


class _Refused(ValueError):
    pass


def _number(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise _Refused("missing-or-invalid-timing")
    if isinstance(value, float) and not math.isfinite(value):
        raise _Refused("missing-or-invalid-timing")
    return value if isinstance(value, Fraction) else Fraction(str(value))


def _tokens(text: Any) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise _Refused("missing-or-invalid-text")
    return text.split()


def _orphan(cue: Mapping[str, Any], minimum: Fraction) -> bool:
    duration = _number(cue["end"]) - _number(cue["start"])
    return duration < minimum or (len(_tokens(cue["text"])) == 1 and duration > Fraction(5, 2))


def _boundary_protected(cue: Mapping[str, Any], side: str) -> bool:
    flag = "caption_boundary_" + side
    reason = cue.get(flag + "_reason")
    # Only a named automatic segment partition may be crossed with positive
    # word/keep proof. Existing unlabelled True boundaries stay hard.
    return reason in ("manual", "protected", "source-cut") or (
        bool(cue.get(flag)) and reason != "segment-partition")


def merge_orphan_cues(
    cues: Sequence[Mapping[str, Any]], *, words: Sequence[Mapping[str, Any]],
    keeps: Sequence[Mapping[str, Any]], fps: tuple[int, int],
    media_sha256: str, evidence_id: str, min_duration: float = .65,
    max_duration: float = 6.5, max_chars: int = 78,
    min_confidence: float = .8,
) -> dict[str, Any]:
    """Return copied cues, merge decisions and unresolved orphan review reasons.

    Only adjacent pairs containing an orphan can change. A pair first tries its
    existing outer endpoints. If that starts outside the unique source keep,
    only a LATER start at its existing first-word onset is allowed. Last end is
    always unchanged. No earlier hold, end extension, tail rebalance or cut
    restoration is implemented. Both returned float timing and the existing
    SRT writer's millisecond rounding must remain within that same keep; an
    unsafe representation is refused, never shifted again to make it fit.
    Missing context is a refusal, not permission.
    Invalid cue/keep/fps structure raises ValueError before any result mutation.
    """
    if (not isinstance(fps, tuple) or len(fps) != 2
            or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in fps)):
        raise ValueError("fps must be an exact positive integer pair")
    if (not isinstance(media_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", media_sha256)
            or not isinstance(evidence_id, str) or not evidence_id.strip()):
        raise ValueError("A content fingerprint and source evidence identity are required")
    rate = Fraction(*fps)
    minimum, maximum, confidence_floor = map(_number, (min_duration, max_duration, min_confidence))
    if (minimum <= 0 or maximum < minimum or not 0 <= confidence_floor <= 1
            or isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars <= 0):
        raise ValueError("Invalid caption layout limits")
    original = copy.deepcopy(list(cues))
    result = copy.deepcopy(original)
    ids = []
    previous_end = Fraction(0)
    for cue in original:
        cue_id = cue.get("id")
        if isinstance(cue_id, bool) or not isinstance(cue_id, (str, int)) or cue_id == "":
            raise ValueError("Every selected cue needs a stable ID")
        ids.append(cue_id)
        start, end = _number(cue.get("start")), _number(cue.get("end"))
        _tokens(cue.get("text"))
        if start < previous_end or end <= start:
            raise ValueError("Cues must be positive ordered non-overlapping intervals")
        previous_end = end
    if len(set(ids)) != len(ids):
        raise ValueError("Cue IDs must be unique")

    checked_keeps = copy.deepcopy(list(keeps))
    previous_end_frame = 0
    keep_ids = set()
    for keep in checked_keeps:
        fields = [keep.get(k) for k in ("start_frame", "end_frame", "source_in_frame", "source_out_frame")]
        if (any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in fields)
                or not isinstance(keep.get("id"), str) or not keep["id"] or keep["id"] in keep_ids):
            raise ValueError("Invalid or duplicate final A1 keep")
        a, b, c, d = fields
        if (a < previous_end_frame or b <= a or d <= c or b-a != d-c
                or keep.get("media_sha256") != media_sha256):
            raise ValueError("Final A1 keeps must be source-bound, ordered and 1x")
        previous_end_frame = b
        keep_ids.add(keep["id"])

    word_index: dict[str, list[Mapping[str, Any]]] = {}
    for word in words:
        word_id = word.get("source_word_id")
        if isinstance(word_id, str) and word_id:
            word_index.setdefault(word_id, []).append(word)
    owners = Counter(word_id for cue in original
                     for word_id in (cue.get("source_word_ids") if isinstance(cue.get("source_word_ids"), list) else [])
                     if isinstance(word_id, str))
    decisions: list[dict[str, Any]] = []
    reasons: dict[Any, set[str]] = {}

    def owned_words(cue):
        selected = cue.get("source_word_ids")
        if not isinstance(selected, list) or not selected or any(not isinstance(i, str) or not i for i in selected):
            raise _Refused("missing-exact-word-ownership")
        if len(set(selected)) != len(selected) or any(owners[i] != 1 for i in selected):
            raise _Refused("ambiguous-word-ownership")
        rows = []
        for word_id in selected:
            found = word_index.get(word_id, [])
            if len(found) != 1:
                raise _Refused("missing-or-ambiguous-word-evidence")
            word = found[0]
            if word.get("media_sha256") != media_sha256 or word.get("source_evidence_id") != evidence_id:
                raise _Refused("word-source-fingerprint-mismatch")
            if word.get("timing_origin") != "asr-word-timestamps":
                raise _Refused("interpolated-or-unknown-word-timing")
            if (_number(word.get("source_coverage")) != 1
                    or word.get("word_boundary_review_required") is not False):
                raise _Refused("partial-or-unreviewed-word-boundary")
            a, b = _number(word.get("acoustic_start")), _number(word.get("acoustic_end"))
            t, u = _number(word.get("start")), _number(word.get("end"))
            confidence = _number(word.get("confidence"))
            if (a < 0 or b <= a or t < 0 or u <= t or b-a > Fraction(5, 2)
                    or not confidence_floor <= confidence <= 1):
                raise _Refused("implausible-or-low-confidence-word-timing")
            if len(_tokens(word.get("text"))) != 1:
                raise _Refused("nonliteral-word-alignment")
            rows.append(word)
        if [word["text"] for word in rows] != _tokens(cue["text"]):
            raise _Refused("nonliteral-word-alignment")
        return rows

    def try_pair(left, right):
        if any(c.get("protected") or c.get("copy_review_required") for c in (left, right)):
            raise _Refused("protected-or-copy-review-required-cue")
        if _boundary_protected(left, "after") or _boundary_protected(right, "before"):
            raise _Refused("protected-caption-boundary")
        if _number(right["start"]) - _number(left["end"]) > Fraction(35, 100):
            raise _Refused("caption-gap-too-large")
        rows = owned_words(left) + owned_words(right)
        for a, b in zip(rows, rows[1:]):
            source_gap = _number(b["acoustic_start"]) - _number(a["acoustic_end"])
            timeline_gap = _number(b["start"]) - _number(a["end"])
            if source_gap < 0 or timeline_gap < 0 or source_gap > Fraction(35, 100):
                raise _Refused("noncontiguous-or-reordered-word-evidence")
        possible = [k for k in checked_keeps
                    if all(_number(w["acoustic_start"]) >= Fraction(k["source_in_frame"], 1)/rate
                           and _number(w["acoustic_end"]) <= Fraction(k["source_out_frame"], 1)/rate for w in rows)]
        if len(possible) != 1:
            raise _Refused("no-unique-whole-word-source-keep")
        keep = possible[0]
        # Rounded prior timeline mappings may differ by less than one frame.
        # This tolerance validates evidence; it NEVER restores or crosses a cut.
        tolerance = min(Fraction(1, 20), 1/rate)
        offset = Fraction(keep["start_frame"]-keep["source_in_frame"], 1)/rate
        if any(abs(_number(w[t])-(_number(w[s])+offset)) > tolerance
               for w in rows for t, s in (("start", "acoustic_start"), ("end", "acoustic_end"))):
            raise _Refused("word-timeline-source-map-mismatch")
        start, end = _number(left["start"]), _number(right["end"])
        if abs(end-_number(rows[-1]["end"])) > tolerance:
            raise _Refused("last-end-not-supported-by-word-evidence")

        def contained(a, b):
            return math.floor(a*rate) >= keep["start_frame"] and math.ceil(b*rate) <= keep["end_frame"]

        mode = "merge-preserve-endpoints"
        if not contained(start, end):
            onset = _number(rows[0]["start"])
            if onset <= start or onset >= end or not contained(onset, end):
                raise _Refused("caption-range-crosses-source-keep")
            start = onset
            mode = "merge-start-later-only"
        joined = _tokens(left["text"]) + _tokens(right["text"])
        if not minimum <= end-start <= maximum or len(" ".join(joined)) > max_chars:
            raise _Refused("merged-caption-exceeds-layout-limits")
        # A valid rational endpoint need not stay valid after conversion. For
        # example 1/3 at 30fps becomes float .3333333333333333 (frame floor 9),
        # then SRT .333 (also frame 9), despite its rational frame being 10.
        # Validate exactly what this helper and write_srt/format_timestamp use.
        returned_start = float(start)
        returned_end = float(end)
        returned_times = (_number(returned_start), _number(returned_end))
        serialized_times = (Fraction(int(round(returned_start*1000)), 1000),
                            Fraction(int(round(returned_end*1000)), 1000))
        for representation, (a, b) in (("returned", returned_times), ("serialized", serialized_times)):
            if not minimum <= b-a <= maximum:
                raise _Refused(representation + "-timing-exceeds-layout-limits")
            if not contained(a, b):
                raise _Refused(representation + "-timing-crosses-source-keep")
        merged = copy.deepcopy(dict(left))
        merged.update(start=returned_start, end=right["end"], text=wrap_caption(" ".join(joined)),
                      source_word_ids=list(left["source_word_ids"])+list(right["source_word_ids"]))
        merged["caption_boundary_after"] = bool(right.get("caption_boundary_after"))
        if "caption_boundary_after_reason" in right:
            merged["caption_boundary_after_reason"] = right["caption_boundary_after_reason"]
        else:
            merged.pop("caption_boundary_after_reason", None)
        source_cues = (left.get("caption_source_cue_ids", [left["id"]])
                       + right.get("caption_source_cue_ids", [right["id"]]))
        merged["caption_source_cue_ids"] = copy.deepcopy(source_cues)
        return merged, {"action": mode, "source_cue_ids": copy.deepcopy(source_cues),
                        "source_word_ids": copy.deepcopy(merged["source_word_ids"]), "keep_id": keep["id"],
                        "before": [left["start"], right["end"]], "after": [returned_start, right["end"]],
                        "frame_envelope": [math.floor(returned_times[0]*rate), math.ceil(returned_times[1]*rate)],
                        "serialized_frame_envelope": [math.floor(serialized_times[0]*rate), math.ceil(serialized_times[1]*rate)]}

    index = 0
    while index < len(result):
        cue = result[index]
        if not _orphan(cue, minimum):
            index += 1
            continue
        merged = False
        for left_index in ([index-1] if index else []) + ([index] if index+1 < len(result) else []):
            try:
                replacement, decision = try_pair(*result[left_index:left_index+2])
            except _Refused as error:
                reasons.setdefault(cue["id"], set()).add(str(error))
                continue
            result[left_index:left_index+2] = [replacement]
            decisions.append(decision)
            index = max(0, left_index)
            merged = True
            break
        if not merged:
            index += 1
    if [t for c in result for t in _tokens(c["text"])] != [t for c in original for t in _tokens(c["text"])]:
        raise AssertionError("Caption literal token order changed")
    if any(_number(a["end"]) > _number(b["start"]) for a, b in zip(result, result[1:])):
        raise AssertionError("Caption merge introduced overlap")
    return {"cues": result, "decisions": decisions,
            "review": [{"cue_id": c["id"], "reasons": sorted(reasons.get(c["id"], {"no-eligible-adjacent-cue"}))}
                       for c in result if _orphan(c, minimum)],
            "audio_or_cuts_changed": False, "publication_ready": False,
            "status": "layout-only-machine-word-evidence-not-audio-verification"}
