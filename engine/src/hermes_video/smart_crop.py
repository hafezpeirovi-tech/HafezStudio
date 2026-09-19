"""Face-aware Premiere Pro/FCP 7 XML motion keyframe generation.

The module never renders video. It reads selected source frames and emits Basic
Motion keyframes that Premiere Pro can import from an xmeml v5 document.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import urllib.parse
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import cv2
import numpy as np
from runtime_paths import face_model_path


DEFAULT_MODEL = face_model_path()
_FACE_CENTER_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_FACE_BOX_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def probe_video(video_path: str) -> dict[str, Any]:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0))
    height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0))
    frame_count = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0))
    sar_num = int(round(capture.get(getattr(cv2, "CAP_PROP_SAR_NUM", 40)) or 1.0))
    sar_den = int(round(capture.get(getattr(cv2, "CAP_PROP_SAR_DEN", 41)) or 1.0))
    capture.release()
    if fps <= 0:
        fps = 30.0
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions: {video_path}")
    return {
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "duration": frame_count / fps if frame_count > 0 else 0.0,
        "sar_num": max(1, sar_num),
        "sar_den": max(1, sar_den),
    }


def get_timebase_and_ntsc(fps: float) -> tuple[int, str]:
    rounded = max(1, int(round(fps)))
    return rounded, "TRUE" if abs(fps - rounded) > 0.01 else "FALSE"


def path_to_url(path: str) -> str:
    absolute = os.path.abspath(path).replace("\\", "/")
    return "file://localhost/" + urllib.parse.quote(absolute)


class FaceDetector:
    """YuNet detector with CUDA auto-selection and Haar fallback."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL, detect_width: int = 640):
        self.detect_width = max(320, int(detect_width))
        self.yunet = None
        self.haar = None
        self.backend = "haar"
        model_path = Path(model_path)

        if model_path.exists() and hasattr(cv2, "FaceDetectorYN"):
            backend = cv2.dnn.DNN_BACKEND_OPENCV
            target = cv2.dnn.DNN_TARGET_CPU
            try:
                if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    backend = cv2.dnn.DNN_BACKEND_CUDA
                    target = cv2.dnn.DNN_TARGET_CUDA_FP16
                self.yunet = cv2.FaceDetectorYN.create(
                    str(model_path),
                    "",
                    (320, 320),
                    0.72,
                    0.3,
                    5000,
                    backend,
                    target,
                )
                self.backend = "yunet-cuda" if target != cv2.dnn.DNN_TARGET_CPU else "yunet-cpu"
            except cv2.error:
                self.yunet = cv2.FaceDetectorYN.create(
                    str(model_path),
                    "",
                    (320, 320),
                    0.72,
                    0.3,
                    5000,
                    cv2.dnn.DNN_BACKEND_OPENCV,
                    cv2.dnn.DNN_TARGET_CPU,
                )
                self.backend = "yunet-cpu"

        if self.yunet is None:
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            self.haar = cv2.CascadeClassifier(str(cascade_path))
            self.backend = "haar-cpu"

    def detect(self, frame: np.ndarray) -> list[tuple[float, float, float, float, float]]:
        height, width = frame.shape[:2]
        scale = min(1.0, self.detect_width / max(1, width))
        resized_width = max(32, int(round(width * scale)))
        resized_height = max(32, int(round(height * scale)))
        resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
        faces: list[tuple[float, float, float, float, float]] = []

        if self.yunet is not None:
            self.yunet.setInputSize((resized_width, resized_height))
            _, detections = self.yunet.detect(resized)
            if detections is not None:
                for row in detections:
                    x, y, box_width, box_height = map(float, row[:4])
                    score = float(row[-1])
                    faces.append(
                        (
                            (x + box_width * 0.5) / resized_width,
                            (y + box_height * 0.45) / resized_height,
                            box_width / resized_width,
                            box_height / resized_height,
                            score,
                        )
                    )
        elif self.haar is not None:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            detections = self.haar.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(28, 28),
            )
            for x, y, box_width, box_height in detections:
                faces.append(
                    (
                        (x + box_width * 0.5) / resized_width,
                        (y + box_height * 0.45) / resized_height,
                        box_width / resized_width,
                        box_height / resized_height,
                        0.7,
                    )
                )
        return faces


