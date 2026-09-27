"""Create a playback copy only after the full AI worker's technical receipt passes."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import psutil

parser = argparse.ArgumentParser()
parser.add_argument("job")
parser.add_argument("--wait-pid", type=int)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
job = Path(args.job).resolve()
receipt_file = job / "receipt.json"
while not receipt_file.exists():
    if not args.wait_pid or not psutil.pid_exists(args.wait_pid):
        raise RuntimeError("AI worker ended without a successful receipt; no delivery generated.")
    time.sleep(5)
receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
assert receipt["ok"] and not receipt["preview"], "Full result required"
ffmpeg = str(root / "runtime/tools/ffmpeg.exe")
ffprobe = str(root / "runtime/tools/ffprobe.exe")
output = job / "Upscaled-1080p.mp4"
subprocess.run([ffmpeg, "-v", "error", "-n", "-i", receipt["output"], "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy",
                "-movflags", "+faststart", str(output)], check=True)
subprocess.run([ffmpeg, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True)
info = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(output)]))
video = next(s for s in info["streams"] if s["codec_type"] == "video")
assert int(video["nb_read_frames"]) == receipt["frameCount"]
for index in range(receipt["audioStreamsPreserved"]):
    def audio_hash(media):
        return subprocess.check_output([ffmpeg, "-v", "error", "-i", media, "-map", f"0:a:{index}", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"])
    assert audio_hash(receipt["original"]) == audio_hash(str(output)), "Playback copy changed original audio"
report = {"playback": str(output), "master": receipt["output"], "frames": receipt["frameCount"],
          "width": video["width"], "height": video["height"], "decodeCheck": True,
          "audioPacketHashesMatch": True, "visualQuality": "requires-review"}
(job / "delivery.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report), flush=True)
