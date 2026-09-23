"""Build one conservative, editable Premiere MOGRT review plan for C3009.

This does not mark the whole edit publication-ready.  It promotes only the
native-QA-approved Glass Insight cue, uses a short verbatim Persian phrase,
and preserves the original full-frame tracking evidence for owner review in
Premiere.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


SOURCE = Path(
    r"C:\Users\1SKY.IR\Videos\Hafez Studio Outputs\20260922-115656-C3009-EUL9E"
    r"\F_Hafez_Youtube_9thvid_C3009.premiere-plan.json"
)
OUTPUT = Path(
    r"C:\Users\1SKY.IR\.n8n\products\HafezStudio\proof"
    r"\c3009-motion-review-20260922-01\C3009-editable-motion-review.premiere-plan.json"
)
PERSIAN = "آیا سیستم داری؟"
ENGLISH = "DO YOU HAVE A SYSTEM?"
EXPECTED_ASSET_SHA256 = "ef9ea80cf7bde54711cf2991324ebdb05d141f103fd96d10e95422086a760da5"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    plan = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    if plan.get("protocol") != "hermes-professional-edit-v2":
        raise RuntimeError("Unexpected plan protocol")

    matches = [item for item in plan.get("graphics", []) if item.get("id") == "graphic-018"]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one graphic-018 cue")

    cue = copy.deepcopy(matches[0])
    provenance = cue.get("copy_provenance", {})
    source_text = str(provenance.get("source_text", ""))
    if PERSIAN not in source_text:
        raise RuntimeError("The proposed Persian copy is not verbatim in the source segment")

    contract = cue.get("native_runtime_contract", {})
    if contract.get("status") != "native-qa-approved":
        raise RuntimeError("Template is not native-QA-approved")
    template_path = Path(cue["template_layers"][0]["template_path"])
    actual_sha = sha256(template_path)
    if actual_sha != EXPECTED_ASSET_SHA256 or contract.get("assetSha256") != actual_sha:
        raise RuntimeError("MOGRT asset hash does not match the approved runtime contract")

    layout = cue.get("layout", {})
    if not layout.get("safe_area_contained"):
        raise RuntimeError("Tracked placement is outside the title-safe area")
    if float(layout.get("tracking_coverage", 0)) < 1.0:
        raise RuntimeError("Full visible-frame tracking evidence is incomplete")
    if float(layout.get("face_overlap_ratio", 1)) != 0.0:
        raise RuntimeError("Tracked placement intersects the face union")
    if float(layout.get("safe_margin_overlap_ratio", 1)) != 0.0:
        raise RuntimeError("Tracked placement intersects the protected subject union")

    cue.update(
        id="graphic-018-owner-motion-review",
        text=PERSIAN,
        headline_fa=PERSIAN,
        kicker_en=ENGLISH,
        headline_en=ENGLISH,
        needs_manual_copy=False,
        review_blocked=False,
        review_blocked_reason="",
        qa_flags=[],
        sfx="none-owner-motion-review",
        editorial_reason="Short verbatim source phrase; native editable motion review.",
        preview_status="premiere-native-review-required",
    )
    cue["copy_provenance"]["display_text"] = PERSIAN
    cue["copy_provenance"]["mode"] = "verbatim-source-subphrase"
    cue["copy_provenance"]["grounding"] = {
        "supported": True,
        "content_token_coverage": 1.0,
        "numbers_locked": True,
        "latin_terms_locked": True,
    }
    cue["bilingual_typography"]["english"]["text"] = ENGLISH
    cue["bilingual_typography"]["persian"]["text"] = PERSIAN
    cue["native_typography_fit"] = {
        "profile": contract["typography"]["profile"],
        "status": "review-ready-short-literal",
        "reason": "Short bilingual copy retained without truncation; Premiere owner review required.",
    }
    cue["layout"]["collision_free"] = True
    cue["layout"]["transform_status"] = "screen-space-mogrt-owner-review"
    cue["layout"]["collision_policy"] = "tracked-union-zero-overlap-owner-review"

    for controls in (cue["controls"], cue["template_layers"][0]["controls"]):
        controls["Title"] = ENGLISH
        controls["Body"] = PERSIAN
        controls["Duration Seconds"] = round(float(cue["end"]) - float(cue["start"]), 3)
    cue["controls"]["FA Headline"] = PERSIAN

    review_plan = copy.deepcopy(plan)
    review_plan["graphics"] = [cue]
    review_plan["sfx_cues"] = []
    review_plan["purpose"] = "owner-requested-native-motion-review"
    review_plan["publication_ready"] = False
    review_plan["review_note"] = (
        "One editable native MOGRT only. Verify appearance, tracking-safe placement, "
        "font and animation in Premiere before approving broader automatic insertion."
    )
    review_plan["source_plan"] = str(SOURCE)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(review_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "sequence": review_plan["sequence"],
        "cue": cue["id"],
        "start": cue["start"],
        "end": cue["end"],
        "template": str(template_path),
        "asset_sha256": actual_sha,
        "tracking_frames": cue["layout"]["tracking_sample_count"],
        "face_overlap_ratio": cue["layout"]["face_overlap_ratio"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
