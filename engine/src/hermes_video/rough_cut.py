"""Non-destructive Safe/Tight rough-cut planning for the Hermes editor.

All edit decisions arrive from an LLM, but this module treats them only as
suggestions.  It validates confidence, caps the amount of removed material and
builds deterministic source/timeline mappings for both camera tracks.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any, Iterable


SAFE_CONFIDENCE = 0.92
TIGHT_CONFIDENCE = 0.82
SAFE_MAX_REMOVAL_RATIO = 0.12
TIGHT_MAX_REMOVAL_RATIO = 0.25

ALLOWED_ACTIONS = {"cut_safe", "cut_tight", "review", "keep"}
ALLOWED_MARKERS = {
    "B-ROLL", "CAM1", "CAM2", "TITLE", "CHAPTER", "SFX", "CHECK",
    "TEXT", "GRAPHIC", "FLOWCHART", "COMPARE", "HOOK", "PUNCH", "PACE",
}


def detect_short_setup_prefix(clips, words, fps):
    """Tight-only removal of isolated sub-half-second pre-speech setup bursts.

    Never remove a full sentence or a long untranscribed passage. Safe remains
    untouched. This is a bounded editorial heuristic, not acoustic validation.
    """
    if not clips or not words or fps <= 0:
        return []
    first_word = min(words, key=lambda w: float(w["start"]))
    prefix = []
    for index, clip in enumerate(clips[:-1]):
        start, end, source_in, source_out = clip[:4]
        following = clips[index+1]
        if (index >= 2 or start != (prefix[-1][1] if prefix else 0)
                or end/fps > 1.0 or (end-start)/fps > .5
                or end/fps > float(first_word["start"]) - .06
                or (following[2]-source_out)/fps < 2.0
                or any(float(w["start"]) < end/fps and float(w["end"]) > start/fps for w in words)):
            break
        prefix.append(clip)
    if not prefix:
        return []
    return [{"segment_id": -1, "action": "cut_tight", "confidence": .96,
             "start": 0.0, "end": prefix[-1][1]/fps, "remove_text": "", "matched_text": "",
             "reason": "حذف Tight-only برش‌های بسیار کوتاه آماده‌سازی پیش از نخستین گفتار؛ Safe دست‌نخورده است.",
             "source": "short-pre-speech-setup-clips", "audio_verified": False}]


def _clean_token(value: str) -> str:
    normalized = str(value).casefold().translate(
        str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"})
    )
    normalized = re.sub(r"[،؛؟«»…]", "", normalized)
    return re.sub(r"[^\w\u0600-\u06ff]+", "", normalized)


def _tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) < 4:
        return False
    return SequenceMatcher(None, left, right).ratio() >= 0.84


def _abandoned_repeat(tokens: list[str]) -> tuple[int, int, int] | None:
    """Return the first abandoned phrase before an immediate verbal restart."""
    best: tuple[int, int, int] | None = None
    for first in range(len(tokens)):
        for second in range(first + 2, min(len(tokens), first + 13)):
            common = 0
            while (
                first + common < second
                and second + common < len(tokens)
                and _tokens_match(tokens[first + common], tokens[second + common])
                and common < 8
            ):
                common += 1
            phrase_chars = sum(len(value) for value in tokens[first : first + common])
            gap_words = second - (first + common)
            if (common >= 3 or (common >= 2 and phrase_chars >= 6)) and gap_words <= 3:
                candidate = (common, first, second)
                if best is None or candidate > best:
                    best = candidate
    return (best[1], best[2], best[0]) if best else None


def _abandoned_cut_end(tokens: list[str], first: int, second: int, common: int) -> int:
    """Include a completed false-start tail, but preserve a corrected lead-in."""
    gap = tokens[first + common : second]
    verb_hints = (
        "کردم", "گفتم", "چیدم", "ساختم", "رفتم", "دیدم", "خواستم", "گذاشتم",
        "میشد", "می‌شد", "شد", "بود", "هست", "است", "میکنم", "می‌کنم",
    )
    if any(any(token.endswith(hint) for hint in verb_hints) for token in gap):
        return second
    return first + common


def _locate_tokens(
    wanted: list[str],
    candidates: list[dict[str, Any]],
    segment: dict[str, Any],
) -> tuple[float, float] | None:
    tokens = [_clean_token(word.get("text", "")) for word in candidates]
    for index in range(0, len(tokens) - len(wanted) + 1):
        if all(_tokens_match(left, right) for left, right in zip(tokens[index : index + len(wanted)], wanted)):
            joined_expected = " ".join(wanted)
            joined_actual = " ".join(tokens[index : index + len(wanted)])
            if joined_actual != joined_expected and SequenceMatcher(None, joined_actual, joined_expected).ratio() < 0.88:
                continue
            start = max(float(segment["start"]), float(candidates[index]["start"]) - 0.025)
            end_word = candidates[index + len(wanted) - 1]
            end = min(float(segment["end"]), float(end_word["end"]) + 0.025)
            if end - start >= 0.10:
                return start, end
    return None


def _matched_text_for_span(words: list[dict[str, Any]], span: tuple[float, float]) -> str:
    start, end = span
    selected = [
        str(word.get("text", "")).strip()
        for word in words
        if start + 0.01
        <= (float(word.get("start", 0.0)) + float(word.get("end", 0.0))) / 2
        <= end - 0.01
    ]
    return " ".join(value for value in selected if value).strip()


def _remove_first_fuzzy_phrase(text: str, phrase: str) -> str:
    """Remove one aligned phrase from corrected text without relying on punctuation."""
    text_matches = list(re.finditer(r"\S+", str(text)))
    text_tokens = [_clean_token(match.group(0)) for match in text_matches]
    wanted = [_clean_token(value) for value in str(phrase).split()]
    wanted = [value for value in wanted if value]
    if not wanted:
        return str(text)
    for index in range(0, len(text_tokens) - len(wanted) + 1):
        if all(_tokens_match(left, right) for left, right in zip(text_tokens[index : index + len(wanted)], wanted)):
            start = text_matches[index].start()
            end = text_matches[index + len(wanted) - 1].end()
            return re.sub(r"\s+", " ", str(text)[:start] + " " + str(text)[end:]).strip(" ،؛")
    best: tuple[float, int, int] | None = None
    for index in range(len(text_tokens)):
        for length in range(max(2, len(wanted) - 3), min(len(text_tokens) - index, len(wanted) + 3) + 1):
            actual = text_tokens[index : index + length]
            if len(actual) < 2 or len(wanted) < 2 or not all(
                _tokens_match(left, right) for left, right in zip(actual[:2], wanted[:2])
            ):
                continue
            token_ratio = SequenceMatcher(None, actual, wanted).ratio()
            character_ratio = SequenceMatcher(None, "".join(actual), "".join(wanted)).ratio()
            score = max(token_ratio, character_ratio)
            if score >= 0.72 and (best is None or score > best[0]):
                best = (score, index, length)
    if best:
        _score, index, length = best
        start = text_matches[index].start()
        end = text_matches[index + length - 1].end()
        return re.sub(r"\s+", " ", str(text)[:start] + " " + str(text)[end:]).strip(" ،؛")
    return str(text)


def _merge_intervals(intervals: Iterable[tuple[float, float]], gap: float = 0.06) -> list[tuple[float, float]]:
    ordered = sorted((max(0.0, float(a)), max(0.0, float(b))) for a, b in intervals if b > a)
    merged: list[list[float]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1] + gap:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(round(a, 4), round(b, 4)) for a, b in merged]


def _interval_duration(intervals: Iterable[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in _merge_intervals(intervals))


def _find_word_span(
    remove_text: str,
    segment: dict[str, Any],
    words: list[dict[str, Any]],
) -> tuple[float, float] | None:
    """Locate a requested phrase, tolerating harmless ASR spelling variants.

    When the requested text itself contains an immediate restart (``A ... A``),
    only the abandoned first attempt is returned so the corrected attempt stays.
    """
    wanted = [_clean_token(token) for token in str(remove_text).split()]
    wanted = [token for token in wanted if token]
    if not wanted:
        return None
    candidates = [
        word
        for word in words
        if float(word.get("end", 0.0)) > float(segment["start"])
        and float(word.get("start", 0.0)) < float(segment["end"])
    ]
    repeated = _abandoned_repeat(wanted)
    if repeated:
        first, second, common = repeated
        cut_end = _abandoned_cut_end(wanted, first, second, common)
        span = _locate_tokens(wanted[first:cut_end], candidates, segment)
        if span:
            return span
    return _locate_tokens(wanted, candidates, segment)


def detect_repeated_speech_edits(
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create Tight-only cuts for high-confidence immediate verbal restarts."""
    edits: list[dict[str, Any]] = []
    stopwords = {"که", "این", "اون", "برای", "از", "به", "و", "رو", "را", "یک", "یه"}
    for segment_index, segment in enumerate(segments):
        candidates = [
            word
            for word in words
            if float(word.get("end", 0.0)) > float(segment["start"])
            and float(word.get("start", 0.0)) < float(segment["end"])
        ]
        tokens = [_clean_token(word.get("text", "")) for word in candidates]
        repeated = _abandoned_repeat(tokens)
        if not repeated:
            continue
        first, second, common = repeated
        # Deterministic cuts are limited to a restart at the beginning of the
        # ASR segment.  Mid-sentence repetition may be rhetorical or may need a
        # preceding preposition, so it remains for the semantic reviewer.
        if first != 0:
            continue
        shared_probe = tokens[first : min(second, first + 4)]
        if not shared_probe or all(token in stopwords for token in shared_probe):
            continue
        gap = tokens[first + common : second]
        if first == 0 and gap and segment_index > 0:
            previous = segments[segment_index - 1]
            previous_words = str(previous.get("text", "")).split()
            previous_tokens = [_clean_token(value) for value in previous_words]
            if len(previous_tokens) >= len(gap) and all(
                _tokens_match(left, right) for left, right in zip(previous_tokens[-len(gap) :], gap)
            ):
                edits.append(
                    {
                        "segment_id": int(previous["id"]),
                        "action": "cut_tight",
                        "confidence": 0.97,
                        "remove_text": " ".join(previous_words[-len(gap) :]),
                        "reason": "شروع تکراری از مرز segment قبلی آغاز شده و نسخه کامل بعدی نگه داشته می‌شود.",
                        "source": "deterministic-boundary-restart",
                    }
                )
        cut_end = _abandoned_cut_end(tokens, first, second, common)
        start = max(float(segment["start"]), float(candidates[first]["start"]) - 0.02)
        end = min(float(segment["end"]), float(candidates[cut_end - 1]["end"]) + 0.025)
        if not 0.18 <= end - start <= 6.0:
            continue
        edits.append(
            {
                "segment_id": int(segment["id"]),
                "action": "cut_tight",
                "confidence": 0.965,
                "remove_text": " ".join(
                    str(word.get("text", "")).strip() for word in candidates[first:cut_end]
                ),
                "reason": "تکرار فوری یا شروع ناقص که با بیان درست‌تر ادامه پیدا کرده است.",
                "source": "deterministic-verbal-restart",
            }
        )

    # ASR segmentation can split a restart across two or three subtitle
    # segments.  Detect a long repeated lead in a nearby later segment, trim
    # only the abandoned suffix of the first segment, and remove the short
    # fragments between the two attempts.  The final/later wording remains.
    for first_index, first_segment in enumerate(segments):
        first_words = str(first_segment.get("text", "")).split()
        first_tokens = [_clean_token(value) for value in first_words]
        best: tuple[int, int, int] | None = None
        for later_index in range(first_index + 1, min(len(segments), first_index + 5)):
            later_segment = segments[later_index]
            if float(later_segment["start"]) - float(first_segment["start"]) > 20.0:
                break
            later_tokens = [_clean_token(value) for value in str(later_segment.get("text", "")).split()]
            for offset in range(min(5, len(first_tokens))):
                common = 0
                while (
                    offset + common < len(first_tokens)
                    and common < len(later_tokens)
                    and _tokens_match(first_tokens[offset + common], later_tokens[common])
                    and common < 16
                ):
                    common += 1
                shared_chars = sum(len(value) for value in later_tokens[:common])
                first_window = first_tokens[offset : offset + 12]
                later_window = later_tokens[:12]
                sequence_ratio = SequenceMatcher(None, first_window, later_window).ratio()
                same_opening = len(first_window) >= 2 and len(later_window) >= 2 and all(
                    _tokens_match(left, right) for left, right in zip(first_window[:2], later_window[:2])
                )
                fuzzy_restart = same_opening and sequence_ratio >= 0.72 and sum(len(value) for value in later_window) >= 30
                if (common >= 6 and shared_chars >= 24) or fuzzy_restart:
                    evidence = max(common, int(round(sequence_ratio * 10)))
                    candidate = (evidence, -offset, later_index)
                    if best is None or candidate > best:
                        best = candidate
        if not best:
            continue
        _common, negative_offset, later_index = best
        offset = -negative_offset
        abandoned = " ".join(first_words[offset:]).strip()
        if abandoned:
            edits.append(
                {
                    "segment_id": int(first_segment["id"]),
                    "action": "cut_tight",
                    "confidence": 0.975,
                    "remove_text": abandoned,
                    "reason": "تکرار بین چند segment و شروع ناقص که با بیان کامل‌تر ادامه پیدا کرده است.",
                    "source": "deterministic-cross-segment-restart",
                }
            )
        for middle in segments[first_index + 1 : later_index]:
            middle_text = str(middle.get("text", "")).strip()
            if middle_text:
                edits.append(
                    {
                        "segment_id": int(middle["id"]),
                        "action": "cut_tight",
                        "confidence": 0.975,
                        "remove_text": middle_text,
                        "reason": "ادامه شروع ناقص میان دو بیان تکراری است و نسخه کامل بعدی نگه داشته می‌شود.",
                        "source": "deterministic-cross-segment-restart",
                    }
                )
    return edits


