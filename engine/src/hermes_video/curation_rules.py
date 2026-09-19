"""Deterministic editorial contracts for Hafez Studio.

The curator never invents artwork.  It validates copy, selects a small approved
template family and emits explicit typography/motion metadata for Premiere.
Generative models may propose copy, but only these rules may approve it.
"""

from __future__ import annotations

import os
import re
import json
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from motion_style import load_motion_style, motion_rule_payload


ELLIPSIS_PATTERN = re.compile(r"(?:\.{3,}|…)")
INCOMPLETE_ENDINGS = {
    "از", "با", "به", "برای", "تا", "توی", "تو", "در", "روی", "که", "و",
    "یا", "اما", "اگر", "وقتی", "چون", "مثلاً", "مثلا", "مثل", "بدون",
    "سمت", "طرف", "این", "اون", "آن", "یک", "ولی", "شاید", "باید", "نباید",
}
PREDICATE_PATTERNS = (
    re.compile(r"(?:^|\s)(?:است|هست|نیست|بود|شد|کرد|داره|دارم|داریم|دارن|نداره|ندارم)(?:[.!؟?]|$)"),
    re.compile(r"(?:^|\s)(?:می|نمی)[‌\- ]?(?:کن|شو|ش|رس|فرست|گیر|بین|زن|ساز|ده|د|اد|خواه|خوا|خواد|مان|مون|ر|گ)(?:م|ی|د|ه|یم|ید|ین|ند|ن)?(?:[.!؟?]|$)"),
    re.compile(r"^به .{3,70} (?:می[‌ ]?گن|می[‌ ]?گویند) [^،؛.!؟?]{2,25}[.!؟?]?$"),
    re.compile(r"(?:زمانبره|سخته|راحت‌تره|بهتره|بدتره|ممکنه|مهمه|کافیه|لازمه|میاد|میرسه|می‌رسه|میده|می‌ده|میشه|می‌شه)(?:[.!؟?]|$)"),
    re.compile(r"(?:^|\s)(?:بزن|بزنه|بده|بگم|بگی|بریم|بکنم|بکنی|بکنه|بکنیم|بکنید|بکنن|کنیم|بگیریم|انجام بده|تموم شده)(?:[.!؟?]|$)"),
)
RESTART_CUES = ("نه بذار", "دوباره بگم", "از اول بگم", "اشتباه گفتم", "یعنی نه")
CLAUSE_SEPARATOR = re.compile(r"[،؛!؟?]+|(?<![0-9۰-۹])\.(?![0-9۰-۹])")
SENTENCE_SEPARATOR = re.compile(r"[!؟?]|(?<![0-9۰-۹])\.(?![0-9۰-۹])")
DANGLING_MODAL = re.compile(r"(?:^|\s)(?:ممکنه|ممکن است|باید|نباید|شاید)[.!؟?]*$")


@dataclass(frozen=True)
class TextRule:
    min_words: int = 4
    max_words: int = 18
    max_characters: int = 118
    preserve_colloquial: bool = True
    allow_ellipsis: bool = False
    require_predicate: bool = True


@dataclass(frozen=True)
class MotionRule:
    entry_easing: str = "hafez-ui-entry"
    exit_easing: str = "hafez-ui-exit"
    entry_curve: tuple[float, float, float, float] = (0.16, 0.84, 0.22, 1.0)
    exit_curve: tuple[float, float, float, float] = (0.4, 0.0, 0.2, 1.0)
    entry_frames: int = 18
    settle_frames: int = 9
    exit_frames: int = 12
    linear_allowed: bool = False
    motion_blur: bool = True
    entry_offset_px: int = 42
    entry_blur_px: int = 9
    maximum_overshoot_percent: float = 1.5
    entry_opacity: int = 0
    settled_opacity: int = 100


@dataclass(frozen=True)
class TemplateRule:
    family_id: str
    asset_mode: str
    template_name: str
    allowed_kinds: tuple[str, ...]
    english_control: str
    persian_control: str
    position_control: str
    scale_control: str
    default_duration: float
    coordinate_width: int
    coordinate_height: int
    motion: MotionRule
    choreography_source: str
    vendor_visual_layers_embedded: bool


