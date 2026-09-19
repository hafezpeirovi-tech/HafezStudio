"""Hermes two-camera edit preparation and Premiere XML finalization.

The proven synchronization and silence-cut logic is intentionally preserved.
The pipeline now has two modes so n8n can review Persian text with its existing
Gemini credential between transcription and final XML/SRT generation.
"""

from __future__ import annotations

import gc
import ctypes
import json
import os
import sys
import urllib.parse
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# n8n may start Python under a legacy Windows code page.  Keep Persian status
# lines machine-readable so a successful render is never reported as failed.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
from xml.sax.saxutils import escape

os.environ["NLTK_ALLOW_PROXIED_URLOPEN"] = "1"

import nltk
import ctranslate2
import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from scipy import signal

from audio_master import build_voice_master
from curation_rules import load_template_family_history
from graphic_framing import coordinate_graphic_framing
from professional_edit import (
    apply_face_safe_layout,
    build_action_markers,
    build_camera_schedule,
    build_graphic_cues,
    guard_automatic_graphic_copy,
    render_graphic_assets,
    split_track_for_camera,
    write_professional_plan,
)
from rough_cut import (
    build_variants,
    remap_segments,
    remap_timed_items,
    remap_time,
    validate_edit_decisions,
    detect_repeated_speech_edits,
    detect_short_setup_prefix,
    guard_retained_retake,
    bind_graphic_markers_to_source,
    validate_markers,
)
from smart_crop import (
    DEFAULT_MODEL as DEFAULT_FACE_MODEL,
    get_timebase_and_ntsc,
    motion_filter_xml,
    prepare_track_motion,
    probe_video,
)
from subtitle_pipeline import (
    build_review_tasks,
    build_review_segments,
    build_srt_cues,
    correct_known_terms,
    ensure_youtube_package,
    load_glossary,
    parse_full_review,
    resolve_review_tasks,
    restore_source_segments,
    source_faithful_subtitles,
    select_events,
    suggest_local_events,
    suggest_local_markers,
    write_srt,
)
from runtime_paths import default_output_root, face_model_path, nltk_data_path, persian_model_path
from word_boundary_guard import assess_word_boundary_gaps, collect_source_words, map_source_words
from caption_provenance import (
    IDENTITY_STRENGTH, PROTOCOL as CAPTION_EVIDENCE_PROTOCOL,
    declared_xml_clock, hash_media_content, variant_caption_context, verify_fresh_caption_source,
)
from caption_timing import build_timeline_word_cues
from asr_recovery import recover_alignment, recovery_windows


nltk.data.path.append(str(nltk_data_path()))

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = default_output_root()
GLOSSARY_PATH = SCRIPT_DIR / "subtitle_glossary.txt"
LOCAL_PERSIAN_MODEL = persian_model_path()
FACE_MODEL_PATH = face_model_path() if face_model_path().exists() else DEFAULT_FACE_MODEL

MIN_SILENCE_MS = 500
SILENCE_THRESHOLD_DB = -40
PADDING_MS = 200


def report_stage(stage: str, progress: int, message: str) -> None:
    """Emit a stable machine-readable milestone for the desktop progress UI."""
    safe_progress = max(0, min(100, int(progress)))
    safe_message = " ".join(str(message).splitlines()).strip()
    print(f"HERMES_STAGE {stage} {safe_progress} {safe_message}", flush=True)


def cuda_asr_runtime_ready() -> bool:
    """Return true only when CTranslate2's Windows CUDA math DLLs can load."""
    if os.name != "nt":
        return True
    try:
        ctypes.WinDLL("cublas64_12.dll")
        ctypes.WinDLL("cublasLt64_12.dll")
        return True
    except OSError:
        return False


def ms_to_frames(milliseconds: float, fps: float) -> int:
    return int(round((milliseconds / 1000.0) * fps))


def find_offset(audio1: AudioSegment, audio2: AudioSegment) -> float:
    """Preserved full-audio cross-correlation used by the working workflow."""
    samples1 = np.array(audio1.get_array_of_samples(), dtype=np.float32)
    samples2 = np.array(audio2.get_array_of_samples(), dtype=np.float32)
    correlation = signal.correlate(samples1, samples2, mode="full")
    offset_samples = int(np.argmax(correlation)) - len(samples2) + 1
    return (offset_samples / audio1.frame_rate) * 1000.0


def path_to_url(path: str) -> str:
    absolute = os.path.abspath(path).replace("\\", "/")
    return "file://localhost/" + urllib.parse.quote(absolute)


