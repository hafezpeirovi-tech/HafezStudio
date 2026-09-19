"""Enable Premiere font-family and font-size editing in AE-authored MOGRTs.

After Effects exposes Source Text through ExtendScript, but its scripting API
does not expose the two Source Text Properties checkboxes used by Essential
Graphics.  Adobe stores those authoring choices in ``definition.json``.  This
post-export step switches only those documented capability flags and leaves the
AE graphic payload untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def _enable_control(control: dict[str, Any]) -> bool:
    if int(control.get("type", -1)) != 6:
        return False
    font_info = control.get("fonteditinfo")
    if not isinstance(font_info, dict):
        return False
    font_info["capPropFontEdit"] = True
    font_info["capPropFontSizeEdit"] = True
    return True


def _enable_capsule_parameters(payload: dict[str, Any]) -> int:
    count = 0
    capsule = payload.get("capsuleparams", {})
    parameters = capsule.get("capParams", []) if isinstance(capsule, dict) else []
    for parameter in parameters:
        if not isinstance(parameter, dict) or int(parameter.get("capPropType", -1)) != 0:
            continue
        parameter["capPropFontEdit"] = True
        parameter["capPropFontSizeEdit"] = True
        count += 1
    return count


def enable_definition(definition: dict[str, Any]) -> dict[str, Any]:
    direct = sum(
        1 for control in definition.get("clientControls", [])
        if isinstance(control, dict) and _enable_control(control)
    )
    nested = 0
    for localized in definition.get("sourceInfoLocalized", {}).values():
        if not isinstance(localized, dict):
            continue
        nested += _enable_capsule_parameters(localized)
        raw = localized.get("appspecificsourceinfo")
        if not isinstance(raw, str):
            continue
        app_info = json.loads(raw)
        nested += _enable_capsule_parameters(app_info)
        localized["appspecificsourceinfo"] = json.dumps(
            app_info, ensure_ascii=False, separators=(",", ":")
        )
    if direct == 0 or nested == 0:
        raise ValueError("MOGRT has no editable Source Text controls to patch")
    return {"client_controls": direct, "capsule_controls": nested}


def patch_mogrt(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.suffix.casefold() != ".mogrt":
        raise FileNotFoundError(path)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}-font-controls-", suffix=".mogrt", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(path, "r") as source:
            names = source.namelist()
            definition_name = next(
                (name for name in names if name.casefold().endswith("definition.json")),
                None,
            )
            if not definition_name:
                raise ValueError(f"MOGRT has no definition.json: {path}")
            definition = json.loads(source.read(definition_name).decode("utf-8-sig"))
            result = enable_definition(definition)
            encoded = json.dumps(definition, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            with zipfile.ZipFile(temporary, "w") as target:
                target.comment = source.comment
                for info in source.infolist():
                    content = encoded if info.filename == definition_name else source.read(info)
                    target.writestr(info, content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(path.resolve()), **result}


def inspect_font_controls(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        definition_name = next(
            name for name in archive.namelist() if name.casefold().endswith("definition.json")
        )
        definition = json.loads(archive.read(definition_name).decode("utf-8-sig"))
    controls: list[dict[str, Any]] = []
    for control in definition.get("clientControls", []):
        info = control.get("fonteditinfo") if isinstance(control, dict) else None
        if int(control.get("type", -1)) != 6 or not isinstance(info, dict):
            continue
        names = control.get("uiName", {}).get("strDB", [])
        label = names[0].get("str", "Source Text") if names else "Source Text"
        controls.append(
            {
                "name": label,
                "font_family_editable": bool(info.get("capPropFontEdit")),
                "font_size_editable": bool(info.get("capPropFontSizeEdit")),
            }
        )
    return {"path": str(path.resolve()), "text_controls": controls}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    results: list[dict[str, Any]] = []
    for value in args.paths:
        targets = sorted(value.glob("*.mogrt")) if value.is_dir() else [value]
        for target in targets:
            results.append(inspect_font_controls(target) if args.inspect else patch_mogrt(target))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
