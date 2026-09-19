"""Exact authored CTA timing from content-bound words and final A1 keeps.

Pure and fail-closed: no ASR correction, word restoration, trim change, native
template approval or audio-review certification. Segment starts are not onsets.
"""
from collections import Counter
from fractions import Fraction
import math
import re


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("invalid-numeric-evidence")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("invalid-numeric-evidence")
    return value if isinstance(value, Fraction) else Fraction(str(value))


def _tokens(value):
    text = str(value).replace("ي", "ی").replace("ك", "ک")
    return re.findall(r"[^\W_]+", text, re.UNICODE)


def exact_trigger_timing(segments, phrase, context, *, fps, timeline_duration, duration=4.2):
    """Choose the first fully retained literal occurrence in final-timeline order.

    A later occurrence can replace an incomplete first occurrence. Every chosen
    word must be owned by that segment, unique, content-bound, confident, uncut,
    and contiguous in BOTH source and final clocks. No missing context fallback.
    Context media identity is verified by finalize, never granted by this helper.
    """
    report = {"policy": "exact-spoken-trigger-final-a1-v1", "status": "review-required",
              "selected": None, "rejections": [], "audio_verified": False,
              "cuts_changed": False, "native_placement_approved": False}
    try:
        if not isinstance(context, dict):
            raise ValueError("missing-content-bound-final-word-context")
        clock = context.get("fps")
        if (not isinstance(clock, tuple) or len(clock) != 2
                or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in clock)):
            raise ValueError("invalid-exact-frame-clock")
        rate = Fraction(*clock)
        if abs(float(rate)-float(_number(fps))) > 1e-7:
            raise ValueError("final-frame-clock-mismatch")
        total, length = _number(timeline_duration), _number(duration)
        if total <= 0 or length <= 0:
            raise ValueError("invalid-duration")
        digest, evidence = context.get("media_sha256"), context.get("evidence_id")
        if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not isinstance(evidence, str) or not evidence):
            raise ValueError("missing-content-identity")
        words, keeps = context.get("words"), context.get("keeps")
        if not isinstance(words, list) or not isinstance(keeps, list) or not keeps:
            raise ValueError("missing-words-or-final-keeps")
        ids = [word.get("source_word_id") for word in words]
        if any(not isinstance(wid, str) or not wid for wid in ids) or len(set(ids)) != len(ids):
            raise ValueError("ambiguous-word-identity")
        index = dict(zip(ids, words))
        positions = {wid: position for position, wid in enumerate(ids)}
        keep_ids, checked = set(), []
        previous_timeline, previous_source = 0, 0
        for keep in keeps:
            a, b, c, d = [keep[k] for k in ("start_frame", "end_frame", "source_in_frame", "source_out_frame")]
            kid = keep.get("id")
            if (any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (a, b, c, d))
                    or b <= a or d <= c or b-a != d-c or a < previous_timeline or c < previous_source
                    or keep.get("media_sha256") != digest or not isinstance(kid, str) or not kid or kid in keep_ids):
                raise ValueError("invalid-ambiguous-or-retimed-final-keeps")
            previous_timeline, previous_source = b, d
            keep_ids.add(kid)
            checked.append((a, b, c, d))
        targets = _tokens(phrase)
        if not targets:
            raise ValueError("empty-exact-trigger")
        owners = Counter(wid for segment in segments for wid in segment.get("source_word_ids", []))
        selected = []
        for segment in segments:
            segment_tokens = _tokens(segment.get("text", ""))
            if not any(segment_tokens[i:i+len(targets)] == targets for i in range(len(segment_tokens))):
                continue
            try:
                segment_ids = segment.get("source_word_ids")
                if (not isinstance(segment_ids, list) or not segment_ids
                        or segment.get("source_evidence_id") != evidence
                        or any(wid not in index for wid in segment_ids)):
                    raise ValueError("missing-segment-word-ownership")
                ordered = [index[wid] for wid in segment_ids]
                if any(positions[segment_ids[i]] >= positions[segment_ids[i+1]] for i in range(len(segment_ids)-1)):
                    raise ValueError("reordered-segment-word-ownership")
                pair_count = 0
                for i in range(len(ordered)):
                    pair = ordered[i:i+len(targets)]
                    if [_tokens(w.get("text", "")) for w in pair] != [[token] for token in targets]:
                        continue
                    pair_count += 1
                    try:
                        if any(positions[pair[j]["source_word_id"]] != positions[pair[j-1]["source_word_id"]]+1
                               for j in range(1, len(pair))):
                            raise ValueError("trigger-skips-intervening-source-word")
                        spans = []
                        for word in pair:
                            wid = word["source_word_id"]
                            if (owners[wid] != 1 or word.get("source_evidence_id") != evidence
                                    or word.get("media_sha256") != digest
                                    or word.get("timing_origin") != "asr-word-timestamps"):
                                raise ValueError("unbound-or-ambiguous-trigger-word")
                            if (word.get("word_boundary_review_required") is not False
                                    or _number(word.get("source_coverage")) != 1
                                    or not Fraction(9, 10) <= _number(word.get("confidence")) <= 1):
                                raise ValueError("partial-or-uncertain-trigger-word")
                            sa, sb = _number(word.get("acoustic_start")), _number(word.get("acoustic_end"))
                            if (sa < 0 or not Fraction(1, 50) <= sb-sa <= Fraction(5, 2)
                                    or abs(_number(word.get("source_start"))-sa) > Fraction(1, 10000)
                                    or abs(_number(word.get("source_end"))-sb) > Fraction(1, 10000)):
                                raise ValueError("invalid-or-clipped-acoustic-span")
                            pieces = []
                            for a, b, c, d in checked:
                                left, right = max(sa, Fraction(c)/rate), min(sb, Fraction(d)/rate)
                                if left < right:
                                    offset = Fraction(a-c)/rate
                                    pieces.append((left, right, left+offset, right+offset))
                            if (not pieces or sum(p[1]-p[0] for p in pieces) != sb-sa
                                    or any(pieces[j-1][1] != pieces[j][0] or pieces[j-1][3] != pieces[j][2]
                                           for j in range(1, len(pieces)))):
                                raise ValueError("trigger-clipped-by-final-edit")
                            spans.append((sa, sb, pieces[0][2], pieces[-1][3]))
                        if any(not 0 <= spans[j][0]-spans[j-1][1] <= Fraction(1, 2)
                               or spans[j][0]-spans[j-1][1] != spans[j][2]-spans[j-1][3]
                               for j in range(1, len(spans))):
                            raise ValueError("trigger-crosses-cut-gap-or-pause")
                        first = math.ceil(spans[0][2]*rate)
                        count = round(length*rate)
                        if first < 0 or count <= 0 or first+count > round(total*rate):
                            raise ValueError("insufficient-room-for-authored-animation")
                        # Segment bounds have millisecond rounding; this is ownership QA, not onset interpolation.
                        if (spans[0][2] < _number(segment["start"])-Fraction(1, 1000)
                                or spans[-1][3] > _number(segment["end"])+Fraction(1, 1000)):
                            raise ValueError("trigger-outside-retained-segment")
                        selected.append({"segment_id": segment["id"], "start_frame": first,
                                         "end_frame": first+count, "start": float(Fraction(first)/rate),
                                         "end": float(Fraction(first+count)/rate),
                                         "spoken_start": float(spans[0][2]), "spoken_end": float(spans[-1][3]),
                                         "source_word_ids": [w["source_word_id"] for w in pair],
                                         "source_acoustic_span": [float(spans[0][0]), float(spans[-1][1])],
                                         "media_sha256": digest, "source_evidence_id": evidence,
                                         "fps": list(clock), "matched_phrase": phrase})
                    except (ValueError, TypeError, KeyError) as error:
                        report["rejections"].append({"segment_id": segment.get("id"),
                                                     "word_ids": [w.get("source_word_id") for w in pair],
                                                     "reason": str(error)})
                if not pair_count:
                    raise ValueError("exact-trigger-not-owned-by-literal-source-words")
            except (ValueError, TypeError, KeyError) as error:
                report["rejections"].append({"segment_id": segment.get("id"), "reason": str(error)})
        if selected:
            report["selected"] = min(selected, key=lambda row: row["start_frame"])
            report["status"] = "exact-final-word-timed-not-audio-verified"
        elif not report["rejections"]:
            report["rejections"].append({"reason": "no-retained-exact-trigger"})
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        report["rejections"].append({"reason": str(error)})
    return report
