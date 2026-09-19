import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import professional_edit as edit
from rough_cut import remap_segments


def marker(segment_id):
    return {"segment_id": segment_id, "type": "GRAPHIC", "visual_kind": "statement",
            "element_id": "hermes-glass-insight", "confidence": 0.9}


class GraphicReviewGateTests(unittest.TestCase):
    def test_unresolved_copy_is_an_editable_blocked_draft_without_sfx(self):
        source = [{"id": 0, "start": 0, "end": 4, "text": "این بخش نامفهوم برای"}]
        with patch.object(edit, "build_sfx_cue") as sfx:
            cues = edit.build_graphic_cues(source, 40, [marker(0)], family_history=[])
        self.assertEqual(len(cues), 1)
        cue = cues[0]
        self.assertEqual(cue["text"], "…")
        self.assertTrue(cue["needs_manual_copy"])
        self.assertTrue(cue["review_blocked"])
        self.assertIn("source-audio review", cue["review_blocked_reason"])
        self.assertTrue(any(value == "…" for layer in cue["template_layers"]
                            for value in layer["controls"].values()))
        self.assertNotIn("sfx_cue", cue)
        self.assertEqual(cue["sfx"], "none-review-blocked")
        sfx.assert_not_called()
        self.assertEqual(cue["family_identity"]["selected"], [])
        self.assertEqual(edit.build_action_markers([], [], cues)[0]["type"], "CHECK")

    def test_sfx_builder_itself_fails_closed_before_resolving_an_asset(self):
        for flags in ({"review_blocked": True}, {"needs_manual_copy": True}):
            with self.subTest(flags=flags), patch.object(edit, "recipe_asset") as asset:
                self.assertIsNone(edit.build_sfx_cue({"id": "draft", "start": 12, **flags}, 30))
                asset.assert_not_called()

    def test_later_corrected_take_uses_the_remapped_tight_anchor(self):
        original = [
            {"id": 0, "start": 100, "end": 108, "text": "من این الگوریتم رو طوری ساختم که"},
            {"id": 1, "start": 108, "end": 112, "text": "نه بذار دوباره بگم"},
            {"id": 2, "start": 120, "end": 128, "text": "من این الگوریتم رو طوری ساختم که سیگنال رو سریع می‌فرسته"},
        ]
        mapped = remap_segments(original, [{"old_start": 100, "old_end": 140, "new_start": 10}], [], "tight")
        cues = edit.build_graphic_cues(mapped, 60, [marker(0)], fps=30, family_history=[])
        self.assertEqual(len(cues), 1)
        cue = cues[0]
        self.assertEqual(cue["requested_segment_id"], 0)
        self.assertEqual(cue["segment_id"], 2)
        self.assertEqual(cue["copy_segment_ids"], [2])
        self.assertEqual(cue["copy_source"], "later-corrected-take")
        self.assertEqual(cue["start"], 30)
        self.assertEqual(cue["sfx_cue"]["start_frame"], 900)
        self.assertFalse(cue["review_blocked"])

    def test_spacing_uses_corrected_take_not_the_old_false_start(self):
        source = [
            {"id": 0, "start": 0, "end": 2, "text": "من این الگوریتم رو طوری ساختم که"},
            {"id": 1, "start": 2, "end": 4, "text": "نه بذار دوباره بگم"},
            {"id": 2, "start": 30, "end": 32, "text": "این نکته درباره روش تحلیل مهم است"},
            {"id": 3, "start": 34, "end": 38, "text": "من این الگوریتم رو طوری ساختم که سیگنال رو سریع می‌فرسته"},
        ]
        with patch.dict(os.environ, {"HERMES_GRAPHIC_DENSITY": "max"}), patch.object(
            edit, "_importance", side_effect=lambda item, target: 100 if item["id"] == 0 else 0
        ):
            cues = edit.build_graphic_cues(source, 120, [marker(0), marker(2)], fps=30, family_history=[])
        self.assertEqual([cue["segment_id"] for cue in cues], [3])

    def test_duration_control_is_opt_in_only_after_native_qa(self):
        element = {"id": "hermes-glass-insight"}
        self.assertEqual(edit._catalog_runtime_controls(element, 4.2), {})
        contract = {"status": "native-qa-approved", "durationControl": "Duration Seconds", "responsiveTiming": True}
        self.assertEqual(edit._catalog_runtime_controls({**element, "runtimeContract": contract}, 3.75), {"Duration Seconds": 3.75})
        for candidate in (
            {**element, "runtimeContract": {**contract, "status": "pending-native-qa"}},
            {**element, "runtimeContract": {**contract, "responsiveTiming": False}},
            {"id": "hermes-title-hero-3", "runtimeContract": contract},
        ):
            self.assertEqual(edit._catalog_runtime_controls(candidate, 4.2), {})
        self.assertEqual(edit._catalog_runtime_controls({**element, "runtimeContract": contract}, float("nan")), {})

    def test_recorded_native_failure_blocks_subscribe_and_regular_templates(self):
        for element_id, spoken, markers in (
            ("hermes-subscribe", "سابسکرایب کن", []),
            ("hermes-glass-insight", "این نکته برای تحلیل مهم است", [marker(0)]),
        ):
            with self.subTest(element=element_id):
                catalog = json.loads(json.dumps(edit.load_editorial_catalog()))
                element = next(value for value in catalog["elements"] if value["id"] == element_id)
                element["runtimeContract"] = {"status": "native-qa-failed", "reason": "Rendered text differs from exposed controls."}
                if element_id == "hermes-subscribe":
                    element["defaultText"] = {"Channel Name": "Hafez-fx", "Channel Subtitle": "حافظ پیروی", "CTA Text": "سابسکرایب کن"}
                source = [{"id": 0, "start": 0, "end": 5, "text": spoken}]
                with patch.object(edit, "load_editorial_catalog", return_value=catalog), patch.object(edit, "build_sfx_cue") as sfx:
                    cues = edit.build_graphic_cues(source, 20, markers, family_history=[])
                cue = next(item for item in cues if item["element_id"] == element_id)
                self.assertTrue(cue["review_blocked"])
                self.assertEqual(cue["review_blocked_reason"], element["runtimeContract"]["reason"])
                self.assertIn("NATIVE_TEMPLATE_QA_FAILED", cue["qa_flags"])
                self.assertTrue(cue["template_layers"][0]["controls"])
                self.assertNotIn("sfx_cue", cue)
                sfx.assert_not_called()

    def test_authored_channel_identity_is_preserved_and_missing_text_not_invented(self):
        element = {"textSlots": ["Channel Name", "Channel Subtitle", "CTA Text"],
                   "defaultText": {"Channel Name": "Hafez-fx", "Channel Subtitle": "حافظ پیروی", "CTA Text": "سابسکرایب کن"}}
        controls = edit._catalog_control_values(element, persian_text="سابسکرایب کن", english_title="SUBSCRIBE")
        self.assertEqual(controls, element["defaultText"])
        missing = edit._catalog_control_values({"textSlots": element["textSlots"]}, persian_text="سابسکرایب کن", english_title="SUBSCRIBE")
        self.assertEqual(missing["Channel Subtitle"], "…")
        self.assertEqual(missing["Channel Name"], "…")

    def test_approved_duration_uses_actual_short_cue_at_timeline_end(self):
        catalog = edit.load_editorial_catalog()
        catalog = json.loads(json.dumps(catalog))
        glass = next(value for value in catalog["elements"] if value["id"] == "hermes-glass-insight")
        glass["runtimeContract"] = {"status": "native-qa-approved", "durationControl": "Duration Seconds", "responsiveTiming": True}
        source = [{"id": 0, "start": 9, "end": 10, "text": "این نکته برای تحلیل مهم است"}]
        with patch.object(edit, "load_editorial_catalog", return_value=catalog):
            cue = edit.build_graphic_cues(source, 10, [marker(0)], family_history=[])[0]
        self.assertEqual(cue["duration"], 1)
        self.assertEqual(cue["controls"]["Duration Seconds"], 1)
        self.assertEqual(cue["template_layers"][0]["controls"]["Duration Seconds"], 1)

    def test_written_plan_ignores_stale_sfx_and_family_on_blocked_draft(self):
        draft = {"id": "draft", "review_blocked": True, "template_family": "obsolete-draft-family",
                 "controls": {"Title": "…"}, "sfx_cue": {"graphic_id": "draft", "start": 0}}
        active = {"id": "active", "template_family": "approved-family", "sfx_cue": {"graphic_id": "active", "start": 4}}
        with tempfile.TemporaryDirectory() as directory, patch.object(edit, "save_template_family_history") as history:
            path = Path(directory) / "plan.json"
            history.return_value = Path(directory) / "history.json"
            edit.write_professional_plan(path, sequence_name="Test", fps=30, camera_schedule=[], events=[],
                                         graphics=[draft, active], history_path=history.return_value)
            result = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertEqual([item["graphic_id"] for item in result["sfx_cues"]], ["active"])
        self.assertEqual(result["curation"]["selected_template_families"], ["approved-family"])
        self.assertTrue(result["graphics"][0]["review_blocked"])


if __name__ == "__main__":
    unittest.main()
