"""Hafez Studio standalone command-line entrypoint."""

from __future__ import annotations

import argparse
import ctypes
import importlib
import json
import math
import os
import platform
import sys
from pathlib import Path
from fractions import Fraction
from typing import Any
from xml.etree import ElementTree


def _configure_utf8_stdio() -> None:
    """Keep Persian progress/error messages safe on legacy Windows code pages."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (OSError, ValueError):
                # Electron also sets PYTHONIOENCODING, so a non-reconfigurable
                # host stream can safely fall back to the process environment.
                pass


_configure_utf8_stdio()


PACKAGE_DIR = Path(__file__).resolve().parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from runtime_paths import (  # noqa: E402
    adobe_apps,
    adobe_mogrt_root,
    config_path,
    default_output_root,
    face_model_path,
    body_model_path,
    find_executable,
    font_candidates,
    persian_model_path,
    studio_root,
    user_data_root,
)


def _json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _windows_cuda_math_ready() -> bool:
    if os.name != "nt":
        return True
    try:
        ctypes.WinDLL("cublas64_12.dll")
        ctypes.WinDLL("cublasLt64_12.dll")
        return True
    except OSError:
        return False


def _probe_asr_runtime() -> dict[str, Any]:
    """Verify the portable CTranslate2 speech backend without loading a model."""
    faster_whisper = importlib.import_module("faster_whisper")
    ctranslate2 = importlib.import_module("ctranslate2")
    whisper_model = getattr(faster_whisper, "WhisperModel")
    cuda_devices = int(ctranslate2.get_cuda_device_count())
    cuda_runtime_ready = cuda_devices > 0 and _windows_cuda_math_ready()
    return {
        "ok": True,
        "backend": "faster-whisper-ctranslate2",
        "fasterWhisper": str(getattr(faster_whisper, "__version__", "bundled")),
        "ctranslate2": str(getattr(ctranslate2, "__version__", "bundled")),
        "modelClass": whisper_model.__name__,
        "cudaDevices": cuda_devices,
        "cudaRuntimeReady": cuda_runtime_ready,
        "cudaStatus": "ready" if cuda_runtime_ready else "cpu-fallback",
    }


def _import_autocut() -> Any:
    _probe_asr_runtime()
    return importlib.import_module("autocut")


def doctor(as_json: bool = False) -> int:
    apps = adobe_apps()
    fonts = [str(path) for path in font_candidates() if path.exists()]
    try:
        asr_report = _probe_asr_runtime()
    except Exception as error:
        asr_report = {"ok": False, "error": f"{type(error).__name__}: {error}"}
    report = {
        "ok": True,
        "platform": platform.platform(),
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "adobe": {
            "premiere": bool(apps["premiere"] and apps["premiere"].exists()),
            "afterEffects": bool(apps["afterEffects"] and apps["afterEffects"].exists()),
        },
        "tools": {
            "ffmpeg": bool(find_executable(("ffmpeg",))),
            "ffprobe": bool(find_executable(("ffprobe",))),
        },
        "assets": {
            "mogrtRoot": str(adobe_mogrt_root()),
            "mogrtRootExists": adobe_mogrt_root().exists(),
            "faceModel": str(face_model_path()),
            "faceModelExists": face_model_path().exists(),
            "bodyModel": str(body_model_path()),
            "bodyModelExists": body_model_path().exists(),
            "persianModel": str(persian_model_path()),
            "persianModelExists": persian_model_path().exists(),
            "fontCount": len(fonts),
        },
        "gpu": {
            "label": "CUDA ASR READY" if asr_report.get("cudaRuntimeReady") else "MAX CPU · GPU AUTO",
            "asrReady": bool(asr_report.get("cudaRuntimeReady")),
        },
        "asr": asr_report,
        "paths": {
            "studio": str(studio_root()),
            "userData": str(user_data_root()),
            "output": str(default_output_root()),
            "config": str(config_path()),
        },
    }
    if not report["asr"]["ok"]:
        report["ok"] = False
        report["error"] = f"ASR runtime import failed: {report['asr'].get('error', 'unknown error')}"
    elif not report["assets"]["faceModelExists"]:
        report["ok"] = False
        report["error"] = "Face model is missing from the portable engine bundle."
    elif not report["assets"]["persianModelExists"]:
        report["ok"] = False
        report["error"] = "Persian speech model is missing from the portable runtime pack."
    elif not report["tools"]["ffmpeg"] or not report["tools"]["ffprobe"]:
        report["ok"] = False
        report["error"] = "FFmpeg tools are missing from the portable runtime pack."
    if as_json:
        _json_print(report)
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0 if report["ok"] else 2


def load_settings() -> dict[str, Any]:
    try:
        return json.loads(config_path().read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _configure_runtime(
    output: Path,
    *,
    style: str = "signal-os",
    density: str = "balanced",
    language: str = "fa-en",
    title_font: str = "",
    title_font_name: str = "Auto Persian",
    title_weight: int = 800,
    body_font: str = "",
    body_font_name: str = "Auto Persian",
    body_weight: int = 400,
    glow_intensity: float = 0.82,
    copy_mode: str = "source-faithful",
    performance: str = "maximum",
    analysis_only: bool = False,
    glass_review: bool = False,
) -> None:
    # A style label must never silently run the legacy graphic generator. Glass
    # currently has an isolated native QA path, not automatic chapter retiming.
    if glass_review and style.strip().lower() != 'glass':
        raise ValueError('--glass-review requires --style glass')
    if style.strip().lower() == "glass" and not (analysis_only or glass_review):
        raise ValueError(
            "Glass automatic editing is not released yet. Use glass-status and "
            "glass-validate --qa for the isolated editable Premiere review; "
            "or opt in to --style glass --glass-review for a separate draft; native QA remains required."
        )
    output.mkdir(parents=True, exist_ok=True)
    os.environ["HERMES_OUTPUT_DIR"] = str(output)
    os.environ["HERMES_STUDIO_ROOT"] = str(studio_root())
    os.environ["HERMES_FACE_MODEL"] = str(face_model_path())
    os.environ["HERMES_MOGRT_ROOT"] = str(adobe_mogrt_root())
    os.environ["HERMES_STYLE_PACK"] = style
    os.environ['HERMES_GLASS_REVIEW_MODE'] = '1' if glass_review else '0'
    os.environ["HERMES_GRAPHIC_DENSITY"] = density
    os.environ["HERMES_LANGUAGE_MODE"] = language
    if title_font:
        os.environ["HERMES_TITLE_FONT_PATH"] = title_font
    if body_font:
        os.environ["HERMES_BODY_FONT_PATH"] = body_font
    os.environ["HERMES_TITLE_FONT_FAMILY"] = title_font_name
    os.environ["HERMES_BODY_FONT_FAMILY"] = body_font_name
    os.environ["HERMES_TITLE_FONT_WEIGHT"] = str(title_weight)
    os.environ["HERMES_BODY_FONT_WEIGHT"] = str(body_weight)
    os.environ["HERMES_GLOW_INTENSITY"] = str(max(0.0, min(1.0, glow_intensity)))
    os.environ["HERMES_COPY_MODE"] = copy_mode
    logical_cores = max(1, int(os.cpu_count() or 1))
    if performance == "balanced":
        cpu_threads = max(2, (logical_cores + 1) // 2)
    elif performance == "adaptive":
        cpu_threads = max(2, logical_cores - 2)
    else:
        performance = "maximum"
        cpu_threads = logical_cores
    os.environ["HERMES_PERFORMANCE_PROFILE"] = performance
    os.environ["HERMES_CPU_THREADS"] = str(cpu_threads)
    os.environ.setdefault("HERMES_ASR_WORKERS", str(max(1, min(4, logical_cores // 6))) if performance == "maximum" else "1")
    os.environ["HERMES_FFMPEG_THREADS"] = str(cpu_threads) if performance == "balanced" else "0"
    os.environ["HERMES_CUDA_PREFERRED"] = "0" if performance == "balanced" else "1"
    for variable in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_MAX_THREADS"):
        os.environ[variable] = str(cpu_threads)
    os.environ["PYTHONUTF8"] = "1"


def _configure_job_runtime(output: Path, args: argparse.Namespace) -> None:
    _configure_runtime(
        output,
        style=args.style,
        density=args.density,
        language=args.language,
        title_font=args.title_font,
        title_font_name=args.title_font_name,
        title_weight=args.title_weight,
        body_font=args.body_font,
        body_font_name=args.body_font_name,
        body_weight=args.body_weight,
        glow_intensity=args.glow_intensity,
        copy_mode=args.copy_mode,
        performance=args.performance,
        analysis_only=getattr(args, 'command', '') == 'prepare',
        glass_review=getattr(args,'glass_review',False),
    )


def _video_paths(cam1_value: str, cam2_value: str) -> tuple[Path, Path]:
    cam1 = Path(cam1_value).expanduser().resolve()
    cam2 = Path(cam2_value).expanduser().resolve()
    if not cam1.is_file() or not cam2.is_file():
        raise FileNotFoundError("هر دو فایل دوربین باید موجود باشند.")
    return cam1, cam2


def prepare_job(args: argparse.Namespace) -> int:
    cam1, cam2 = _video_paths(args.cam1, args.cam2)
    output = Path(args.output).expanduser().resolve()
    _configure_job_runtime(output, args)
    autocut = _import_autocut()

    manifest_path = autocut.prepare_edit(str(cam1), str(cam2))
    _json_print({"event": "prepared", "manifest": manifest_path, "output": str(output)})
    return 0


def finalize_job(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    review = Path(args.review).expanduser().resolve() if args.review else None
    if not manifest.is_file():
        raise FileNotFoundError("Manifest تدوین پیدا نشد.")
    if review is not None and not review.is_file():
        raise FileNotFoundError("فایل پاسخ AI پیدا نشد.")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        xml_path = Path(payload.get("outputs", {}).get("xml", "")).expanduser()
        output = xml_path.parent if str(xml_path) else default_output_root()
    except (OSError, json.JSONDecodeError):
        payload = {}
        output = default_output_root()
    _configure_job_runtime(output, args)
    if args.style.strip().lower() == 'glass' and payload.get('glass_review'):
        if review is not None:
            raise ValueError('Existing Glass review is immutable; use a new job for changed review decisions')
        summary = validate_job_outputs(manifest)
        print('HERMES_STAGE finish 100 بستهٔ Glass قبلی اعتبارسنجی شد؛ بازبینی Premiere لازم است', flush=True)
        _json_print({'event':'completed','jobId':args.job_id,'manifest':str(manifest),
                     'xml':summary['xml'],'srt':summary['srt'],'summary':summary,'reusedVerifiedReview':True})
        return 0
    autocut = _import_autocut()

    xml_path, srt_path = autocut.finalize_edit(str(manifest), str(review) if review else None)
    summary = validate_job_outputs(manifest)
    print("HERMES_STAGE finish 100 خروجی Premiere آمادهٔ ورود است", flush=True)
    _json_print({"event": "completed", "jobId": args.job_id, "manifest": str(manifest), "xml": xml_path, "srt": srt_path, "summary": summary})
    return 0


def run_job(args: argparse.Namespace) -> int:
    cam1, cam2 = _video_paths(args.cam1, args.cam2)
    output = Path(args.output).expanduser().resolve()
    _configure_job_runtime(output, args)

    print(f"HERMES_JOB {args.job_id}")
    print("HERMES_PROGRESS 2")
    print("HERMES_STAGE analyze 2 راه‌اندازی موتور و بررسی منابع", flush=True)
    print("در حال بارگذاری Hafez Video Engine…")
    autocut = _import_autocut()  # Imported only after portable environment is configured.

    print("HERMES_PROGRESS 5")
    manifest_path = autocut.prepare_edit(str(cam1), str(cam2))
    autocut.finalize_edit(manifest_path)
    print("HERMES_STAGE finish 99 کنترل یکپارچگی خروجی‌ها", flush=True)
    summary = validate_job_outputs(manifest_path)
    print("HERMES_PROGRESS 100")
    _json_print(
        {
            "event": "completed",
            "jobId": args.job_id,
            "manifest": manifest_path,
            "output": str(output),
            "summary": summary,
        }
    )
    return 0


def _camera_schedule_failures(plan: dict[str, Any], xml_text: str) -> list[str]:
    """Validate coverage on the actual final XML clock, not the input duration.

    Scheduling emits millisecond-rounded times and XML snaps them to frames.
    Adjacent edges must share a frame and differ by at most the two rounding
    errors (1 ms); the outer edges must map to the exact XML frame endpoints.
    A single short hero shot is valid under the existing pacing policy.
    """
    from professional_edit import (
        CAMERA_INITIAL_HOLD_SECONDS,
        CAMERA_BOUNDARY_WINDOW_SECONDS,
        CAMERA_SCHEDULE_TAIL_SECONDS,
    )

    malformed = "برنامه دوربین یا پوشش زمانی XML نهایی معتبر نیست"
    try:
        name = plan.get("sequence")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("missing final sequence name")
        sequences = [node for node in ElementTree.fromstring(xml_text).iter("sequence")
                     if node.findtext("name") == name]
        if len(sequences) != 1:
            raise ValueError("ambiguous final sequence")
        sequence = sequences[0]
        duration_text = sequence.findtext("duration", "").strip()
        timebase_text = sequence.findtext("rate/timebase", "").strip()
        ntsc = sequence.findtext("rate/ntsc", "").strip()
        if (not duration_text.isdecimal() or not timebase_text.isdecimal()
                or ntsc not in {"TRUE", "FALSE"}):
            raise ValueError("missing exact XML clock")
        frames, timebase = int(duration_text), int(timebase_text)
        if frames <= 0 or timebase <= 0:
            raise ValueError("nonpositive XML duration/rate")
        rate = Fraction(timebase * 1000, 1001) if ntsc == "TRUE" else Fraction(timebase)
        duration = Fraction(frames, 1) / rate
        schedule = plan.get("camera_schedule")
        if not isinstance(schedule, list) or not schedule:
            raise ValueError("missing camera schedule")

        def seconds(value: Any) -> Fraction:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or isinstance(value, float) and not math.isfinite(value)):
                raise ValueError("invalid camera timing")
            return Fraction(str(value))

        prior_end = Fraction(0)
        prior_frame = 0
        for index, shot in enumerate(schedule):
            if not isinstance(shot, dict) or shot.get("camera") not in {"cam1", "cam2"}:
                raise ValueError("invalid camera")
            start, end = seconds(shot.get("start")), seconds(shot.get("end"))
            if start < 0 or end <= start:
                raise ValueError("nonpositive camera shot")
            first_frame, last_frame = round(start * rate), round(end * rate)
            if (first_frame != prior_frame or last_frame <= first_frame or last_frame > frames
                    or abs(start - prior_end) > Fraction(1 if index else 0, 1000)):
                raise ValueError("camera coverage gap/overlap/out-of-range")
            prior_end, prior_frame = end, last_frame
        # Half a frame from XML snapping plus half a millisecond from the
        # scheduler's round(..., 3). Never permit a missing final frame.
        if (prior_frame != frames
                or abs(prior_end - duration) > Fraction(1, 2) / rate + Fraction(1, 2000)):
            raise ValueError("incomplete final camera coverage")
        # Initial 24 s hold can move at most +7 s to a speech boundary; the
        # scheduler can omit only its 0.05 s loop tail. No new pacing choice.
        single_shot_limit = sum(Fraction(str(value)) for value in (
            CAMERA_INITIAL_HOLD_SECONDS, CAMERA_BOUNDARY_WINDOW_SECONDS,
            CAMERA_SCHEDULE_TAIL_SECONDS,
        ))
        if len(schedule) < 2 and duration > single_shot_limit:
            return ["کات دوربین هوشمند کافی نیست"]
    except (ElementTree.ParseError, TypeError, ValueError, OverflowError):
        return [malformed]
    return []


def validate_job_outputs(manifest_path: str | Path) -> dict[str, Any]:
    """Reject visually empty jobs and return UI-friendly completion counts."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    if manifest.get('style_pack') == 'glass':
        from glass_finalize import validate_review_outputs
        return validate_review_outputs(manifest)
    outputs = manifest.get("outputs", {})
    plan_path = Path(str(outputs.get("professional_plan", "")))
    xml_path = Path(str(outputs.get("xml", "")))
    srt_path = Path(str(outputs.get("tight_srt", "")))
    youtube_path = Path(str(outputs.get("youtube", "")))
    required = {
        "Premiere XML": xml_path,
        "Professional Plan": plan_path,
        "Tight SRT": srt_path,
        "YouTube Package": youtube_path,
    }
    missing = [label for label, path in required.items() if not path.is_file() or path.stat().st_size < 16]
    if missing:
        raise RuntimeError("خروجی‌های ضروری ناقص‌اند: " + "، ".join(missing))

    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    xml_text = xml_path.read_text(encoding="utf-8-sig")
    srt_text = srt_path.read_text(encoding="utf-8-sig")
    graphics = list(plan.get("graphics", []))
    punches = list(plan.get("punch_ins", []))
    camera = list(plan.get("camera_schedule", []))
    subtitle_cues = srt_text.count("-->")
    mapped_words = len(manifest.get("mapped_words", []))
    duration = float(manifest.get("timeline_duration", 0.0))
    failures: list[str] = []
    if mapped_words <= 0 or subtitle_cues <= 0:
        failures.append("زیرنویس واقعی تولید نشده")
    if not graphics:
        failures.append("هیچ برنامه MOGRT قابل‌ویرایشی تولید نشده")
    missing_mogrts = []
    for graphic in graphics:
        layers = graphic.get("template_layers") or [graphic]
        for layer in layers:
            template_path = Path(str(layer.get("template_path") or graphic.get("template_path", "")))
            if not template_path.is_file():
                missing_mogrts.append(str(template_path))
    if missing_mogrts:
        failures.append(f"{len(missing_mogrts)} فایل MOGRT پیدا نشد")
    if "<stillframe>TRUE</stillframe>" in xml_text or "-graphic-" in xml_text:
        failures.append("PNG گرافیکی نباید داخل Timeline نهایی باشد")
    if duration > 90 and not punches:
        failures.append("هیچ Punch-in معنایی تولید نشده")
    failures.extend(_camera_schedule_failures(plan, xml_text))
    if failures:
        raise RuntimeError("کنترل کیفیت خروجی رد شد: " + "؛ ".join(failures))

    # Match the Finisher's pre-import rejection rules. Planned proposals are
    # not usable MOGRTs when editorial, typography or placement QA blocks them.
    blocked_graphics = [item for item in graphics if item.get("review_blocked") is True
                        or (item.get("layout") or {}).get("collision_free") is False]
    usable_graphics = [item for item in graphics if item not in blocked_graphics]
    kinds: dict[str, int] = {}
    for graphic in usable_graphics:
        kind = str(graphic.get("kind", "unknown"))
        kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "mappedWords": mapped_words,
        "subtitleCues": subtitle_cues,
        "graphics": len(usable_graphics),
        "plannedGraphics": len(graphics),
        "blockedGraphics": len(blocked_graphics),
        "graphicsReviewRequired": sum(item in blocked_graphics or bool(item.get("needs_manual_copy")) for item in graphics),
        "editableMogrtLayers": sum(len(item.get("template_layers") or [item]) for item in usable_graphics),
        "pngTimelineAssets": 0,
        "premiereFinisherRequired": True,
        "copyReviewRequired": sum(bool(item.get("needs_manual_copy")) for item in graphics),
        "publicationReady": False,
        "reviewStatus": "Premiere visual check and source-audio transcript review required before publishing",
        "graphicKinds": kinds,
        "punchIns": len(punches),
        "cameraShots": len(camera),
        "cameraSwitches": max(0, len(camera) - 1),
        "xml": str(xml_path),
        "plan": str(plan_path),
        "srt": str(srt_path),
        "youtube": str(youtube_path),
        "finisher": "Import the XML, select Director Cut, then apply the Premiere Plan with Hafez Finisher to insert editable MOGRTs on V4.",
    }