def _cut_reason_is_safe(reason: str) -> bool:
    normalized = _clean_token(reason)
    cues = (
        "تکرار", "تپق", "ناقص", "اصلاح", "اشتباه", "بی معنی", "بیمعنی",
        "دوباره", "شروع مجدد", "سکوت", "false start", "self correction", "restart",
    )
    return any(_clean_token(cue) in normalized for cue in cues)


def guard_retained_retake(edits, words):
    """Do not let an LLM's reason stand in for an actual retained later take.

    Align against nearby original word timing, independently of model IDs or
    ASR segment partitions. Require a shared opening and substantial overlap;
    both takes being proposed for deletion is not evidence of a safe cut.
    """
    tokens = [_clean_token(w.get("text", "")) for w in words]
    proposed = [e for e in edits if e["action"] in {"cut_safe", "cut_tight"}]
    accepted, warnings = [], []
    for edit in sorted(edits, key=lambda e: float(e["start"]), reverse=True):
        if edit not in proposed:
            accepted.append(edit)
            continue
        wanted = [_clean_token(w) for w in str(edit.get("matched_text") or edit.get("remove_text", "")).split()]
        wanted = [w for w in wanted if w]
        proof = None
        if len(wanted) >= 2:
            for index, word in enumerate(words):
                start = float(word["start"])
                if start < float(edit["end"]) or start-float(edit["end"]) > 30:
                    continue
                probe = tokens[index:index+len(wanted)+6]
                prefix = min(4, len(wanted))
                if len(probe) < len(wanted) or probe[0] != wanted[0]:
                    continue
                same = sum(_tokens_match(a, b) for a, b in zip(wanted[:prefix], probe[:prefix]))
                if prefix < 4:
                    prefix_ok = same == prefix and sum(len(x) for x in wanted) >= 8 and start-float(edit["end"]) <= 6
                else:
                    prefix_ok = same >= 3 and sum(len(x) for x in wanted[:4]) >= 12
                matched = sum(block.size for block in SequenceMatcher(None, wanted, probe).get_matching_blocks())
                if not prefix_ok or matched / len(wanted) < .60:
                    continue
                end = float(words[min(len(words)-1, index+len(wanted)-1)]["end"])
                if any(min(end, float(other["end"])) > max(start, float(other["start"]))
                       for other in accepted if other["action"] in {"cut_safe", "cut_tight"}):
                    continue
                proof = {"start": start, "end": end, "opening_match_words": same,
                         "matched_word_ratio": round(matched/len(wanted), 3), "authority": "machine-transcript-retake-match"}
                break
        if proof is None:
            warnings.append(f"حذف segment {edit['segment_id']} رد شد: نسخهٔ بعدیِ هم‌آغاز و باقی‌مانده در متن پیدا نشد.")
            accepted.append({**edit, "action": "review", "retake_gate": "blocked-no-retained-later-take"})
        else:
            accepted.append({**edit, "retained_retake": proof})
    return sorted(accepted, key=lambda e: float(e["start"])), warnings


