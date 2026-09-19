import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import professional_edit as edit


class NativeTemplateReleaseGateTests(unittest.TestCase):
    def test_only_exact_existing_native_approval_status_is_released(self):
        self.assertEqual(edit._catalog_review_failure({
            "runtimeContract": {"status": "native-qa-approved"}
        }), "")
        for status in (None, "", "pending-native-qa", "unknown", "draft", "failed",
                       "approved", "native-qa-approved ", "NATIVE-QA-APPROVED",
                       True, [], {}):
            with self.subTest(status=status):
                self.assertIn("native QA", edit._catalog_review_failure({
                    "runtimeContract": {"status": status}
                }))

    def test_missing_legacy_or_malformed_contracts_do_not_self_authorize(self):
        for element in (None, {}, {"id": "legacy", "mogrtName": "Exists.mogrt"},
                        {"runtimeContract": None}, {"runtimeContract": []},
                        {"runtimeContract": "native-qa-approved"}):
            with self.subTest(element=element):
                self.assertIn("before automatic insertion", edit._catalog_review_failure(element))

    def test_recorded_native_failure_reason_is_preserved(self):
        self.assertEqual(edit._catalog_review_failure({"runtimeContract": {
            "status": "native-qa-failed", "reason": "Actual rendered control failed."
        }}), "Actual rendered control failed.")

    def test_current_approved_glass_remains_eligible_without_catalog_changes(self):
        catalog = edit.load_editorial_catalog()
        frozen = copy.deepcopy(catalog)
        glass = next(e for e in catalog["elements"] if e["id"] == "hermes-glass-insight")
        self.assertEqual(glass["runtimeContract"]["status"], "native-qa-approved")
        self.assertEqual(edit._catalog_review_failure(glass), "")
        marker = {"segment_id": 0, "type": "GRAPHIC", "visual_kind": "statement",
                  "element_id": "hermes-glass-insight", "confidence": .9}
        source = [{"id": 0, "start": 0, "end": 5, "text": "این نکته برای تحلیل مهم است"}]
        with patch.object(edit, "load_editorial_catalog", return_value=catalog), \
                patch.object(edit, "build_sfx_cue", return_value={"start_frame": 0, "role": "entry"}) as sfx:
            cues = edit.build_graphic_cues(source, 20, [marker], family_history=[])
        self.assertEqual(len(cues), 1)
        self.assertFalse(cues[0]["review_blocked"])
        self.assertEqual(cues[0]["element_id"], "hermes-glass-insight")
        self.assertTrue(cues[0]["family_identity"]["selected"])
        sfx.assert_called_once()
        self.assertEqual(catalog, frozen)

    def test_unqualified_regular_and_subscribe_keep_editable_drafts_but_no_sfx(self):
        for element_id, spoken in (("hermes-glass-insight", "این نکته برای تحلیل مهم است"),
                                    ("hermes-subscribe", "سابسکرایب کن")):
            for contract in (None, {}, {"status": "pending-native-qa"},
                             {"status": "unknown"}, {"status": "native-qa-failed"}):
                with self.subTest(element=element_id, contract=contract):
                    catalog = copy.deepcopy(edit.load_editorial_catalog())
                    element = next(e for e in catalog["elements"] if e["id"] == element_id)
                    if contract is None:
                        element.pop("runtimeContract", None)
                    else:
                        element["runtimeContract"] = contract
                    if element_id == "hermes-subscribe":
                        element["defaultText"] = {"Channel Name": "Hafez-fx",
                            "Channel Subtitle": "حافظ پیروی", "CTA Text": "سابسکرایب کن"}
                    markers = [] if element_id == "hermes-subscribe" else [{
                        "segment_id": 0, "type": "GRAPHIC", "visual_kind": "statement",
                        "element_id": element_id, "confidence": .9}]
                    with patch.object(edit, "load_editorial_catalog", return_value=catalog), \
                            patch.object(edit, "build_sfx_cue") as sfx:
                        cues = edit.build_graphic_cues([
                            {"id": 0, "start": 0, "end": 5, "text": spoken}
                        ], 20, markers, family_history=[])
                    cue = next(c for c in cues if c["element_id"] == element_id)
                    self.assertTrue(cue["review_blocked"])
                    self.assertTrue(cue["review_blocked_reason"])
                    self.assertTrue(cue["template_layers"][0]["controls"])
                    self.assertEqual(cue["family_identity"]["selected"], [])
                    self.assertNotIn("sfx_cue", cue)
                    self.assertEqual(cue["sfx"], "none-review-blocked")
                    sfx.assert_not_called()

    def test_uncatalogued_fallback_is_not_automatically_placed(self):
        source = [{"id": 0, "start": 0, "end": 5, "text": "این نکته برای تحلیل مهم است"}]
        marker = {"segment_id": 0, "type": "GRAPHIC", "visual_kind": "statement"}
        with patch.object(edit, "select_editorial_element", return_value=(None, {})), \
                patch.object(edit, "_template_for", return_value=("Unknown.mogrt", Path("Unknown.mogrt"))), \
                patch.object(edit, "build_sfx_cue") as sfx:
            cues = edit.build_graphic_cues(source, 20, [marker], family_history=[])
        self.assertEqual(len(cues), 1)
        self.assertTrue(cues[0]["review_blocked"])
        self.assertEqual(cues[0]["element_id"], "")
        self.assertFalse(cues[0]["element_mogrt_available"])
        self.assertTrue(cues[0]["template_layers"][0]["controls"])
        self.assertEqual(cues[0]["family_identity"]["selected"], [])
        sfx.assert_not_called()


if __name__ == "__main__":
    unittest.main()