@dataclass(frozen=True)
class SfxRule:
    asset_name: str = "hafez-hero-glass.wav"
    role: str = "hafez-layered-motion"
    duration: float = 0.86
    sample_rate: int = 48_000
    channels: int = 2
    audio_track: int = 3


_STYLE = load_motion_style()
_MOTION = motion_rule_payload(_STYLE)
_FULLSCREEN_GLASS = _STYLE["families"]["fullscreen-glass"]
TEXT_ANIMATION_TITLE = TemplateRule(
    family_id=str(_FULLSCREEN_GLASS["familyId"]),
    asset_mode="bundled-curated",
    template_name=str(_FULLSCREEN_GLASS["template"]),
    allowed_kinds=("hook", "chapter"),
    english_control=str(_STYLE["typography"]["englishControl"]),
    persian_control=str(_STYLE["typography"]["persianControl"]),
    position_control="Layout Position",
    scale_control="Layout Scale",
    default_duration=4.8,
    coordinate_width=1920,
    coordinate_height=1080,
    motion=MotionRule(
        entry_easing=str(_MOTION["entry_easing"]),
        exit_easing=str(_MOTION["exit_easing"]),
        entry_curve=tuple(_MOTION["entry_curve"]),
        exit_curve=tuple(_MOTION["exit_curve"]),
        entry_frames=int(_MOTION["entry_frames"]),
        settle_frames=int(_MOTION["settle_frames"]),
        exit_frames=int(_MOTION["exit_frames"]),
        linear_allowed=bool(_MOTION["linear_allowed"]),
        motion_blur=bool(_MOTION["motion_blur"]),
        entry_offset_px=int(_MOTION["entry_offset_px"]),
        entry_blur_px=int(_MOTION["entry_blur_px"]),
        maximum_overshoot_percent=float(_MOTION["maximum_overshoot_percent"]),
        entry_opacity=int(_MOTION["entry_opacity"]),
        settled_opacity=int(_MOTION["settled_opacity"]),
    ),
    choreography_source="05. Highlight (Cut Transition).mogrt",
    vendor_visual_layers_embedded=False,
)

TEXT_ANIMATION_SFX = SfxRule()

DEFAULT_TEXT_RULE = TextRule()

COPY_STOPWORDS = {
    "از", "با", "به", "برای", "تا", "توی", "تو", "در", "روی", "که", "و", "یا",
    "اما", "اگر", "وقتی", "چون", "مثل", "یک", "این", "اون", "آن", "را", "رو",
    "من", "ما", "شما", "هم", "همین", "همون", "همان", "مثلا", "مثلاً",
}


def normalize_copy(value: Any) -> str:
    """Normalize whitespace without formalising the speaker's Persian."""
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ،؛:-")
    text = re.sub(r"^(?:خب|حالا|ببینید|ببین|یعنی|در واقع|مثلا|مثلاً)\s+", "", text)
    text = re.sub(r"\b(من من|که که|و و)\b", lambda match: match.group(0).split()[0], text)
    return text.strip()


def _copy_tokens(value: Any) -> list[str]:
    normalized = normalize_copy(value).casefold().translate(str.maketrans({"ي": "ی", "ك": "ک"}))
    normalized = normalized.replace("‌", " ")
    return re.findall(r"[a-z0-9۰-۹\u0600-\u06ff]+", normalized)


def copy_grounding(candidate: Any, sources: Iterable[Any]) -> dict[str, Any]:
    """Measure whether display copy is supported by nearby transcript words.

    Numbers and Latin identifiers are hard-locked.  Remaining content words
    must be present in the source window; fluent but invented model copy is
    rejected even when it looks grammatically complete.
    """
    candidate_tokens = _copy_tokens(candidate)
    source_tokens = _copy_tokens(" ".join(str(value or "") for value in sources))
    source_counts = Counter(source_tokens)
    content = [token for token in candidate_tokens if token not in COPY_STOPWORDS]
    matched = 0
    remaining = Counter(source_counts)
    for token in content:
        if remaining[token] > 0:
            matched += 1
            remaining[token] -= 1
    coverage = matched / max(1, len(content))
    candidate_numbers = {token for token in candidate_tokens if re.search(r"[0-9۰-۹]", token)}
    source_numbers = {token for token in source_tokens if re.search(r"[0-9۰-۹]", token)}
    candidate_latin = {token for token in candidate_tokens if re.search(r"[a-z]", token)}
    source_latin = {token for token in source_tokens if re.search(r"[a-z]", token)}
    return {
        "supported": coverage >= 0.82 and candidate_numbers <= source_numbers and candidate_latin <= source_latin,
        "content_token_coverage": round(coverage, 3),
        "numbers_locked": candidate_numbers <= source_numbers,
        "latin_terms_locked": candidate_latin <= source_latin,
    }


