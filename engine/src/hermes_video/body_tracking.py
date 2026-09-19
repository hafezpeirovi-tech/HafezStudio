"""Local-only person segmentation and exact requested-frame coverage.

Model/preprocessing: OpenCV Zoo PPHumanSeg (PaddlePaddle, Apache-2.0).
No network or face-derived body fallback. A miss is evidence, not an empty safe area.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import cv2
import numpy as np

from runtime_paths import body_model_path
from smart_crop import FaceDetector, _union_normalized_boxes

MODEL_SHA256 = "552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24"
METHOD = "pphumanseg-independent-person-union"
SAFETY_MARGIN = 0.06


def protected_union(boxes):
    box = _union_normalized_boxes(boxes)
    if box is None:
        return None
    x, y, w, h = box
    left, top = max(0.0, x - SAFETY_MARGIN), max(0.0, y - SAFETY_MARGIN)
    right, bottom = min(1.0, x + w + SAFETY_MARGIN), min(1.0, y + h + SAFETY_MARGIN)
    return (left, top, right - left, bottom - top)


def person_box(scores: np.ndarray):
    """Union ALL person pixels, including disconnected hands; no largest-component shortcut."""
    scores = np.asarray(scores)
    if scores.ndim != 4 or scores.shape[:2] != (1, 2) or not np.isfinite(scores).all():
        return None
    foreground = scores[0, 1] > scores[0, 0]
    area = float(foreground.mean())
    if not 0.01 <= area <= 0.98:
        return None
    # This model outputs class probabilities. Never silently treat arbitrary logits as confidence.
    if scores.min() < -0.001 or scores.max() > 1.001:
        return None
    if float(scores[0, 1][foreground].mean()) < 0.60:
        return None
    ys, xs = np.nonzero(foreground)
    h, w = foreground.shape
    # Two model pixels protect coarse segmentation edges, but are not a hand-detection guarantee.
    left, top = max(0, int(xs.min()) - 2) / w, max(0, int(ys.min()) - 2) / h
    right, bottom = min(w, int(xs.max()) + 3) / w, min(h, int(ys.max()) + 3) / h
    return (left, top, right - left, bottom - top)


class PersonSegmenter:
    def __init__(self, model=None):
        path = Path(model) if model is not None else body_model_path()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError("Approved local PPHumanSeg model missing or SHA256 mismatch")
        self.net = cv2.dnn.readNet(str(path))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def detect(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (192, 192)).astype(np.float32) / 255.0
        self.net.setInput(cv2.dnn.blobFromImage((rgb - 0.5) / 0.5))
        return person_box(self.net.forward())


def detect_subject_box_unions(video_path, source_frame_groups, model_path):
    """Decode/infer each requested source frame once, sequentially inside contiguous runs.

    Caller supplies every visible source frame (not sparse endpoints). Failed reads,
    missing model, non-finite inference and person misses make the interval incomplete.
    No cross-run cache can accidentally reuse evidence from replaced source media.
    """
    groups = [sorted(set(int(f) for f in group)) for group in source_frame_groups]
    requested = sorted({f for group in groups for f in group})
    rows = {}
    backend = "not-needed"
    error = None
    capture = None
    if requested:
        try:
            person, face = PersonSegmenter(), FaceDetector(model_path)
            backend = "pphumanseg-cpu+" + face.backend
            capture = cv2.VideoCapture(video_path)
            if not capture.isOpened():
                raise ValueError("Cannot decode source video")
            previous = None
            last_report = time.monotonic()
            for n, frame_no in enumerate(requested):
                row = {"frame": frame_no, "decoded": False, "face": None, "body": None}
                rows[frame_no] = row
                if frame_no < 0:
                    continue
                if previous is None or frame_no != previous + 1:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                ok, frame = capture.read()
                previous = frame_no if ok else None
                if ok and abs(capture.get(cv2.CAP_PROP_POS_FRAMES) - (frame_no + 1)) <= 0.5:
                    row["decoded"] = True
                    try:
                        row["body"] = person.detect(frame)
                        faces = face.detect(frame)
                        row["face"] = _union_normalized_boxes([
                            (max(0, x - w / 2), max(0, y - h * .45), w, h)
                            for x, y, w, h, confidence in faces
                        ])
                    except (cv2.error, ValueError, TypeError) as exc:
                        row["error"] = type(exc).__name__
                        row["body"] = None
                if time.monotonic() - last_report >= 5:
                    print(f"BODY_TRACKING {Path(video_path).name} {n + 1}/{len(requested)} frames", flush=True)
                    last_report = time.monotonic()
        except (cv2.error, ValueError, OSError) as exc:
            error = str(exc)
            backend = "body-tracking-unavailable"
        finally:
            if capture is not None:
                capture.release()
    results = []
    for group in groups:
        evidence = [rows.get(f, {"frame": f, "decoded": False, "face": None, "body": None}) for f in group]
        bodies = [r["body"] for r in evidence if r["body"] is not None]
        faces = [r["face"] for r in evidence if r["face"] is not None]
        complete = bool(group) and len(bodies) == len(group) and all(r["decoded"] for r in evidence)
        results.append({
            "sample_frames": group, "sample_count": len(group), "detected_count": len(bodies),
            "coverage": len(bodies) / max(1, len(group)), "body_complete": complete,
            "body_tracking_method": METHOD, "model_sha256": MODEL_SHA256,
            "decoded_count": sum(r["decoded"] for r in evidence), "face_detected_count": len(faces),
            "face_union": _union_normalized_boxes(faces), "body_union": _union_normalized_boxes(bodies),
            "subject_union": protected_union(bodies + faces), "safety_margin": SAFETY_MARGIN,
            "frame_evidence": evidence, "error": error,
        })
    return results, backend