def generate_output_paths(cam_path: str) -> dict[str, str]:
    source_without_extension = os.path.splitext(cam_path)[0]
    clean_name = (
        source_without_extension.replace(":\\", "_")
        .replace("\\", "_")
        .replace("/", "_")
        .replace(" ", "")
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = str(OUTPUT_DIR / clean_name)
    return {
        "xml": base + ".xml",
        "srt": base + ".safe.srt",
        "safe_srt": base + ".safe.srt",
        "tight_srt": base + ".tight.srt",
        "safe_audio": base + ".safe.voice-master.wav",
        "tight_audio": base + ".tight.voice-master.wav",
        "manifest": base + ".edit.json",
        "prompt": base + ".review.txt",
        "review_tasks": base + ".review-tasks.json",
        "resolved_review": base + ".resolved-review.json",
        "audit": base + ".review-result.json",
        "youtube": base + ".youtube-package.md",
        "edit_notes": base + ".edit-notes.md",
        "professional_plan": base + ".premiere-plan.json",
        "graphics_dir": base + ".graphics",
    }


def build_timeline(
    nonsilent_ranges: list[list[int]] | list[tuple[int, int]],
    offset_ms: float,
    fps: float,
    cam1_length_ms: int,
) -> tuple[dict[str, list[tuple[int, int, int, int]]], list[dict[str, float]], int]:
    """Create exactly the same padded cuts and fixed offset mapping as before."""
    clips: dict[str, list[tuple[int, int, int, int]]] = {"cam1": [], "cam2": []}
    mapping: list[dict[str, float]] = []
    current_timeline_frame = 0

    for start, end in nonsilent_ranges:
        padded_start = max(0, int(start) - PADDING_MS)
        padded_end = min(cam1_length_ms, int(end) + PADDING_MS)
        media_in_cam1 = ms_to_frames(padded_start, fps)
        media_out_cam1 = ms_to_frames(padded_end, fps)
        duration_frames = media_out_cam1 - media_in_cam1
        if duration_frames <= 0:
            continue

        cam2_start_ms = max(0.0, padded_start - offset_ms)
        media_in_cam2 = ms_to_frames(cam2_start_ms, fps)
        media_out_cam2 = media_in_cam2 + duration_frames
        timeline_start = current_timeline_frame
        timeline_end = timeline_start + duration_frames

        clips["cam1"].append((timeline_start, timeline_end, media_in_cam1, media_out_cam1))
        clips["cam2"].append((timeline_start, timeline_end, media_in_cam2, media_out_cam2))
        mapping.append(
            {
                "orig_start_ms": float(padded_start),
                "orig_end_ms": float(padded_end),
                "tl_start_ms": timeline_start / fps * 1000.0,
                "tl_end_ms": timeline_end / fps * 1000.0,
            }
        )
        current_timeline_frame = timeline_end

    return clips, mapping, current_timeline_frame


def build_initial_timeline(ranges, offset_ms, fps, duration_ms):
    """Preserve the approved pacing for ALL styles, including Glass.

    Owner rejected the global 600/350ms Glass handles on 2026-09-14. Do not
    activate that experiment by style/environment. Word-boundary repair must
    be a separate targeted change, not more silence throughout the video.
    """
    clips, mapping, length = build_timeline(ranges, offset_ms, fps, duration_ms)
    policy = dict(id='legacy-silence-v1', head_ms=PADDING_MS, tail_ms=PADDING_MS)
    return clips, mapping, length, policy


def transcribe_and_map(
    cam1_path: str,
    mapping: list[dict[str, float]],
    glossary: list[str],
    *, evidence_sink: dict[str, Any] | None = None, recovery_audio: Any = None,
) -> list[dict[str, Any]]:
    media_path = Path(cam1_path).resolve()
    media_before = media_path.stat()
    media_sha_before = hash_media_content(
        media_path, progress=lambda done, total, elapsed: report_stage(
            "analyze", 28, f"اثر انگشت منبع پیش از ASR: {done}/{total} bytes · {elapsed:.1f}s"),
    )
    prefer_cuda = os.environ.get("HERMES_CUDA_PREFERRED", "1") != "0"
    cuda_devices = ctranslate2.get_cuda_device_count()
    cuda_ready = cuda_devices > 0 and cuda_asr_runtime_ready()
    device = "cuda" if prefer_cuda and cuda_ready else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    cpu_threads = max(1, int(os.environ.get("HERMES_CPU_THREADS", str(os.cpu_count() or 1))))
    asr_workers = max(1, int(os.environ.get("HERMES_ASR_WORKERS", "1")))
    prompt = "، ".join(glossary) if glossary else None
    if not LOCAL_PERSIAN_MODEL.exists():
        raise RuntimeError("مدل آفلاین فارسی موجود نیست؛ دانلود خودکار مجاز نیست.")
    primary_model = str(LOCAL_PERSIAN_MODEL)
    model_label = "مدل فارسی محلی" if LOCAL_PERSIAN_MODEL.exists() else "Whisper large-v3"
    if prefer_cuda and cuda_devices > 0 and not cuda_ready:
        print("CUDA Driver موجود است اما cuBLAS 12 برای ASR در دسترس نیست؛ Whisper مستقیم با تمام هسته‌های CPU اجرا می‌شود.")
    print(f"بارگذاری {model_label} روی {device}...")
    try:
        model = WhisperModel(primary_model, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=asr_workers, local_files_only=True)
    except Exception as error:
        if device != "cuda":
            raise
        print(f"هشدار: CUDA برای ASR آماده نیست؛ ادامه با CPU: {error}")
        device, compute_type = "cpu", "int8"
        model = WhisperModel(primary_model, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=1, local_files_only=True)

    def run_transcription(active_model: WhisperModel) -> tuple[list[Any], Any]:
        """Materialize segments so deferred CUDA load failures can fall back safely."""
        iterator, detected_info = active_model.transcribe(
            cam1_path,
            language=None if os.environ.get("HERMES_LANGUAGE_MODE", "fa-en") == "auto" else "fa",
            beam_size=5,
            best_of=5,
            patience=1.2,
            repetition_penalty=1.08,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.3,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            initial_prompt=prompt,
            hotwords=prompt,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 320,
                "speech_pad_ms": 180,
            },
            log_progress=True,
        )
        return list(iterator), detected_info

    try:
        source_iterator, info = run_transcription(model)
    except Exception as error:
        if device != "cuda":
            raise
        print(f"هشدار: اجرای CUDA برای ASR ممکن نیست؛ ادامه با CPU: {error}")
        del model
        gc.collect()
        device, compute_type = "cpu", "int8"
        model = WhisperModel(primary_model, device=device, compute_type=compute_type, cpu_threads=cpu_threads, num_workers=1, local_files_only=True)
        source_iterator, info = run_transcription(model)

    source_segments: list[dict[str, Any]] = []
    for segment in source_iterator:
        text = str(segment.text or "").strip()
        if not text or float(segment.end) <= float(segment.start):
            continue
        word_rows = [
            {
                "word": str(word.word or "").strip(),
                "start": float(word.start),
                "end": float(word.end),
                "probability": float(word.probability),
                "timing_origin": "asr-word-timestamps",
            }
            for word in (segment.words or [])
            if word.start is not None and word.end is not None and str(word.word or "").strip()
        ]
        if not word_rows:
            words = text.split()
            step = max(0.01, (float(segment.end) - float(segment.start)) / max(1, len(words)))
            word_rows = [
                {
                    "word": word,
                    "start": float(segment.start) + index * step,
                    "end": min(float(segment.end), float(segment.start) + (index + 1) * step),
                    "probability": None,
                    "timing_origin": "segment-interpolation",
                }
                for index, word in enumerate(words)
            ]
        source_segments.append(
            {
                "text": text,
                "start": float(segment.start),
                "end": float(segment.end),
                "avg_logprob": float(segment.avg_logprob),
                "words": word_rows,
            }
        )
    intervals = [(m["orig_start_ms"]/1000, m["orig_end_ms"]/1000) for m in mapping]
    available_duration = max((b for _, b in intervals), default=0)
    planned, _ = recovery_windows(source_segments, intervals, duration=available_duration)
    recovery_audit: dict[str, Any] = {"decisions": [], "authority": "machine-asr-only", "publication_ready": False}
    if planned:
        # Use the intact camera-1 waveform, not the silence-cut output. Cached
        # prepare audio saves a second full decode in normal desktop jobs.
        audio = recovery_audio if recovery_audio is not None else AudioSegment.from_file(cam1_path).set_channels(1).set_frame_rate(16000)
        samples = np.asarray(audio.get_array_of_samples(), dtype=np.float32) / float(1 << (8*audio.sample_width-1))
        def re_recognize(start: float, end: float) -> list[dict[str, Any]]:
            iterator, _ = model.transcribe(samples[int(start*16000):int(end*16000)], language="fa",
                beam_size=5, best_of=1, temperature=0.0, condition_on_previous_text=False,
                word_timestamps=True, vad_filter=False, initial_prompt=None)
            return [{"text": s.text, "start": start+s.start, "end": start+s.end, "words": [
                {"word": w.word.strip(), "start": start+w.start, "end": start+w.end,
                 "probability": w.probability, "timing_origin": "asr-word-timestamps"}
                for w in (s.words or []) if w.end > w.start]} for s in iterator]
        source_segments, recovery_audit = recover_alignment(source_segments, intervals, duration=len(audio)/1000,
            transcribe_window=re_recognize, progress=lambda i, total, a, b: report_stage(
                "analyze", 43, f"بازشناسی موضعی {i}/{total} · صدای اصلی {a:.1f} تا {b:.1f} ثانیه"))
        del samples
        print("ASR_ALIGNMENT_RECOVERY accepted=" + str(sum(d["status"] == "accepted-machine-retranscription"
            for d in recovery_audit["decisions"])) + " attempted=" + str(len(recovery_audit["decisions"])), flush=True)
    del model
    gc.collect()
    if not source_segments:
        raise RuntimeError("هیچ گفتار قابل‌استفاده‌ای از صدای دوربین اول تشخیص داده نشد.")
    print(
        f"ASR آماده: زبان {getattr(info, 'language', 'fa')}، "
        f"احتمال زبان {float(getattr(info, 'language_probability', 0.0)):.2f}، "
        f"{len(source_segments)} بخش گفتار"
    )

    run_id = str(uuid.uuid4())
    source_words = collect_source_words(source_segments, run_id)
    media_stat = media_path.stat()
    if (media_stat.st_size, media_stat.st_mtime_ns) != (media_before.st_size, media_before.st_mtime_ns):
        raise RuntimeError("Source media changed during transcription; source-word evidence cannot be trusted.")
    media_sha_after = hash_media_content(
        media_path, progress=lambda done, total, elapsed: report_stage(
            "analyze", 44, f"تأیید اثر انگشت پس از ASR: {done}/{total} bytes · {elapsed:.1f}s"),
    )
    if media_sha_after != media_sha_before:
        raise RuntimeError("Source media changed during transcription; content fingerprint mismatch.")
    evidence = {
        "protocol": "hafez-source-word-evidence-v1", "evidence_id": run_id,
        "kind": "original-asr-not-audio-verified", "model_id": primary_model,
        "device": device, "compute_type": compute_type,
        "media_identity": {"path": str(media_path), "size_bytes": media_stat.st_size,
                           "mtime_ns": media_stat.st_mtime_ns,
                           "strength": IDENTITY_STRENGTH, "sha256": media_sha_after},
        "words": source_words,
        "alignment_recovery": recovery_audit,
    }
    if evidence_sink is not None:
        evidence_sink.update(evidence)
    mapped_words = map_source_words(source_words, mapping)
    for word in mapped_words:
        word["media_sha256"] = media_sha_after
    if not mapped_words:
        raise RuntimeError("متن تشخیص داده شد، اما هیچ کلمه‌ای روی Timeline نگاشت نشد.")
    return mapped_words


