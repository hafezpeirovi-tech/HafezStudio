"""Source-preserving caption grouping; never changes words or edits audio.

Decimal fragments remain spaced as transcribed, but are kept on one screen and
line. Joining them visually is not verification of the number that was spoken.
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any


def caption_atoms(text: str) -> list[str]:
    """Group adjacent digit/separator fragments without changing any character."""
    words = str(text).split()
    atoms: list[str] = []
    index = 0
    while index < len(words):
        atom = words[index]
        index += 1
        if re.fullmatch(r"[+−-]?\d+", atom):
            if index < len(words) and re.fullmatch(r"[.٫]\d+[,،؛;:!?؟]?", words[index]):
                atom += " " + words[index]
                index += 1
            elif (index + 1 < len(words) and words[index] in (".", "٫")
                  and re.fullmatch(r"\d+[,،؛;:!?؟]?", words[index + 1])):
                atom += " " + words[index] + " " + words[index + 1]
                index += 2
        atoms.append(atom)
    return atoms


def wrap_caption(text: str, line_chars: int = 42) -> str:
    atoms = caption_atoms(text)
    flat = " ".join(atoms)
    if len(flat) <= line_chars or len(atoms) < 2:
        return flat
    choices = []
    for index in range(1, len(atoms)):
        left, right = " ".join(atoms[:index]), " ".join(atoms[index:])
        overflow = max(0, len(left) - line_chars) + max(0, len(right) - line_chars)
        choices.append((overflow, abs(len(left) - len(right)), index))
    index = min(choices)[2]
    return " ".join(atoms[:index]) + "\n" + " ".join(atoms[index:])


def regroup_short_cues(cues: list[dict[str, Any]], *, min_duration: float = .65,
                       max_chars: int = 78, max_duration: float = 6.5,
                       max_gap: float = .35) -> list[dict[str, Any]]:
    """Merge adjacent orphan captions only; retain lexical order and provenance.

    No new hold is invented and a hard caption boundary is never crossed.
    Unmergeable short/long-single cues remain explicit QA findings.
    """
    result = copy.deepcopy(cues)
    for cue in result:
        if not (math.isfinite(float(cue["start"])) and math.isfinite(float(cue["end"]))
                and float(cue["start"]) >= 0 and float(cue["end"]) > float(cue["start"])
                and isinstance(cue.get("text"), str) and cue["text"].strip()):
            raise ValueError("Caption times must be finite positive intervals")
    if any(float(a["start"]) > float(b["start"]) for a, b in zip(result, result[1:])):
        raise ValueError("Caption sequence is not timeline ordered")
    if any(float(a["end"]) > float(b["start"]) for a, b in zip(result, result[1:])):
        raise ValueError("Caption intervals overlap; timing review is required")

    def eligible(left, right):
        gap = float(right["start"]) - float(left["end"])
        return (not right.get("caption_boundary_before") and not left.get("caption_boundary_after")
                and -.001 <= gap <= max_gap
                and float(right["end"]) - float(left["start"]) <= max_duration
                and len(" ".join((str(left["text"]) + " " + str(right["text"])).split())) <= max_chars)

    index = 0
    while index < len(result):
        cue = result[index]
        duration = float(cue["end"]) - float(cue["start"])
        orphan = duration < min_duration or (len(str(cue["text"]).split()) == 1 and duration > 2.5)
        if not orphan:
            index += 1
            continue
        left_index = None
        if index + 1 < len(result) and eligible(cue, result[index + 1]):
            left_index = index
        elif index > 0 and eligible(result[index - 1], cue):
            left_index = index - 1
        if left_index is None:
            cue.setdefault("layout_review", []).append("orphan-caption-needs-timing-review")
            index += 1
            continue
        left, right = result[left_index:left_index + 2]
        merged = copy.deepcopy(left)
        merged["end"] = right["end"]
        merged["text"] = wrap_caption(str(left["text"]) + " " + str(right["text"]))
        merged["layout_source_cues"] = (left.get("layout_source_cues", [copy.deepcopy(left)])
                                        + right.get("layout_source_cues", [copy.deepcopy(right)]))
        merged["caption_boundary_after"] = bool(right.get("caption_boundary_after"))
        if "words" in left or "words" in right:
            merged["words"] = copy.deepcopy(left.get("words", []) + right.get("words", []))
        merged.pop("layout_review", None)
        result[left_index:left_index + 2] = [merged]
        index = max(0, left_index)
    return result


def build_source_word_cues(words: list[dict[str, Any]], *, max_chars: int = 74,
                          max_duration: float = 4.5) -> list[dict[str, Any]]:
    """Rewrap already-selected words only; deleted/omitted words cannot reappear."""
    rows = copy.deepcopy(words)
    for row in rows:
        if not (math.isfinite(float(row["start"])) and math.isfinite(float(row["end"]))
                and float(row["start"]) >= 0 and float(row["end"]) > float(row["start"])
                and isinstance(row.get("text"), str) and row["text"].strip()):
            raise ValueError("Invalid source word")
    if any(a["start"] > b["start"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Source words are not timeline ordered")

    units: list[list[dict[str, Any]]] = []
    def adjacent(left, right):
        source_gap = float(right.get("source_start", right["start"])) - float(left.get("source_end", left["end"]))
        return (not left.get("caption_boundary_after") and not right.get("caption_boundary_before")
                and -.001 <= float(right["start"]) - float(left["end"]) <= .65
                and -.001 <= source_gap <= 1.0)
    index = 0
    while index < len(rows):
        count = 1
        # Look ahead to the complete token; an intermediate "1 ." is not
        # itself a decimal and must not be committed as a separate unit.
        for size in (3, 2):
            candidate = rows[index:index + size]
            if len(candidate) != size:
                continue
            text = " ".join(str(w["text"]).strip() for w in candidate)
            if (len(caption_atoms(text)) == 1 and len(text.split()) > 1
                    and all(adjacent(a, b) for a, b in zip(candidate, candidate[1:]))):
                count = size
                break
        units.append(rows[index:index + count])
        index += count
    groups: list[list[dict[str, Any]]] = []
    group: list[dict[str, Any]] = []
    source_boundary_starts: set[int] = set()
    for unit in units:
        first, last = unit[0], unit[-1]
        source_gap = (float(first.get("source_start", first["start"]))
                      - float(group[-1].get("source_end", group[-1]["end"]))) if group else 0
        should_break = group and (first.get("caption_boundary_before") or group[-1].get("caption_boundary_after")
            or float(first["start"]) - float(group[-1]["end"]) > .65
            or abs(source_gap) > .8
            or float(last["end"]) - float(group[0]["start"]) > max_duration
            or len(" ".join(str(w["text"]).strip() for w in group + unit)) > max_chars)
        if should_break:
            if abs(source_gap) > .8:
                source_boundary_starts.add(id(first))
            groups.append(group)
            group = []
        group.extend(unit)
    if group:
        groups.append(group)
    cues = []
    for index, group in enumerate(groups):
        start, end = float(group[0]["start"]), max(float(w["end"]) for w in group)
        if index + 1 < len(groups):
            end = min(end, float(groups[index + 1][0]["start"]))
        if end <= start:
            raise ValueError("Overlapping ASR words cannot form positive caption intervals")
        cues.append({"start": start, "end": end,
                     "text": wrap_caption(" ".join(str(w["text"]).strip() for w in group)),
                     "words": group, "caption_boundary_before": bool(group[0].get("caption_boundary_before")
                                                                               or id(group[0]) in source_boundary_starts),
                     "caption_boundary_after": bool(group[-1].get("caption_boundary_after"))})
    return regroup_short_cues(cues, max_chars=max_chars)
