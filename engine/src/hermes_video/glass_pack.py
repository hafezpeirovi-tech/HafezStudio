"""Local vendor MOGRT inventory and typed, palette-bound Glass plans.

No artwork generation, downloads, speech rewriting or implicit native approval.
Native plans use typed bindings because vendors reuse display names for colors,
text, groups and sometimes multiple independent scalar controls.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from runtime_paths import studio_root

TYPES = {1: "boolean", 2: "scalar", 3: "scalar", 4: "color", 5: "point",
         6: "text", 9: "vector", 10: "group", 13: "scalar", 14: "media"}
DEFAULT_PALETTE = {"id": "smoked-emerald", "background": "#060B09",
                   "surface": "#14291F", "accent": "#43E878",
                   "accentLight": "#B0F6CB", "text": "#F3F7F4", "muted": "#B5C9BE"}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def localized(value: Any) -> str:
    if isinstance(value, str):
        return value
    rows = value.get("strDB", []) if isinstance(value, dict) else []
    return str(next((x.get("str", "") for x in rows if x.get("localeString") == "en_US"),
                    rows[0].get("str", "") if rows else ""))


def read_mogrt(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        entry = archive.getinfo("definition.json")
        if entry.file_size > 16_000_000:
            raise ValueError("Unexpectedly large MOGRT definition")
        definition = json.loads(archive.read(entry).decode("utf-8-sig"))
    infos = definition.get("sourceInfoLocalized", {})
    info = infos.get("en_US") or next(iter(infos.values()), {})
    size = info.get("framesize", {}).get("size", {})
    duration = info.get("duration", {})
    seconds = float(duration.get("value", 0)) / max(1, float(duration.get("scale", 1)))
    controls, seen = [], Counter()
    for control in definition.get("clientControls", []):
        name, kind = localized(control.get("uiName")), TYPES.get(control.get("type"), "unsupported")
        occurrence = seen[(name, kind)]
        seen[(name, kind)] += 1
        value = control.get("value")
        if kind == "text":
            value = localized(value)
        controls.append({"name": name, "kind": kind, "occurrence": occurrence,
                         "default": value, "font": control.get("fonteditinfo", {})})
    return {"name": definition.get("capsuleName", path.stem), "sha256": sha256(path),
            "width": size.get("x", 0), "height": size.get("y", 0), "duration": seconds,
            "fps": 254016000000 / info["framerate"]["ticksperframe"] if info.get("framerate", {}).get("ticksperframe") else 0,
            "responsive": info.get("hasFrozenUnstretchableRegions", False),
            "controls": controls, "nativeQA": {"status": "pending"},
            "hasMediaReplacement": any(x["kind"] == "media" for x in controls),
            "fontLocked": [x["name"] for x in controls if x["kind"] == "text" and not x["font"].get("capPropFontEdit")],
            "leadingControls": [x["name"] for x in controls if re.search(r"line.?spacing|leading", x["name"], re.I)]}


def import_library(sources_path: Path, root: Path | None = None) -> dict:
    """Idempotent local-only ingest; never overwrite changed asset payloads."""
    root = root or studio_root()
    spec = json.loads(sources_path.read_text(encoding="utf-8-sig"))
    entries, packs, seen_roots = [], [], set()
    target = root / "motion-pack/vendor/glass"
    for source in spec["sources"]:
        source_root = Path(source["path"]).resolve(strict=True)
        if source_root in seen_roots:
            raise ValueError("Duplicate package root")
        seen_roots.add(source_root)
        if not re.fullmatch(r"[a-z0-9-]+", source["id"]):
            raise ValueError("Invalid package id")
        files = sorted(source_root.rglob("*.mogrt"))
        if not files:
            raise ValueError("Package has no MOGRTs: " + source["id"])
        packs.append({k: source[k] for k in ("id", "role", "core") } | {"count": len(files)})
        for path in files:
            relative = path.relative_to(source_root)
            asset = read_mogrt(path)
            asset_id = source["id"] + "-" + hashlib.sha256(relative.as_posix().encode()).hexdigest()[:12]
            destination = target / source["id"] / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if sha256(destination) != asset["sha256"]:
                    raise ValueError("Refusing to overwrite modified local template: " + str(destination))
            else:
                shutil.copy2(path, destination)
                if sha256(destination) != asset["sha256"]:
                    raise ValueError("Local copy hash mismatch")
            asset.update(id=asset_id, family=source["id"], core=source["core"],
                         role=source["role"], path=destination.relative_to(root).as_posix(),
                         sourcePath=str(path), relativePath=relative.as_posix())
            entries.append(asset)
    library = {"schemaVersion": 1, "id": "glass", "grainAllowed": True,
               "familyLimit": 4, "downloadAllowed": False, "palette": DEFAULT_PALETTE,
               "persianFont": "AbarHighFaNum-SemiBold", "fontSelection": "provisional-owner-selection-pending",
               "packages": packs, "assets": entries}
    out = root / "config/glass-library.json"
    # Preserve genuine QA from a prior import only when the exact payload still matches.
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    approvals = {(a["id"], a["sha256"]): a.get("nativeQA", {}) for a in old.get("assets", [])}
    for asset in entries:
        asset["nativeQA"] = approvals.get((asset["id"], asset["sha256"]), asset["nativeQA"])
    out.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")
    return library


def load_library(root: Path | None = None) -> dict:
    return json.loads(((root or studio_root()) / "config/glass-library.json").read_text(encoding="utf-8"))


def palette_values(palette: Mapping[str, str]) -> dict:
    result = {}
    for key in DEFAULT_PALETTE:
        if key == "id":
            continue
        value = palette.get(key, "")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Missing/invalid shared palette token: " + key)
        result[key] = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)] + [1.0]
    return result


def default_color_token(name: str) -> str:
    """All exposed colors are bound, including shadow and gradient endpoints."""
    name = name.lower()
    if "shadow" in name or "dust" in name:
        return "background"
    if re.search(r"bg color 0[1-4]", name):
        return "accent" if name.endswith(("01", "03")) else "accentLight"
    if "background" in name or "bg color" in name:
        return "background"
    if "gradient" in name:
        return "accentLight" if name.endswith(("b", "2", "02")) else "accent"
    if "glow" in name or "accent" in name or "bar color" in name or "icon" in name:
        return "accent"
    if "color 2" in name:
        return "accentLight"
    return "text"


def typed_layer(asset: Mapping, *, text: Mapping[str, str], track: int,
                palette: Mapping = DEFAULT_PALETTE, font: str = "AbarHighFaNum-SemiBold",
                sizes: Mapping | None = None, values: Mapping | None = None, fonts: Mapping | None = None,
                color_tokens: Mapping | None = None, root: Path | None = None) -> dict:
    root = root or studio_root()
    path = (root / asset["path"]).resolve()
    if not path.is_relative_to((root / "motion-pack").resolve()) or sha256(path) != asset["sha256"]:
        raise ValueError("MOGRT path/hash does not match the local inventory")
    if isinstance(track, bool) or not isinstance(track, int) or track < 0:
        raise ValueError("Invalid graphic track")
    colors, bindings, used_text, used_values = palette_values(palette), [], set(), set()
    sizes, values, color_tokens = sizes or {}, values or {}, color_tokens or {}
    fonts = fonts or {}
    for control in asset["controls"]:
        name, kind = control["name"], control["kind"]
        binding = {k: control[k] for k in ("name", "kind", "occurrence")}
        if kind == "text":
            if name not in text:
                raise ValueError("Every vendor text needs explicit replacement/blanking: " + name)
            value = text[name]
            if not isinstance(value, str) or "…" in value or "..." in value:
                raise ValueError("Unresolved text must not be rendered")
            binding["value"] = value
            control_font = fonts.get(name, font)
            if control_font:
                if not control["font"].get("capPropFontEdit"):
                    raise ValueError("Font is locked: " + name)
                binding["font"] = control_font
            if name in sizes:
                size = sizes[name]
                if not control["font"].get("capPropFontSizeEdit") or not isinstance(size, (int, float)) or not math.isfinite(size) or size <= 0:
                    raise ValueError("Unsupported font size: " + name)
                binding["fontSize"] = size
            used_text.add(name)
        elif kind == "color":
            token = color_tokens.get(name, default_color_token(name))
            binding.update(value=colors[token], paletteToken=token)
        elif name in values:
            binding["value"] = values[name]
            if kind not in {"scalar", "point", "vector", "boolean"}:
                raise ValueError("Unsupported typed control: " + name)
            used_values.add(name)
        else:
            continue
        bindings.append(binding)
    if set(text) != used_text or set(values) != used_values or not set(sizes).issubset(used_text) or not set(fonts).issubset(used_text):
        raise ValueError("Unknown text/size/control binding")
    return {"template": path.name, "template_path": str(path), "template_sha256": asset["sha256"],
            "asset_id": asset["id"], "family_id": asset["family"], "track": track,
            "role": "vendor-background" if not used_text else "vendor-typed-mogrt",
            "typed_controls": bindings, "allow_no_text": not used_text,
            "palette_id": palette["id"], "coordinate_space": [asset["width"], asset["height"]]}


def _validate_binding(binding: Mapping, control: Mapping) -> None:
    kind, value = binding["kind"], binding.get("value")
    numeric = lambda x: type(x) in (int, float) and math.isfinite(x)
    if kind == "text":
        if not isinstance(value, str) or "…" in value or "..." in value:
            raise ValueError("Unresolved/invalid text binding")
        font = binding.get("font", "")
        if not isinstance(font, str) or (font and not control.get("font", {}).get("capPropFontEdit")):
            raise ValueError("Unsupported native font")
        if "fontSize" in binding:
            size = binding["fontSize"]
            if not numeric(size) or size <= 0 or not control.get("font", {}).get("capPropFontSizeEdit"):
                raise ValueError("Unsupported native font size")
    elif kind == "scalar":
        if not numeric(value):
            raise ValueError("Non-finite scalar")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("Boolean control requires boolean")
    elif kind in {"point", "vector", "color"}:
        length = {"point": 2, "color": 4}.get(kind)
        if not isinstance(value, list) or not value or (length and len(value) != length) or not all(numeric(x) for x in value):
            raise ValueError("Malformed vector/color")
        if kind == "color" and not all(0 <= x <= 1 for x in value):
            raise ValueError("Color outside RGBA range")
    else:
        raise ValueError("Unsupported native control kind")


def validate_plan(plan: Mapping, library: Mapping, *, qa: bool = False, root: Path | None = None) -> None:
    """Release check is separate from generating an inspectable QA plan."""
    colors = palette_values(plan["palette"])
    assets = {a["id"]: a for a in library["assets"]}
    families = set()
    if plan.get("style_pack") != "glass" or plan.get("protocol") != "hermes-professional-edit-v2":
        raise ValueError("Not a Glass native plan")
    if qa and (plan.get("purpose") != "isolated-native-qa" or not plan.get("expected_project_path")):
        raise ValueError("QA requires an exact separate project target")
    if not isinstance(plan.get("graphics"), list) or not plan["graphics"]:
        raise ValueError("Empty native plan")
    cue_ids = set()
    for cue in plan["graphics"]:
        cue_id = cue.get("id", "")
        if not isinstance(cue_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", cue_id) or cue_id in cue_ids:
            raise ValueError("Invalid/duplicate cue identity")
        cue_ids.add(cue_id)
        if not all(isinstance(cue.get(k), (int, float)) and math.isfinite(cue[k]) for k in ("start", "end")) or not 0 <= cue["start"] < cue["end"]:
            raise ValueError("Invalid cue timing")
        tracks = set()
        if not cue.get("template_layers"):
            raise ValueError("Empty cue layers")
        for layer in cue["template_layers"]:
            asset = assets[layer["asset_id"]]
            if layer["template_sha256"] != asset["sha256"]:
                raise ValueError("Stale asset binding")
            if layer.get("family_id") != asset["family"] or layer.get("coordinate_space") != [asset["width"], asset["height"]]:
                raise ValueError("Stale template identity/geometry")
            track = layer.get("track")
            if type(track) is not int or track < 0 or track in tracks:
                raise ValueError("Invalid/overlapping layer track")
            tracks.add(track)
            scale = layer.get("native_motion_scale", 100)
            if type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 400:
                raise ValueError("Invalid native scale")
            if root is not None:
                actual = Path(layer["template_path"]).resolve(strict=True)
                expected = (root / asset["path"]).resolve(strict=True)
                if actual != expected or not actual.is_relative_to((root / "motion-pack").resolve()) or sha256(actual) != asset["sha256"]:
                    raise ValueError("Native plan path/hash mismatch")
            families.add(asset["family"])
            if not qa and (asset.get("nativeQA", {}).get("status") != "approved" or asset["nativeQA"].get("sha256") != asset["sha256"]):
                raise ValueError("Template has not passed native QA: " + asset["name"])
            bindings = layer["typed_controls"]
            controls = {(c["name"], c["kind"], c["occurrence"]): c for c in asset["controls"]}
            seen_bindings = set()
            expected_text = {key for key in controls if key[1] == "text"}
            expected_colors = {(c["name"], c["occurrence"]) for c in asset["controls"] if c["kind"] == "color"}
            actual_colors = set()
            for binding in bindings:
                identity = (binding["name"], binding["kind"], binding["occurrence"])
                if identity not in controls or identity in seen_bindings:
                    raise ValueError("Unknown/duplicate typed control")
                seen_bindings.add(identity)
                _validate_binding(binding, controls[identity])
                if binding["kind"] == "color":
                    if binding["value"] != colors[binding["paletteToken"]]:
                        raise ValueError("Mixed palette on the same video")
                    actual_colors.add((binding["name"], binding["occurrence"]))
            if expected_colors != actual_colors or layer["palette_id"] != plan["palette"]["id"]:
                raise ValueError("Unbound vendor colors")
            if not expected_text.issubset(seen_bindings):
                raise ValueError("Unbound vendor text")
            if not expected_text and (layer.get("role") != "vendor-background" or layer.get("allow_no_text") is not True):
                raise ValueError("Unqualified background-only layer")
    if len(families) > 4:
        raise ValueError("A video may use at most four families")


def capability_report(library: Mapping | None = None) -> dict:
    library = library or load_library()
    assets = library["assets"]
    return {"style": "glass", "assets": len(assets), "packages": library["packages"],
            "fontSelection": library.get("fontSelection", "pending"),
            "nativeApproved": sum(a.get("nativeQA", {}).get("status") == "approved" and
                                  a["nativeQA"].get("sha256") == a["sha256"] for a in assets),
            "fontLockedAssets": sum(bool(a.get("fontLocked")) for a in assets),
            "automaticEditingReady": False,
            "planningCatalogConnected": True,
            "chapterTimelineCompiler": "isolated-review-only",
            "ordinaryRunIntegration": "opt-in-review-only",
            "reviewCommand": "run/finalize --style glass --glass-review",
            "packagedAppDeployed": False,
            "remaining": ["owner font selection and native font/render QA",
                          "fresh source-bound chapter review and packaged-app integration",
                          "vendor SFX audition, curated music choice and end-to-end review"],
            "palette": library["palette"], "downloadAllowed": False}


def prompt_summary(library: Mapping | None = None) -> str:
    library = library or load_library()
    lines = ["Glass: local vendor MOGRT only; one shared palette; at most 4 families; no invented data."]
    for pack in library["packages"]:
        lines.append(f"{pack['id']} | {pack['role']} | {pack['count']} assets | {'core' if pack['core'] else 'optional'}")
    lines.append("Availability is not native approval. Subscribe Glass is not selected. Persian font is provisional.")
    lines.append("Selectable native review candidates (NOT publication-approved):")
    lines.extend(json.dumps(item, ensure_ascii=False) for item in planning_catalog(library))
    lines.append("Chapter = standalone SaaS over matching gradient BEFORE camera, not over a face. "
                 "Propose real topic boundaries only; timing is validated by the rule engine. "
                 "No Grunge/legacy substitution, no fabricated chart values; one video palette.")
    return "\n".join(lines)


def planning_catalog(library: Mapping | None = None) -> list[dict]:
    """Expose actual local IDs/capabilities to the editor, not unrelated legacy IDs."""
    library = library or load_library()
    candidates = {
        ('foslight-saas', 'SaaS Pack Title 01'): ['chapter', 'topic'],
        ('foslight-trendy', 'Trendy Title 01'): ['keyword', 'hook'],
        ('motionstate-liquid', '01 Progress Bar'): ['metric'],
    }
    return [{'id': a['id'], 'family': a['family'], 'name': a['name'],
             'roles': candidates[(a['family'], a['name'])],
             'requires': {'source_grounded_copy': True, 'native_review': True,
                          'explicit_numeric_evidence': a['family'] == 'motionstate-liquid'},
             'native_status': a.get('nativeQA', {}).get('status', 'pending')}
            for a in library['assets'] if (a['family'], a['name']) in candidates
            and a['width'] > a['height'] and not a.get('fontLocked')]
