"""Fresh-job content identity and the explicitly declared XML sequence clock.

No ASR inference, media mutation, clock guessing, or legacy retrofit occurs.
The clock identifies XML playback frames, NOT a newly verified source-frame
rate. Ordinary ASR remains machine evidence and cannot authorize cut repair.
"""
from __future__ import annotations

import hashlib
import math
import re
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

PROTOCOL = "hafez-fresh-caption-context-v1"
IDENTITY_STRENGTH = "sha256-content-before-after-asr"


def hash_media_content(
    path: str | Path, *, progress: Callable[[int, int, float], None] | None = None,
    cancelled: Callable[[], bool] | None = None, chunk_bytes: int = 8 * 1024 * 1024,
) -> str:
    """Stream bytes with progress, bounded memory, and no partial hash result.

    Desktop currently cancels by terminating its child process. This in-process
    reader does not hide that termination or swallow KeyboardInterrupt/SystemExit.
    A cooperative callback is supported when a future caller actually has one.
    """
    if isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int) or chunk_bytes <= 0:
        raise ValueError("Hash chunk size must be a positive integer")
    source = Path(path)
    before = source.stat()
    started = last_report = time.monotonic()
    processed = 0
    digest = hashlib.sha256()
    if progress:
        progress(0, before.st_size, 0.0)
    with source.open("rb") as stream:
        while True:
            if cancelled and cancelled():
                raise InterruptedError("Media fingerprint cancelled; no evidence committed")
            block = stream.read(chunk_bytes)
            if not block:
                break
            digest.update(block)
            processed += len(block)
            now = time.monotonic()
            if progress and now - last_report >= 2.0:
                progress(processed, before.st_size, now - started)
                last_report = now
    after = source.stat()
    if ((before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
            or processed != before.st_size):
        raise RuntimeError("Source media changed during fingerprinting")
    if progress:
        progress(processed, before.st_size, time.monotonic() - started)
    return digest.hexdigest()


def declared_xml_clock(processing_fps: float, timebase: int, ntsc: str) -> dict[str, Any]:
    """Describe the exporter's actual rate, never Fraction(float).limit_denominator.

    A processing rate inconsistent with that declared playback clock disables
    this optimization. Existing video timing/export behavior is not changed.
    """
    if (isinstance(timebase, bool) or not isinstance(timebase, int) or timebase <= 0
            or not isinstance(ntsc, str) or ntsc not in {"TRUE", "FALSE"}
            or isinstance(processing_fps, bool) or not isinstance(processing_fps, (int, float))
            or not math.isfinite(processing_fps) or processing_fps <= 0):
        return {"status": "disabled", "reason": "invalid-xml-frame-clock"}
    rate = Fraction(timebase * 1000, 1001) if ntsc == "TRUE" else Fraction(timebase, 1)
    if not math.isclose(processing_fps, float(rate), rel_tol=0, abs_tol=1e-7):
        return {"status": "disabled", "reason": "processing-rate-xml-clock-mismatch"}
    return {"status": "available", "origin": "premiere-xml-export-declared-rate",
            "timebase": timebase, "ntsc": ntsc,
            "numerator": rate.numerator, "denominator": rate.denominator}


def verify_fresh_caption_source(
    manifest: dict[str, Any], *, timebase: int, ntsc: str,
    progress: Callable[[int, int, float], None] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Verify only new producer manifests; legacy performs no media read.

    Content replacement on a fresh job invalidates its analysis and stops the
    finalize caller before AI/output writes, rather than trusting stale evidence.
    """
    specification = manifest.get("caption_evidence")
    if not isinstance(specification, dict) or specification.get("protocol") != PROTOCOL:
        return None, {"status": "disabled", "reason": "legacy-no-caption-provenance"}
    evidence = manifest.get("source_word_evidence", {})
    identity = evidence.get("media_identity", {}) if isinstance(evidence, dict) else {}
    sha = identity.get("sha256") if isinstance(identity, dict) else None
    evidence_id = evidence.get("evidence_id") if isinstance(evidence, dict) else None
    if (not isinstance(identity, dict) or identity.get("strength") != IDENTITY_STRENGTH
            or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
            or not isinstance(evidence_id, str) or not evidence_id
            or specification.get("source_evidence_id") != evidence_id):
        return None, {"status": "disabled", "reason": "missing-fresh-content-evidence"}
    if (not isinstance(manifest.get("cam1_path"), str) or not isinstance(identity.get("path"), str)
            or Path(manifest["cam1_path"]).resolve() != Path(identity["path"]).resolve()):
        raise RuntimeError("Source media identity changed since prepare")
    actual_sha = hash_media_content(manifest["cam1_path"], progress=progress)
    if actual_sha != sha:
        raise RuntimeError("Source media changed since prepare; stale caption evidence refused")
    # A nonstandard/changed output clock disables layout, not source identity
    # verification. Fresh content replacement must still stop finalization.
    clock = declared_xml_clock(manifest.get("fps"), timebase, ntsc)
    if clock.get("status") != "available" or specification.get("clock") != clock:
        return None, {"status": "disabled", "reason": "unverified-or-changed-xml-clock",
                      "content_verified": True}
    words = manifest.get("mapped_words")
    if not isinstance(words, list) or any(not isinstance(word, dict) for word in words):
        return None, {"status": "disabled", "reason": "missing-source-word-evidence"}
    # Per-word ID, hash, raw-acoustic, coverage, and literal selection checks
    # remain in the optional binder. No missing word fingerprint is stamped here.
    return {"words": words, "media_sha256": sha, "evidence_id": evidence_id,
            "fps": (clock["numerator"], clock["denominator"])}, {
                "status": "content-and-output-clock-verified", "clock": clock,
                "source_evidence_id": evidence_id, "publication_ready": False,
            }


def variant_caption_context(source: dict[str, Any] | None, clips: list[Any]) -> dict[str, Any] | None:
    """Bind the exact finalized A1 clips; do not round or repair frame values."""
    if source is None:
        return None
    keeps = []
    for index, clip in enumerate(clips):
        if (not isinstance(clip, (list, tuple)) or len(clip) != 4
                or any(isinstance(frame, bool) or not isinstance(frame, int) for frame in clip)):
            return None
        keeps.append(dict(zip(("start_frame", "end_frame", "source_in_frame", "source_out_frame"), clip),
                          id=f"final-a1-{index}", media_sha256=source["media_sha256"]))
    return {**source, "keeps": keeps}
