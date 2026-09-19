"""Optional exact binding from selected SRT chunks to source-word evidence.

Context supplies original mapped ``words``, final 1x A1 ``keeps``, exact tuple
``fps``, ``evidence_id`` and caller-verified content ``media_sha256``. Each word
and keep must already carry that fingerprint; this module never invents one,
hashes media, infers FPS from floats, searches transcript text, or edits cuts.
Legacy/missing/ambiguous binding retains the prior caption output. Successful
binding is machine timing evidence, not proof that the ASR text was spoken.
"""
from __future__ import annotations

import copy
import math
from fractions import Fraction
from typing import Any

from caption_evidence import merge_orphan_cues


def apply_caption_context(
    baseline: list[dict[str, Any]], raw_cues: list[dict[str, Any]],
    bindings: list[tuple[dict[str, Any], int, int]],
    context: dict[str, Any] | None, audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Bind only explicit owned IDs, then attempt conservative orphan merges.

    bindings parallels raw_cues: (selected segment, literal token start, end).
    A segment's full old source_text is intentionally never read. Any removed
    owned word must be wholly outside every final keep; partial/ambiguous words
    refuse binding. The retained ordered tokens must equal the selected text.
    The caller keeps responsibility for verifying the supplied content hash.
    """
    report: dict[str, Any] = {
        "status": "unchanged", "applied": False, "decisions": [], "review": [],
        "context_rejections": [], "audio_or_cuts_changed": False, "publication_ready": False,
    }

    def finish(rows, reason=None):
        if reason:
            report["context_rejections"].append({"reason": reason})
        if audit is not None:
            audit.update(copy.deepcopy(report))
        return rows

    if context is None:
        return finish(baseline, "missing-caption-context")
    if not isinstance(context, dict) or any(
        key not in context for key in ("words", "keeps", "fps", "media_sha256", "evidence_id")
    ):
        return finish(baseline, "incomplete-caption-context")
    words, keeps = context["words"], context["keeps"]
    if (not isinstance(words, list) or not isinstance(keeps, list)
            or any(not isinstance(row, dict) for row in words + keeps)):
        return finish(baseline, "invalid-caption-context-rows")
    try:
        # Reuse the helper's exact clock/fingerprint/1x keep validation, without
        # passing cues or performing a layout change during this preflight.
        merge_orphan_cues([], words=[], keeps=keeps, fps=context["fps"],
                          media_sha256=context["media_sha256"], evidence_id=context["evidence_id"])
    except ValueError:
        return finish(baseline, "invalid-caption-clock-fingerprint-or-keeps")
    if len(raw_cues) != len(bindings):
        return finish(baseline, "invalid-caption-chunk-ownership")
    rate = Fraction(*context["fps"])
    word_index: dict[str, list[dict[str, Any]]] = {}
    for word in words:
        if isinstance(word.get("source_word_id"), str):
            word_index.setdefault(word["source_word_id"], []).append(word)

    def number(value):
        if (isinstance(value, bool) or not isinstance(value, (int, float, Fraction))
                or isinstance(value, float) and not math.isfinite(value)):
            raise ValueError("missing-or-invalid-acoustic-timing")
        return value if isinstance(value, Fraction) else Fraction(str(value))

    expected_tokens: dict[int, list[str]] = {}
    for cue, (segment, _, _) in zip(raw_cues, bindings):
        expected_tokens.setdefault(id(segment), []).extend(cue["text"].split())
    segment_cache: dict[int, list[str] | None] = {}
    mapped_words: dict[str, dict[str, Any]] = {}

    def bind_segment(segment):
        cache_key = id(segment)
        if cache_key in segment_cache:
            return segment_cache[cache_key]
        selected = segment.get("source_word_ids")
        try:
            if (not isinstance(selected, list) or not selected
                    or any(not isinstance(value, str) or not value for value in selected)):
                raise ValueError("missing-exact-word-ownership")
            if len(set(selected)) != len(selected):
                raise ValueError("ambiguous-word-ownership")
            if segment.get("source_evidence_id") != context["evidence_id"]:
                raise ValueError("segment-evidence-id-mismatch")
            retained = []
            for word_id in selected:
                matches = word_index.get(word_id, [])
                if len(matches) != 1:
                    raise ValueError("missing-or-ambiguous-word-evidence")
                word = matches[0]
                if (word.get("media_sha256") != context["media_sha256"]
                        or word.get("source_evidence_id") != context["evidence_id"]):
                    raise ValueError("word-source-fingerprint-mismatch")
                start, end = number(word.get("acoustic_start")), number(word.get("acoustic_end"))
                if start < 0 or end <= start:
                    raise ValueError("missing-or-invalid-acoustic-timing")
                overlapping = [keep for keep in keeps
                               if start < Fraction(keep["source_out_frame"], 1) / rate
                               and end > Fraction(keep["source_in_frame"], 1) / rate]
                if not overlapping:
                    # Exclusion is based only on the physical final keep map.
                    # The selected caption must already omit this exact word.
                    continue
                if len(overlapping) != 1:
                    raise ValueError("ambiguous-final-word-keep")
                keep = overlapping[0]
                if (start < Fraction(keep["source_in_frame"], 1) / rate
                        or end > Fraction(keep["source_out_frame"], 1) / rate):
                    raise ValueError("partial-word-after-final-cut")
                offset = Fraction(keep["start_frame"] - keep["source_in_frame"], 1) / rate
                mapped = dict(word, start=start + offset, end=end + offset)
                retained.append(mapped)
            if [word.get("text") for word in retained] != expected_tokens[cache_key]:
                raise ValueError("selected-text-word-mismatch")
            selected_ids = [word["source_word_id"] for word in retained]
            mapped_words.update({word["source_word_id"]: word for word in retained})
            segment_cache[cache_key] = selected_ids
            return selected_ids
        except ValueError as error:
            segment_cache[cache_key] = None
            report["context_rejections"].append({"segment_id": segment.get("id"), "reason": str(error)})
            return None

    def cue_key(cue):
        return cue["start"], cue["end"], cue["text"]

    raw_lookup = {cue_key(cue): index for index, cue in enumerate(raw_cues)}
    if len(raw_lookup) != len(raw_cues):
        return finish(baseline, "ambiguous-caption-chunk-ownership")
    prepared = []
    for cue in baseline:
        leaves = cue.get("layout_source_cues", [cue])
        try:
            indices = [raw_lookup[cue_key(leaf)] for leaf in leaves]
        except (KeyError, TypeError):
            return finish(baseline, "missing-caption-chunk-ownership")
        if (not indices or indices != list(range(indices[0], indices[-1] + 1))
                or [token for leaf in leaves for token in leaf["text"].split()] != cue["text"].split()):
            return finish(baseline, "nonliteral-regrouped-chunk-ownership")
        owned_ids = []
        valid = True
        mapped = copy.deepcopy(cue)
        mapped["id"] = f"caption-{indices[0]}"
        internal_protection = []
        for left_index, right_index in zip(indices, indices[1:]):
            left_segment, _, left_end = bindings[left_index]
            right_segment, right_start, _ = bindings[right_index]
            for segment, side, is_outer in (
                (left_segment, "after", left_end == len(expected_tokens[id(left_segment)])),
                (right_segment, "before", right_start == 0),
            ):
                key = "caption_boundary_" + side
                reason = segment.get(key + "_reason")
                if is_outer and reason != "segment-partition" and (
                    segment.get(key) or isinstance(reason, str) and reason.strip()
                ):
                    internal_protection.append(reason or "unlabelled-boundary")
        if internal_protection:
            # Old regrouping uses booleans only. Never let a reason hidden in
            # its composite authorize an additional merge. Do not undo the old
            # baseline layout or silently rewrite the protected input instead.
            mapped["protected"] = True
            report["context_rejections"].append({
                "cue_id": mapped["id"], "reason": "protected-internal-regroup-boundary",
                "boundary_reasons": list(dict.fromkeys(internal_protection)),
            })
        for index in indices:
            segment, first, last = bindings[index]
            selected_ids = bind_segment(segment)
            if selected_ids is None:
                valid = False
            else:
                owned_ids.extend(selected_ids[first:last])
            for flag in ("protected", "copy_review_required"):
                if segment.get(flag):
                    mapped[flag] = True
        mapped["source_word_ids"] = owned_ids if valid else []
        for side, index in (("before", indices[0]), ("after", indices[-1])):
            segment, first, last = bindings[index]
            is_outer = first == 0 if side == "before" else last == len(expected_tokens[id(segment)])
            key = "caption_boundary_" + side
            if is_outer and isinstance(segment.get(key + "_reason"), str):
                mapped[key + "_reason"] = segment[key + "_reason"]
                if segment[key + "_reason"] != "segment-partition":
                    mapped[key] = True
        prepared.append(mapped)
    try:
        result = merge_orphan_cues(prepared, words=list(mapped_words.values()), keeps=keeps,
                                  fps=context["fps"], media_sha256=context["media_sha256"],
                                  evidence_id=context["evidence_id"])
    except ValueError:
        return finish(baseline, "invalid-bound-caption-context")
    report.update({key: result[key] for key in ("status", "decisions", "review")})
    report["applied"] = bool(result["decisions"])
    # Failed or inapplicable optimization must not alter even legacy metadata.
    return finish(result["cues"] if report["applied"] else baseline)
