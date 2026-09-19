from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PRODUCT_ROOT / "engine" / "src" / "hermes_video"
sys.path.insert(0, str(ENGINE_DIR))

import professional_edit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Hafez Studio graphic proof frames from an existing edit manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target", type=float, default=177.0)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    review = json.loads(args.review.read_text(encoding="utf-8"))
    segments = list(manifest.get("review_segments") or [])
    markers = list(review.get("markers") or [])
    if not segments:
        raise ValueError("The manifest does not contain review_segments.")

    width = int(manifest["cam1_metadata"]["width"])
    height = int(manifest["cam1_metadata"]["height"])
    duration = float(manifest.get("timeline_duration") or segments[-1]["end"])
    planned = professional_edit.build_graphic_cues(segments, duration, markers)

    target_index = min(
        range(len(segments)),
        key=lambda index: abs(float(segments[index].get("start", 0.0)) - args.target),
    )
    target_segment = segments[target_index]
    target_marker = next(
        (item for item in markers if int(item.get("segment_id", -1)) == int(target_segment["id"])),
        {},
    )
    statement = professional_edit._complete_statement(segments, target_index, target_marker)
    target_cue = {
        "id": "proof-target",
        "segment_id": int(target_segment["id"]),
        "start": float(target_segment["start"]),
        "end": min(duration, float(target_segment["start"]) + 4.5),
        "duration": 4.5,
        "text": statement,
        "headline_fa": statement,
        "kicker_en": professional_edit._english_kicker(statement, target_marker),
        "kind": "statement",
        "placement": "right",
        "font_family": "Auto Persian",
        "controls": {"FA Headline": statement},
    }

    representatives = [target_cue]
    for cue in planned:
        if cue["segment_id"] == target_cue["segment_id"]:
            continue
        if cue["kind"] not in {item["kind"] for item in representatives}:
            representatives.append(cue)
        if len(representatives) >= 6:
            break

    args.output.mkdir(parents=True, exist_ok=True)
    rendered = professional_edit.render_graphic_assets(representatives, args.output, width, height)
    summary = {
        "source": args.manifest.name,
        "target_seconds": args.target,
        "dimensions": {"width": width, "height": height, "source": "camera1"},
        "planned_graphic_count": len(planned),
        "proof_assets": rendered,
    }
    (args.output / "proof-plan.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "count": len(rendered), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
