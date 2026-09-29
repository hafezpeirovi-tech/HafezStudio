"""High-bit-depth SDR I/O for pinned SeedVR2 CLI; vendor source remains unchanged.

Input: FFmpeg RGB48 -> float32 [0,1]. Output: float32 -> RGB48 -> ProRes HQ 10-bit.
Single GPU video-only adapter. No uint8 bottleneck, no automatic HDR tone mapping.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from fractions import Fraction
import numpy as np

FLAGS = 0x08000000 if os.name == "nt" else 0

class Capture16:
    def __init__(self, source):
        self.source = source
        data = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                        "-show_streams", "-of", "json", source], creationflags=FLAGS)
        self.info = json.loads(data)["streams"][0]
        self.width, self.height = self.info["width"], self.info["height"]
        self.rate = self.info["avg_frame_rate"]
        self.count = int(self.info["nb_read_frames"])
        self.proc = None
        self.position = 0
    def isOpened(self):
        return True
    def get(self, prop):
        import cv2
        return {cv2.CAP_PROP_FPS: float(Fraction(self.rate)), cv2.CAP_PROP_FRAME_COUNT: self.count,
                cv2.CAP_PROP_FRAME_WIDTH: self.width, cv2.CAP_PROP_FRAME_HEIGHT: self.height}.get(prop, 0)
    def set(self, prop, value):
        import cv2
        if prop != cv2.CAP_PROP_POS_FRAMES:
            raise ValueError("Unsupported capture property")
        self.release()
        self.position = int(value)
        return True
    def read_rgb(self):
        if self.proc is None:
            cmd = ["ffmpeg", "-v", "error", "-i", self.source]
            if self.position:
                cmd += ["-vf", f"trim=start_frame={self.position}"]
            cmd += ["-map", "0:v:0", "-an", "-sn", "-dn", "-fps_mode", "passthrough",
                    "-pix_fmt", "rgb48le", "-f", "rawvideo", "pipe:1"]
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, creationflags=FLAGS)
        size = self.width * self.height * 6
        raw = self.proc.stdout.read(size)
        if not raw:
            if self.proc.wait() != 0:
                raise RuntimeError("High-bit-depth decoder failed")
            return None
        if len(raw) != size:
            raise RuntimeError("Truncated decoded frame")
        return np.frombuffer(raw, dtype="<u2").reshape(self.height, self.width, 3).astype(np.float32) / 65535.0
    def release(self):
        if self.proc:
            if self.proc.poll() is None:
                self.proc.terminate()
            self.proc.wait()
            self.proc.stdout.close()
            self.proc = None

def read_frames(cap, maximum):
    import torch
    frames = []
    for _ in range(maximum):
        frame = cap.read_rgb()
        if frame is None:
            break
        frames.append(frame)
    return torch.from_numpy(np.stack(frames)) if frames else None

class Writer16:
    def __init__(self, output, width, height, fps):
        # ProRes HQ intermediate: editing-friendly, avoids a lossy H.265 generation.
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-n", "-f", "rawvideo", "-pixel_format", "rgb48le",
            "-video_size", f"{width}x{height}", "-framerate", str(Fraction(fps).limit_denominator(1001000)),
            "-i", "pipe:0", "-an", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-colorspace", "bt709", "-color_range", "tv", "-f", "mov", output], stdin=subprocess.PIPE, creationflags=FLAGS)
    def write(self, frames):
        values = np.rint(np.clip(frames.float().cpu().numpy(), 0, 1) * 65535).astype("<u2")
        self.proc.stdin.write(values.tobytes())
    def release(self):
        if self.proc:
            self.proc.stdin.close()
            code = self.proc.wait()
            self.proc = None
            if code:
                raise RuntimeError(f"ProRes encoder failed: {code}")

def save_video(frames_tensor, output_path, fps, writer=None, **kwargs):
    if writer is None:
        _, height, width, _ = frames_tensor.shape
        writer = Writer16(output_path, width, height, fps)
    writer.write(frames_tensor)
    return writer

if __name__ == "__main__":
    vendor = Path(os.environ["HAFEZ_SEEDVR2_VENDOR"])
    sys.path.insert(0, str(vendor))
    import inference_cli as cli
    cli.cv2.VideoCapture = Capture16
    cli._read_frames_from_cap = read_frames
    cli.save_frames_to_video = save_video
    cli.main()