def validate_edit_decisions(
    raw_edits: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    words: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {int(segment["id"]): segment for segment in segments}
    segment_positions = {int(segment["id"]): index for index, segment in enumerate(segments)}
    validated: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[int, str, str]] = set()

    for raw in raw_edits:
        if not isinstance(raw, dict):
            continue
        try:
            segment_id = int(raw.get("segment_id"))
            confidence = float(raw.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        segment = by_id.get(segment_id)
        action = str(raw.get("action", "keep")).strip().casefold()
        if segment is None or action not in ALLOWED_ACTIONS:
            continue
        reason = str(raw.get("reason", "")).strip()
        if action in {"cut_safe", "cut_tight"} and not _cut_reason_is_safe(reason):
            warnings.append(f"پیشنهاد حذف segment {segment_id} چون تکرار/تپق/اصلاح قطعی نبود رد شد.")
            continue
        confidence = min(1.0, max(0.0, confidence))
        remove_text = str(raw.get("remove_text", "")).strip()
        signature = (segment_id, action, remove_text.casefold())
        if signature in seen:
            continue
        seen.add(signature)

        span = _find_word_span(remove_text, segment, words) if remove_text else None
        if remove_text and span is None:
            position = segment_positions.get(segment_id, -99)
            nearby_matches: list[tuple[dict[str, Any], tuple[float, float]]] = []
            for nearby in segments[max(0, position - 3) : min(len(segments), position + 4)]:
                if int(nearby["id"]) == segment_id:
                    continue
                nearby_span = _find_word_span(remove_text, nearby, words)
                if nearby_span:
                    nearby_matches.append((nearby, nearby_span))
            if len(nearby_matches) == 1:
                segment, span = nearby_matches[0]
                old_segment_id = segment_id
                segment_id = int(segment["id"])
                warnings.append(
                    f"عبارت حذف segment {old_segment_id} با تطبیق زمانی به segment {segment_id} منتقل شد."
                )
        if remove_text and span is None:
            warnings.append(f"عبارت حذف پیشنهادی segment {segment_id} دقیقاً پیدا نشد؛ پیشنهاد رد شد.")
            continue
        start, end = span or (float(segment["start"]), float(segment["end"]))
        if end - start < 0.10:
            continue
        validated.append(
            {
                "segment_id": segment_id,
                "action": action,
                "confidence": round(confidence, 3),
                "reason": reason[:240],
                "remove_text": remove_text,
                "matched_text": _matched_text_for_span(words, (start, end)) if remove_text else "",
                "start": round(start, 4),
                "end": round(end, 4),
            }
        )
    return validated, warnings


def _choose_intervals(
    edits: list[dict[str, Any]],
    actions: set[str],
    confidence_threshold: float,
    timeline_duration: float,
    maximum_ratio: float,
) -> list[tuple[float, float]]:
    budget = max(0.0, timeline_duration * maximum_ratio)
    selected: list[tuple[float, float]] = []
    # High confidence wins. Short exact word removals win ties over whole sentences.
    candidates = sorted(
        (
            edit
            for edit in edits
            if edit["action"] in actions and float(edit["confidence"]) >= confidence_threshold
        ),
        key=lambda item: (-float(item["confidence"]), float(item["end"]) - float(item["start"])),
    )
    for edit in candidates:
        candidate = selected + [(float(edit["start"]), float(edit["end"]))]
        if _interval_duration(candidate) <= budget + 1e-6:
            selected.append((float(edit["start"]), float(edit["end"])))
    return _merge_intervals(selected)


def _complement(intervals: list[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    kept: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in _merge_intervals(intervals):
        start = min(duration, max(cursor, start))
        end = min(duration, max(start, end))
        if start - cursor >= 0.02:
            kept.append((cursor, start))
        cursor = max(cursor, end)
    if duration - cursor >= 0.02:
        kept.append((cursor, duration))
    return kept


def _timeline_mapping(kept: list[tuple[float, float]]) -> list[dict[str, float]]:
    mapping: list[dict[str, float]] = []
    cursor = 0.0
    for old_start, old_end in kept:
        length = old_end - old_start
        mapping.append(
            {
                "old_start": round(old_start, 6),
                "old_end": round(old_end, 6),
                "new_start": round(cursor, 6),
                "new_end": round(cursor + length, 6),
            }
        )
        cursor += length
    return mapping


def remap_time(value: float, mapping: list[dict[str, float]]) -> float | None:
    moment = float(value)
    for item in mapping:
        if item["old_start"] - 1e-6 <= moment <= item["old_end"] + 1e-6:
            clamped = min(item["old_end"], max(item["old_start"], moment))
            return float(item["new_start"]) + clamped - float(item["old_start"])
    return None


def _build_track(
    base_clips: list[list[int]],
    mapping: list[dict[str, float]],
    fps: float,
) -> list[list[int]]:
    result: list[list[int]] = []
    for raw_clip in base_clips:
        tl_start, tl_end, media_in, _media_out = map(int, raw_clip)
        old_start = tl_start / fps
        old_end = tl_end / fps
        for item in mapping:
            overlap_start = max(old_start, float(item["old_start"]))
            overlap_end = min(old_end, float(item["old_end"]))
            if overlap_end - overlap_start < 0.5 / fps:
                continue
            new_start_s = float(item["new_start"]) + overlap_start - float(item["old_start"])
            new_end_s = new_start_s + overlap_end - overlap_start
            source_start = media_in + int(round((overlap_start - old_start) * fps))
            source_end = source_start + int(round((overlap_end - overlap_start) * fps))
            new_start = int(round(new_start_s * fps))
            new_end = max(new_start + 1, int(round(new_end_s * fps)))
            source_end = source_start + (new_end - new_start)
            result.append([new_start, new_end, source_start, source_end])
    return result


def build_variants(
    clips: dict[str, list[list[int]]],
    edits: list[dict[str, Any]],
    fps: float,
    timeline_duration: float,
) -> dict[str, dict[str, Any]]:
    definitions = {
        "safe": ({"cut_safe"}, SAFE_CONFIDENCE, SAFE_MAX_REMOVAL_RATIO),
        "tight": ({"cut_safe", "cut_tight"}, TIGHT_CONFIDENCE, TIGHT_MAX_REMOVAL_RATIO),
    }
    variants: dict[str, dict[str, Any]] = {}
    for name, (actions, confidence, maximum_ratio) in definitions.items():
        cuts = _choose_intervals(edits, actions, confidence, timeline_duration, maximum_ratio)
        kept = _complement(cuts, timeline_duration)
        mapping = _timeline_mapping(kept)
        variant_clips = {
            camera: _build_track(track, mapping, fps)
            for camera, track in clips.items()
        }
        frames = max((clip[1] for clip in variant_clips.get("cam1", [])), default=0)
        variants[name] = {
            "name": "01 - Hafez Safe Cut" if name == "safe" else "02 - Hafez Tight Cut",
            "clips": variant_clips,
            "mapping": mapping,
            "cut_intervals": cuts,
            "timeline_frames": frames,
            "timeline_duration": frames / fps if fps else 0.0,
            "removed_seconds": round(_interval_duration(cuts), 3),
        }
    return variants


def remap_segments(
    segments: list[dict[str, Any]],
    mapping: list[dict[str, float]],
    edits: list[dict[str, Any]],
    variant: str,
) -> list[dict[str, Any]]:
    cleaned_text: dict[int, list[str]] = {}
    cleaned_spans: dict[int, list[tuple[float, float]]] = {}
    eligible_actions = {"cut_safe"} if variant == "safe" else {"cut_safe", "cut_tight"}
    threshold = SAFE_CONFIDENCE if variant == "safe" else TIGHT_CONFIDENCE
    for edit in edits:
        if edit["action"] in eligible_actions and edit["confidence"] >= threshold and edit["remove_text"]:
            segment_id = int(edit["segment_id"])
            span = (float(edit["start"]), float(edit["end"]))
            overlaps_existing = any(
                min(span[1], old_end) - max(span[0], old_start)
                >= 0.5 * min(span[1] - span[0], old_end - old_start)
                for old_start, old_end in cleaned_spans.get(segment_id, [])
            )
            if overlaps_existing:
                continue
            cleaned_spans.setdefault(segment_id, []).append(span)
            cleaned_text.setdefault(segment_id, []).append(str(edit.get("matched_text") or edit["remove_text"]))

    result: list[dict[str, Any]] = []
    for segment in segments:
        overlaps: list[tuple[float, float]] = []
        start, end = float(segment["start"]), float(segment["end"])
        for item in mapping:
            overlap_start = max(start, float(item["old_start"]))
            overlap_end = min(end, float(item["old_end"]))
            if overlap_end > overlap_start:
                new_start = float(item["new_start"]) + overlap_start - float(item["old_start"])
                overlaps.append((new_start, new_start + overlap_end - overlap_start))
        if not overlaps:
            continue
        item = dict(segment)
        item["start"] = round(overlaps[0][0], 3)
        item["end"] = round(overlaps[-1][1], 3)
        text = str(item.get("text", ""))
        for phrase in cleaned_text.get(int(item["id"]), []):
            text = _remove_first_fuzzy_phrase(text, phrase)
        item["text"] = re.sub(r"\s+", " ", text).strip(" ،؛")
        if item["text"]:
            result.append(item)
    return result


def validate_markers(
    raw_markers: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {int(item["id"]): item for item in segments}
    result: list[dict[str, Any]] = []
    for raw in raw_markers:
        if not isinstance(raw, dict):
            continue
        try:
            segment_id = int(raw.get("segment_id"))
            confidence = float(raw.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        marker_type = str(raw.get("type", "CHECK")).upper().strip()
        segment = by_id.get(segment_id)
        if marker_type not in ALLOWED_MARKERS or segment is None or confidence < 0.70:
            continue
        try:
            duration = min(12.0, max(0.5, float(raw.get("duration", 3.0))))
        except (TypeError, ValueError):
            duration = 3.0
        item = {
            "segment_id": segment_id,
            "type": marker_type,
            "start": float(segment["start"]),
            "end": min(float(segment["end"]), float(segment["start"]) + duration),
            "comment": str(raw.get("comment", "")).strip()[:500],
            "confidence": round(min(1.0, confidence), 3),
        }
        for key in (
            "overlay_text", "headline_fa", "summary_fa", "kicker_en", "visual_kind",
            "compare_a", "compare_b", "template_hint", "transition", "sfx", "priority", "visual",
            "semantic_role", "element_id", "title_en", "headline_en", "semantic_subtitle_fa", "short_title_fa",
        ):
            value = str(raw.get(key, "")).strip()
            if value:
                item[key] = value[:300]
        nodes = raw.get("nodes")
        if isinstance(nodes, list):
            cleaned_nodes = [str(node).strip()[:90] for node in nodes if str(node).strip()]
            if 3 <= len(cleaned_nodes) <= 5:
                item["nodes"] = cleaned_nodes
        result.append(item)
    # Professional mode needs enough actionable beats, while same-type markers
    # are still de-duplicated when they land almost on top of each other.
    maximum = max(1, int(math.ceil(max(1.0, segments[-1]["end"] if segments else 1.0) / 600 * 64)))
    chosen: list[dict[str, Any]] = []
    for marker in sorted(result, key=lambda item: (-item["confidence"], item["start"])):
        if all(abs(marker["start"] - old["start"]) >= 2.0 or marker["type"] != old["type"] for old in chosen):
            chosen.append(marker)
            if len(chosen) >= maximum:
                break
    return sorted(chosen, key=lambda item: item["start"])


def bind_graphic_markers_to_source(markers, segments, words):
    """Bind quoted graphics to actual words, not a model's guessed segment ID."""
    tokens = [_clean_token(w.get("text", "")) for w in words]
    offsets, cursor = [], 0
    for token in tokens:
        offsets.append(cursor)
        cursor += len(token)
    stream = "".join(tokens)
    starts = {offset: i for i, offset in enumerate(offsets) if tokens[i]}
    ends = {offset+len(tokens[i]): i for i, offset in enumerate(offsets) if tokens[i]}
    result, warnings = [], []
    for marker in markers:
        quote = str(marker.get("headline_fa") or marker.get("overlay_text") or "")
        if marker["type"] not in {"TEXT", "GRAPHIC", "TITLE", "CHAPTER"} or not quote:
            result.append(marker)
            continue
        wanted = "".join(_clean_token(w) for w in quote.split())
        found = []
        index = stream.find(wanted) if wanted else -1
        while index >= 0:
            if index in starts and index+len(wanted) in ends:
                found.append((starts[index], ends[index+len(wanted)]))
            index = stream.find(wanted, index+1)
        referenced = next((s for s in segments if s["id"] == marker["segment_id"]), None)
        local = [(a, b) for a, b in found if referenced and float(referenced["start"])-.002
                 <= float(words[a]["start"]) < float(referenced["end"])]
        selected = local if len(local) == 1 else found
        if len(selected) != 1:
            warnings.append(f"Marker segment {marker['segment_id']} رد شد: نقل‌قول یکتا و هم‌زمان در متن منبع پیدا نشد.")
            continue
        a, b = selected[0]
        start = float(words[a]["start"])
        word_id = words[a].get("source_word_id")
        if word_id:
            owners = [s for s in segments if word_id in s.get("source_word_ids", [])]
        else:
            midpoint = (start+float(words[a]["end"]))/2
            owners = [s for s in segments if float(s["start"]) <= midpoint < float(s["end"])]
        if len(owners) != 1:
            warnings.append("Marker رد شد: مالک زمانی نقل‌قول مبهم است.")
            continue
        duration = float(marker["end"])-float(marker["start"])
        result.append({**marker, "segment_id": owners[0]["id"], "start": start,
                       "end": min(float(words[b]["end"]), start+duration),
                       "copy_time_binding": "unique-original-word-quote",
                       "requested_segment_id": marker["segment_id"]})
    return result, warnings


def remap_timed_items(items: list[dict[str, Any]], mapping: list[dict[str, float]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for original in items:
        old_start = float(original["start"])
        old_end = max(old_start, float(original.get("end", old_start)))
        overlaps: list[tuple[float, float]] = []
        for span in mapping:
            overlap_start = max(old_start, float(span["old_start"]))
            overlap_end = min(old_end, float(span["old_end"]))
            if overlap_end < overlap_start:
                continue
            new_start = float(span["new_start"]) + overlap_start - float(span["old_start"])
            overlaps.append((new_start, new_start + max(0.0, overlap_end - overlap_start)))
        if not overlaps:
            continue
        item = dict(original)
        item["start"] = round(overlaps[0][0], 3)
        item["end"] = round(max(overlaps[0][0], overlaps[-1][1]), 3)
        result.append(item)
    return result
