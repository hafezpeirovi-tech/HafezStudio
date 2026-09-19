"""Create a separate, reversible native layout / safe-system-font test."""
import json
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "proof/glass-pack-20260913-01"
plan = json.loads((out / "font-ab.plan.json").read_text(encoding="utf-8"))
plan["qa_notes"] = ["Tahoma/Arial provisional native compatibility test; final font pair awaits owner choice."]
for cue in plan["graphics"]:
    for layer in cue["template_layers"]:
        if cue["id"] == "glass-data-qa":
            layer["native_motion_scale"] = 70
        for binding in layer["typed_controls"]:
            if binding["kind"] == "text":
                binding["font"] = "Tahoma" if any("\u0600" <= ch <= "\u06ff" for ch in binding["value"]) else "ArialMT"

def save(name, data):
    with (out / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)

save("review-layout.plan.json", plan)
for mode in ("apply", "inspect"):
    save(f"review-layout-{mode}.request.json", {
        "mode": mode, "request_id": f"glass-layout-{mode}-20260913-01",
        "plan_path": str(out / "review-layout.plan.json"),
        "expected_project_path": plan["expected_project_path"],
        "expected_sequence_name": plan["sequence"],
        "expected_sequence_id": plan["expected_sequence_id"], "mute_guide": False,
    })
print("Reversible layout/font test prepared.")
