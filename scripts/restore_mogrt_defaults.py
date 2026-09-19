"""Restore Essential Graphics defaults from a known-good sibling MOGRT.

After Effects can retain the Essential Graphics controller list when a comp is
duplicated while exporting zero/empty defaults for the duplicate.  This tool
copies only controller defaults, matched by visible UI name, and leaves the
target's AE graphic payload and capability flags untouched.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def _label(control: dict[str, Any]) -> str:
    strings = control.get("uiName", {}).get("strDB", [])
    return str(strings[0].get("str", "")) if strings else ""


def _capsule_defaults(localized: dict[str, Any]) -> dict[str, Any]:
    capsule = localized.get("capsuleparams", {})
    params = capsule.get("capParams", []) if isinstance(capsule, dict) else []
    return {
        str(parameter.get("capPropUIName", "")): copy.deepcopy(parameter.get("capPropDefault"))
        for parameter in params
        if isinstance(parameter, dict) and parameter.get("capPropUIName")
    }


def _apply_overrides(
    target: dict[str, Any],
    overrides: dict[str, Any],
    ranges: dict[str, tuple[float, float]],
) -> dict[str, int]:
    controls_patched = 0
    ranges_patched = 0
    for control in target.get("clientControls", []):
        if not isinstance(control, dict):
            continue
        name = _label(control)
        if name in overrides:
            control["value"] = copy.deepcopy(overrides[name])
            controls_patched += 1
        if name in ranges:
            control["min"], control["max"] = ranges[name]
            ranges_patched += 1

    capsules_patched = 0
    capsule_ranges_patched = 0
    for localized in target.get("sourceInfoLocalized", {}).values():
        if not isinstance(localized, dict):
            continue
        capsule = localized.get("capsuleparams", {})
        params = capsule.get("capParams", []) if isinstance(capsule, dict) else []
        for parameter in params:
            if not isinstance(parameter, dict):
                continue
            name = str(parameter.get("capPropUIName", ""))
            if name in overrides:
                parameter["capPropDefault"] = copy.deepcopy(overrides[name])
                capsules_patched += 1
            if name in ranges:
                parameter["capPropMin"], parameter["capPropMax"] = ranges[name]
                capsule_ranges_patched += 1

    return {
        "override_client_controls": controls_patched,
        "override_capsule_defaults": capsules_patched,
        "range_client_controls": ranges_patched,
        "range_capsule_controls": capsule_ranges_patched,
    }


def restore_definition(
    reference: dict[str, Any],
    target: dict[str, Any],
    *,
    overrides: dict[str, Any] | None = None,
    ranges: dict[str, tuple[float, float]] | None = None,
) -> dict[str, int]:
    reference_controls = {
        _label(control): control
        for control in reference.get("clientControls", [])
        if isinstance(control, dict) and _label(control)
    }
    controls_patched = 0
    for control in target.get("clientControls", []):
        if not isinstance(control, dict):
            continue
        source = reference_controls.get(_label(control))
        if source is None or "value" not in source:
            continue
        control["value"] = copy.deepcopy(source["value"])
        controls_patched += 1

    capsules_patched = 0
    reference_localized = reference.get("sourceInfoLocalized", {})
    target_localized = target.get("sourceInfoLocalized", {})
    for locale, localized in target_localized.items():
        if not isinstance(localized, dict):
            continue
        source_localized = reference_localized.get(locale)
        if not isinstance(source_localized, dict) and reference_localized:
            source_localized = next(iter(reference_localized.values()))
        if not isinstance(source_localized, dict):
            continue
        defaults = _capsule_defaults(source_localized)
        capsule = localized.get("capsuleparams", {})
        params = capsule.get("capParams", []) if isinstance(capsule, dict) else []
        for parameter in params:
            if not isinstance(parameter, dict):
                continue
            name = str(parameter.get("capPropUIName", ""))
            if name not in defaults:
                continue
            parameter["capPropDefault"] = copy.deepcopy(defaults[name])
            capsules_patched += 1

    if not controls_patched or not capsules_patched:
        raise ValueError("No matching MOGRT controller defaults were found")
    result = {"client_controls": controls_patched, "capsule_defaults": capsules_patched}
    result.update(_apply_overrides(target, overrides or {}, ranges or {}))
    return result


def _read_definition(path: Path) -> tuple[str, dict[str, Any]]:
    with zipfile.ZipFile(path, "r") as archive:
        name = next(
            (item for item in archive.namelist() if item.casefold().endswith("definition.json")),
            None,
        )
        if not name:
            raise ValueError(f"MOGRT has no definition.json: {path}")
        return name, json.loads(archive.read(name).decode("utf-8-sig"))


def restore(
    reference_path: Path,
    target_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    ranges: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    _, reference = _read_definition(reference_path)
    definition_name, target = _read_definition(target_path)
    result = restore_definition(reference, target, overrides=overrides, ranges=ranges)
    encoded = json.dumps(target, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target_path.stem}-defaults-", suffix=".mogrt", dir=target_path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(target_path, "r") as source, zipfile.ZipFile(temporary, "w") as output:
            output.comment = source.comment
            for info in source.infolist():
                payload = encoded if info.filename == definition_name else source.read(info)
                output.writestr(info, payload)
        os.replace(temporary, target_path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"reference": str(reference_path.resolve()), "target": str(target_path.resolve()), **result}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="NAME=JSON",
        help="Override one controller default after restoring the reference values.",
    )
    parser.add_argument(
        "--range",
        action="append",
        default=[],
        metavar="NAME=MIN:MAX",
        help="Override the editable range of one numeric controller.",
    )
    args = parser.parse_args()

    overrides: dict[str, Any] = {}
    for item in args.set:
        if "=" not in item:
            parser.error(f"Invalid --set value: {item!r}")
        name, encoded = item.split("=", 1)
        overrides[name] = json.loads(encoded)

    ranges: dict[str, tuple[float, float]] = {}
    for item in args.range:
        if "=" not in item or ":" not in item.split("=", 1)[1]:
            parser.error(f"Invalid --range value: {item!r}")
        name, encoded = item.split("=", 1)
        minimum, maximum = encoded.split(":", 1)
        ranges[name] = (float(minimum), float(maximum))

    print(
        json.dumps(
            restore(
                args.reference,
                args.target,
                overrides=overrides,
                ranges=ranges,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
