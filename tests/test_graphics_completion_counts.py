"""Completion must not advertise review-blocked proposals as usable graphics."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import studio_cli
from autocut import write_edit_notes


class GraphicsCompletionCountsTests(unittest.TestCase):
    def test_notes_distinguish_proposals_from_native_insertions(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "notes.md"
            cues = [{"start": 2, "text": "Original long source", "controls": {"Title": "SMART\rTRADER", "Body": "تریدر باهوش"}},
                    {"start": 4, "text": "…", "review_blocked": True, "review_blocked_reason": "Copy | unverified"},
                    {"start": 6, "text": "Another", "layout": {"collision_free": False}}]
            write_edit_notes(str(target), {}, {}, {}, {}, [], graphics=cues)
            notes = target.read_text(encoding="utf-8-sig")
            self.assertIn("تعداد پیشنهادهای گرافیکی: 3", notes)
            self.assertIn("آمادهٔ درخواست درج MOGRT: 1", notes)
            self.assertIn("مسدود/نیازمند بازبینی: 2", notes)
            self.assertIn("SMART TRADER / تریدر باهوش", notes)
            self.assertNotIn("گرافیک واقعی روی تصویر", notes)
            self.assertNotIn("V3 راهنمای PNG", notes)
            self.assertIn("Copy - unverified", notes)

    def summarize(self, cues):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "fixture.mogrt"
            template.write_bytes(b"Existence fixture; not a native MOGRT verification")
            graphics = copy.deepcopy(cues)
            for cue in graphics:
                cue.setdefault("template_path", str(template))
                for layer in cue.get("template_layers", []):
                    layer.setdefault("template_path", str(template))
            files = {k: root / n for k, n in {
                "professional_plan": "plan.json", "xml": "cut.xml",
                "tight_srt": "cut.srt", "youtube": "youtube.md"}.items()}
            plan = {"sequence": "03 - Hafez Director Cut", "graphics": graphics,
                    "camera_schedule": [{"start": 0, "end": 12, "camera": "cam1"}]}
            files["professional_plan"].write_text(json.dumps(plan), encoding="utf-8")
            files["xml"].write_text(
                '<xmeml><sequence><name>03 - Hafez Director Cut</name><duration>360</duration>'
                '<rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate></sequence></xmeml>', encoding="utf-8")
            files["tight_srt"].write_text("1\n00:00:00,000 --> 00:00:01,000\nSource text\n", encoding="utf-8")
            files["youtube"].write_text("# Draft YouTube package\n", encoding="utf-8")
            manifest = root / "edit.json"
            manifest.write_text(json.dumps({"timeline_duration": 12, "mapped_words": [{"text": "word"}],
                                            "outputs": {k: str(v) for k, v in files.items()}}), encoding="utf-8")
            before = {p: p.read_bytes() for p in [manifest, *files.values()]}
            summary = studio_cli.validate_job_outputs(manifest)
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertFalse(summary["publicationReady"])
            return summary

    def test_typography_blocked_only_is_zero_usable_not_one_success(self):
        result = self.summarize([{"kind": "statement", "review_blocked": True,
                                  "needs_manual_copy": False}])
        self.assertEqual(0, result["graphics"])
        self.assertEqual(0, result["editableMogrtLayers"])
        self.assertEqual({}, result["graphicKinds"])
        self.assertEqual(1, result["plannedGraphics"])
        self.assertEqual(1, result["blockedGraphics"])
        self.assertEqual(1, result["graphicsReviewRequired"])
        self.assertEqual(0, result["copyReviewRequired"])

    def test_mixed_counts_exclude_blocked_layers_and_kinds(self):
        result = self.summarize([
            {"kind": "hook", "template_layers": [{}, {}]},
            {"kind": "statement", "review_blocked": True, "template_layers": [{}, {}, {}]},
            {"kind": "title", "needs_manual_copy": True},
        ])
        self.assertEqual(2, result["graphics"])
        self.assertEqual(3, result["editableMogrtLayers"])
        self.assertEqual({"hook": 1, "title": 1}, result["graphicKinds"])
        self.assertEqual(3, result["plannedGraphics"])
        self.assertEqual(1, result["blockedGraphics"])
        self.assertEqual(2, result["graphicsReviewRequired"])
        self.assertEqual(1, result["copyReviewRequired"])

    def test_collision_rejected_by_finisher_is_also_not_usable(self):
        result = self.summarize([{"kind": "hook", "layout": {"collision_free": False}}])
        self.assertEqual(0, result["graphics"])
        self.assertEqual(1, result["blockedGraphics"])

    def test_double_reason_is_counted_once(self):
        result = self.summarize([{"review_blocked": True, "needs_manual_copy": True,
                                  "layout": {"collision_free": False}}])
        self.assertEqual(1, result["graphicsReviewRequired"])
        self.assertEqual(1, result["blockedGraphics"])

    def test_normal_legacy_plan_retains_usable_counts(self):
        result = self.summarize([{"kind": "hook"}])
        self.assertEqual(1, result["graphics"])
        self.assertEqual(1, result["editableMogrtLayers"])
        self.assertEqual(0, result["blockedGraphics"])
        self.assertEqual(0, result["graphicsReviewRequired"])


if __name__ == "__main__":
    unittest.main()
