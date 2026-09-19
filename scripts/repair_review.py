"""Retry selected Hafez AI review tasks and merge them into a legacy JSON review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PRODUCT_ROOT / "engine" / "src" / "hermes_video"
sys.path.insert(0, str(ENGINE_DIR))

import subtitle_pipeline as review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--task", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
    resolved_path = Path(manifest["outputs"]["resolved_review"])
    merged = json.loads(resolved_path.read_text(encoding="utf-8-sig"))
    tasks = {str(item["task_id"]): item for item in manifest.get("review_tasks", [])}
    repaired: list[dict[str, object]] = []

    for task_id in args.task:
        task = tasks.get(task_id)
        if task is None:
            raise KeyError(f"Unknown review task: {task_id}")
        print(f"REPAIR_TASK_START {task_id}", flush=True)
        parsed = None
        error = None
        for budget in (1900, 2400):
            parsed, error = review._call_local_json(
                str(task.get("prompt", "")),
                num_predict=budget,
                model=review.LOCAL_FAST_MODEL,
                num_ctx=12288,
                timeout=720,
            )
            if review._task_response_is_valid(str(task.get("task_type", "")), parsed):
                repaired.append({"task_id": task_id, "budget": budget, "valid": True})
                break
            print(f"REPAIR_TASK_RETRY {task_id} budget={budget}", flush=True)
        else:
            raise RuntimeError(f"Task {task_id} remained invalid: {error or 'invalid JSON'}")

        assert isinstance(parsed, dict)
        task_type = str(task.get("task_type", ""))
        if task_type == "subtitle":
            by_id = {int(item["id"]): item for item in merged.get("segments", []) if "id" in item}
            for item in parsed.get("segments", []):
                by_id[int(item["id"])] = item
            merged["segments"] = list(by_id.values())
        elif task_type == "editor":
            for key in ("events", "edits", "markers"):
                merged.setdefault(key, []).extend(parsed.get(key, []))
        elif task_type == "youtube":
            merged.setdefault("youtube", {}).update(parsed.get("youtube", {}))
        print(f"REPAIR_TASK_DONE {task_id}", flush=True)

    merged["repair_audit"] = repaired
    output = Path(args.output)
    output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "tasks": repaired}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
