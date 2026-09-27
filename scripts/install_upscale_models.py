"""Explicit installer only. Inference never downloads weights."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = "09ced71023636e9bc8cdf9cdecfb2625d1e691e8"
MODELS = {
    "seedvr2_ema_3b_fp16.safetensors": "2fd0e03a3dad24e07086750360727ca437de4ecd456f769856e960ae93e2b304",
    "ema_vae_fp16.safetensors": "20678548f420d98d26f11442d3528f8b8c94e57ee046ef93dbb7633da8612ca1",
}

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

if __name__ == "__main__":
    folder = ROOT / "runtime/upscale/models"
    folder.mkdir(parents=True, exist_ok=True)
    receipt = {"revision": REVISION, "repository": "numz/SeedVR2_comfyUI", "models": {}}
    for name, expected in MODELS.items():
        target = folder / name
        if not target.exists():
            partial = target.with_suffix(".part")
            url = f"https://huggingface.co/numz/SeedVR2_comfyUI/resolve/{REVISION}/{name}"
            print(f"Downloading {name}", flush=True)
            subprocess.run(["curl.exe", "--fail", "--location", "--retry", "3", "--continue-at", "-", "--output", str(partial), url], check=True)
            if digest(partial) != expected:
                raise RuntimeError(f"Hash mismatch: {name}; partial retained, not installed")
            partial.rename(target)
        if digest(target) != expected:
            raise RuntimeError(f"Hash mismatch: {name}")
        receipt["models"][name] = {"sha256": expected, "bytes": target.stat().st_size}
        print(f"Verified {name}", flush=True)
    (folder.parent / "models-verified.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
