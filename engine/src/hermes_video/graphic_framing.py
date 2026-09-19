"""Give qualified native graphics room by coordinating the existing cameras.

Never changes media trims, source audio, copy decisions, or tracking thresholds.
Alternative angles are candidates, not safety approvals: the caller must rerun
all-frame placement on the final split tracks before producing XML/MOGRT plans.
"""
from copy import deepcopy
import math


def override_camera_interval(schedule, *, start, end, camera, fps, cue_id):
    """Frame-exact exclusive replacement; absorb short residual shot slivers."""
    if camera not in {"cam1", "cam2"} or not math.isfinite(fps) or fps <= 0:
        raise ValueError("Invalid camera/frame clock")
    rows = [(round(s["start"] * fps), round(s["end"] * fps), s) for s in schedule]
    if not rows or any(b <= a for a, b, _ in rows) or any(rows[i][0] != rows[i-1][1] for i in range(1, len(rows))):
        raise ValueError("Camera schedule must be contiguous and exclusive")
    first, last = rows[0][0], rows[-1][1]
    if not all(math.isfinite(v) for v in (start, end)) or not first <= round(start*fps) < round(end*fps) <= last:
        raise ValueError("Graphic interval is outside the schedule")
    a, b = max(first, math.floor(start*fps) - math.ceil(.65*fps)), min(last, math.ceil(end*fps) + math.ceil(.65*fps))
    minimum = math.ceil(3.5*fps)
    for x, y, _ in rows:
        if x < a < y and a-x < minimum:
            a = x
        if x < b < y and y-b < minimum:
            b = y
    pieces = []
    for x, y, s in rows:
        if x < min(y, a):
            pieces.append({**s, "start": x/fps, "end": min(y, a)/fps})
        if max(x, b) < y:
            pieces.append({**s, "start": max(x, b)/fps, "end": y/fps})
    pieces.append({"start": a/fps, "end": b/fps, "camera": camera,
                   "reason": "Room for source-grounded native graphic: " + str(cue_id),
                   "graphic_priority_ids": [str(cue_id)]})
    merged = []
    for s in sorted(pieces, key=lambda v: v["start"]):
        if merged and merged[-1]["camera"] == s["camera"]:
            merged[-1]["end"] = s["end"]
            ids = merged[-1].get("graphic_priority_ids", []) + s.get("graphic_priority_ids", [])
            if ids:
                merged[-1]["graphic_priority_ids"] = sorted(set(ids))
        else:
            merged.append(dict(s))
    assert round(merged[0]["start"]*fps) == first and round(merged[-1]["end"]*fps) == last
    assert all(round(merged[i]["start"]*fps) == round(merged[i-1]["end"]*fps) for i in range(1, len(merged)))
    return merged


def coordinate_graphic_framing(raw_cues, placed_cues, schedule, events, *, paths, clips, fps, width, height):
    # Local import avoids a module cycle and keeps the pure interval helper testable.
    from professional_edit import (apply_face_safe_layout, guard_automatic_graphic_copy,
                                   _native_glass_editorial_copy, NATIVE_GLASS_PROFILE)
    adjusted, remaining = deepcopy(schedule), deepcopy(events)
    audit = {"policy": "qualified-graphic-priority-camera-v1", "changes": [], "deferred": [],
             "audio_unchanged": True, "source_trims_unchanged": True,
             "final_visible_frames_require_recheck": True}
    current = {c["id"]: c for c in placed_cues}
    protected = [(c["start"], c["end"]) for c in placed_cues if not c.get("review_blocked")]
    for cue in raw_cues:
        if cue.get("review_blocked") or not current.get(cue["id"], {}).get("review_blocked"):
            continue
        contract = cue.get("native_runtime_contract", {})
        if (cue.get("element_id") != "hermes-glass-insight"
                or contract.get("typography", {}).get("profile") != NATIVE_GLASS_PROFILE):
            continue
        _, copy = _native_glass_editorial_copy(cue, cue.get("controls", {}))
        if not copy or copy.get("display_kind") not in {"term-label", "topic-label"}:
            continue
        alternatives = []
        for camera in ("cam1", "cam2"):
            proposed, _ = apply_face_safe_layout([deepcopy(cue)], video_path=paths[camera], clips=clips[camera],
                fps=fps, width=width, height=height, motion_events=[])
            proposed = guard_automatic_graphic_copy(proposed)[0]
            if not proposed.get("review_blocked"):
                alternatives.append((camera, proposed))
        if not alternatives:
            audit["deferred"].append({"id": cue["id"], "reason": "No angle passed full-frame tracking and native typography."})
            continue
        existing = {s["camera"] for s in adjusted if max(s["start"], cue["start"]) < min(s["end"], cue["end"])}
        camera, proof = min(alternatives, key=lambda p: (0 if existing == {p[0]} else 1, -p[1]["layout"]["scale"]))
        candidate = override_camera_interval(adjusted, start=cue["start"], end=cue["end"], camera=camera, fps=fps, cue_id=cue["id"])
        # Do not change an already-safe graphic's camera as a side effect of
        # absorbing a short neighbouring shot. Final placement still rechecks all.
        def angle_at(shots, tick):
            return next((s["camera"] for s in shots if round(s["start"]*fps) <= tick < round(s["end"]*fps)), None)
        if any(angle_at(adjusted, t) != angle_at(candidate, t)
               for a, b in protected for t in range(round(a*fps), round(b*fps))):
            audit["deferred"].append({"id": cue["id"], "reason": "Would change an already-qualified neighbouring graphic."})
            continue
        kept, removed = [], []
        for event in remaining:
            if max(cue["start"]*fps, event["start"]*fps-7) < min(cue["end"]*fps, event["end"]*fps+7):
                removed.append(event)
            else:
                kept.append(event)
        adjusted, remaining = candidate, kept
        protected.append((cue["start"], cue["end"]))
        audit["changes"].append({"id": cue["id"], "camera": camera, "start": cue["start"], "end": cue["end"],
                                 "removed_competing_punches": removed, "candidate_tracking_frames": proof["layout"]["tracking_sample_count"],
                                 "candidate_scale": proof["layout"]["scale"]})
    return adjusted, remaining, audit