def has_spoken_predicate(value: Any) -> bool:
    text = normalize_copy(value).rstrip()
    return any(pattern.search(text) for pattern in PREDICATE_PATTERNS)


def is_complete_statement(value: Any, rule: TextRule = DEFAULT_TEXT_RULE) -> bool:
    """Return True only for a compact, closed Persian statement.

    Terminal punctuation is not considered proof of completeness.  A valid
    statement must contain a spoken predicate and must never end in an
    ellipsis or a connective.
    """
    text = normalize_copy(value)
    if not text or (not rule.allow_ellipsis and ELLIPSIS_PATTERN.search(text)):
        return False
    words = text.rstrip(".!؟?").split()
    if not rule.min_words <= len(words) <= rule.max_words:
        return False
    if len(text) > rule.max_characters:
        return False
    if SENTENCE_SEPARATOR.search(text.rstrip(".!؟?")):
        return False
    if words[-1].casefold() in INCOMPLETE_ENDINGS:
        return False
    if DANGLING_MODAL.search(text):
        return False
    # A finite-looking verb in an unfinished conditional is not a main clause:
    # "... بعضی از این استراتژیا وقتی می‌دازیش" was previously approved.
    conditional = list(re.finditer(r"(?:^|\s)(?:وقتی|اگر|اگه)\s+", text))
    if conditional:
        tail = text[conditional[-1].end():].rstrip(".!؟?")
        if not CLAUSE_SEPARATOR.search(tail):
            prefixes = [" ".join(tail.split()[:index]) for index in range(1, len(tail.split()) + 1)]
            if sum(has_spoken_predicate(prefix) for prefix in prefixes) < 2:
                return False
    if rule.require_predicate and not has_spoken_predicate(text):
        return False
    return True


def _candidate_clauses(values: Iterable[str]) -> list[str]:
    # Whisper review segments are fixed windows, NOT linguistic boundaries.
    # Inserting commas here turned arbitrary later windows into false clauses.
    joined = " ".join(normalize_copy(value) for value in values if normalize_copy(value))
    if not joined:
        return []
    return [clause for part in CLAUSE_SEPARATOR.split(joined) if (clause := normalize_copy(part))]


def _anchored_complete_clauses(values: list[str], rule: TextRule) -> list[str]:
    """Select only contiguous clauses beginning in the selected source window.

    A later sentence may finish the selected opening, but it must never replace
    it silently while the cue retains the earlier timestamp and English label.
    """
    if not values:
        return []
    joined = " ".join(values)
    selected_length = len(values[0])
    result: list[str] = []
    for clause in _candidate_clauses(values):
        position = joined.find(clause)
        if position < 0 or position >= selected_length:
            continue
        if is_complete_statement(clause, rule):
            result.append(clause)
            continue
        # Spoken definitions often have no ASR punctuation before a NEW
        # subject: "به این وضعیت ... می‌گن فلج تحلیلی تو انقدر ...".
        # Recognize this grammatical boundary only for an explicit naming
        # clause; never truncate an arbitrary sentence at a pronoun.
        for boundary in re.finditer(r"\s+(?:تو|شما|من|ما)\s+(?:انقدر|اینقدر|دیگه|داری|دارید|داریم|می[‌\w]+|نمی[‌\w]+)(?=\s|$)", clause):
            prefix = clause[:boundary.start()].strip()
            if (re.fullmatch(r"به .{3,70} (?:می[‌ ]?گن|می[‌ ]?گویند) [^،؛.!؟?]{2,25}", prefix)
                    and is_complete_statement(prefix, rule)):
                result.append(prefix)
                break
        # Preserve a complete independent prefix before a relative extension,
        # e.g. "تریدینگ‌ویو یک بخش کامیونیتی داره که ...". Never word-truncate.
        for boundary in re.finditer(r"\s+که\s+", clause):
            prefix = clause[:boundary.start()].strip()
            if is_complete_statement(prefix, rule):
                result.append(prefix)
                break
    return result


