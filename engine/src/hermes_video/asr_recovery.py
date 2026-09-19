"""Bounded re-recognition of implausible ASR alignment, using original audio.

This is new machine evidence, NOT audio-reviewed copy or authority to restore
removed footage. No lexical corrections, internet calls, or cut edits occur.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Callable


def _words(segments):
    return [dict(word) for segment in segments for word in segment.get("words", [])
            if str(word.get("word", "")).strip()]


def recovery_windows(segments, speech_intervals, *, duration, maximum=12):
    """Return non-overlapping cores; inference may add context outside cores."""
    words = _words(segments)
    anomalies = []
    for word in words:
        a, b = float(word["start"]), float(word["end"])
        if b - a > 2.5:
            anomalies.append((a, b, "implausibly-long-word"))
    for left, right in zip(words, words[1:]):
        a, b = float(left["end"]), float(right["start"])
        if b - a < 2:
            continue
        voiced = sum(max(0, min(b, y) - max(a, x)) for x, y in speech_intervals)
        if voiced >= 1.6:
            anomalies.append((a, b, "untranscribed-nonsilent-gap"))
    merged = []
    for a, b, reason in sorted(anomalies):
        a, b = max(0, a - 1), min(duration, b + 1)
        if b <= a:
            continue
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(b, merged[-1][1])
            merged[-1][2].add(reason)
        else:
            merged.append([a, b, {reason}])
    result = []
    for a, b, reasons in merged:
        for word in words:
            s, e = float(word["start"]), float(word["end"])
            if s < a < e:
                a = s
            if s < b < e:
                b = e
        # Equal cores avoid an arbitrarily tiny final recognition window.
        pieces = max(1, math.ceil((b-a) / 40))
        for index in range(pieces):
            result.append({"start": a + (b-a)*index/pieces,
                           "end": a + (b-a)*(index+1)/pieces,
                           "reasons": sorted(reasons)})
    return result[:maximum], result[maximum:]


def recover_alignment(segments, speech_intervals, *, duration: float,
                      transcribe_window: Callable[[float, float], list[dict[str, Any]]],
                      progress=None, maximum=12):
    """Replace only anomaly cores with plausible fresh local recognition.

    Callbacks return source-clock segments/words. Context is not imported twice.
    Original rows and each replacement are retained in the caller's audit.
    Failed/empty/implausible re-recognition leaves original evidence unchanged.
    """
    cores, deferred = recovery_windows(segments, speech_intervals, duration=duration, maximum=maximum)
    original = _words(segments)
    replacements = []
    decisions = []
    for index, core in enumerate(cores):
        a, b = core["start"], core["end"]
        # Snap a core outward around an existing plausible boundary word, so a
        # retained word cannot overlap a replacement. Long broken words are
        # removed separately only when all their replacement cores succeed.
        if progress:
            progress(index+1, len(cores), a, b)
        try:
            candidate_segments = transcribe_window(max(0, a-2), min(duration, b+2))
            candidate = [w for w in _words(candidate_segments)
                         if a <= (float(w["start"])+float(w["end"]))/2 < b]
            valid = bool(candidate)
            for wi, word in enumerate(candidate):
                s, e = float(word["start"]), float(word["end"])
                confidence = word.get("probability")
                valid &= (math.isfinite(s) and math.isfinite(e) and 0 <= s < e <= duration
                          and e-s <= 2.5 and isinstance(confidence, (int, float))
                          and math.isfinite(confidence) and 0 <= confidence <= 1)
                if wi and s < float(candidate[wi-1]["end"]) - .001:
                    valid = False
            mean_confidence = sum(float(w.get("probability") or 0) for w in candidate)/max(1, len(candidate))
            valid &= mean_confidence >= .45
            decision = {**core, "status": "accepted-machine-retranscription" if valid else "rejected-implausible-retranscription",
                        "mean_confidence": round(mean_confidence, 4), "candidate_word_count": len(candidate)}
            if valid:
                replacements.append((a, b, candidate))
        except Exception as error:
            decision = {**core, "status": "rejected-recognition-error", "error_type": type(error).__name__}
        decisions.append(decision)

    # Partial repair of one very long source token must not erase its other
    # half. Refuse an entire connected group unless every core succeeded.
    accepted = []
    for a, b, candidate in replacements:
        overlapping = [w for w in original if float(w["start"]) < b and float(w["end"]) > a]
        related = [c for c in cores if any(float(w["start"]) < c["end"] and float(w["end"]) > c["start"]
                                         for w in overlapping)]
        if all(any(x == c["start"] and y == c["end"] for x, y, _ in replacements) for c in related):
            accepted.append((a, b, candidate))
        else:
            next(d for d in decisions if d["start"] == a)["status"] = "rejected-incomplete-connected-repair"
    if not accepted:
        return copy.deepcopy(segments), {"decisions": decisions, "deferred": deferred, "publication_ready": False}
    # Reliable original words are anchors, not collateral replacements. A
    # bounded decode can omit the final intact take in its context; preserve
    # those original words and only fill gaps/replace implausibly long tokens.
    def preserved(rows):
        return [w for w in original if not (float(w["end"])-float(w["start"]) > 2.5
            and any(float(w["start"]) < b and float(w["end"]) > a for a, b, _ in rows))]

    kept = preserved(accepted)
    accepted = [(a, b, [w for w in rows if not any(
        min(float(w["end"]), float(anchor["end"]))-max(float(w["start"]), float(anchor["start"])) > .001
        for anchor in kept)]) for a, b, rows in accepted]
    for a, _, rows in accepted:
        if not rows:
            next(d for d in decisions if d["start"] == a)["status"] = "rejected-no-new-word-evidence"
    accepted = [row for row in accepted if row[2]]
    # A failed boundary must not discard unrelated successful repairs. Refuse
    # only connected candidate cores that introduce an overlapping word.
    while accepted:
        kept = preserved(accepted)
        tagged = [(w, None) for w in kept] + [(w, i) for i, (_, _, rows) in enumerate(accepted) for w in rows]
        tagged.sort(key=lambda pair: float(pair[0]["start"]))
        bad = set()
        for (left, li), (right, ri) in zip(tagged, tagged[1:]):
            if float(right["start"]) < float(left["end"]) - .001:
                bad.update(i for i in (li, ri) if i is not None)
        if not bad:
            break
        for i in bad:
            a, _, _ = accepted[i]
            next(d for d in decisions if d["start"] == a)["status"] = "rejected-overlapping-repair"
        accepted = [row for i, row in enumerate(accepted) if i not in bad]
    kept = preserved(accepted)
    result_words = sorted(kept + [w for _, _, rows in accepted for w in rows], key=lambda w: float(w["start"]))
    if any(float(r["start"]) < float(l["end"]) - .001 for l, r in zip(result_words, result_words[1:])):
        for decision in decisions:
            if decision["status"] == "accepted-machine-retranscription":
                decision["status"] = "rejected-overlapping-repair"
        return copy.deepcopy(segments), {"decisions": decisions, "deferred": deferred, "publication_ready": False}
    # One source word per evidence segment preserves order and exact timestamps;
    # downstream review grouping is deliberately independent of ASR partitions.
    result = [{"text": w["word"], "start": w["start"], "end": w["end"], "words": [w]} for w in result_words]
    return result, {"decisions": decisions, "deferred": deferred,
                    "original_word_count": len(original), "result_word_count": len(result_words),
                    "original_plausible_words_preserved": True,
                    "publication_ready": False, "authority": "machine-asr-only"}
