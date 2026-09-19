"""Extract exact After Effects preview media from the fullscreen glass MOGRTs."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "motion-pack" / "dist"
OUTPUT = ROOT / "proof" / "glass-title-variants"
FFMPEG = ROOT / "runtime" / "tools" / "ffmpeg.exe"
TEMPLATES = (
    ("focus", "FOCUS HERO", "Hafez Fullscreen Glass Focus.mogrt"),
    ("prism", "PRISM STATEMENT", "Hafez Fullscreen Glass Prism.mogrt"),
    ("chapter", "CHAPTER PORTAL", "Hafez Fullscreen Glass Chapter.mogrt"),
)


def _extract_member(archive: zipfile.ZipFile, suffix: str, destination: Path) -> None:
    member = next(
        (item for item in archive.infolist() if item.filename.casefold().endswith(suffix)),
        None,
    )
    if member is None:
        raise FileNotFoundError(f"MOGRT does not contain {suffix}")
    with archive.open(member) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def _settled_frame(video: Path, destination: Path) -> None:
    command = [
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", "1.6", "-i", str(video), "-frames:v", "1", str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr[-2000:])


def _contact_sheet(stills: list[tuple[str, Path]], destination: Path) -> None:
    tile_width, tile_height = 960, 540
    footer = 72
    canvas = Image.new("RGB", (tile_width * 2, (tile_height + footer) * 2), (2, 3, 3))
    font_path = ROOT / "app" / "assets" / "fonts" / "Estedad-VF.ttf"
    font = ImageFont.truetype(str(font_path), 28)
    draw = ImageDraw.Draw(canvas)
    for index, (label, path) in enumerate(stills):
        frame = Image.open(path).convert("RGB").resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (index % 2) * tile_width
        y = (index // 2) * (tile_height + footer)
        canvas.paste(frame, (x, y))
        draw.rectangle((x, y + tile_height, x + tile_width, y + tile_height + footer), fill=(10, 12, 11))
        draw.text((x + 34, y + tile_height + 18), label, font=font, fill=(85, 255, 114))
    canvas.save(destination, quality=96)


def main() -> int:
    if not FFMPEG.is_file():
        raise FileNotFoundError(FFMPEG)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stills: list[tuple[str, Path]] = []
    for slug, label, filename in TEMPLATES:
        mogrt = DIST / filename
        if not mogrt.is_file():
            raise FileNotFoundError(mogrt)
        video = OUTPUT / f"hafez-fullscreen-glass-{slug}.mp4"
        still = OUTPUT / f"hafez-fullscreen-glass-{slug}.png"
        with zipfile.ZipFile(mogrt) as archive:
            _extract_member(archive, "thumb.mp4", video)
        _settled_frame(video, still)
        stills.append((label, still))
    _contact_sheet(stills, OUTPUT / "hafez-fullscreen-glass-variants.png")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
