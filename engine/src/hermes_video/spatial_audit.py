"""Opt-in, pure spatial evidence gate. No media reads or timeline mutations.

The caller supplies resolved visible source spans and independently measured
face/body observations. A face-derived rectangle is never body evidence.
Transforms must already be calibrated to normalized sequence coordinates.
"""
from __future__ import annotations

import math
import re
import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

PROFILE = "hafez-strict-spatial-v1"
BODY_METHODS = frozenset({"human-segmentation", "person-mask-and-pose", "manual-reviewed-silhouette"})
SAFE_AREA = (0.05, 0.05, 0.90, 0.90)
CLEARANCE = 0.018
MAX_OVERLAP = 0.001


def render_context_sha256(cue: Mapping[str, Any], clips: Sequence[Mapping[str, Any]]) -> str:
    """Bind a measurement to the exact cue and visible-source contracts.

    Includes placement, scale, all supplied effect/text controls, interval,
    source schedule and transforms. Metadata changes conservatively invalidate
    the measurement too. A digest is a binding, not proof a render occurred.
    """
    payload = json.dumps({"cue": cue, "clips": clips}, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Expected a nonnegative integer frame")
    return value


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite number")
    return float(value)


def _box(value: Any, *, source: bool = False) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("Expected x/y/width/height")
    x, y, w, h = map(_finite, value)
    if w <= 0 or h <= 0:
        raise ValueError("Empty bounding box is not evidence of no person")
    if source and (x < 0 or y < 0 or x + w > 1.0000001 or y + h > 1.0000001):
        raise ValueError("Source observation lies outside normalized image")
    return x, y, w, h


def _union(boxes):
    if not boxes:
        return None
    x, y = min(b[0] for b in boxes), min(b[1] for b in boxes)
    right, bottom = max(b[0] + b[2] for b in boxes), max(b[1] + b[3] for b in boxes)
    return [x, y, right - x, bottom - y]


def _clamp(box):
    x, y, w, h = box
    left, top, right, bottom = max(0, x), max(0, y), min(1, x + w), min(1, y + h)
    if right <= left or bottom <= top:
        raise ValueError("Transformed person leaves the sequence; require visibility review")
    return left, top, right - left, bottom - top


def exact_frame_map(start_frame: int, end_frame: int, clips: Sequence[Mapping[str, Any]]) -> tuple[list[dict], list[str]]:
    """Map every [start,end) frame through caller-resolved visible spans.

    Explicit visible=False means fully hidden/disabled. Multiple visible camera
    spans are all audited (e.g. a declared dissolve); none are silently dropped.
    Unknown visibility, speed changes, duplicate clip IDs and gaps fail closed.
    """
    issues: list[str] = []
    mappings: list[dict] = []
    try:
        start, end = _integer(start_frame), _integer(end_frame)
        if end <= start:
            raise ValueError("Empty cue interval")
    except ValueError as error:
        return [], ["INVALID_CUE_INTERVAL: " + str(error)]
    # IDs are global lookup keys. Validate before ANY visibility/interval
    # filtering so a hidden or out-of-cue record cannot shadow a visible clip.
    seen = set()
    for clip in clips:
        if not isinstance(clip, Mapping):
            return [], ["INVALID_CLIP_IDENTITY: Invalid clip record"]
        clip_id = clip.get("id")
        if not isinstance(clip_id, str) or not clip_id.strip() or clip_id in seen:
            return [], ["INVALID_CLIP_IDENTITY: Missing, non-string or duplicate global clip ID"]
        seen.add(clip_id)
    valid = []
    for clip in clips:
        try:
            if not isinstance(clip, Mapping):
                raise ValueError("Invalid clip record")
            begin, finish = _integer(clip["start_frame"]), _integer(clip["end_frame"])
            if finish <= begin:
                raise ValueError("Empty clip interval")
            if finish <= start or begin >= end:
                continue
            if clip.get("visible") is False:
                continue
            if clip.get("visible") is not True:
                raise ValueError("Visibility not resolved")
            if not clip.get("camera_id") or not clip.get("media_id"):
                raise ValueError("Missing camera/media identity")
            media_in, media_out = _integer(clip["source_in"]), _integer(clip["source_out"])
            if (media_out - media_in != finish - begin or clip.get("speed", 1) != 1
                    or clip.get("reverse") or clip.get("time_remap")):
                raise ValueError("Retimed source mapping is unsupported")
            valid.append(clip)
        except (KeyError, TypeError, ValueError) as error:
            issues.append("INVALID_VISIBLE_SPAN: " + str(error))
    for frame in range(start, end):
        active = [clip for clip in valid if clip["start_frame"] <= frame < clip["end_frame"]]
        if not active:
            issues.append("UNMAPPED_TIMELINE_FRAME: " + str(frame))
        for clip in active:
            mappings.append({"timeline_frame": frame, "source_frame": clip["source_in"] + frame - clip["start_frame"],
                             "clip_id": clip["id"], "camera_id": str(clip["camera_id"]), "media_id": str(clip["media_id"])})
    return mappings, issues


def _curve(curve: Mapping[str, Any], frame: int, dimensions: int):
    if not isinstance(curve, Mapping):
        raise ValueError("Missing curve contract")
    def value(raw):
        if dimensions == 1:
            return [_finite(raw)]
        if not isinstance(raw, (list, tuple)) or len(raw) != dimensions:
            raise ValueError("Invalid vector curve value")
        return list(map(_finite, raw))
    mode = curve.get("interpolation")
    if mode == "constant":
        if set(curve) - {"interpolation", "value"}:
            raise ValueError("Unknown constant curve fields")
        return value(curve["value"])
    if mode != "linear":
        raise ValueError("Unknown/unsupported transform easing")
    keys = curve.get("keyframes", [])
    if set(curve) - {"interpolation", "keyframes"} or any(set(key) - {"frame", "value"} for key in keys):
        raise ValueError("Unsupported easing/tangent metadata")
    if len(keys) < 2:
        raise ValueError("Linear transform requires bracketing keys")
    frames = [_integer(key["frame"]) for key in keys]
    if frames != sorted(set(frames)) or frame < frames[0] or frame > frames[-1]:
        raise ValueError("Invalid or unbracketed transform keys")
    values = [value(key["value"]) for key in keys]
    for index, keyframe in enumerate(frames):
        if frame == keyframe:
            return values[index]
        if frame < keyframe:
            ratio = (frame - frames[index - 1]) / (keyframe - frames[index - 1])
            return [a + ratio * (b - a) for a, b in zip(values[index - 1], values[index])]
    raise ValueError("Transform key evaluation failed")


def transform_box(box, transform: Mapping[str, Any], timeline_frame: int):
    """Apply calibrated uniform scale about image center plus sequence offset.

    Linear is a supported audit of an existing transform, not a recommendation
    to author linear motion. FCPCurve/Bezier are rejected until implemented and
    native-calibrated; verified per-frame values can represent any known ease.
    """
    if not isinstance(transform, Mapping):
        raise ValueError("Missing transform contract")
    if set(transform) - {"verified", "kind", "coordinate_space", "rotation", "anchor", "mode", "frames", "scale", "center", "evidence_id"}:
        raise ValueError("Unknown transform properties")
    if (transform.get("verified") is not True or transform.get("kind") != "normalized-scale-center-v1"
            or transform.get("coordinate_space") != "sequence-normalized"):
        raise ValueError("Transform has not been calibrated to sequence coordinates")
    if not isinstance(transform.get("evidence_id"), str) or not transform["evidence_id"].strip():
        raise ValueError("Native transform calibration evidence is missing")
    if transform.get("rotation", 0) != 0 or transform.get("anchor", [0.5, 0.5]) != [0.5, 0.5]:
        raise ValueError("Rotation/noncentral anchor is unsupported")
    if transform.get("mode") == "per-frame":
        if "scale" in transform or "center" in transform:
            raise ValueError("Per-frame transform conflicts with curve fields")
        samples = transform.get("frames", {})
        if not isinstance(samples, Mapping):
            raise ValueError("Invalid measured transform frame table")
        canonical_samples = {}
        for key, entry in samples.items():
            if isinstance(key, str) and re.fullmatch(r"0|[1-9][0-9]*", key):
                key = int(key)
            key = _integer(key)
            if key in canonical_samples:
                raise ValueError("Duplicate canonical transform frame")
            if not isinstance(entry, Mapping) or set(entry) != {"scale", "center"}:
                raise ValueError("Per-frame sample must contain exactly scale and center")
            canonical_samples[key] = entry
        sample = canonical_samples.get(timeline_frame)
        if not isinstance(sample, Mapping):
            raise ValueError("Missing measured transform frame")
        scale = _finite(sample["scale"])
        center = _curve({"interpolation": "constant", "value": sample["center"]}, timeline_frame, 2)
    elif transform.get("mode") == "curves":
        if "frames" in transform:
            raise ValueError("Curve transform conflicts with per-frame fields")
        scale = _curve(transform["scale"], timeline_frame, 1)[0]
        center = _curve(transform["center"], timeline_frame, 2)
    else:
        raise ValueError("Unknown transform representation")
    if scale <= 0:
        raise ValueError("Nonpositive scale")
    x, y, w, h = _box(box, source=True)
    return _clamp((0.5 + scale * (x - 0.5) + center[0],
                   0.5 + scale * (y - 0.5) + center[1], w * scale, h * scale))


def audit_spatial_cue(cue: Mapping[str, Any], clips: Sequence[Mapping[str, Any]],
                      observations: Mapping[str, Mapping[Any, Mapping[str, Any]]], footprint: Mapping[str, Any] | None,
                      *, profile: str | None = None) -> dict[str, Any]:
    """Return an advisory strict result without mutating any supplied object.

    Observations are keyed by exact media identity, then source frame. All face
    and independent-body boxes are normalized source coordinates. Footprint is
    a style/asset-bound all-frame alpha union already calibrated to sequence.
    """
    if profile != PROFILE:
        return {"profile": profile, "status": "not-requested", "timeline_mutated": False}
    start, end = cue.get("start_frame"), cue.get("end_frame")
    mappings, issues = exact_frame_map(start, end, clips)
    context_sha256 = None
    try:
        context_sha256 = render_context_sha256(cue, clips)
    except (TypeError, ValueError) as error:
        issues.append("INVALID_RENDER_CONTEXT: " + str(error))
    if not isinstance(observations, Mapping):
        observations = {}
        issues.append("OBSERVATION_TABLE_UNAVAILABLE")
    # exact_frame_map has validated global typed uniqueness. Build no lookup
    # on identity failure, including an unhashable hidden ID.
    by_id = {clip["id"]: clip for clip in clips} if mappings else {}
    counts = {camera: {"expected": count, "decoded": 0, "face_observed": 0, "body_observed": 0, "transformed": 0}
              for camera, count in Counter(row["camera_id"] for row in mappings).items()}
    faces, bodies = [], []
    for row in mappings:
        camera_counts = counts[row["camera_id"]]
        source = observations.get(row["media_id"], {})
        observation = source.get(row["source_frame"], source.get(str(row["source_frame"]))) if isinstance(source, Mapping) else None
        label = f"{row['camera_id']}:{row['source_frame']}@{row['timeline_frame']}"
        if not isinstance(observation, Mapping) or observation.get("decoded") is not True:
            issues.append("MISSING_DECODED_FRAME: " + label)
            continue
        camera_counts["decoded"] += 1
        try:
            if observation.get("face_verified") is not True:
                raise ValueError("Face observation unavailable")
            face = _box(observation.get("face_box"), source=True)
            camera_counts["face_observed"] += 1
            if (observation.get("body_verified") is not True or observation.get("body_method") not in BODY_METHODS
                    or not isinstance(observation.get("body_evidence_id"), str) or not observation["body_evidence_id"].strip()):
                raise ValueError("Independent body evidence unavailable")
            body = _box(observation.get("body_box"), source=True)
            camera_counts["body_observed"] += 1
            transform = by_id[row["clip_id"]].get("transform", {})
            transformed_face = transform_box(face, transform, row["timeline_frame"])
            transformed_body = transform_box(body, transform, row["timeline_frame"])
            faces.append(transformed_face)
            bodies.append(transformed_body)
            camera_counts["transformed"] += 1
        except (KeyError, TypeError, ValueError) as error:
            issues.append("FRAME_EVIDENCE_REJECTED: " + label + " | " + str(error))
    face_union, body_union = _union(faces), _union(bodies)
    protected = _union(faces + bodies)
    footprint_box = None
    try:
        if not isinstance(footprint, Mapping) or footprint.get("verified") is not True:
            raise ValueError("Native artwork footprint unavailable")
        if (footprint.get("coordinate_space") != "sequence-normalized" or footprint.get("placement_transform_verified") is not True
                or footprint.get("includes_glow_and_motion") is not True):
            raise ValueError("Footprint transform or glow/motion coverage not verified")
        if context_sha256 is None or footprint.get("render_context_sha256") != context_sha256:
            raise ValueError("Footprint render context is missing or stale")
        if (footprint.get("start_frame") != start or footprint.get("end_frame") != end
                or footprint.get("observed_frame_count") != end - start):
            raise ValueError("Footprint does not cover exact cue interval")
        frame_ids = footprint.get("frame_ids")
        if not isinstance(frame_ids, (list, tuple)) or sorted(_integer(frame) for frame in frame_ids) != list(range(start, end)):
            raise ValueError("Footprint frame IDs must cover the interval exactly once")
        for key in ("template_sha256", "text_style_sha256"):
            if not re.fullmatch(r"[0-9a-fA-F]{64}", str(footprint.get(key, ""))):
                raise ValueError("Footprint lacks asset/style fingerprint")
            if str(cue.get(key, "")).lower() != str(footprint[key]).lower():
                raise ValueError("Footprint asset/style differs from current cue")
        authored_size = footprint.get("authored_size", [])
        if len(authored_size) != 2 or any(_finite(value) <= 0 for value in authored_size):
            raise ValueError("Authored footprint coordinate size missing")
        footprint_box = _box(footprint.get("bounds_union"))
        x, y, w, h = footprint_box
        sx, sy, sw, sh = SAFE_AREA
        if x < sx or y < sy or x + w > sx + sw or y + h > sy + sh:
            raise ValueError("Footprint lies outside title-safe area")
        if not protected:
            raise ValueError("No complete sequence-space human union")
        bx, by, bw, bh = protected
        left, top = max(x, bx - CLEARANCE), max(y, by - CLEARANCE)
        right, bottom = min(x + w, bx + bw + CLEARANCE), min(y + h, by + bh + CLEARANCE)
        if max(0, right - left) * max(0, bottom - top) / (w * h) > MAX_OVERLAP:
            raise ValueError("Footprint overlaps full human union or clearance")
    except (KeyError, TypeError, ValueError) as error:
        issues.append("FOOTPRINT_REJECTED: " + str(error))
    if not mappings:
        issues.append("NO_VISIBLE_FRAME_EVIDENCE")
    verified = bool(mappings) and not issues
    return {"profile": PROFILE, "status": "verified" if verified else "blocked", "cue_id": cue.get("id"),
            "strict_spatial_verified": verified, "allow_sfx": verified, "timeline_mutated": False,
            "render_context_sha256": context_sha256,
            "expected_timeline_frames": end - start if isinstance(start, int) and isinstance(end, int) else None,
            "frame_mappings": mappings, "per_camera_coverage": counts, "face_union": face_union,
            "independent_body_union": body_union, "protected_union": protected,
            "footprint_sequence_union": footprint_box, "safe_area": list(SAFE_AREA),
            "subject_clearance": CLEARANCE, "max_overlap_ratio": MAX_OVERLAP, "issues": issues}
