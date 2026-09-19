"""Versioned, deterministic catalog for curated editorial elements.

The language model may propose an element id, but eligibility and final
selection are resolved here from transcript facts.  This keeps vendor artwork
out of the decision loop and gives both the editor and final reviewer the same
inventory, constraints and selection trace.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime_paths import studio_root


CATALOG_ENV = "HERMES_EDITORIAL_ELEMENT_CATALOG"
CATALOG_FILENAME = "editorial-element-catalog.json"
SUBSCRIBE_ELEMENT_ID = "hermes-subscribe"
_NUMBER_PATTERN = re.compile(r"[0-9۰-۹]")
_PERCENT_PATTERN = re.compile(r"(?:%|درصد)")
_NUMBER_WORDS = {
    "صفر", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده",
    "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده",
    "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود", "صد", "هزار", "میلیون",
}
_INCOMPLETE_ENDINGS = {
    "از", "با", "به", "برای", "تا", "توی", "تو", "در", "روی", "که", "و",
    "یا", "اما", "اگر", "وقتی", "چون", "مثل", "بدون", "این", "اون", "آن", "یک",
}
_FINANCIAL_WORDS = {
    "درآمد", "هزینه", "سود", "زیان", "موجودی", "مبلغ", "دلار", "تومان", "ریال",
    "قیمت", "مالی", "سرمایه", "برداشت", "واریز",
}
_PRICING_WORDS = {"قیمت", "پلن", "پکیج", "اشتراک", "ماهانه", "سالانه", "تعرفه"}
_WEEKLY_WORDS = {"هفته", "هفتگی", "روزانه", "دوشنبه", "شنبه", "تداوم", "استریک"}
_TIME_SERIES_WORDS = {
    "روند", "ماه", "ماهانه", "روز", "روزانه", "هفته", "هفتگی", "سال", "سالانه", "نمودار",
}


def catalog_path() -> Path:
    override = os.environ.get(CATALOG_ENV, "").strip()
    return Path(override).expanduser() if override else studio_root() / "config" / CATALOG_FILENAME


def normalize_spoken(value: Any) -> str:
    text = str(value or "").casefold().replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^0-9۰-۹a-zآ-ی%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_exact_phrase(value: Any, phrase: Any) -> bool:
    text = f" {normalize_spoken(value)} "
    needle = f" {normalize_spoken(phrase)} "
    return bool(needle.strip()) and needle in text


def _validate_catalog(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(payload))
    if int(result.get("schemaVersion", 0)) != 1:
        raise ValueError("Unsupported editorial element catalog schema")
    rules = result.get("rules", {})
    if bool(rules.get("grainAllowed", True)):
        raise ValueError("Editorial element catalog must remain grain-free")
    family_limit = int(rules.get("maximumFamiliesPerVideo", 0))
    if not 1 <= family_limit <= 4:
        raise ValueError("Editorial family limit must be between one and four")
    palette = result.get("palette", {})
    for key in ("ink", "glassSurface", "coolSlate", "sand", "champagne", "textPrimary"):
        value = str(palette.get(key, ""))
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError(f"Invalid editorial palette token: {key}")
    elements = result.get("elements")
    if not isinstance(elements, list) or len(elements) != 14:
        raise ValueError("Hermes editorial catalog must contain exactly fourteen elements")
    identifiers: set[str] = set()
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError("Every editorial element must be an object")
        element_id = str(element.get("id", "")).strip()
        if not element_id or element_id in identifiers:
            raise ValueError(f"Missing or duplicate editorial element id: {element_id}")
        identifiers.add(element_id)
        if bool(element.get("grainAllowed", True)):
            raise ValueError(f"Grain is forbidden in editorial element: {element_id}")
        if not str(element.get("mogrtName", "")).casefold().endswith(".mogrt"):
            raise ValueError(f"Missing MOGRT target for editorial element: {element_id}")
        if int(element.get("maxPerVideo", 0)) < 1:
            raise ValueError(f"Invalid per-video limit for editorial element: {element_id}")
    if SUBSCRIBE_ELEMENT_ID not in identifiers:
        raise ValueError("The deterministic Subscribe element is missing")
    return result


def load_editorial_catalog(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else catalog_path()
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    validated = _validate_catalog(payload)
    validated["path"] = str(source.resolve())
    return validated


def element_by_id(element_id: str, catalog: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    source = catalog or load_editorial_catalog()
    requested = str(element_id).strip()
    for element in source.get("elements", []):
        if str(element.get("id", "")) == requested:
            return deepcopy(dict(element))
    return None


def resolve_catalog_mogrt(element: Mapping[str, Any]) -> Path:
    return studio_root() / "motion-pack" / "dist" / str(element["mogrtName"])


def transcript_features(text: Any, cue: Mapping[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_spoken(text)
    words = normalized.split()
    cue = cue or {}
    nodes = [str(value).strip() for value in cue.get("nodes", []) if str(value).strip()]
    explicit_options = cue.get("options", [])
    options = [str(value).strip() for value in explicit_options if str(value).strip()] if isinstance(explicit_options, list) else []
    option_count = max(len(nodes), len(options), int(cue.get("option_count", 0) or 0))
    return {
        "normalized": normalized,
        "word_count": len(words),
        "number": bool(_NUMBER_PATTERN.search(normalized)) or any(word in _NUMBER_WORDS for word in words),
        "percentage": bool(_PERCENT_PATTERN.search(normalized)),
        "financial": any(word in normalized for word in _FINANCIAL_WORDS),
        "pricing": any(word in normalized for word in _PRICING_WORDS),
        "weekly": any(word in normalized for word in _WEEKLY_WORDS),
        "time_series": any(word in normalized for word in _TIME_SERIES_WORDS),
        "node_count": len(nodes),
        "option_count": option_count,
        "complete_statement": _looks_complete(text),
    }


def _looks_complete(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or "…" in text or "..." in text:
        return False
    words = normalize_spoken(text).split()
    return bool(words) and words[-1] not in _INCOMPLETE_ENDINGS


def _requirement_result(element: Mapping[str, Any], features: Mapping[str, Any], text: str) -> tuple[bool, list[str]]:
    requirements = element.get("requires", {})
    failures: list[str] = []
    if requirements.get("number") and not features["number"]:
        failures.append("requires-number")
    if requirements.get("financialContext") and not features["financial"]:
        failures.append("requires-financial-context")
    if requirements.get("pricingContext") and not features["pricing"]:
        failures.append("requires-pricing-context")
    if requirements.get("weeklyContext") and not features["weekly"]:
        failures.append("requires-weekly-context")
    if requirements.get("completeStatement") and not features["complete_statement"]:
        failures.append("requires-complete-statement")
    if int(requirements.get("maximumWords", 9999)) < int(features["word_count"]):
        failures.append("too-many-words")
    if int(requirements.get("minimumNodes", 0)) > int(features["node_count"]):
        failures.append("not-enough-nodes")
    if int(requirements.get("maximumNodes", 9999)) < int(features["node_count"]):
        failures.append("too-many-nodes")
    if int(requirements.get("minimumOptions", 0)) > int(features["option_count"]):
        failures.append("not-enough-options")
    if int(requirements.get("maximumOptions", 9999)) < int(features["option_count"]):
        failures.append("too-many-options")
    exact_phrase = str(requirements.get("exactPhrase", "")).strip()
    if exact_phrase and not contains_exact_phrase(text, exact_phrase):
        failures.append("exact-trigger-not-present")
    return not failures, failures


def _candidate_score(
    element: Mapping[str, Any],
    cue: Mapping[str, Any],
    features: Mapping[str, Any],
    text: str,
    history: set[str],
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    kind = str(cue.get("kind", cue.get("visual_kind", ""))).casefold()
    role = str(cue.get("semantic_role", "")).casefold()
    kinds = {str(value).casefold() for value in element.get("visualKinds", [])}
    roles = {str(value).casefold() for value in element.get("semanticRoles", [])}
    score = float(element.get("priority", 0)) / 25.0
    if kind and kind in kinds:
        score += 12.0
        reasons.append("visual-kind")
    if role and role in roles:
        score += 14.0
        reasons.append("semantic-role")
    trigger_count = sum(contains_exact_phrase(text, phrase) for phrase in element.get("triggerPhrases", []))
    if trigger_count:
        score += min(6.0, trigger_count * 3.0)
        reasons.append("transcript-trigger")
    if str(element.get("familyId", "")) in history:
        score += 2.0
        reasons.append("family-history")
    element_id = str(element.get("id", ""))
    if element_id == "hermes-user-growth" and features["percentage"]:
        score += 8.0
        reasons.append("percentage-fit")
    if element_id == "hermes-revenue-chart" and features["financial"] and features["time_series"]:
        score += 8.0
        reasons.append("financial-series-fit")
    if element_id == "hermes-saving-balance" and features["financial"] and features["number"]:
        score += 5.0
        reasons.append("financial-value-fit")
    if element_id == "hermes-glass-selector" and 3 <= features["option_count"] <= 6:
        score += 7.0
        reasons.append("option-count-fit")
    if element_id == "hermes-price-list" and features["pricing"] and features["option_count"] == 3:
        score += 10.0
        reasons.append("three-plan-fit")
    if element_id == "hermes-flowchart" and 3 <= features["node_count"] <= 6:
        score += 10.0
        reasons.append("node-count-fit")
    if element_id == "hermes-title-hero-3" and kind in {"hook", "chapter"}:
        score += 9.0
        reasons.append("hero-title-fit")
    if element_id == "hermes-title-hero-2" and role in {"claim", "conclusion"}:
        score += 8.0
        reasons.append("claim-title-fit")
    return score, reasons


def select_editorial_element(
    cue: Mapping[str, Any],
    text: Any,
    *,
    catalog: Mapping[str, Any] | None = None,
    family_history: Iterable[str] = (),
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    source = catalog or load_editorial_catalog()
    features = transcript_features(text, cue)
    history = {str(value) for value in family_history}
    requested_id = str(cue.get("element_id", cue.get("element_hint", ""))).strip()
    candidates: list[tuple[float, dict[str, Any], list[str]]] = []
    rejected: list[dict[str, Any]] = []
    for raw in source.get("elements", []):
        element = dict(raw)
        eligible, failures = _requirement_result(element, features, str(text or ""))
        if not eligible:
            rejected.append({"id": element["id"], "reasons": failures})
            continue
        score, reasons = _candidate_score(element, cue, features, str(text or ""), history)
        if requested_id == element.get("id"):
            score += 30.0
            reasons.append("valid-model-hint")
        if bool(element.get("exactTrigger")):
            score += 100.0
            reasons.append("deterministic-exact-trigger")
        candidates.append((score, element, reasons))
    candidates.sort(key=lambda item: (-item[0], -int(item[1].get("priority", 0)), str(item[1].get("id", ""))))
    selected = candidates[0] if candidates and candidates[0][0] >= 8.0 else None
    trace = {
        "catalog_id": source.get("id", ""),
        "requested_id": requested_id,
        "selected_id": selected[1]["id"] if selected else "",
        "score": round(selected[0], 3) if selected else 0.0,
        "reasons": selected[2] if selected else ["no-eligible-semantic-match"],
        "features": {key: value for key, value in features.items() if key != "normalized"},
        "rejected": rejected,
    }
    return (deepcopy(selected[1]) if selected else None), trace


def exact_subscribe_segments(
    segments: Iterable[Mapping[str, Any]],
    catalog: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source = catalog or load_editorial_catalog()
    subscribe = element_by_id(SUBSCRIBE_ELEMENT_ID, source)
    if not subscribe:
        return []
    phrase = str(subscribe.get("requires", {}).get("exactPhrase", "سابسکرایب کن"))
    matches: list[dict[str, Any]] = []
    for segment in segments:
        if contains_exact_phrase(segment.get("text", ""), phrase):
            matches.append(
                {
                    "segment_id": int(segment["id"]),
                    "start": float(segment.get("start", 0.0)),
                    "end": float(segment.get("end", segment.get("start", 0.0))),
                    "matched_phrase": phrase,
                    "element_id": SUBSCRIBE_ELEMENT_ID,
                }
            )
        if len(matches) >= int(subscribe.get("maxPerVideo", 1)):
            break
    return matches


def catalog_prompt_summary(catalog: Mapping[str, Any] | None = None) -> str:
    source = catalog or load_editorial_catalog()
    lines = [
        f"Catalog={source.get('id')} (Rule-Based؛ element_id فقط پیشنهاد است و موتور اعتبارسنجی می‌کند):"
    ]
    for element in source.get("elements", []):
        requirements = json.dumps(element.get("requires", {}), ensure_ascii=False, separators=(",", ":"))
        lines.append(
            "- {id} | {label} | roles={roles} | kinds={kinds} | requires={requirements} | max={maximum}".format(
                id=element["id"],
                label=element.get("labelFa", ""),
                roles=",".join(element.get("semanticRoles", [])),
                kinds=",".join(element.get("visualKinds", [])),
                requirements=requirements,
                maximum=element.get("maxPerVideo", 1),
            )
        )
    return "\n".join(lines)


def catalog_plan_payload(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = catalog or load_editorial_catalog()
    assets = []
    for element in source.get("elements", []):
        mogrt_path = resolve_catalog_mogrt(element)
        assets.append(
            {
                "id": element["id"],
                "label_fa": element.get("labelFa", ""),
                "family_id": element.get("familyId", ""),
                "priority": int(element.get("priority", 0)),
                "mogrt": str(mogrt_path),
                "mogrt_available": mogrt_path.is_file(),
                "semantic_roles": list(element.get("semanticRoles", [])),
                "visual_kinds": list(element.get("visualKinds", [])),
                "transparent_by_default": bool(element.get("transparentByDefault", False)),
                "grain_allowed": False,
            }
        )
    return {
        "id": source.get("id", ""),
        "schema_version": int(source.get("schemaVersion", 1)),
        "path": source.get("path", ""),
        "rules": deepcopy(source.get("rules", {})),
        "palette": deepcopy(source.get("palette", {})),
        "font_system": deepcopy(source.get("fontSystem", {})),
        "elements": assets,
    }
