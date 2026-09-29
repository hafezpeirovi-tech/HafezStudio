"""Quality-first SeedVR2 adapter. No source overwrite, cloud calls or Adobe writes."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from fractions import Fraction

class JobLock:
    """Cross-instance exclusion; stale locks are reclaimed only when their process is gone."""
    def __init__(self, runtime):
        self.path = runtime / "active-job.json"
    def __enter__(self):
        import psutil
        for _ in range(2):
            try:
                with self.path.open("x", encoding="utf-8") as stream:
                    json.dump({"pid": os.getpid(), "created": time.time()}, stream)
                return self
            except FileExistsError:
                owner = json.loads(self.path.read_text(encoding="utf-8"))
                if psutil.pid_exists(int(owner["pid"])):
                    raise RuntimeError("Another Upscale job is already running.")
                self.path.unlink()
        raise RuntimeError("Could not acquire Upscale lock")
    def __exit__(self, *_):
        if self.path.exists() and json.loads(self.path.read_text(encoding="utf-8"))["pid"] == os.getpid():
            self.path.unlink()

MODEL = "seedvr2_ema_3b_fp16.safetensors"
HASHES = {
    MODEL: "2fd0e03a3dad24e07086750360727ca437de4ecd456f769856e960ae93e2b304",
    "ema_vae_fp16.safetensors": "20678548f420d98d26f11442d3528f8b8c94e57ee046ef93dbb7633da8612ca1",
}

def emit(stage, **data):
    print(json.dumps({"stage": stage, **data}, ensure_ascii=False), flush=True)

def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", creationflags=0x08000000 if os.name == "nt" else 0)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or f"Process failed: {result.returncode}")
    return result.stdout

def probe(ffprobe, source, count=False):
    return json.loads(run([ffprobe, "-v", "error", *(["-count_frames"] if count else []),
                          "-show_streams", "-show_format", "-of", "json", source]))

def validate_video(info):
    videos = [s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    if len(videos) != 1:
        raise ValueError("Exactly one video stream is required.")
    video = videos[0]
    if video.get("pix_fmt") not in {"yuv420p", "yuvj420p", "yuv422p", "yuvj422p", "yuv444p", "yuvj444p", "rgb24", "bgr24", "nv12", "yuv420p10le", "yuv422p10le", "yuv444p10le"}:
        raise ValueError("Supported inputs: 8/10-bit SDR only; unsupported pixel format, source untouched.")
    if video.get("color_transfer") in {"smpte2084", "arib-std-b67"} or video.get("color_primaries") == "bt2020":
        raise ValueError("HDR/wide-gamut source is not supported; no automatic tone mapping.")
    if video.get("color_space", "bt709") not in {"bt709", "unknown"} or video.get("color_transfer", "bt709") not in {"bt709", "unknown"}:
        raise ValueError("Only Rec.709 SDR is validated. Explicit color management is required for this footage.")
    if video.get("field_order", "progressive") not in {"progressive", "unknown"}:
        raise ValueError("Interlaced footage must be deinterlaced explicitly first.")
    if video.get("sample_aspect_ratio", "1:1") not in {"1:1", "N/A"}:
        raise ValueError("Non-square pixels require explicit conforming first.")
    if any(abs(float(s.get("rotation", 0))) > 0 for s in video.get("side_data_list", [])):
        raise ValueError("Rotated source requires explicit conforming first.")
    fps = float(Fraction(video["avg_frame_rate"]))
    if not math.isfinite(fps) or fps <= 0 or fps > 120:
        raise ValueError("Unsupported frame rate.")
    if abs(float(Fraction(video["r_frame_rate"])) - fps) > .001:
        raise ValueError("Variable frame rate requires explicit conforming; timestamps will not be silently changed.")
    return video, fps

def verify_cfr(ffprobe, source, fps):
    """Inspect every timestamp, not just the container's nominal FPS."""
    video_info = next(s for s in probe(ffprobe, source)["streams"] if s["codec_type"] == "video")
    tolerance = max(.00015, 1.1 * float(Fraction(video_info.get("time_base", "1/1000000"))))
    child = subprocess.Popen([str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(source)],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                             creationflags=0x08000000 if os.name == "nt" else 0)
    previous = None
    count = 0
    try:
        for line in child.stdout:
            token = line.strip().split(",")[0]
            if not token:
                continue
            stamp = float(token)
            if previous is not None and abs(stamp - previous - 1 / fps) > tolerance:
                raise ValueError("Non-constant frame timestamps detected; refusing a potentially desynchronized output.")
            previous = stamp
            count += 1
        if child.wait() or count < 2:
            raise ValueError("Could not verify source timestamps.")
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    return count