def prepare_edit(cam1_path: str, cam2_path: str) -> str:
    if not os.path.isfile(cam1_path):
        raise FileNotFoundError(f"فایل دوربین اول پیدا نشد: {cam1_path}")
    if not os.path.isfile(cam2_path):
        raise FileNotFoundError(f"فایل دوربین دوم پیدا نشد: {cam2_path}")

    report_stage("analyze", 5, "بررسی فایل‌ها و مشخصات ویدیو")
    outputs = generate_output_paths(cam1_path)
    cam1_metadata = probe_video(cam1_path)
    cam2_metadata = probe_video(cam2_path)
    fps = float(cam1_metadata["fps"])
    report_stage("analyze", 9, "مشخصات دو دوربین آماده شد")

    report_stage("analyze", 12, "استخراج و آماده‌سازی صدای دو دوربین")
    print("خواندن صدای دو دوربین...")
    cam1_audio_raw = AudioSegment.from_file(cam1_path)
    cam2_audio_raw = AudioSegment.from_file(cam2_path)
    audio_metadata = {
        "cam1": {
            "sample_rate": cam1_audio_raw.frame_rate,
            "channels": cam1_audio_raw.channels,
            "depth": cam1_audio_raw.sample_width * 8,
        },
        "cam2": {
            "sample_rate": cam2_audio_raw.frame_rate,
            "channels": cam2_audio_raw.channels,
            "depth": cam2_audio_raw.sample_width * 8,
        },
    }
    cam1_audio = cam1_audio_raw.set_channels(1).set_frame_rate(16000)
    cam2_audio = cam2_audio_raw.set_channels(1).set_frame_rate(16000)
    del cam1_audio_raw, cam2_audio_raw

    print("سینک دو دوربین با منطق فعلی...")
    offset_ms = find_offset(cam1_audio, cam2_audio)
    print(f"Offset: {offset_ms:.2f} ms")
    report_stage("analyze", 18, "سینک دو دوربین تکمیل شد")

    print("تشخیص سکوت با تنظیمات تأییدشده فعلی...")
    nonsilent_ranges = detect_nonsilent(
        cam1_audio,
        min_silence_len=MIN_SILENCE_MS,
        silence_thresh=SILENCE_THRESHOLD_DB,
    )
    clips, mapping, timeline_frames, silence_cut_policy = build_initial_timeline(
        nonsilent_ranges,
        offset_ms,
        fps,
        len(cam1_audio),
    )
    print(f"SILENCE_CUT_POLICY {silence_cut_policy['id']} "
          f"head_ms={silence_cut_policy['head_ms']} tail_ms={silence_cut_policy['tail_ms']}", flush=True)
    timeline_duration = timeline_frames / fps if fps > 0 else 0.0
    glossary = load_glossary(GLOSSARY_PATH)
    report_stage("analyze", 24, "سکوت‌ها و Timeline اولیه تحلیل شد")

    report_stage("analyze", 28, "پیاده‌سازی گفتار با Whisper در حال اجراست")
    source_evidence: dict[str, Any] = {}
    mapped_words = transcribe_and_map(cam1_path, mapping, glossary, evidence_sink=source_evidence, recovery_audio=cam1_audio)
    if not mapped_words:
        raise RuntimeError("زیرنویس خالی است؛ تدوین برای جلوگیری از خروجی ناقص متوقف شد.")

    report_stage("analyze", 46, "گفتار روی Timeline نگاشت شد")
    boundary_review = assess_word_boundary_gaps(
        clips["cam1"], source_evidence.get("words", []), fps=fps,
        media_identity=source_evidence.get("media_identity", {}), gap_origin="vad_silence",
    )
    # Ordinary ASR grants no restoration authority. Keeps, sync, and intentional
    # downstream cuts remain unchanged; this is evidence for a later review.
    print(f"WORD_BOUNDARY_REVIEW candidates={len(boundary_review['decisions'])} "
          f"review_required={boundary_review['review_required']} restored_frames=0", flush=True)
    review_segments = build_review_segments(mapped_words)
    review_tasks = build_review_tasks(review_segments, timeline_duration, glossary)
    review_prompt = "\n\n".join(
        f"===== {task['task_id']} / {task['task_type']} =====\n{task['prompt']}"
        for task in review_tasks
    )
    Path(outputs["prompt"]).write_text(review_prompt, encoding="utf-8")
    Path(outputs["review_tasks"]).write_text(
        json.dumps({"protocol": "hermes-ai-tasks-v1", "tasks": review_tasks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "version": 5,
        "cam1_path": cam1_path,
        "cam2_path": cam2_path,
        "cam1_metadata": cam1_metadata,
        "cam2_metadata": cam2_metadata,
        "audio_metadata": audio_metadata,
        "fps": fps,
        "offset_ms": offset_ms,
        "timeline_frames": timeline_frames,
        "timeline_duration": timeline_duration,
        "clips": {key: [list(item) for item in values] for key, values in clips.items()},
        "mapping": mapping,
        "silence_cut_policy": silence_cut_policy,
        "review_segments": review_segments,
        "review_tasks": review_tasks,
        "mapped_words": mapped_words,
        "source_word_evidence": source_evidence,
        "caption_evidence": {
            "protocol": CAPTION_EVIDENCE_PROTOCOL,
            "source_evidence_id": source_evidence.get("evidence_id"),
            "clock": declared_xml_clock(fps, *get_timebase_and_ntsc(fps)),
        },
        "word_boundary_review": boundary_review,
        "outputs": outputs,
    }
    Path(outputs["manifest"]).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"MANIFEST_PATH: {outputs['manifest']}")
    print(f"REVIEW_PATH: {outputs['prompt']}")
    print(f"REVIEW_TASKS_PATH: {outputs['review_tasks']}")
    report_stage("analyze", 49, "تحلیل کامل و Manifest پروژه آماده شد")
    return outputs["manifest"]


def _pixel_aspect_label(metadata: dict[str, Any]) -> str:
    numerator = int(metadata.get("sar_num", 1))
    denominator = int(metadata.get("sar_den", 1))
    if numerator == denominator:
        return "square"
    known = {
        (8, 9): "NTSC-CCIR-601/DV",
        (10, 11): "PAL-CCIR-601",
        (32, 27): "HD-(960x720)",
        (40, 33): "HD-(1280x1080)",
    }
    return known.get((numerator, denominator), "square")


def _sequence_xml(
    manifest: dict[str, Any],
    variant_key: str,
    variant: dict[str, Any],
    events: list[dict[str, Any]],
    markers: list[dict[str, Any]],
    master_audio: dict[str, Any] | None,
    graphics: list[dict[str, Any]] | None = None,
) -> tuple[list[str], dict[str, str]]:
    cam1_path = str(manifest["cam1_path"])
    cam2_path = str(manifest["cam2_path"])
    cam1_metadata = manifest["cam1_metadata"]
    cam2_metadata = manifest["cam2_metadata"]
    audio_metadata = manifest["audio_metadata"]
    clips = variant["clips"]
    fps = float(manifest["fps"])
    timeline_frames = int(variant["timeline_frames"])
    timebase, ntsc = get_timebase_and_ntsc(fps)
    rate_tag = f"<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>"

    motion_clips1 = [list(map(int, raw[:4])) for raw in clips["cam1"]]
    motion_clips2 = [list(map(int, raw[:4])) for raw in clips["cam2"]]
    export_progress = {"safe": 92, "tight": 93, "director": 94}.get(variant_key, 92)
    report_stage("finish", export_progress, f"ساخت {variant_key} · حرکت تصویر دوربین اول")
    motion_cam1, backend1 = prepare_track_motion(cam1_path, motion_clips1, events, fps, FACE_MODEL_PATH)
    report_stage("finish", export_progress, f"ساخت {variant_key} · حرکت تصویر دوربین دوم")
    motion_cam2, backend2 = prepare_track_motion(cam2_path, motion_clips2, events, fps, FACE_MODEL_PATH)
    prefix = variant_key.replace(" ", "-")
    name1 = escape(Path(cam1_path).name)
    name2 = escape(Path(cam2_path).name)
    sequence_aspect = _pixel_aspect_label(cam1_metadata)
    lines = [
        "  <sequence>",
        f"    <name>{escape(str(variant['name']))}</name>",
        f"    <duration>{timeline_frames}</duration>",
        f"    {rate_tag}",
        "    <media>",
        "      <video>",
        "        <format>",
        "          <samplecharacteristics>",
        f"            {rate_tag}",
        f"            <width>{int(cam1_metadata['width'])}</width>",
        f"            <height>{int(cam1_metadata['height'])}</height>",
        f"            <pixelaspectratio>{sequence_aspect}</pixelaspectratio>",
        "          </samplecharacteristics>",
        "        </format>",
    ]

    def add_source_track(
        track_clips: list[list[int]],
        source_path: str,
        file_id: str,
        source_metadata: dict[str, Any],
        source_audio: dict[str, Any],
        track_type: str,
        enabled: bool,
        motion_by_clip: dict[int, dict[str, list[Any]]] | None = None,
    ) -> list[str]:
        source_name = escape(Path(source_path).name)
        source_url = escape(path_to_url(source_path))
        track_lines = [
            "        <track>",
            f"          <enabled>{'TRUE' if enabled else 'FALSE'}</enabled>",
            "          <locked>FALSE</locked>",
        ]
        for index, raw_clip in enumerate(track_clips):
            timeline_start, timeline_end, media_in, media_out = map(int, raw_clip[:4])
            # The fifth flag belongs only to the visual camera decision.  Raw
            # camera audio must stay disabled when the camera-1 Voice Master
            # exists, regardless of which visual angle is on screen.
            clip_enabled = enabled
            if track_type == "video" and len(raw_clip) >= 5:
                clip_enabled = bool(raw_clip[4])
            duration = timeline_end - timeline_start
            track_lines.extend(
                [
                    f'          <clipitem id="{prefix}-{track_type}-{file_id}-{index}">',
                    f"            <name>{source_name}</name>",
                    f"            <duration>{duration}</duration>",
                    f"            <enabled>{'TRUE' if clip_enabled else 'FALSE'}</enabled>",
                    f"            <start>{timeline_start}</start>",
                    f"            <end>{timeline_end}</end>",
                    f"            <in>{media_in}</in>",
                    f"            <out>{media_out}</out>",
                    f'            <file id="{prefix}-{file_id}">',
                    f"              <name>{source_name}</name>",
                    f"              <pathurl>{source_url}</pathurl>",
                    f"              <duration>{int(source_metadata.get('frame_count', 0))}</duration>",
                    f"              {rate_tag}",
                    "              <media>",
                    "                <video><samplecharacteristics>",
                    f"                  {rate_tag}",
                    f"                  <width>{int(source_metadata['width'])}</width>",
                    f"                  <height>{int(source_metadata['height'])}</height>",
                    f"                  <pixelaspectratio>{_pixel_aspect_label(source_metadata)}</pixelaspectratio>",
                    "                </samplecharacteristics></video>",
                    "                <audio><samplecharacteristics>",
                    f"                  <depth>{int(source_audio['depth'])}</depth>",
                    f"                  <samplerate>{int(source_audio['sample_rate'])}</samplerate>",
                    "                </samplecharacteristics>",
                    f"                <channelcount>{int(source_audio['channels'])}</channelcount></audio>",
                    "              </media>",
                    "            </file>",
                ]
            )
            if track_type == "video" and motion_by_clip and index in motion_by_clip:
                track_lines.extend(motion_filter_xml(motion_by_clip[index]))
            track_lines.append("          </clipitem>")
        track_lines.append("        </track>")
        return track_lines

    lines.extend(add_source_track(clips["cam1"], cam1_path, "file-1", cam1_metadata, audio_metadata["cam1"], "video", True, motion_cam1))
    lines.extend(add_source_track(clips["cam2"], cam2_path, "file-2", cam2_metadata, audio_metadata["cam2"], "video", True, motion_cam2))
    if graphics:
        # FCP XML cannot carry an editable After Effects MOGRT.  Older builds
        # embedded PNG stand-ins here and could therefore look finished even
        # though Premiere never received a single editable graphic.  Keep an
        # empty disabled guide track for stable V4/V5 indices, then reserve the
        # two real MOGRT tracks for the Premiere Finisher.
        lines.extend(
            [
                "        <track>",
                "          <enabled>FALSE</enabled>",
                "          <locked>FALSE</locked>",
                "        </track>",
            ]
        )
        for _ in range(2):
            lines.extend(
                [
                    "        <track>",
                    "          <enabled>TRUE</enabled>",
                    "          <locked>FALSE</locked>",
                    "        </track>",
                ]
            )
    lines.extend(
        [
            "      </video>",
            "      <audio>",
            "        <format><samplecharacteristics>",
            "          <depth>24</depth>",
            "          <samplerate>48000</samplerate>",
            "        </samplecharacteristics></format>",
        ]
    )
    has_master = bool(master_audio and master_audio.get("output_path")
                      and Path(str(master_audio["output_path"])).is_file())
    lines.extend(add_source_track(clips["cam1"], cam1_path, "file-1", cam1_metadata, audio_metadata["cam1"], "audio", not has_master))
    lines.extend(add_source_track(clips["cam2"], cam2_path, "file-2", cam2_metadata, audio_metadata["cam2"], "audio", False))

    if has_master and master_audio:
        master_path = str(master_audio["output_path"])
        master_name = escape(Path(master_path).name)
        master_url = escape(path_to_url(master_path))
        lines.extend(
            [
                "        <track>",
                "          <enabled>TRUE</enabled>",
                "          <locked>FALSE</locked>",
                f'          <clipitem id="{prefix}-voice-master">',
                f"            <name>{master_name}</name>",
                f"            <duration>{timeline_frames}</duration>",
                "            <enabled>TRUE</enabled>",
                "            <start>0</start>",
                f"            <end>{timeline_frames}</end>",
                "            <in>0</in>",
                f"            <out>{timeline_frames}</out>",
                f'            <file id="{prefix}-voice-master-file">',
                f"              <name>{master_name}</name>",
                f"              <pathurl>{master_url}</pathurl>",
                f"              <duration>{timeline_frames}</duration>",
                f"              {rate_tag}",
                "              <media><audio><samplecharacteristics>",
                f"                <depth>{int(master_audio.get('depth', 24))}</depth>",
                f"                <samplerate>{int(master_audio.get('sample_rate', 48000))}</samplerate>",
                "              </samplecharacteristics>",
                f"              <channelcount>{int(master_audio.get('channels', 1))}</channelcount></audio></media>",
                "            </file>",
                "          </clipitem>",
                "        </track>",
            ]
        )

    # Keep A3 reserved for the untouched dialogue master so SFX is always A4,
    # even when a voice master could not be rendered and camera-1 audio stays active.
    if graphics and not has_master:
        lines.extend(
            [
                "        <track>",
                "          <enabled>TRUE</enabled>",
                "          <locked>FALSE</locked>",
                "        </track>",
            ]
        )

    sfx_cues = [
        dict(graphic["sfx_cue"])
        for graphic in (graphics or [])
        if not graphic.get("review_blocked")
        and isinstance(graphic.get("sfx_cue"), dict)
        and Path(str(graphic["sfx_cue"].get("asset_path", ""))).is_file()
    ]
    if sfx_cues:
        sfx_lines = [
            "        <track>",
            "          <enabled>TRUE</enabled>",
            "          <locked>FALSE</locked>",
        ]
        for index, cue in enumerate(sfx_cues):
            asset_path = str(cue["asset_path"])
            asset_name = escape(Path(asset_path).name)
            asset_url = escape(path_to_url(asset_path))
            start = max(0, int(cue.get("start_frame", round(float(cue.get("start", 0.0)) * fps))))
            asset_frames = max(1, int(round(float(cue.get("duration", 2.0)) * fps)))
            end = min(timeline_frames, start + asset_frames)
            if end <= start:
                continue
            duration_frames = end - start
            sample_rate = int(cue.get("sample_rate", 44_100))
            channels = int(cue.get("channels", 2))
            sfx_lines.extend(
                [
                    f'          <clipitem id="{prefix}-entry-sfx-{index}">',
                    f"            <name>{asset_name}</name>",
                    f"            <duration>{duration_frames}</duration>",
                    "            <enabled>TRUE</enabled>",
                    f"            <start>{start}</start>",
                    f"            <end>{end}</end>",
                    "            <in>0</in>",
                    f"            <out>{duration_frames}</out>",
                    f'            <file id="{prefix}-entry-sfx-file-{index}">',
                    f"              <name>{asset_name}</name>",
                    f"              <pathurl>{asset_url}</pathurl>",
                    f"              <duration>{asset_frames}</duration>",
                    f"              {rate_tag}",
                    "              <media><audio><samplecharacteristics>",
                    "                <depth>16</depth>",
                    f"                <samplerate>{sample_rate}</samplerate>",
                    "              </samplecharacteristics>",
                    f"              <channelcount>{channels}</channelcount></audio></media>",
                    "            </file>",
                    "            <sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>",
                    "          </clipitem>",
                ]
            )
        sfx_lines.append("        </track>")
        lines.extend(sfx_lines)
    lines.extend(["      </audio>", "    </media>"])
    for marker in markers:
        marker_in = max(0, int(round(float(marker["start"]) * fps)))
        marker_out = min(timeline_frames, max(marker_in + 1, int(round(float(marker.get("end", marker["start"])) * fps))))
        lines.extend(
            [
                "    <marker>",
                f"      <name>{escape(str(marker['type']))}</name>",
                f"      <in>{marker_in}</in>",
                f"      <out>{marker_out}</out>",
                f"      <comment>{escape(str(marker.get('comment', '')))}</comment>",
                "    </marker>",
            ]
        )
    lines.append("  </sequence>")
    return lines, {"cam1": backend1, "cam2": backend2}


def generate_xml(
    manifest: dict[str, Any],
    variants: dict[str, dict[str, Any]],
    events_by_variant: dict[str, list[dict[str, Any]]],
    markers_by_variant: dict[str, list[dict[str, Any]]],
    audio_reports: dict[str, dict[str, Any]],
    director_variant: dict[str, Any] | None = None,
    director_events: list[dict[str, Any]] | None = None,
    director_markers: list[dict[str, Any]] | None = None,
    director_graphics: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, str]]:
    lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        "<!DOCTYPE xmeml>",
        '<xmeml version="5">',
        "  <importoptions>",
        "    <filterincludemarkers>TRUE</filterincludemarkers>",
        "    <filterincludeeffects>TRUE</filterincludeeffects>",
        "    <filterincludesequencesettings>TRUE</filterincludesequencesettings>",
        "  </importoptions>",
    ]
    backends: dict[str, dict[str, str]] = {}
    for key in ("safe", "tight"):
        sequence_lines, backend = _sequence_xml(
            manifest,
            key,
            variants[key],
            events_by_variant.get(key, []),
            markers_by_variant.get(key, []),
            audio_reports.get(key),
        )
        lines.extend(sequence_lines)
        backends[key] = backend
    if director_variant is not None:
        sequence_lines, backend = _sequence_xml(
            manifest,
            "director",
            director_variant,
            director_events or [],
            director_markers or [],
            audio_reports.get("tight"),
            director_graphics or [],
        )
        lines.extend(sequence_lines)
        backends["director"] = backend
    lines.append("</xmeml>")
    Path(manifest["outputs"]["xml"]).write_text("\n".join(lines), encoding="utf-8")
    return backends