def _matching_complete_continuation(
    segments: list[dict[str, Any]],
    selected_index: int,
    rule: TextRule,
    *,
    search_ahead: int = 40,
) -> dict[str, Any] | None:
    """Find a later corrected take that repeats the incomplete opening.

    Talking-head recordings commonly contain a false start followed by a full
    retake.  Matching requires the same first three normalized words; semantic
    similarity alone is intentionally insufficient.
    """
    seed = normalize_copy(segments[selected_index].get("text", "")).rstrip(".!؟?")
    seed_words = seed.split()
    if len(seed_words) < 3:
        return None
    prefix = [word.casefold() for word in seed_words[: min(5, len(seed_words))]]
    stop = min(len(segments), selected_index + 1 + search_ahead)
    for start in range(selected_index + 1, stop):
        collected: list[str] = []
        collected_ids: list[int] = []
        for offset in range(5):
            position = start + offset
            if position >= stop:
                break
            value = normalize_copy(segments[position].get("text", ""))
            if not value:
                continue
            collected.append(value)
            collected_ids.append(int(segments[position]["id"]))
            combined = normalize_copy(" ".join(collected))
            candidate_words = [word.casefold() for word in combined.rstrip(".!؟?").split()]
            shared = min(len(prefix), len(candidate_words))
            same_opening = shared >= 3 and candidate_words[:shared] == prefix[:shared]
            if same_opening and is_complete_statement(combined, rule):
                return {
                    "text": combined if combined.endswith((".", "!", "؟", "?")) else combined + ".",
                    "source": "later-corrected-take",
                    "segment_ids": collected_ids,
                    "source_text": combined,
                    "grounding": {"supported": True, "content_token_coverage": 1.0, "numbers_locked": True, "latin_terms_locked": True},
                    "rewritten": False,
                    "needs_manual_copy": False,
                    "anchor_segment_id": int(segments[start]["id"]),
                    "anchor_start": float(segments[start].get("start", 0.0)),
                }
    return None