def seed_arguments(runtime, source, output, resolution):
    return [sys.executable, str(Path(__file__).with_name("upscale-seed-bridge.py")), str(source),
            "--output", str(output), "--output_format", "mp4", "--video_backend", "ffmpeg", "--10bit",
            "--model_dir", str(runtime / "models"), "--dit_model", MODEL,
            "--resolution", str(resolution), "--batch_size", "9", "--uniform_batch_size",
            "--chunk_size", "25", "--temporal_overlap", "4", "--prepend_frames", "0",
            "--seed", "42", "--color_correction", "lab", "--input_noise_scale", "0",
            "--latent_noise_scale", "0", "--dit_offload_device", "cpu", "--vae_offload_device", "cpu",
            "--tensor_offload_device", "cpu", "--blocks_to_swap", "32", "--swap_io_components",
            "--vae_encode_tiled", "--vae_decode_tiled", "--vae_encode_tile_size", "512",
            "--vae_decode_tile_size", "512", "--vae_encode_tile_overlap", "128",
            "--vae_decode_tile_overlap", "128", "--attention_mode", "sdpa"]

def process(request, runtime, tools):
    start_time = time.monotonic()
    source = Path(request["input"]).resolve(strict=True)
    job = Path(request["jobDir"]).resolve(strict=True)
    resolution = int(request["resolution"])
    if resolution not in {720, 1080, 1440, 2160}:
        raise ValueError("Unsupported resolution")
    preview = request.get("mode") == "preview"
    if request.get("mode") not in {"preview", "full"}:
        raise ValueError("Invalid mode")
    if not preview and request.get("qualityConfirmed") is not True and request.get("directFullRequest") is not True:
        raise ValueError("Review a preview before full processing.")
    ffmpeg, ffprobe = tools / "ffmpeg.exe", tools / "ffprobe.exe"
    emit("checking", message="بررسی فایل، دقت رنگ و مدل‌ها")
    metadata = probe(ffprobe, source)
    video, fps = validate_video(metadata)
    duration = float(metadata["format"]["duration"])
    scale = resolution / min(video["width"], video["height"])
    reserve = int(video["width"] * video["height"] * scale * scale * fps * (min(5, duration) if preview else duration) + 2 * 1024**3)
    if shutil.disk_usage(job).free < reserve:
        raise ValueError(f"Insufficient disk space for quality intermediate + output (reserve about {reserve / 1024**3:.1f} GiB).")
    if resolution < min(video["width"], video["height"]):
        raise ValueError("Target must not be smaller than the source. Upscale never downsizes automatically.")
    for name, expected in HASHES.items():
        with (runtime / "models" / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Model checksum failed: {name}")
    original_stamp = (source.stat().st_size, source.stat().st_mtime_ns)
    work_input = source
    if preview:
        offset = float(request.get("start", 0))
        if not math.isfinite(offset) or not 0 <= offset < duration - .1:
            raise ValueError("Preview start is outside the source.")
        # Lossless 5-second excerpt, with aligned audio. Original footage remains untouched.
        work_input = job / "before.mkv"
        run([ffmpeg, "-v", "error", "-n", "-i", source, "-ss", str(offset), "-t", "5",
             "-map", "0:v:0", "-map", "0:a?", "-c:v", "ffv1", "-level", "3",
             "-c:a", "pcm_s24le", "-fps_mode", "passthrough", work_input])
    expected_frames = verify_cfr(ffprobe, work_input, fps)
    before = probe(ffprobe, work_input)
    interim = job / "restored-video.mov"
    command = seed_arguments(runtime, work_input, interim, resolution)
    (job / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    env = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ.get("PATH", ""),
           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONUTF8": "1",
           "HAFEZ_SEEDVR2_VENDOR": str(runtime / "seedvr2"),
           "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
    emit("processing", message="SeedVR2 FP16 — پردازش محلی؛ تخمین زمان بعد از اولین بخش")
    with (job / "inference.log").open("w", encoding="utf-8") as log:
        child = subprocess.Popen(command, cwd=runtime / "seedvr2", env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                 creationflags=0x08000000 if os.name == "nt" else 0)
        for line in child.stdout:
            log.write(line)
            log.flush()
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            match = re.search(r"Chunk (\d+)/(\d+)", clean)
            if match:
                done, total = int(match[1]) - 1, int(match[2])
                elapsed = time.monotonic() - start_time
                emit("processing", progress=round(done / total * 90),
                     etaSeconds=round(elapsed / done * (total - done)) if done else None,
                     message=f"بخش {done + 1} از {total}")
        if child.wait() != 0:
            raise RuntimeError("SeedVR2 failed. See inference.log; no fallback or quality reduction was applied.")
    emit("verifying", progress=92, message="کنترل تعداد فریم، زمان‌بندی و حفظ صدا")
    restored = probe(ffprobe, interim, count=True)
    result_video = next(s for s in restored["streams"] if s["codec_type"] == "video")
    if int(result_video.get("nb_read_frames", 0)) != expected_frames:
        raise ValueError("Frame count mismatch; output not approved.")
    if abs(float(Fraction(result_video["avg_frame_rate"])) - fps) > .001:
        raise ValueError("Output FPS mismatch.")
    if min(result_video["width"], result_video["height"]) != resolution:
        raise ValueError("Output dimensions mismatch.")
    final_partial = job / "upscaled.partial.mov"
    # Stream-copy original audio, no denoise, loudness processing, music or re-encoding.
    work_video = next(s for s in before["streams"] if s["codec_type"] == "video")
    video_start = float(work_video.get("start_time", 0))
    run([ffmpeg, "-v", "error", "-n", "-itsoffset", str(video_start), "-i", interim, "-i", work_input,
         "-map", "0:v:0", "-map", "1:a?", "-map_metadata", "1", "-c", "copy",
         "-movflags", "+faststart", final_partial])
    after = probe(ffprobe, final_partial)
    before_audio = [s for s in before["streams"] if s["codec_type"] == "audio"]
    after_audio = [s for s in after["streams"] if s["codec_type"] == "audio"]
    fields = ("codec_name", "sample_rate", "channels")
    if [[s.get(k) for k in fields] for s in before_audio] != [[s.get(k) for k in fields] for s in after_audio]:
        raise ValueError("Audio stream preservation check failed.")
    for index, (src_audio, dst_audio) in enumerate(zip(before_audio, after_audio)):
        def audio_hash(media):
            return run([ffmpeg, "-v", "error", "-i", media, "-map", f"0:a:{index}", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"]).strip()
        if audio_hash(work_input) != audio_hash(final_partial):
            raise ValueError("Audio packet hash mismatch.")
        if abs(float(src_audio.get("start_time", 0)) - float(dst_audio.get("start_time", 0))) > 1 / fps:
            raise ValueError("Audio timing mismatch.")
    if (source.stat().st_size, source.stat().st_mtime_ns) != original_stamp:
        raise ValueError("Source changed during processing.")
    final = job / "upscaled.mov"
    final_partial.rename(final)
    comparison = job / "comparison.png"
    # Still comparison is for inspection only, never a timeline graphic replacement.
    compare_time = str(min(1, (expected_frames - 1) / fps / 2))
    run([ffmpeg, "-v", "error", "-n", "-ss", compare_time, "-i", work_input, "-ss", compare_time, "-i", final,
         "-filter_complex", "[0:v]scale=-2:540[a];[1:v]scale=-2:540[b];[a][b]hstack=inputs=2",
         "-frames:v", "1", comparison])
    receipt = {"ok": True, "qualityApproval": "owner-review-required", "model": MODEL,
               "output": str(final), "comparison": str(comparison), "original": str(source),
               "preview": preview, "frameCount": expected_frames, "fps": fps,
               "resolution": resolution, "audioStreamsPreserved": len(after_audio),
               "seconds": round(time.monotonic() - start_time, 2)}
    (job / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    emit("completed", progress=100, **receipt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--tools", required=True)
    args = parser.parse_args()
    try:
        with JobLock(Path(args.runtime)):
            process(json.loads(Path(args.request).read_text(encoding="utf-8-sig")), Path(args.runtime), Path(args.tools))
    except Exception as exc:
        emit("failed", error=str(exc))
        sys.exit(1)
