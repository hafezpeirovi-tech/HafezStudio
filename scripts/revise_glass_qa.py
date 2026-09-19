"""Preserve baseline evidence; produce an isolated native font A/B revision."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proof/glass-pack-20260913-01"
plan = json.loads((OUT / "baseline.plan.json").read_text(encoding="utf-8"))
plan["expected_sequence_id"] = "8e0d1a31-eb21-479b-865c-ac5974ba4fd1"
plan["fps"] = 30000 / 1001
plan["qa_notes"] = ["Arial native renderer diagnostic; NOT final font selection or production approval."]
for cue in plan["graphics"]:
    for key in ("start", "end"):
        cue[key] = round(cue[key] * plan["fps"]) / plan["fps"]
    for layer in cue["template_layers"]:
        for binding in layer["typed_controls"]:
            if binding["kind"] == "text":
                binding["font"] = "ArialMT"

def save(name, data):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)

save("font-ab.plan.json", plan)
for mode in ("apply", "inspect"):
    save(f"font-ab-{mode}.request.json", {
        "mode": mode, "request_id": f"glass-font-ab-{mode}-20260913-01",
        "plan_path": str(OUT / "font-ab.plan.json"),
        "expected_project_path": plan["expected_project_path"],
        "expected_sequence_name": plan["sequence"],
        "expected_sequence_id": plan["expected_sequence_id"], "mute_guide": False,
    })
print("Font A/B request prepared; source MOGRTs and baseline unchanged.")
