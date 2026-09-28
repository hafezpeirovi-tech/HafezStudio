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