def curate_complete_statement(
    segments: list[dict[str, Any]],
    selected_index: int,
    editorial_candidates: Iterable[Any] = (),
    rule: TextRule = DEFAULT_TEXT_RULE,
) -> dict[str, Any] | None:
    """Approve complete display copy while preserving the speaker's register.

    Source-faithful mode never accepts generated wording.  The optional
    grounded-summary mode accepts a proposal only when its content words,
    numbers and identifiers are supported by the local transcript window.
    """
    collected: list[str] = []
    collected_ids: list[int] = []
    source_window = [normalize_copy(item.get("text", "")) for item in segments[selected_index:selected_index + 3]]
    exact_source = " ".join(source_window)
    for candidate in editorial_candidates:
        proposed = normalize_copy(candidate).rstrip(".!؟?")
        position = exact_source.find(proposed) if proposed else -1
        if (proposed and 0 <= position < len(source_window[0])
                and is_complete_statement(proposed, rule)):
            return {"text": proposed + ".", "source": "speaker-exact-selection",
                    "segment_ids": [int(segments[selected_index]["id"])], "source_text": exact_source,
                    "grounding": {"supported": True, "content_token_coverage": 1.0, "numbers_locked": True, "latin_terms_locked": True},
                    "rewritten": False, "needs_manual_copy": False}
    for offset in range(5):
        position = selected_index + offset
        if position >= len(segments):
            break
        text = normalize_copy(segments[position].get("text", ""))
        if not text:
            continue
        if offset > 0 and collected and re.search(r"[.!؟?]$", collected[-1]):
            break
        if offset > 0 and any(cue in text.casefold() for cue in RESTART_CUES):
            break
        collected.append(text)
        collected_ids.append(int(segments[position]["id"]))
        combined = normalize_copy(" ".join(collected))
        if is_complete_statement(combined, rule):
            return {
                "text": combined if combined.endswith((".", "!", "؟", "?")) else combined + ".",
                "source": "speaker-exact",
                "segment_ids": list(collected_ids),
                "source_text": combined,
                "grounding": {"supported": True, "content_token_coverage": 1.0, "numbers_locked": True, "latin_terms_locked": True},
                "rewritten": False,
                "needs_manual_copy": False,
            }
        # Only actual punctuation or an independently complete relative-clause
        # prefix is a boundary. The clause must start in the selected segment.
        local_clauses = _anchored_complete_clauses(collected, rule)
        if local_clauses:
            best = local_clauses[0]
            return {"text": best.rstrip(".!؟?") + ".", "source": "speaker-clause",
                    "segment_ids": list(collected_ids), "source_text": combined,
                    "grounding": {"supported": True, "content_token_coverage": 1.0, "numbers_locked": True, "latin_terms_locked": True},
                    "rewritten": False, "needs_manual_copy": False}

    corrected_take = _matching_complete_continuation(segments, selected_index, rule)
    if corrected_take:
        return corrected_take

    copy_mode = os.environ.get("HERMES_COPY_MODE", "source-faithful").casefold()
    source_window = [
        normalize_copy(segments[position].get("text", ""))
        for position in range(max(0, selected_index - 1), min(len(segments), selected_index + 4))
    ]
    if copy_mode == "grounded-summary":
        for candidate in editorial_candidates:
            proposed = normalize_copy(candidate)
            grounding = copy_grounding(proposed, source_window)
            if is_complete_statement(proposed, rule) and grounding["supported"]:
                return {
                    "text": proposed if proposed.endswith((".", "!", "؟", "?")) else proposed + ".",
                    "source": "grounded-summary",
                    "segment_ids": [int(segments[selected_index]["id"])],
                    "source_text": " ".join(source_window),
                    "grounding": grounding,
                    "rewritten": True,
                    "needs_manual_copy": False,
                }
    return {
        "text": "…",
        "source": "manual-placeholder",
        "segment_ids": [int(segments[selected_index]["id"])],
        "source_text": " ".join(source_window),
        "grounding": {"supported": False, "content_token_coverage": 0.0, "numbers_locked": True, "latin_terms_locked": True},
        "rewritten": False,
        "needs_manual_copy": True,
    }


def project_personal_asset_root() -> Path:
    return Path(__file__).resolve().parents[3] / "personal-assets"


