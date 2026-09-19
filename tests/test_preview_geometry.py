import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import professional_edit as edit


class PreviewGeometryTests(unittest.TestCase):
    def cue(self, **changes):
        return {"id": "review-only", "kind": "statement", "text": "A complete statement.",
                "controls": {"Body": "A complete statement."}, "start": 1, "end": 4,
                "layout": {"max_width": 420, "max_height": 240}, **changes}

    def test_blocked_cue_keeps_editable_data_without_rendering_a_preview(self):
        for kind in ("statement", "flowchart", "subscribe"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                cue = self.cue(kind=kind, review_blocked=True,
                               review_blocked_reason="No safe native placement",
                               layout={"max_width": 100, "max_height": 20},
                               asset_path="stale-preview.png")
                original = copy.deepcopy(cue)
                with patch.object(edit.Image, "new", side_effect=AssertionError("Blocked preview rendered")):
                    result = edit.render_graphic_assets([cue], folder, 1280, 720)
                self.assertEqual(cue, original)
                self.assertTrue(result[0]["review_blocked"])
                self.assertEqual(result[0]["controls"], original["controls"])
                self.assertEqual(result[0]["preview_status"], "skipped-review-blocked")
                self.assertNotIn("asset_path", result[0])
                self.assertEqual(list(Path(folder).glob("*.png")), [])

    def test_invalid_or_tiny_preview_geometry_never_reaches_pillow(self):
        for key, value in (("max_height", 0), ("max_height", -20), ("max_height", 20),
                           ("max_height", 39), ("max_width", 0), ("max_width", 12),
                           ("max_width", 2000), ("max_height", float("nan")),
                           ("max_height", float("inf")), ("max_height", None),
                           ("max_height", "bad"), ("x", float("nan")), ("y", float("inf"))):
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as folder:
                cue = self.cue()
                cue["layout"][key] = value
                with patch.object(edit.Image, "new", side_effect=AssertionError("Invalid preview rendered")):
                    result = edit.render_graphic_assets([cue], folder, 1280, 720)
                self.assertEqual(result[0]["preview_status"], "skipped-invalid-geometry")
                self.assertEqual(result[0]["controls"], cue["controls"])
                self.assertNotIn("asset_path", result[0])
                self.assertNotIn("review_blocked", result[0])

    def test_valid_preview_still_renders_and_remains_preview_only(self):
        with tempfile.TemporaryDirectory() as folder:
            result = edit.render_graphic_assets([self.cue()], folder, 1280, 720)
            self.assertTrue(Path(result[0]["asset_path"]).is_file())
            self.assertNotIn("review_blocked", result[0])


if __name__ == "__main__":
    unittest.main()
