"""Portable runtime discovery for Hafez Studio.

No machine-specific absolute path belongs in the product.  All locations can
be overridden with environment variables and otherwise follow the operating
system's standard user folders.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Iterable


PACKAGE_DIR = Path(__file__).resolve().parent
ENGINE_DIR = PACKAGE_DIR.parents[1]
SOURCE_ROOT = ENGINE_DIR.parent


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else None


def studio_root() -> Path:
    override = _env_path("HERMES_STUDIO_ROOT")
    if override:
        return override
    seeds = [PACKAGE_DIR, Path(sys.executable).resolve().parent]
    for seed in seeds:
        for candidate in (seed, *seed.parents):
            if (candidate / "motion-pack").exists() and (candidate / "config").exists():
                return candidate
    return SOURCE_ROOT


def portable_runtime_root() -> Path:
    return _env_path("HERMES_RUNTIME_ROOT") or studio_root() / "runtime"


def user_data_root() -> Path:
    override = _env_path("HERMES_USER_DATA")
    if override:
        return override
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local / "Hafez Studio"


def default_output_root() -> Path:
    override = _env_path("HERMES_OUTPUT_DIR")
    if override:
        return override
    return Path.home() / "Videos" / "Hafez Studio Outputs"


def config_path() -> Path:
    return _env_path("HERMES_STUDIO_CONFIG") or user_data_root() / "settings.json"


def adobe_mogrt_root() -> Path:
    override = _env_path("HERMES_MOGRT_ROOT")
    if override:
        return override
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "Adobe" / "Common" / "Motion Graphics Templates"


def face_model_path() -> Path:
    override = _env_path("HERMES_FACE_MODEL")
    if override:
        return override
    bundled = ENGINE_DIR / "models" / "face_detection_yunet_2026may.onnx"
    legacy = PACKAGE_DIR / "models" / "face_detection_yunet_2026may.onnx"
    return bundled if bundled.exists() else legacy


def body_model_path() -> Path:
    override = _env_path("HERMES_BODY_MODEL")
    if override:
        return override
    name = "human_segmentation_pphumanseg_2023mar.onnx"
    bundled = ENGINE_DIR / "models" / name
    return bundled if bundled.exists() else PACKAGE_DIR / "models" / name


def persian_model_path() -> Path:
    override = _env_path("HERMES_PERSIAN_MODEL")
    if override:
        return override
    bundled = portable_runtime_root() / "models" / "whisper-fa-ct2"
    legacy = Path.home() / "whisper-fa-ct2"
    return bundled if bundled.exists() else legacy


def nltk_data_path() -> Path:
    override = _env_path("HERMES_NLTK_DATA")
    if override:
        return override
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "nltk_data"


def font_candidates(preferred: str = "") -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    roots = [local / "Microsoft" / "Windows" / "Fonts", windows / "Fonts"]
    names = [
        preferred,
        "YekanBakh-ExtraBlack.ttf",
        "YekanBakh-Bold.ttf",
        "Peyda-Bold.ttf",
        "IRANSansX-Bold.ttf",
        "Vazirmatn-Bold.ttf",
        "AbarHigh-Regular.ttf",
        "tahomabd.ttf",
        "tahoma.ttf",
    ]
    explicit = _env_path("HERMES_FONT_PATH")
    bundled = studio_root() / "fonts" / "Estedad-VF.ttf"
    development = studio_root() / "app" / "assets" / "fonts" / "Estedad-VF.ttf"
    result = [explicit] if explicit else []
    result.extend((bundled, development))
    result.extend(root / name for root in roots for name in names if name)
    return [path for path in result if path is not None]


def find_executable(names: Iterable[str]) -> str | None:
    for name in names:
        tool_name = name if name.lower().endswith(".exe") else f"{name}.exe"
        bundled = portable_runtime_root() / "tools" / tool_name
        if bundled.is_file():
            return str(bundled)
        found = shutil.which(name)
        if found:
            return found
    return None


def adobe_apps() -> dict[str, Path | None]:
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Adobe"
    premiere = next(iter(sorted(root.glob("Adobe Premiere Pro *"), reverse=True)), None)
    after_effects = next(iter(sorted(root.glob("Adobe After Effects *"), reverse=True)), None)
    return {"premiere": premiere, "afterEffects": after_effects}