def _choose_main_face(
    faces: list[tuple[float, float, float, float, float]],
    previous: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if not faces:
        return None
    best = None
    best_score = -float("inf")
    for center_x, center_y, width, height, confidence in faces:
        area = max(0.0, width * height)
        center_distance = math.hypot(center_x - 0.5, center_y - 0.45)
        continuity = 0.0 if previous is None else math.hypot(center_x - previous[0], center_y - previous[1])
        score = area * 4.0 + confidence * 0.45 - center_distance * 0.25 - continuity * 1.4
        if score > best_score:
            best_score = score
            best = (center_x, center_y)
    return best


def _choose_main_face_box(
    faces: list[tuple[float, float, float, float, float]],
    previous: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    """Return the main face as a normalized ``(x, y, width, height)`` box.

    YuNet reports the eye-weighted centre used by the reframing code.  For
    layout collision tests we convert it back to a conventional top-left box
    and keep temporal continuity so a background face cannot steal a graphic.
    """
    if not faces:
        return None
    best: tuple[float, float, float, float] | None = None
    best_score = -float("inf")
    previous_center = None
    if previous is not None:
        previous_center = (previous[0] + previous[2] * 0.5, previous[1] + previous[3] * 0.45)
    for center_x, center_y, width, height, confidence in faces:
        area = max(0.0, width * height)
        centre_distance = math.hypot(center_x - 0.5, center_y - 0.43)
        continuity = 0.0 if previous_center is None else math.hypot(
            center_x - previous_center[0], center_y - previous_center[1]
        )
        score = area * 5.0 + confidence * 0.5 - centre_distance * 0.22 - continuity * 1.6
        if score > best_score:
            best_score = score
            best = (
                max(0.0, center_x - width * 0.5),
                max(0.0, center_y - height * 0.45),
                min(1.0, width),
                min(1.0, height),
            )
    return best


def detect_face_boxes(
    video_path: str,
    source_frames: list[int],
    model_path: str | Path = DEFAULT_MODEL,
) -> tuple[dict[int, tuple[float, float, float, float]], str]:
    """Detect normalized main-face boxes for sparse editorial layout samples."""
    if not source_frames:
        return {}, "not-needed"
    requested = sorted(set(max(0, int(value)) for value in source_frames))
    cache_key = (
        os.path.normcase(os.path.abspath(video_path)),
        os.path.normcase(os.path.abspath(str(model_path))),
    )
    cached = _FACE_BOX_CACHE.setdefault(
        cache_key,
        {"processed": set(), "boxes": {}, "backend": "not-needed"},
    )
    missing = [frame for frame in requested if frame not in cached["processed"]]
    if missing:
        detector = FaceDetector(model_path)
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            return {}, detector.backend
        boxes: dict[int, tuple[float, float, float, float]] = cached["boxes"]
        previous: tuple[float, float, float, float] | None = None
        previous_frame: int | None = None
        for frame_number in missing:
            if previous_frame is None or frame_number - previous_frame > 90:
                previous = None
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if ok:
                selected = _choose_main_face_box(detector.detect(frame), previous)
                if selected is not None:
                    boxes[frame_number] = selected
                    previous = selected
            cached["processed"].add(frame_number)
            previous_frame = frame_number
        capture.release()
        cached["backend"] = detector.backend
    boxes = cached["boxes"]
    return ({frame: boxes[frame] for frame in requested if frame in boxes}, str(cached["backend"]))


def _union_normalized_boxes(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    """Return the clamped union of normalized top-left boxes."""
    if not boxes:
        return None
    left = max(0.0, min(box[0] for box in boxes))
    top = max(0.0, min(box[1] for box in boxes))
    right = min(1.0, max(box[0] + box[2] for box in boxes))
    bottom = min(1.0, max(box[1] + box[3] for box in boxes))
    return (left, top, max(0.0, right - left), max(0.0, bottom - top))


def _presenter_envelope_from_face(
    face: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Infer a conservative seated upper-body envelope from one face box.

    YuNet is substantially more stable than generic pedestrian detection for a
    seated presenter.  The expanded envelope protects hair, shoulders, chest
    and hand gestures; unioning these envelopes over time gives the spatial QA
    layer a body-safe region even when the torso detector would miss a frame.
    """
    x, y, width, height = face
    left = max(0.0, x - width * 0.90)
    top = max(0.0, y - height * 0.35)
    right = min(1.0, x + width * 1.90)
    bottom = min(1.0, y + height * 4.80)
    return (left, top, max(0.0, right - left), max(0.0, bottom - top))


def detect_subject_box_unions(
    video_path: str,
    source_frame_groups: list[list[int]],
    model_path: str | Path = DEFAULT_MODEL,
) -> tuple[list[dict[str, Any]], str]:
    """Track the presenter across every graphic interval.

    Each input group represents several source frames sampled from the full
    lifetime of one graphic.  The result contains both a face union and a
    conservative presenter/body union, plus coverage metadata for QA.
    """
    normalized_groups = [sorted(set(max(0, int(frame)) for frame in group)) for group in source_frame_groups]
    all_frames = sorted({frame for group in normalized_groups for frame in group})
    detected, backend = detect_face_boxes(video_path, all_frames, model_path)
    results: list[dict[str, Any]] = []
    for group in normalized_groups:
        faces = [detected[frame] for frame in group if frame in detected]
        face_union = _union_normalized_boxes(faces)
        presenter_union = _union_normalized_boxes([_presenter_envelope_from_face(face) for face in faces])
        results.append(
            {
                "sample_frames": group,
                "sample_count": len(group),
                "detected_count": len(faces),
                "coverage": round(len(faces) / max(1, len(group)), 4),
                "face_union": face_union,
                "subject_union": presenter_union,
            }
        )
    return results, backend


def detect_face_centers(
    video_path: str,
    source_frames: list[int],
    model_path: str | Path = DEFAULT_MODEL,
) -> tuple[dict[int, tuple[float, float]], str]:
    if not source_frames:
        return {}, "not-needed"
    requested = sorted(set(max(0, int(value)) for value in source_frames))
    cache_key = (
        os.path.normcase(os.path.abspath(video_path)),
        os.path.normcase(os.path.abspath(str(model_path))),
    )
    cached = _FACE_CENTER_CACHE.setdefault(
        cache_key,
        {"processed": set(), "centers": {}, "backend": "not-needed"},
    )
    missing = [frame for frame in requested if frame not in cached["processed"]]
    if not missing:
        return (
            {frame: cached["centers"][frame] for frame in requested if frame in cached["centers"]},
            str(cached["backend"]),
        )
    detector = FaceDetector(model_path)
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        return {}, detector.backend
    centers: dict[int, tuple[float, float]] = cached["centers"]
    previous: tuple[float, float] | None = None
    previous_frame: int | None = None
    for frame_number in missing:
        if previous_frame is None or frame_number - previous_frame > 60:
            previous = None
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = capture.read()
        if not ok:
            continue
        selected = _choose_main_face(detector.detect(frame), previous)
        if selected is not None:
            centers[frame_number] = selected
            previous = selected
        cached["processed"].add(frame_number)
        previous_frame = frame_number
    capture.release()
    cached["backend"] = detector.backend
    return ({frame: centers[frame] for frame in requested if frame in centers}, detector.backend)


def _smooth_samples(samples: list[tuple[int, tuple[float, float] | None]]) -> list[tuple[int, tuple[float, float]]]:
    if not samples:
        return []
    valid_indices = [index for index, (_, value) in enumerate(samples) if value is not None]
    if not valid_indices:
        return [(when, (0.5, 0.42)) for when, _ in samples]
    values = np.array(
        [
            samples[index][1] if samples[index][1] is not None else (np.nan, np.nan)
            for index in range(len(samples))
        ],
        dtype=np.float64,
    )
    x_axis = np.arange(len(samples), dtype=np.float64)
    for axis in (0, 1):
        valid = ~np.isnan(values[:, axis])
        values[:, axis] = np.interp(x_axis, x_axis[valid], values[valid, axis])
        padded = np.pad(values[:, axis], (2, 2), mode="edge")
        values[:, axis] = np.convolve(padded, np.ones(5) / 5.0, mode="valid")
    return [
        (samples[index][0], (float(values[index, 0]), float(values[index, 1])))
        for index in range(len(samples))
    ]


def _center_for_face(
    face: tuple[float, float],
    scale_percent: float,
    target_x: float = 0.5,
    target_y: float = 0.42,
) -> tuple[float, float]:
    zoom = scale_percent / 100.0
    face_x, face_y = face
    horizontal = target_x - (0.5 + zoom * (face_x - 0.5))
    vertical = target_y - (0.5 + zoom * (face_y - 0.5))
    margin = max(0.0, (zoom - 1.0) / 2.0)
    horizontal = max(-margin, min(margin, horizontal))
    vertical = max(-margin, min(margin, vertical))
    return horizontal, vertical


def prepare_track_motion(
    video_path: str,
    clips: list[list[int]] | list[tuple[int, int, int, int]],
    events: list[dict[str, Any]],
    fps: float,
    model_path: str | Path = DEFAULT_MODEL,
    punch_scale: float = 115.0,
    sample_seconds: float = 0.18,
) -> tuple[dict[int, dict[str, list[Any]]], str]:
    """Return Basic Motion keyframes keyed by clip index."""
    step = max(1, int(round(fps * sample_seconds)))
    requests: dict[tuple[int, int], int] = {}
    event_ranges: dict[int, list[tuple[int, int, float]]] = {}

    for clip_index, raw_clip in enumerate(clips):
        timeline_start, timeline_end, media_in, _ = map(int, raw_clip)
        duration = timeline_end - timeline_start
        for event in events:
            event_start = int(round(float(event["start"]) * fps))
            event_end = int(round(float(event["end"]) * fps))
            overlap_start = max(timeline_start, event_start)
            overlap_end = min(timeline_end, event_end)
            if overlap_end - overlap_start < 2:
                continue
            local_start = overlap_start - timeline_start
            local_end = overlap_end - timeline_start
            try:
                event_scale = min(122.0, max(106.0, float(event.get("scale", punch_scale))))
            except (TypeError, ValueError):
                event_scale = punch_scale
            event_ranges.setdefault(clip_index, []).append((local_start, local_end, event_scale))
            sample_positions = list(range(local_start, local_end, step))
            if not sample_positions or sample_positions[-1] != local_end - 1:
                sample_positions.append(local_end - 1)
            for local_when in sample_positions:
                requests[(clip_index, local_when)] = media_in + local_when

    source_frames = list(requests.values())
    centers, backend = detect_face_centers(video_path, source_frames, model_path)
    result: dict[int, dict[str, list[Any]]] = {}

    for clip_index, ranges in event_ranges.items():
        timeline_start, timeline_end, media_in, _ = map(int, clips[clip_index])
        duration = timeline_end - timeline_start
        scale_keys: dict[int, float] = {0: 100.0, max(0, duration - 1): 100.0}
        center_keys: dict[int, tuple[float, float]] = {0: (0.0, 0.0), max(0, duration - 1): (0.0, 0.0)}

        for local_start, local_end, event_scale in ranges:
            event_length = max(2, local_end - local_start)
            ramp_frames = max(2, min(12, int(round(fps * 0.27)), max(2, event_length // 3)))
            ramp_in_start = max(0, local_start - ramp_frames // 2)
            hold_start = min(local_end - 1, local_start + ramp_frames)
            hold_end = max(hold_start, local_end - ramp_frames)
            ramp_out_end = min(duration - 1, local_end + ramp_frames // 2)
            scale_keys[ramp_in_start] = 100.0
            center_keys[ramp_in_start] = (0.0, 0.0)

            raw_samples: list[tuple[int, tuple[float, float] | None]] = []
            for local_when in sorted(
                key[1] for key in requests if key[0] == clip_index and local_start <= key[1] < local_end
            ):
                face = centers.get(media_in + local_when)
                raw_samples.append((local_when, face))
            smooth_samples = _smooth_samples(raw_samples)
            for local_when, face in smooth_samples:
                if hold_start <= local_when <= hold_end:
                    scale_keys[local_when] = event_scale
                    center_keys[local_when] = _center_for_face(face, event_scale)

            nearest_face = next(
                (face for when, face in smooth_samples if when >= hold_start),
                (0.5, 0.42),
            )
            center_value = _center_for_face(nearest_face, event_scale)
            scale_keys[hold_start] = event_scale
            center_keys[hold_start] = center_value
            scale_keys[hold_end] = event_scale
            center_keys[hold_end] = center_value
            scale_keys[ramp_out_end] = 100.0
            center_keys[ramp_out_end] = (0.0, 0.0)

        result[clip_index] = {
            "scale": sorted(scale_keys.items()),
            "center": sorted(center_keys.items()),
            "anchor": [(0, (0.0, 0.0)), (max(0, duration - 1), (0.0, 0.0))],
        }
    return result, backend


def _scalar_parameter(parameter_id: str, name: str, keyframes: list[tuple[int, float]], indent: str) -> list[str]:
    lines = [
        f"{indent}<parameter>",
        f"{indent}  <parameterid>{parameter_id}</parameterid>",
        f"{indent}  <name>{name}</name>",
        f"{indent}  <valuemin>0</valuemin>",
        f"{indent}  <valuemax>1000</valuemax>",
        f"{indent}  <interpolation><name>FCPCurve</name></interpolation>",
    ]
    for when, value in keyframes:
        lines.extend(
            [
                f"{indent}  <keyframe>",
                f"{indent}    <when>{int(when)}</when>",
                f"{indent}    <value>{float(value):.6f}</value>",
                f"{indent}  </keyframe>",
            ]
        )
    lines.append(f"{indent}</parameter>")
    return lines


def _point_parameter(
    parameter_id: str,
    name: str,
    keyframes: list[tuple[int, tuple[float, float]]],
    indent: str,
) -> list[str]:
    lines = [
        f"{indent}<parameter>",
        f"{indent}  <parameterid>{parameter_id}</parameterid>",
        f"{indent}  <name>{name}</name>",
        f"{indent}  <interpolation><name>FCPCurve</name></interpolation>",
    ]
    for when, (horizontal, vertical) in keyframes:
        lines.extend(
            [
                f"{indent}  <keyframe>",
                f"{indent}    <when>{int(when)}</when>",
                f"{indent}    <value><horiz>{horizontal:.8f}</horiz><vert>{vertical:.8f}</vert></value>",
                f"{indent}  </keyframe>",
            ]
        )
    lines.append(f"{indent}</parameter>")
    return lines


def motion_filter_xml(motion: dict[str, list[Any]], indent: str = "            ") -> list[str]:
    effect_indent = indent + "  "
    parameter_indent = effect_indent + "  "
    lines = [
        f"{indent}<filter>",
        f"{indent}  <enabled>TRUE</enabled>",
        f"{indent}  <start>-1</start>",
        f"{indent}  <end>-1</end>",
        f"{effect_indent}<effect>",
        f"{effect_indent}  <name>Basic Motion</name>",
        f"{effect_indent}  <effectid>basic</effectid>",
        f"{effect_indent}  <effectcategory>motion</effectcategory>",
        f"{effect_indent}  <effecttype>motion</effecttype>",
        f"{effect_indent}  <mediatype>video</mediatype>",
    ]
    lines.extend(_scalar_parameter("scale", "Scale", motion["scale"], parameter_indent))
    lines.extend(_point_parameter("center", "Center", motion["center"], parameter_indent))
    lines.extend(_point_parameter("anchorpoint", "Anchor Point", motion["anchor"], parameter_indent))
    lines.extend([f"{effect_indent}</effect>", f"{indent}</filter>"])
    return lines


def _standalone_xml(
    video_path: str,
    output_path: str,
    events: list[dict[str, Any]],
    model_path: str | Path,
) -> None:
    metadata = probe_video(video_path)
    fps = metadata["fps"]
    duration_frames = metadata["frame_count"]
    timebase, ntsc = get_timebase_and_ntsc(fps)
    rate = f"<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>"
    clip = (0, duration_frames, 0, duration_frames)
    motion, backend = prepare_track_motion(video_path, [clip], events, fps, model_path)
    name = escape(Path(video_path).name)
    source_url = escape(path_to_url(video_path))
    lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        "<!DOCTYPE xmeml>",
        '<xmeml version="5">',
        "  <sequence>",
        "    <name>Hafez Smart Crop</name>",
        f"    <duration>{duration_frames}</duration>",
        f"    {rate}",
        "    <media>",
        "      <video>",
        "        <format><samplecharacteristics>",
        f"          {rate}<width>{metadata['width']}</width><height>{metadata['height']}</height>",
        "          <pixelaspectratio>square</pixelaspectratio>",
        "        </samplecharacteristics></format>",
        "        <track>",
        '          <clipitem id="smart-crop-video-1">',
        f"            <name>{name}</name>",
        f"            <duration>{duration_frames}</duration>",
        "            <start>0</start>",
        f"            <end>{duration_frames}</end>",
        "            <in>0</in>",
        f"            <out>{duration_frames}</out>",
        '            <file id="smart-crop-file-1">',
        f"              <name>{name}</name>",
        f"              <pathurl>{source_url}</pathurl>",
        f"              <duration>{duration_frames}</duration>",
        f"              {rate}",
        "              <media><video><samplecharacteristics>",
        f"                {rate}<width>{metadata['width']}</width><height>{metadata['height']}</height>",
        "              </samplecharacteristics></video></media>",
        "            </file>",
    ]
    if 0 in motion:
        lines.extend(motion_filter_xml(motion[0]))
    lines.extend(
        [
            "          </clipitem>",
            "        </track>",
            "      </video>",
            "    </media>",
            "  </sequence>",
            "</xmeml>",
        ]
    )
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Face detector backend: {backend}")
    print(f"Premiere XML created: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Premiere-compatible face-aware FCP 7 XML.")
    parser.add_argument("input", help="Input MP4 path")
    parser.add_argument("output", help="Output XML path")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="YuNet ONNX model path")
    parser.add_argument(
        "--punch-at",
        default="",
        help="Comma-separated semantic punch times in seconds (for standalone use)",
    )
    parser.add_argument("--punch-duration", type=float, default=3.2)
    args = parser.parse_args()
    metadata = probe_video(args.input)
    events = []
    for value in filter(None, (part.strip() for part in args.punch_at.split(","))):
        start = max(0.0, float(value))
        events.append(
            {
                "start": start,
                "end": min(metadata["duration"], start + max(2.5, min(4.5, args.punch_duration))),
            }
        )
    if not events:
        print("No semantic punch times supplied; XML will contain the linked source without zoom events.")
    _standalone_xml(args.input, args.output, events, args.model)


if __name__ == "__main__":
    main()
