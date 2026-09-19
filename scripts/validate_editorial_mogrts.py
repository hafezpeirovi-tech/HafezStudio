"""Validate the curated Hermes editorial MOGRT delivery.

The catalog is the contract: every declared template must exist, expose its
declared text slots, use only ABAR High FaNum weights, keep Premiere font and
font-size editing enabled, and contain no Grain references in the template
definition or packaged file names.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any


STANDARD_CONTROLS = {
    "Layout Scale",
    "Layout Position",
    "Glow Radius",
    "Glow Intensity",
    "Glass Opacity",
    "Background Color",
    "Text Primary",
    "Champagne Border",
    "Cool Accent",
    "Sand Accent",
    "Glass Surface",
}
TEXT_STYLE_SUFFIXES = ("Text Color", "Line Spacing", "Tracking")
REQUIRED_MEMBERS = {"definition.json", "project.aegraphic", "thumb.mp4", "thumb.png"}


def _control_name(control: dict[str, Any]) -> str:
    names = control.get("uiName", {}).get("strDB", [])
    if not names or not isinstance(names[0], dict):
        return ""
    return str(names[0].get("str", ""))


def _font_names(definition: dict[str, Any]) -> list[str]:
    fonts: list[str] = []
    for localized in definition.get("usedFontsLocalized", {}).values():
        if isinstance(localized, list):
            fonts.extend(str(value) for value in localized)
    return sorted(set(fonts))


def validate_mogrt(path: Path, element: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not path.is_file():
        return {"id": element["id"], "path": str(path), "ok": False, "errors": ["missing-file"]}

    try:
        with zipfile.ZipFile(path) as archive:
            members = set(archive.namelist())
            missing_members = sorted(REQUIRED_MEMBERS - members)
            if missing_members:
                errors.append("missing-members:" + ",".join(missing_members))
            definition_name = next(
                (name for name in members if name.casefold().endswith("definition.json")),
                None,
            )
            if not definition_name:
                errors.append("missing-definition")
                return {"id": element["id"], "path": str(path), "ok": False, "errors": errors}
            raw_definition = archive.read(definition_name)
            project_payload = archive.read("project.aegraphic") if "project.aegraphic" in members else b""
            definition = json.loads(raw_definition.decode("utf-8-sig"))
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "id": element["id"],
            "path": str(path),
            "ok": False,
            "errors": [f"invalid-package:{type(exc).__name__}"],
        }

    controls = [value for value in definition.get("clientControls", []) if isinstance(value, dict)]
    names = {_control_name(value) for value in controls}
    text_controls = [value for value in controls if int(value.get("type", -1)) == 6]
    text_names = {_control_name(value) for value in text_controls}

    missing_text = sorted(set(element.get("textSlots", [])) - text_names)
    if missing_text:
        errors.append("missing-text-controls:" + ",".join(missing_text))
    required_text_style_controls = {
        f"{slot} · {suffix}"
        for slot in element.get("textSlots", [])
        for suffix in TEXT_STYLE_SUFFIXES
    }
    missing_text_styles = sorted(required_text_style_controls - names)
    if missing_text_styles:
        errors.append("missing-text-style-controls:" + ",".join(missing_text_styles))
    for control in text_controls:
        info = control.get("fonteditinfo", {})
        if not info.get("capPropFontEdit") or not info.get("capPropFontSizeEdit"):
            errors.append("font-controls-disabled:" + (_control_name(control) or "Source Text"))

    fonts = _font_names(definition)
    invalid_fonts = [font for font in fonts if not font.startswith("AbarHighFaNum-")]
    if not fonts:
        errors.append("missing-font-metadata")
    if invalid_fonts:
        errors.append("non-abar-fonts:" + ",".join(invalid_fonts))

    required_controls = set(STANDARD_CONTROLS)
    if element.get("backgroundToggle"):
        required_controls.add("Show Background")
    missing_controls = sorted(required_controls - names)
    if missing_controls:
        errors.append("missing-style-controls:" + ",".join(missing_controls))

    definition_text = raw_definition.decode("utf-8-sig").casefold()
    grain_members = [name for name in members if "grain" in name.casefold()]
    if "grain" in definition_text or b"grain" in project_payload.lower() or grain_members:
        errors.append("grain-reference")

    return {
        "id": element["id"],
        "path": str(path.resolve()),
        "ok": not errors,
        "size_bytes": path.stat().st_size,
        "text_controls": len(text_controls),
        "fonts": fonts,
        "errors": errors,
    }


def validate_delivery(product_root: Path) -> dict[str, Any]:
    catalog_path = product_root / "config" / "editorial-element-catalog.json"
    output_dir = product_root / "motion-pack" / "dist"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    results = [
        validate_mogrt(output_dir / element["mogrtName"], element)
        for element in catalog.get("elements", [])
    ]
    expected = {element["mogrtName"] for element in catalog.get("elements", [])}
    actual = {path.name for path in output_dir.glob("Hafez Hermes *.mogrt")}
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    ok = bool(results) and all(item["ok"] for item in results) and not unexpected and not missing
    return {
        "ok": ok,
        "catalog_id": catalog.get("id"),
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing": missing,
        "unexpected": unexpected,
        "templates": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--product-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_delivery(args.product_root.resolve())
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