def _timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def write_youtube_package(
    path: str,
    youtube: dict[str, Any],
    segments: list[dict[str, Any]],
    timeline_mapping: list[dict[str, float]],
    markers: list[dict[str, Any]],
    *,
    sequence_name: str = "unspecified",
    timeline_duration: float | None = None,
) -> None:
    by_id = {int(item["id"]): item for item in segments}
    titles = [str(item).strip() for item in youtube.get("titles", []) if str(item).strip()][:5]
    thumbnails = [str(item).strip() for item in youtube.get("thumbnail_texts", []) if str(item).strip()][:5]
    chapters: list[tuple[float, str]] = [(0.0, "شروع")]
    for raw in youtube.get("chapters", []):
        if not isinstance(raw, dict):
            continue
        try:
            segment = by_id[int(raw.get("segment_id"))]
        except (KeyError, TypeError, ValueError):
            continue
        mapped = remap_time(float(segment["start"]), timeline_mapping)
        title = str(raw.get("title", "")).strip()
        if mapped is not None and 0 <= mapped < (timeline_duration if timeline_duration is not None else float("inf")) and title and all(abs(mapped - old[0]) >= 15 for old in chapters):
            chapters.append((mapped, title[:100]))
    for marker in markers:
        if marker["type"] == "CHAPTER" and 0 <= marker["start"] < (timeline_duration if timeline_duration is not None else float("inf")) and all(abs(marker["start"] - old[0]) >= 15 for old in chapters):
            chapters.append((float(marker["start"]), str(marker.get("comment") or "بخش جدید")[:100]))
    lines = [
        "# پیش‌نویس بسته یوتیوب Hafez Studio", "",
        "وضعیت: نیازمند بازبینی؛ این فایل تأیید آماده‌بودن برای انتشار نیست.",
        f"سکانس مرجع زمان فصل‌ها: {sequence_name}",
        "عنوان‌ها، ادعاها، عددها و لینک فایل‌های هدیه را پیش از انتشار با ویدیوی نهایی بررسی کنید.",
        "زمان فصل‌ها پس از هر تغییر برش باید دوباره تولید شود.", "", "## عنوان‌های پیشنهادی", "",
    ]
    lines.extend(f"- {title}" for title in titles or ["عنوان پیشنهادی توسط AI تولید نشد."])
    lines.extend(["", "## توضیحات", "", str(youtube.get("description", "")).strip() or "—", "", "## Chapterها", ""])
    lines.extend(f"{_timestamp(moment)} {title}" for moment, title in sorted(chapters))
    lines.extend(["", "## کامنت پین‌شده", "", str(youtube.get("pinned_comment", "")).strip() or "—", "", "## متن Thumbnail", ""])
    lines.extend(f"- {text}" for text in thumbnails or ["—"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_director_youtube_package(
    path: str,
    youtube: dict[str, Any],
    segments: list[dict[str, Any]],
    director_variant: dict[str, Any],
    director_markers: list[dict[str, Any]],
) -> None:
    # Director inherits Tight's final clock. Never substitute Safe's mapping or markers.
    write_youtube_package(
        path, youtube, segments, director_variant["mapping"], director_markers,
        sequence_name=str(director_variant["name"]),
        timeline_duration=float(director_variant["timeline_duration"]),
    )


def write_edit_notes(
    path: str,
    markers_by_variant: dict[str, list[dict[str, Any]]],
    events_by_variant: dict[str, list[dict[str, Any]]],
    ai_review: dict[str, Any],
    audio_reports: dict[str, dict[str, Any]],
    warnings: list[str],
    camera_schedule: list[dict[str, Any]] | None = None,
    director_events: list[dict[str, Any]] | None = None,
    graphics: list[dict[str, Any]] | None = None,
) -> None:
    """Write a human-readable backup of every timeline recommendation."""
    lines = [
        "# راهنمای تدوین Hermes",
        "",
        "## وضعیت تحلیل هوشمند",
        "",
        f"- پروتکل: {ai_review.get('mode', 'unknown')}",
    ]
    for task in ai_review.get("tasks", []):
        state = "موفق" if task.get("valid") else "fallback قطعی"
        lines.append(
            f"- {task.get('task_id', 'task')}: {state} — {task.get('backend', 'unknown')}"
        )

    for key, title in (("safe", "Safe Cut"), ("tight", "Tight Cut")):
        lines.extend(["", f"## Markerهای {title}", ""])
        markers = markers_by_variant.get(key, [])
        if markers:
            for marker in markers:
                lines.append(
                    f"- {_timestamp(float(marker['start']))} [{marker['type']}] {marker.get('comment', '')}"
                )
        else:
            lines.append("- مارکری تولید نشد.")
        lines.extend(["", f"## Punch-inهای {title}", ""])
        events = events_by_variant.get(key, [])
        if events:
            for event in events:
                lines.append(
                    f"- {_timestamp(float(event['start']))} تا {_timestamp(float(event['end']))}: "
                    f"{event.get('kind', 'important')} (score={event.get('score', 0)})"
                )
        else:
            lines.append("- Punch-in معنایی تولید نشد.")

    camera_schedule = camera_schedule or []
    director_events = director_events or []
    graphics = graphics or []
    blocked_graphics = [g for g in graphics if g.get("review_blocked") or g.get("needs_manual_copy")
                        or g.get("layout", {}).get("collision_free") is False]
    eligible_graphics = [g for g in graphics if g not in blocked_graphics]
    lines.extend(
        [
            "",
            "## 03 - Hafez Director Cut",
            "",
            f"- تعداد شات‌های انحصاری دوربین: {len(camera_schedule)}",
            f"- تعداد Punch-in حرفه‌ای: {len(director_events)}",
            f"- تعداد پیشنهادهای گرافیکی: {len(graphics)}",
            f"- آمادهٔ درخواست درج MOGRT: {len(eligible_graphics)}؛ مسدود/نیازمند بازبینی: {len(blocked_graphics)}",
            "- این گزارشِ برنامهٔ تدوین است؛ تعداد درج واقعی فقط با رسید و بازبینی داخل Premiere تأیید می‌شود.",
            "- در هر شات فقط یکی از دوربین‌ها Enabled است؛ دوربین دیگر Disabled است.",
            "- PNG پیش‌نمایش، جایگزین MOGRT روی تایم‌لاین نیست؛ ترک و کنترل‌های هر قالب در Premiere Plan مشخص است.",
            "",
            "### Camera Cut Sheet",
            "",
            "| شروع | پایان | دوربین فعال | دستور |",
            "|---:|---:|:---:|---|",
        ]
    )
    for shot in camera_schedule:
        lines.append(
            f"| {_timestamp(float(shot['start']))} | {_timestamp(float(shot['end']))} | "
            f"{str(shot['camera']).upper()} | دوربین دیگر Disabled؛ {str(shot.get('reason', ''))[:90]} |"
        )
    lines.extend(
        [
            "",
            "### Punch-in Sheet",
            "",
            "| زمان | مدت | Scale | دلیل |",
            "|---:|---:|---:|---|",
        ]
    )
    for event in director_events:
        lines.append(
            f"| {_timestamp(float(event['start']))} | {float(event['end']) - float(event['start']):.1f}s | "
            f"{float(event.get('scale', 112)):.0f}% | {event.get('kind', 'important')}؛ ورود و خروج نرم 8 فریم |"
        )
    lines.extend(
        [
            "",
            "### Text & Graphics Sheet",
            "",
            "| زمان | متن نمایشی | Template | مدت | Font | وضعیت |",
            "|---:|---|---|---:|---|---|",
        ]
    )
    for graphic in graphics:
        controls = graphic.get("controls", {})
        display = " / ".join(str(controls[slot]) for slot in ("Title", "Body") if controls.get(slot))
        safe_text = str(display or graphic.get("text", "")).replace("|", "-").replace("\r", " ").replace("\n", " ")
        status = "مسدود — " + str(graphic.get("review_blocked_reason", "بازبینی متن/جای‌گذاری لازم است")) if graphic in blocked_graphics else "آمادهٔ درخواست درج؛ بازبینی Native لازم است"
        status = status.replace("|", "-").replace("\r", " ").replace("\n", " ")
        lines.append(
            f"| {_timestamp(float(graphic['start']))} | {safe_text} | {graphic.get('template', '')} | "
            f"{float(graphic.get('duration', 0)):.1f}s | {graphic.get('font_family', '')} | {status} |"
        )

    lines.extend(
        [
            "",
            "## صدا",
            "",
            "- منبع گفتار: صدای میکروفون دوربین اول؛ دوربین دوم بی‌صداست.",
        ]
    )
    for key, report in audio_reports.items():
        if report.get("source_preserved"):
            lines.append(f"- {key}: صدای اصلی A1 فعال و دست‌نخورده؛ بدون EQ، کمپرسور یا Ducking روی گفتار.")
            continue
        lines.append(
            f"- {key}: {report.get('processing_backend', 'unknown')}، "
            f"هدف {report.get('target_lufs', '?')} LUFS، True Peak {report.get('target_true_peak_db', '?')} dB"
        )
    if warnings:
        lines.extend(["", "## هشدارها", ""])
        lines.append(f"- تعداد هشدارهای محافظتی: {len(warnings)}")
        lines.extend(f"- {warning}" for warning in warnings[:12])
        if len(warnings) > 12:
            lines.append(f"- … {len(warnings) - 12} هشدار مشابه دیگر در فایل audit ثبت شده است.")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def finalize_edit(manifest_path: str, review_path: str | None = None) -> tuple[str, str]:
    glass_review = os.environ.get('HERMES_STYLE_PACK','').strip().lower() == 'glass'
    if glass_review and os.environ.get('HERMES_GLASS_REVIEW_MODE') != '1':
        raise ValueError('Glass requires explicit isolated review mode; no legacy fallback')
    report_stage("direct", 50, "ساخت تصمیم‌های تدوین و روایت")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    caption_source, caption_source_audit = verify_fresh_caption_source(
        manifest, timebase=get_timebase_and_ntsc(float(manifest["fps"]))[0],
        ntsc=get_timebase_and_ntsc(float(manifest["fps"]))[1],
        progress=lambda done, total, elapsed: report_stage(
            "direct", 50, f"اعتبارسنجی منبع زیرنویس: {done}/{total} bytes · {elapsed:.1f}s"),
    )
    words = manifest.get("mapped_words", [])
    segments = restore_source_segments(manifest.get("review_segments", []), words)
    outputs = manifest.setdefault("outputs", {})
    xml_path = str(outputs.get("xml", ""))
    base = xml_path[:-4] if xml_path.lower().endswith(".xml") else str(Path(manifest_path).with_suffix(""))
    outputs.setdefault("edit_notes", base + ".edit-notes.md")
    outputs.setdefault("review_tasks", base + ".review-tasks.json")
    outputs.setdefault("resolved_review", base + ".resolved-review.json")
    outputs.setdefault("professional_plan", base + ".premiere-plan.json")
    outputs.setdefault("graphics_dir", base + ".graphics")
    saved_tasks = manifest.get('review_tasks')
    if glass_review and any(t.get('style_pack') != 'glass' for t in (saved_tasks or []) if t.get('task_type') == 'editor'):
        saved_tasks = None
    expected_tasks = saved_tasks or build_review_tasks(
        segments,
        float(manifest.get("timeline_duration", 0.0)),
        load_glossary(GLOSSARY_PATH),
    )
    raw_response: Any = None
    if review_path and Path(review_path).exists():
        response_text = Path(review_path).read_text(encoding="utf-8-sig")
        try:
            raw_response = json.loads(response_text)
        except json.JSONDecodeError:
            raw_response = response_text

    resolved_response, ai_review, task_warnings = resolve_review_tasks(
        raw_response,
        expected_tasks,
        checkpoint_path=base + ".ai-checkpoint.json",
    )
    report_stage("direct", 60, "بازبینی متن و تصمیم‌های محلی تکمیل شد")
    Path(outputs["resolved_review"]).write_text(
        json.dumps(resolved_response, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    corrections: dict[int, str] = {}
    raw_events: list[dict[str, Any]] = []
    raw_edits: list[dict[str, Any]] = []
    raw_markers: list[dict[str, Any]] = []
    youtube: dict[str, Any] = {}
    warnings: list[str] = list(task_warnings)
    subtitle_review: list[dict[str, Any]] = []
    if resolved_response:
        corrections, raw_events, raw_edits, raw_markers, youtube, parse_warnings = parse_full_review(
            resolved_response, segments, review_metadata=subtitle_review
        )
        warnings.extend(parse_warnings)
    strict_subtitles = source_faithful_subtitles()
    rejected_subtitles = sum(item["status"] == "draft-review-required" for item in subtitle_review)
    if strict_subtitles:
        print(f"SUBTITLE_COPY_REVIEW policy=source-faithful accepted_formatting={len(corrections)} rejected={rejected_subtitles} status=draft-source-asr", flush=True)
    if not raw_events:
        raw_events = suggest_local_events(segments)
    if not raw_markers:
        raw_markers.extend(
            suggest_local_markers(segments, float(manifest.get("timeline_duration", 0.0)))
        )
    for marker in raw_markers:
        if isinstance(marker, dict):
            marker["comment"] = correct_known_terms(marker.get("comment", ""))
    youtube = ensure_youtube_package(youtube, segments)

    raw_edits.extend(detect_repeated_speech_edits(segments, words))
    edits, edit_warnings = validate_edit_decisions(raw_edits, segments, words)
    edits, retake_warnings = guard_retained_retake(edits, words)
    edit_warnings.extend(retake_warnings)
    edits.extend(detect_short_setup_prefix(manifest["clips"]["cam1"], words, float(manifest["fps"])))
    warnings.extend(edit_warnings)
    for edit in edits:
        if edit["action"] == "review" and edit["confidence"] >= 0.70:
            raw_markers.append(
                {
                    "segment_id": edit["segment_id"],
                    "type": "CHECK",
                    "confidence": edit["confidence"],
                    "comment": edit["reason"] or "این بخش نیاز به تصمیم دستی دارد.",
                }
            )
    markers = validate_markers(raw_markers, segments)
    markers, marker_binding_warnings = bind_graphic_markers_to_source(markers, segments, words)
    warnings.extend(marker_binding_warnings)
    base_events = select_events(raw_events, segments, float(manifest.get("timeline_duration", 0.0)))
    variants = build_variants(
        manifest["clips"],
        edits,
        float(manifest["fps"]),
        float(manifest.get("timeline_duration", 0.0)),
    )
    report_stage("direct", 61, "نسخه‌های Safe و Tight تدوین شدند")
    corrected_segments = [
        {**segment, "text": corrections.get(int(segment["id"]), str(segment.get("text", "")))}
        for segment in segments
    ]
    variant_segments: dict[str, list[dict[str, Any]]] = {}
    events_by_variant: dict[str, list[dict[str, Any]]] = {}
    markers_by_variant: dict[str, list[dict[str, Any]]] = {}
    for key in ("safe", "tight"):
        mapping = variants[key]["mapping"]
        variant_segments[key] = remap_segments(corrected_segments, mapping, edits, key)
        events_by_variant[key] = remap_timed_items(base_events, mapping)
        markers_by_variant[key] = remap_timed_items(markers, mapping)

    director_events = list(events_by_variant["tight"])
    camera_schedule = build_camera_schedule(
        variant_segments["tight"],
        float(variants["tight"]["timeline_duration"]),
        markers_by_variant["tight"],
    )
    report_stage("direct", 62, "ریتم دوربین و Punch-inها انتخاب شد")
    director_variant = {
        **variants["tight"],
        "name": "03 - Hafez Director Cut",
        "clips": {
            "cam1": split_track_for_camera(
                variants["tight"]["clips"]["cam1"], camera_schedule, float(manifest["fps"]), "cam1"
            ),
            "cam2": split_track_for_camera(
                variants["tight"]["clips"]["cam2"], camera_schedule, float(manifest["fps"]), "cam2"
            ),
        },
    }
    if glass_review:
        from glass_finalize import finalize_review
        report_stage('design',65,'ساخت مستقل Glass؛ بدون تولید گرافیک قدیمی')
        result = finalize_review(manifest_path=manifest_path,manifest=manifest,
                                 director_variant=director_variant,events=director_events,
                                 camera_schedule=camera_schedule,markers=raw_markers,
                                 caption_source=caption_source,sequence_builder=_sequence_xml)
        report_stage('finish',98,'بستهٔ Glass ساخته شد؛ ورود به Premiere و بازبینی لازم است')
        return result
    report_stage("design", 65, "انتخاب Rule-Based المان‌های موشن")
    family_history_path = Path(outputs["professional_plan"]).parent / ".hafez-curator-history.json"
    graphic_cues = build_graphic_cues(
        variant_segments["tight"],
        float(variants["tight"]["timeline_duration"]),
        markers_by_variant["tight"],
        fps=float(manifest["fps"]),
        family_history=load_template_family_history(family_history_path) or load_template_family_history(),
        word_context=variant_caption_context(caption_source, variants["tight"]["clips"]["cam1"]),
    )
    report_stage("design", 69, "Templateها و متن‌های مهم انتخاب شدند")
    report_stage("design", 71, "ردیابی چندفریمی سوژه و Safe Placement")
    raw_graphic_cues = graphic_cues
    graphic_cues, graphic_face_backend = apply_face_safe_layout(
        graphic_cues,
        video_path=str(manifest["cam1_path"]),
        clips=director_variant["clips"]["cam1"],
        fps=float(manifest["fps"]),
        width=int(manifest["cam1_metadata"]["width"]),
        height=int(manifest["cam1_metadata"]["height"]),
        secondary_video_path=str(manifest["cam2_path"]),
        secondary_clips=director_variant["clips"]["cam2"],
        motion_events=director_events,
    )
    graphic_cues = guard_automatic_graphic_copy(graphic_cues)
    report_stage("design", 73, "هماهنگی فضای موشن با دوربین و حذف زوم‌های مزاحم")
    original_camera_schedule, original_director_events = camera_schedule, director_events
    original_graphic_cues, original_graphic_backend = graphic_cues, graphic_face_backend
    camera_schedule, director_events, graphic_framing_audit = coordinate_graphic_framing(
        raw_graphic_cues, graphic_cues, camera_schedule, director_events,
        paths={"cam1": str(manifest["cam1_path"]), "cam2": str(manifest["cam2_path"])},
        clips=variants["tight"]["clips"], fps=float(manifest["fps"]),
        width=int(manifest["cam1_metadata"]["width"]), height=int(manifest["cam1_metadata"]["height"]),
    )
    if graphic_framing_audit["changes"]:
        director_variant["clips"] = {
            camera: split_track_for_camera(variants["tight"]["clips"][camera], camera_schedule, float(manifest["fps"]), camera)
            for camera in ("cam1", "cam2")
        }
        graphic_cues, graphic_face_backend = apply_face_safe_layout(
            raw_graphic_cues, video_path=str(manifest["cam1_path"]), clips=director_variant["clips"]["cam1"],
            fps=float(manifest["fps"]), width=int(manifest["cam1_metadata"]["width"]),
            height=int(manifest["cam1_metadata"]["height"]), secondary_video_path=str(manifest["cam2_path"]),
            secondary_clips=director_variant["clips"]["cam2"], motion_events=director_events,
        )
        graphic_cues = guard_automatic_graphic_copy(graphic_cues)
        expected_ids = {c["id"] for c in original_graphic_cues if not c.get("review_blocked")}
        expected_ids.update(c["id"] for c in graphic_framing_audit["changes"])
        final_ids = {c["id"] for c in graphic_cues if not c.get("review_blocked")}
        if not expected_ids.issubset(final_ids):
            # Atomic rollback: candidate-angle evidence cannot approve a
            # different actual timeline after splitting/rounding/other cues.
            camera_schedule, director_events = original_camera_schedule, original_director_events
            graphic_cues, graphic_face_backend = original_graphic_cues, original_graphic_backend
            director_variant["clips"] = {
                camera: split_track_for_camera(variants["tight"]["clips"][camera], camera_schedule, float(manifest["fps"]), camera)
                for camera in ("cam1", "cam2")
            }
            graphic_framing_audit["status"] = "rolled-back-final-visible-frame-check"
            graphic_framing_audit["unqualified_ids"] = sorted(expected_ids - final_ids)
        else:
            graphic_framing_audit["status"] = "final-visible-source-frames-rechecked"
    manifest["graphic_framing_audit"] = graphic_framing_audit
    report_stage("design", 76, "کنترل جانمایی و مجوز نمایش متن موشن‌ها تکمیل شد")
    graphics = render_graphic_assets(
        graphic_cues,
        outputs["graphics_dir"],
        int(manifest["cam1_metadata"]["width"]),
        int(manifest["cam1_metadata"]["height"]),
    )
    report_stage("design", 81, "موشن‌ها، SFX و Assetهای قابل واردکردن آماده شد")
    director_markers = sorted(
        list(markers_by_variant["tight"])
        + build_action_markers(director_events, camera_schedule, graphics),
        key=lambda item: (float(item["start"]), str(item.get("type", ""))),
    )

    report_stage("finish", 83, "ساخت زیرنویس‌های Safe و Tight")
    caption_layout_audits: dict[str, dict[str, Any]] = {"safe": {}, "tight": {}}
    safe_cues = build_srt_cues(
        variant_segments["safe"], caption_context=variant_caption_context(caption_source, variants["safe"]["clips"]["cam1"]),
        layout_audit=caption_layout_audits["safe"],
    )
    tight_cues = build_srt_cues(
        variant_segments["tight"], caption_context=variant_caption_context(caption_source, variants["tight"]["clips"]["cam1"]),
        layout_audit=caption_layout_audits["tight"],
    )
    # Fresh word timing supersedes the old character-weighted display timing.
    # It changes only caption grouping/times, never audio, cuts, or lexical copy.
    if caption_source is not None:
        for key in ("safe", "tight"):
            try:
                timed, timing_audit = build_timeline_word_cues(
                    variant_caption_context(caption_source, variants[key]["clips"]["cam1"]))
                if not timed:
                    raise ValueError("No retained word captions")
                caption_layout_audits[key] = timing_audit
                if key == "safe":
                    safe_cues = timed
                else:
                    tight_cues = timed
            except (ValueError, KeyError, TypeError, OverflowError) as error:
                caption_layout_audits[key]["word_timing_fallback"] = type(error).__name__ + ": " + str(error)
    write_srt(manifest["outputs"]["safe_srt"], safe_cues)
    write_srt(manifest["outputs"]["tight_srt"], tight_cues)

    report_stage("finish", 86, "آماده‌سازی صدای اصلی دوربین اول")
    audio_reports: dict[str, dict[str, Any]] = {}
    for key in ("safe", "tight"):
        if os.environ.get("HERMES_PRESERVE_CAMERA1_AUDIO", "1") == "1":
            audio_reports[key] = {"source_role": "camera1_external_microphone", "processing": "none", "source_preserved": True}
            continue
        try:
            audio_reports[key] = build_voice_master(
                str(manifest["cam1_path"]),
                variants[key]["clips"]["cam1"],
                float(manifest["fps"]),
                str(manifest["outputs"][f"{key}_audio"]),
            )
        except Exception as error:
            warnings.append(f"مسترینگ صدای {key} انجام نشد و صدای اصلی فعال می‌ماند: {error}")

    report_stage("finish", 90, "مسیرهای صوتی و صدای گوینده آماده شد")
    report_stage("finish", 92, "ساخت Premiere XML و Timeline نهایی")
    backends = generate_xml(
        manifest,
        variants,
        events_by_variant,
        markers_by_variant,
        audio_reports,
        director_variant,
        director_events,
        director_markers,
        graphics,
    )
    write_professional_plan(
        outputs["professional_plan"],
        sequence_name="03 - Hafez Director Cut",
        fps=float(manifest["fps"]),
        camera_schedule=camera_schedule,
        events=director_events,
        graphics=graphics,
        history_path=family_history_path,
    )
    report_stage("finish", 96, "برنامهٔ Premiere/MOGRT و بستهٔ YouTube آماده شد")
    write_director_youtube_package(manifest["outputs"]["youtube"], youtube, segments, director_variant, director_markers)
    write_edit_notes(
        manifest["outputs"]["edit_notes"],
        markers_by_variant,
        events_by_variant,
        ai_review,
        audio_reports,
        warnings,
        camera_schedule,
        director_events,
        graphics,
    )

    audit = {
        "ai_review": ai_review,
        "corrections_accepted": len(corrections),
        "subtitle_review": {
            "policy": "source-faithful" if strict_subtitles else "experimental-grounded-summary",
            "status": "draft-source-asr-not-audio-verified" if strict_subtitles else "experimental-model-review",
            "publication_ready": False,
            "rejected_corrections": rejected_subtitles,
            "source_unverified_segment_ids": [int(item["id"]) for item in segments if item.get("source_text_provenance") == "legacy-segment-source-unverified"],
            "decisions": subtitle_review,
            "caption_source": caption_source_audit,
            "caption_layout": caption_layout_audits,
        },
        "edits": edits,
        "variants": {
            key: {
                "duration": variants[key]["timeline_duration"],
                "removed_seconds": variants[key]["removed_seconds"],
                "subtitle_cues": len(safe_cues if key == "safe" else tight_cues),
                "semantic_punches": events_by_variant[key],
                "markers": markers_by_variant[key],
            }
            for key in ("safe", "tight")
        },
        "audio": audio_reports,
        "warnings": warnings,
        "face_detector": {**backends, "graphics": graphic_face_backend},
        "professional": {
            "graphic_framing": graphic_framing_audit,
            "sequence": "03 - Hafez Director Cut",
            "camera_shots": camera_schedule,
            "camera_switches": max(0, len(camera_schedule) - 1),
            "punch_ins": director_events,
            "graphics": graphics,
            "plan_path": outputs["professional_plan"],
        },
    }
    Path(manifest["outputs"]["audit"]).write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    report_stage("finish", 98, "کنترل کیفیت و Audit پروژه تکمیل شد")
    for warning in warnings:
        print(f"هشدار: {warning}")
    print(f"Rough Cut ایمن: {variants['safe']['removed_seconds']:.2f} ثانیه حذف")
    print(f"Rough Cut فشرده: {variants['tight']['removed_seconds']:.2f} ثانیه حذف")
    print(f"فایل پریمیر ساخته شد: {manifest['outputs']['xml']}")
    print(f"فایل زیرنویس Safe ساخته شد: {manifest['outputs']['safe_srt']}")
    print(f"فایل زیرنویس Tight ساخته شد: {manifest['outputs']['tight_srt']}")
    print(f"بسته یوتیوب ساخته شد: {manifest['outputs']['youtube']}")
    print(f"راهنمای تدوین ساخته شد: {manifest['outputs']['edit_notes']}")
    print(f"برنامه حرفه‌ای Premiere ساخته شد: {manifest['outputs']['professional_plan']}")
    if audio_reports.get("safe", {}).get("output_path"):
        print(f"مستر صدای Safe ساخته شد: {manifest['outputs']['safe_audio']}")
    if audio_reports.get("tight", {}).get("output_path"):
        print(f"مستر صدای Tight ساخته شد: {manifest['outputs']['tight_audio']}")
    return str(manifest["outputs"]["xml"]), str(manifest["outputs"]["safe_srt"])


def main() -> int:
    try:
        if len(sys.argv) >= 2 and sys.argv[1] == "--prepare":
            if len(sys.argv) != 4:
                raise ValueError("Usage: autocut.py --prepare cam1.mp4 cam2.mp4")
            prepare_edit(sys.argv[2], sys.argv[3])
            return 0
        if len(sys.argv) >= 2 and sys.argv[1] == "--finalize":
            if len(sys.argv) not in (3, 4):
                raise ValueError("Usage: autocut.py --finalize manifest.json [review.json]")
            finalize_edit(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
            return 0
        if len(sys.argv) != 3:
            raise ValueError("Usage: autocut.py cam1.mp4 cam2.mp4")

        manifest_path = prepare_edit(sys.argv[1], sys.argv[2])
        finalize_edit(manifest_path)
        return 0
    except Exception as error:
        print(f"خطای اجرای تدوین: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
