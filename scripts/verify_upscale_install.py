"""Record an actual CUDA/import check and exact installed dependency versions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import torch

root = Path(__file__).resolve().parents[1]
runtime = root / "runtime/upscale"
assert torch.cuda.is_available(), "CUDA unavailable"
env = {**os.environ, "PYTHONUTF8": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
check = subprocess.run([sys.executable, str(runtime / "seedvr2/inference_cli.py"), "--help"], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
assert check.returncode == 0, check.stderr
freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
(runtime / "requirements.lock.txt").write_text(freeze, encoding="utf-8")
revision = subprocess.check_output(["git", "-C", str(runtime / "seedvr2"), "rev-parse", "HEAD"], text=True).strip()
assert revision == "4490bd1f482e026674543386bb2a4d176da245b9"
receipt = {"vendorCommit": revision, "torch": torch.__version__, "cuda": torch.version.cuda,
           "gpu": torch.cuda.get_device_name(0), "python": sys.version,
           "dependencyLockSHA256": hashlib.sha256(freeze.encode()).hexdigest(),
           "cliImportCheck": True, "qualityValidated": False}
(runtime / "environment-verified.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt))