def asr_smoke(args: argparse.Namespace) -> int:
    audio = Path(args.audio).expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError("فایل تست صدا پیدا نشد.")
    output = Path(args.output).expanduser().resolve()
    _configure_runtime(output)
    autocut = _import_autocut()
    duration_ms = max(1000.0, float(autocut.probe_video(str(audio)).get("duration", 0.0)) * 1000.0)
    mapping = [
        {
            "orig_start_ms": 0.0,
            "orig_end_ms": duration_ms,
            "tl_start_ms": 0.0,
            "tl_end_ms": duration_ms,
        }
    ]
    words = autocut.transcribe_and_map(str(audio), mapping, autocut.load_glossary(autocut.GLOSSARY_PATH))
    _json_print({"event": "asr-smoke", "ok": bool(words), "words": len(words), "preview": " ".join(item["text"] for item in words[:20])})
    return 0


def _add_typography_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--title-font", default="")
    parser.add_argument("--title-font-name", default="Auto Persian")
    parser.add_argument("--title-weight", type=int, choices=(600, 700, 800, 900), default=800)
    parser.add_argument("--body-font", default="")
    parser.add_argument("--body-font-name", default="Auto Persian")
    parser.add_argument("--body-weight", type=int, choices=(300, 400, 500, 600), default=400)
    parser.add_argument("--glow-intensity", type=float, default=0.82)
    parser.add_argument("--copy-mode", choices=("source-faithful", "grounded-summary"), default="source-faithful")
    parser.add_argument("--performance", choices=("maximum", "adaptive", "balanced"), default="maximum")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("glass-status", help="Read local Glass inventory and honest readiness status")
    glass_validate = subparsers.add_parser("glass-validate", help="Validate a typed Glass plan without touching Premiere")
    glass_validate.add_argument("--plan", required=True)
    glass_validate.add_argument("--qa", action="store_true", help="Permit isolated native QA, never production approval")
    glass_assemble = subparsers.add_parser("glass-assemble", help="Assemble an isolated Glass review from a completed two-camera XML and fresh word evidence")
    for option in ("manifest", "xml", "base-plan", "captions", "chapters", "output", "project"):
        glass_assemble.add_argument("--" + option, required=True)
    glass_assemble.add_argument("--source-sequence")
    glass_assemble.add_argument('--storyboard',help='Source-bound, context-reviewed semantic decisions')
    glass_assemble.add_argument('--audio',action='store_true',help='Add bound local vendor SFX, never process dialogue')
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--json", action="store_true")
    smoke_parser = subparsers.add_parser("asr-smoke")
    smoke_parser.add_argument("--audio", required=True)
    smoke_parser.add_argument("--output", default=str(default_output_root()))
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--cam1", required=True)
    run_parser.add_argument("--cam2", required=True)
    run_parser.add_argument("--output", default=str(default_output_root()))
    run_parser.add_argument("--job-id", default="HS-LOCAL")
    run_parser.add_argument("--style", default="signal-os")
    run_parser.add_argument("--density", choices=("balanced", "dense", "max"), default="balanced")
    run_parser.add_argument("--language", choices=("fa", "fa-en", "auto"), default="fa-en")
    _add_typography_arguments(run_parser)
    run_parser.add_argument('--glass-review',action='store_true',help='Opt in to an isolated Glass draft; not production approval')
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--cam1", required=True)
    prepare_parser.add_argument("--cam2", required=True)
    prepare_parser.add_argument("--output", default=str(default_output_root()))
    prepare_parser.add_argument("--style", default="signal-os")
    prepare_parser.add_argument("--density", choices=("balanced", "dense", "max"), default="balanced")
    prepare_parser.add_argument("--language", choices=("fa", "fa-en", "auto"), default="fa-en")
    _add_typography_arguments(prepare_parser)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--manifest", required=True)
    finalize_parser.add_argument("--review")
    finalize_parser.add_argument("--job-id", default="HS-RESUME")
    finalize_parser.add_argument("--style", default="signal-os")
    finalize_parser.add_argument("--density", choices=("balanced", "dense", "max"), default="balanced")
    finalize_parser.add_argument("--language", choices=("fa", "fa-en", "auto"), default="fa-en")
    _add_typography_arguments(finalize_parser)
    finalize_parser.add_argument('--glass-review',action='store_true',help='Opt in to an isolated Glass draft; not production approval')
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        if args.command == "glass-status":
            from glass_pack import capability_report
            _json_print(capability_report())
            return 0
        if args.command == "glass-assemble":
            from glass_assembly import assemble_review
            report = assemble_review(manifest_path=args.manifest, xml_path=args.xml,
                                     base_plan_path=args.base_plan, captions_path=args.captions,
                                     requests_path=args.chapters, output_dir=args.output,
                                     project_path=args.project, source_sequence=args.source_sequence,
                                     include_audio=args.audio,
                                     storyboard=json.loads(Path(args.storyboard).read_text(encoding='utf-8-sig')) if args.storyboard else None)
            _json_print({"ok": True, "status": report["status"], "output": args.output,
                         "chapters": len(report["selected_chapters"]),
                         "rejected": len(report["rejected_chapters"]),
                         "contentCards": len(report['selected_cutaways']),
                         "editableMogrtLayers": report['native_mogrt_instances_planned'],
                         "publicationReady": False, "premiereImportRequired": True})
            return 0
        if args.command == "glass-validate":
            from glass_pack import load_library, validate_plan
            payload = json.loads(Path(args.plan).read_text(encoding="utf-8-sig"))
            validate_plan(payload, load_library(), qa=args.qa, root=studio_root())
            _json_print({"ok": True, "mode": "isolated-native-qa" if args.qa else "native-approved-plan",
                         "graphics": len(payload["graphics"]), "publicationReady": False})
            return 0
        if args.command == "doctor":
            return doctor(args.json)
        if args.command == "asr-smoke":
            return asr_smoke(args)
        if args.command == "run":
            return run_job(args)
        if args.command == "prepare":
            return prepare_job(args)
        if args.command == "finalize":
            return finalize_job(args)
        return 2
    except Exception as error:
        print(f"HERMES_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