def personal_asset_root() -> Path:
    explicit = os.environ.get("HERMES_PERSONAL_ASSET_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local / "Hafez Studio" / "assets"


def personal_asset_roots() -> list[Path]:
    """Return curated roots without downloading or inventing any asset."""
    roots: list[Path] = []
    explicit = os.environ.get("HERMES_PERSONAL_ASSET_ROOT", "").strip()
    if explicit:
        roots.append(Path(explicit).expanduser())
    project_root = project_personal_asset_root()
    if project_root.exists():
        roots.append(project_root)
    default_root = personal_asset_root()
    if default_root not in roots:
        roots.append(default_root)
    return roots


def resolve_text_animation_title() -> Path | None:
    explicit = os.environ.get("HERMES_TEXT_ANIMATION_ROOT", "").strip()
    roots = [Path(explicit).expanduser()] if explicit else []
    motion_pack = os.environ.get("HERMES_MOTION_PACK", "").strip()
    if motion_pack:
        roots.append(Path(motion_pack).expanduser())
    roots.append(Path(__file__).resolve().parents[3] / "motion-pack" / "dist")
    for asset_root in personal_asset_roots():
        roots.extend(
            (
                asset_root / "Text Animation" / "MOGRTs",
                asset_root / "mogrt" / "Text Animation",
            )
        )
    for root in roots:
        candidate = root / TEXT_ANIMATION_TITLE.template_name
        if candidate.is_file():
            return candidate
    return None


def resolve_text_animation_sfx(asset_name: str = TEXT_ANIMATION_SFX.asset_name) -> Path | None:
    explicit = os.environ.get("HERMES_TEXT_ANIMATION_SFX_ROOT", "").strip()
    roots = [Path(explicit).expanduser()] if explicit else []
    template_root = os.environ.get("HERMES_TEXT_ANIMATION_ROOT", "").strip()
    if template_root:
        roots.append(Path(template_root).expanduser().parent / "Sound Effects")
    for asset_root in personal_asset_roots():
        roots.extend(
            (
                asset_root / "Text Animation" / "Sound Effects",
                asset_root / "sfx" / "Text Animation",
            )
        )
    for root in roots:
        candidate = root / asset_name
        if candidate.is_file():
            return candidate
    return None


def resolve_relaxe_font() -> Path | None:
    explicit = os.environ.get("HERMES_ENGLISH_TITLE_FONT_PATH", "").strip()
    candidates = [Path(explicit).expanduser()] if explicit else []
    for asset_root in personal_asset_roots():
        candidates.extend(
            (
                asset_root / "fonts" / "Relaxe-Hafez.ttf",
                asset_root / "fonts" / "Relaxe.ttf",
                asset_root / "fonts" / "Relaxe.otf",
            )
        )
    return next((path for path in candidates if path.is_file()), None)


def inspect_mogrt_asset(path: str | Path) -> dict[str, Any]:
    """Fail closed when a selected MOGRT contains a forbidden Grain asset/effect."""
    asset = Path(path)
    if not asset.is_file():
        raise FileNotFoundError(asset)
    forbidden_ascii = b"grain"
    forbidden_utf16 = "grain".encode("utf-16-le")
    scanned_entries: list[str] = []
    exposed_controls: list[str] = []
    font_controls: dict[str, dict[str, bool]] = {}
    with zipfile.ZipFile(asset) as archive:
        for info in archive.infolist():
            if info.file_size > 64 * 1024 * 1024:
                continue
            payload = archive.read(info)
            lowered = payload.lower()
            if forbidden_ascii in lowered or forbidden_utf16 in lowered:
                raise ValueError(f"Forbidden visual texture found in curated MOGRT entry: {info.filename}")
            scanned_entries.append(info.filename)
            if info.filename.casefold().endswith("definition.json"):
                definition = json.loads(payload.decode("utf-8-sig"))
                text = json.dumps(definition, ensure_ascii=False)
                for client_control in definition.get("clientControls", []):
                    if not isinstance(client_control, dict) or int(client_control.get("type", -1)) != 6:
                        continue
                    labels = client_control.get("uiName", {}).get("strDB", [])
                    label = str(labels[0].get("str", "")) if labels else ""
                    font_info = client_control.get("fonteditinfo", {})
                    if label and isinstance(font_info, dict):
                        font_controls[label] = {
                            "font_family_editable": bool(font_info.get("capPropFontEdit")),
                            "font_size_editable": bool(font_info.get("capPropFontSizeEdit")),
                        }
                for control in (
                    TEXT_ANIMATION_TITLE.english_control,
                    TEXT_ANIMATION_TITLE.persian_control,
                    TEXT_ANIMATION_TITLE.position_control,
                    TEXT_ANIMATION_TITLE.scale_control,
                ):
                    if control in text:
                        exposed_controls.append(control)
    required = {
        TEXT_ANIMATION_TITLE.english_control,
        TEXT_ANIMATION_TITLE.persian_control,
        TEXT_ANIMATION_TITLE.position_control,
        TEXT_ANIMATION_TITLE.scale_control,
    }
    if not required.issubset(exposed_controls):
        raise ValueError("Curated title MOGRT does not expose the required editable controls")
    for text_control in (TEXT_ANIMATION_TITLE.english_control, TEXT_ANIMATION_TITLE.persian_control):
        status = font_controls.get(text_control, {})
        if not status.get("font_family_editable") or not status.get("font_size_editable"):
            raise ValueError(f"Curated title MOGRT does not expose font family/size editing for {text_control}")
    return {
        "path": str(asset.resolve()),
        "grain_free": True,
        "editable_controls": sorted(set(exposed_controls)),
        "font_controls": font_controls,
        "scanned_entries": scanned_entries,
    }


def curator_history_path() -> Path:
    explicit = os.environ.get("HERMES_CURATOR_HISTORY", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local / "Hafez Studio" / "curator-family-history.json"


def load_template_family_history(path: str | Path | None = None) -> list[str]:
    source = Path(path) if path else curator_history_path()
    if not source.is_file():
        return []
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    values = payload.get("families", []) if isinstance(payload, dict) else []
    return [str(value) for value in values if str(value).strip()][:4]


def select_template_families(
    cues: Iterable[dict[str, Any]],
    history: Iterable[str] = (),
    *,
    limit: int = 4,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep a stable, high-value visual identity of at most four families."""
    items = [dict(cue) for cue in cues]
    bounded_limit = max(1, min(4, int(limit)))
    family_counts = Counter(str(cue.get("template_family", "hafez-statement")) for cue in items)
    first_seen: dict[str, int] = {}
    scores: Counter[str] = Counter()
    for index, cue in enumerate(items):
        family = str(cue.get("template_family", "hafez-statement"))
        first_seen.setdefault(family, index)
        scores[family] += 2.0
        if str(cue.get("priority", "normal")) == "high":
            scores[family] += 4.0
        if str(cue.get("kind", "")) in {"flowchart", "compare", "chapter", "hook"}:
            scores[family] += 5.0
        if bool(cue.get("required_by_trigger", False)):
            scores[family] += 100.0
    present = set(family_counts)
    selected: list[str] = []
    required_families = [
        str(cue.get("template_family", "hafez-statement"))
        for cue in items
        if bool(cue.get("required_by_trigger", False))
    ]
    for family in required_families:
        if family in present and family not in selected:
            selected.append(family)
        if len(selected) >= bounded_limit:
            break
    for family in history:
        value = str(family)
        if value in present and value not in selected:
            selected.append(value)
        if len(selected) >= bounded_limit:
            break
    ranked = sorted(present, key=lambda family: (-scores[family], first_seen[family], family))
    for family in ranked:
        if family not in selected:
            selected.append(family)
        if len(selected) >= bounded_limit:
            break
    curated = [cue for cue in items if str(cue.get("template_family", "hafez-statement")) in selected]
    metadata = {
        "limit": bounded_limit,
        "selected": selected,
        "history_preferred": [family for family in history if str(family) in selected],
        "omitted_cue_ids": [str(cue.get("id", "")) for cue in items if cue not in curated],
        "family_counts": dict(family_counts),
    }
    return curated, metadata


def save_template_family_history(
    families: Iterable[str],
    path: str | Path | None = None,
) -> Path:
    destination = Path(path) if path else curator_history_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    unique: list[str] = []
    for family in families:
        value = str(family).strip()
        if value and value not in unique:
            unique.append(value)
        if len(unique) >= 4:
            break
    destination.write_text(
        json.dumps({"version": 1, "families": unique}, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    return destination


def bilingual_typography_contract(
    *,
    english_title: str,
    persian_statement: str,
    persian_font_family: str,
) -> dict[str, Any]:
    """Return an explicit editable bilingual typography contract."""
    return {
        "layout": "stacked-en-fa",
        "english": {
            "text": english_title.strip().upper(),
            "font_family": "Relaxe",
            "font_path": str(resolve_relaxe_font() or ""),
            "adobe_host_default": "Arial Bold",
            "relaxe_override_required": True,
            "compatibility_status": "blocked-by-adobe-2026-font-crash",
            "role": "display-title",
            "editable": True,
        },
        "persian": {
            "text": persian_statement,
            "font_family": persian_font_family,
            "role": "semantic-subtitle",
            "editable": True,
        },
        "motion": asdict(TEXT_ANIMATION_TITLE.motion),
    }


def template_rule_payload(rule: TemplateRule = TEXT_ANIMATION_TITLE) -> dict[str, Any]:
    payload = asdict(rule)
    payload["motion"] = asdict(rule.motion)
    return payload
