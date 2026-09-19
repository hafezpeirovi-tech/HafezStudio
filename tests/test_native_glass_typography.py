import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import professional_edit as edit


class MeasuredFont:
    def __init__(self, size):
        self.size = size

    def getbbox(self, text):
        return (0, 0, round(len(text) * self.size * 0.38), round(self.size * 0.75))


class NativeGlassTypographyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.asset = Path(self.folder.name) / "Hafez Hermes Glass Insight Review 8.mogrt"
        self.asset.write_bytes(b"native-glass-fixture")
        self.contract = {
            "status": "native-qa-approved", "responsiveTiming": True,
            "durationControl": "Duration Seconds",
            "assetSha256": hashlib.sha256(self.asset.read_bytes()).hexdigest(),
            "typography": {"profile": edit.NATIVE_GLASS_PROFILE},
        }
        self.controls = {"Title": "A VERIFIED TITLE", "Body": "This complete sentence must remain fully editable.",
                         "Layout Position": [270, 615], "Layout Scale": 60}
        self.cue = {"id": "generic", "element_id": "hermes-glass-insight",
                    "template": self.asset.name, "template_path": str(self.asset),
                    "start": 10.001, "end": 14.805, "kind": "statement", "text": self.controls["Body"],
                    "headline_fa": self.controls["Body"], "controls": dict(self.controls),
                    "native_runtime_contract": copy.deepcopy(self.contract),
                    "layout": {"scale": 60, "collision_free": True},
                    "sfx_cue": {"asset_path": "unchanged.wav", "start": 10, "start_frame": 300},
                    "copy_provenance": {"source_text": self.controls["Body"]},
                    "template_layers": [{"role": "catalog-curated-element", "template_path": str(self.asset),
                                         "controls": dict(self.controls), "text_controls": ["Title", "Body"]}]}
        self.addCleanup(patch.stopall)
        patch.object(edit, "_native_abar_font_path", return_value=Path("exact-abar.ttf")).start()
        patch.object(edit.ImageFont, "truetype", side_effect=lambda path, size: MeasuredFont(size)).start()

    def fit(self, **kwargs):
        edit._apply_native_glass_typography(self.cue, fps=kwargs.get("fps", 30000 / 1001), height=kwargs.get("height", 1080))

    def test_complete_words_maps_palette_and_typography_bounds_are_preserved(self):
        original = copy.deepcopy(self.cue)
        self.fit()
        self.assertFalse(self.cue.get("review_blocked"), self.cue.get("review_blocked_reason"))
        report = self.cue["native_typography_fit"]
        for slot in ("Title", "Body"):
            self.assertEqual(self.cue["controls"][slot].split(), original["controls"][slot].split())
            self.assertLessEqual(report["slots"][slot]["width"], 604)
            self.assertLessEqual(self.cue["controls"][slot + " · Line Spacing"], 100)
            self.assertEqual(self.cue["text_fonts"][slot], "AbarHighFaNum-Black")
            self.assertIn(slot + " · Text Color", self.cue["required_controls"])
        self.assertEqual(self.cue["headline_fa"], original["headline_fa"])
        self.assertEqual(self.cue["copy_provenance"], original["copy_provenance"])
        self.assertEqual(self.cue["template_layers"][0]["text_sizes"], self.cue["text_sizes"])
        title, body = report["slots"]["Title"], report["slots"]["Body"]
        self.assertLessEqual(-92 + title["height"] / 2 + 12, 42 - body["height"] / 2)
        self.assertGreaterEqual(title["screen_px_1080"], 28)
        self.assertGreaterEqual(body["screen_px_1080"], 30)

    def test_native_duration_and_sfx_share_frames_inside_the_tracked_interval(self):
        fps = 30000 / 1001
        self.fit(fps=fps)
        self.assertGreaterEqual(self.cue["start"], 10.001)
        self.assertLessEqual(self.cue["end"], 14.805)
        self.assertAlmostEqual(self.cue["start"] * fps, round(self.cue["start"] * fps))
        self.assertAlmostEqual(self.cue["end"] * fps, round(self.cue["end"] * fps))
        self.assertAlmostEqual(self.cue["controls"]["Duration Seconds"], self.cue["end"] - self.cue["start"])
        self.assertEqual(self.cue["sfx_cue"]["start_frame"], round(self.cue["start"] * fps))
        self.assertEqual(self.cue["sfx_cue"]["asset_path"], "unchanged.wav")

    def test_hd_and_4k_use_same_native_sizes_and_proportional_screen_pixels(self):
        second = copy.deepcopy(self.cue)
        self.fit(height=1080)
        edit._apply_native_glass_typography(second, fps=30000 / 1001, height=2160)
        self.assertEqual(self.cue["text_sizes"], second["text_sizes"])
        for slot in ("Title", "Body"):
            self.assertAlmostEqual(second["native_typography_fit"]["slots"][slot]["screen_px"],
                                   2 * self.cue["native_typography_fit"]["slots"][slot]["screen_px"])

    def test_narrow_safe_region_blocks_instead_of_shrinking_below_readable_minimum(self):
        self.cue["layout"]["scale"] = 15
        self.fit()
        self.assertTrue(self.cue["review_blocked"])
        self.assertNotIn("sfx_cue", self.cue)
        self.assertEqual(self.cue["controls"]["Body"], self.controls["Body"])

    def test_long_unbroken_token_and_long_clause_never_truncate(self):
        for text in ("W" * 200, " ".join(["whole"] * 80)):
            with self.subTest(text=text[:20]):
                cue = copy.deepcopy(self.cue)
                cue["template_layers"][0]["controls"]["Body"] = text
                cue["controls"]["Body"] = text
                edit._apply_native_glass_typography(cue, fps=30, height=1080)
                self.assertTrue(cue["review_blocked"])
                self.assertEqual(cue["controls"]["Body"], text)
                self.assertNotIn("sfx_cue", cue)

    def test_overlapping_or_overlarge_measured_slots_are_rejected(self):
        bad = [{"size": 80, "height": 180, "width": 500, "leading": 90, "lines": ["one", "two"]}]
        with patch.object(edit, "_native_glass_candidates", return_value=bad):
            self.fit()
        self.assertTrue(self.cue["review_blocked"])

    def test_asset_identity_and_unapproved_contract_fail_closed(self):
        for change in ({"assetSha256": "0" * 64}, {"status": "pending-native-qa"}, {"responsiveTiming": False}):
            with self.subTest(change=change):
                cue = copy.deepcopy(self.cue)
                cue["native_runtime_contract"].update(change)
                edit._apply_native_glass_typography(cue, fps=30, height=1080)
                self.assertTrue(cue["review_blocked"])
                self.assertNotIn("sfx_cue", cue)

    def test_missing_exact_font_and_short_duration_fail_closed(self):
        with patch.object(edit, "_native_abar_font_path", side_effect=FileNotFoundError("ABAR missing")):
            self.fit()
        self.assertIn("ABAR missing", self.cue["review_blocked_reason"])
        self.cue.pop("review_blocked")
        self.cue["end"] = 11
        self.fit()
        self.assertIn("responsive range", self.cue["review_blocked_reason"])

    def test_old_contract_and_other_elements_are_untouched(self):
        for change in ({"native_runtime_contract": {}}, {"element_id": "hermes-title-hero-3"}):
            cue = copy.deepcopy(self.cue)
            cue.update(change)
            original = copy.deepcopy(cue)
            edit._apply_native_glass_typography(cue, fps=30, height=1080)
            self.assertEqual(cue, original)

    def test_catalog_contract_flows_into_post_placement_native_fit(self):
        catalog = json.loads(json.dumps(edit.load_editorial_catalog()))
        glass = next(item for item in catalog["elements"] if item["id"] == "hermes-glass-insight")
        glass["mogrtName"] = self.asset.name
        glass["runtimeContract"] = copy.deepcopy(self.contract)
        source = [{"id": 0, "start": 0, "end": 5, "text": "این نکته برای تحلیل مهم است"}]
        marker = {"segment_id": 0, "type": "GRAPHIC", "visual_kind": "statement",
                  "element_id": "hermes-glass-insight", "confidence": 0.99}
        with patch.object(edit, "load_editorial_catalog", return_value=catalog), patch.object(
                edit, "resolve_catalog_mogrt", return_value=self.asset), patch.object(edit, "build_sfx_cue", return_value=None):
            cue = edit.build_graphic_cues(source, 20, [marker], family_history=[])[0]
        self.assertEqual(cue["native_runtime_contract"], self.contract)
        approved_copy = cue["controls"]["Body"]
        cue["layout"] = {"scale": 60, "collision_free": True}
        edit._apply_native_glass_typography(cue, fps=30, height=1080)
        self.assertFalse(cue.get("review_blocked"), cue.get("review_blocked_reason"))
        self.assertEqual(cue["controls"]["Body"].split(), approved_copy.split())

    def test_profile_runs_after_real_safe_layout_and_preserves_input_cue(self):
        self.cue["start"], self.cue["end"] = 0, 4
        self.cue["controls"].update(Title="CORE IDEA", Body="Every word stays.")
        self.cue["template_layers"][0]["controls"].update(Title="CORE IDEA", Body="Every word stays.")
        self.cue["text"] = self.cue["headline_fa"] = "Every word stays."
        original = copy.deepcopy(self.cue)
        def detector(path, groups, model):
            return ([{"face_union": (0.4, 0.15, 0.2, 0.3),
                      "subject_union": (0.28, 0.06, 0.45, 0.9),
                      "sample_frames": frames, "sample_count": len(frames),
                      "detected_count": len(frames), "coverage": 1.0,
                      "body_complete": True, "body_tracking_method": "pphumanseg-independent-person-union"} for frames in groups], "fixture")
        with patch.object(edit, "detect_subject_box_unions", side_effect=detector):
            placed, _ = edit.apply_face_safe_layout([self.cue], video_path="fixture", clips=[[0, 120, 0, 120, 1]],
                                                   fps=30, width=1920, height=1080)
        fitted = placed[0]
        self.assertEqual(self.cue, original)
        self.assertFalse(fitted.get("review_blocked"), fitted.get("review_blocked_reason"))
        self.assertEqual(fitted["layout"]["template_fit"]["profile"], edit.NATIVE_GLASS_PROFILE)
        self.assertEqual(fitted["template_layers"][0]["controls"]["Layout Position"], fitted["layout"]["mogrt_layout_position"])
        self.assertEqual(fitted["controls"]["Body"].split(), ["Every", "word", "stays."])

    def test_grounded_definition_is_committed_only_after_successful_fit(self):
        body = "به این وضعیت می‌گن فلج تحلیلی."
        self.cue["headline_fa"] = body
        self.cue["copy_provenance"] = {"source_text": body, "grounding": {"supported": True}}
        for controls in (self.cue["controls"], self.cue["template_layers"][0]["controls"]):
            controls.update(Title="ORIGINAL TITLE", Body=body)
        original = copy.deepcopy(self.cue)
        self.fit()
        self.assertFalse(self.cue.get("review_blocked"))
        self.assertEqual(self.cue["controls"]["Body"], "فلج تحلیلی")
        self.assertTrue(self.cue["native_copy_selection"]["applied"])
        self.assertFalse(self.cue["native_typography_fit"]["source_words_preserved"])
        self.assertEqual(self.cue["headline_fa"], body)
        self.assertEqual(self.cue["copy_provenance"], original["copy_provenance"])
        original["layout"]["scale"] = 15
        edit._apply_native_glass_typography(original, fps=30, height=1080)
        self.assertTrue(original["review_blocked"])
        self.assertEqual(original["controls"]["Body"], body)
        self.assertFalse(original["native_copy_selection"]["applied"])

    def test_wide_presenter_uses_real_plate_in_free_top_band(self):
        self.cue.update(start=0, end=4, text="Every word stays.", headline_fa="Every word stays.")
        self.cue["template_layers"][0]["controls"].update(Title="CORE IDEA", Body="Every word stays.")
        subject = (.1014583, .2889583, .7554167, .7110417)
        tracking = {"sample_frames": list(range(120)), "sample_count": 120, "detected_count": 120,
                    "coverage": 1.0, "body_complete": True, "subject_union": subject, "face_union": None}
        with patch.object(edit, "detect_subject_box_unions", return_value=([tracking], "fixture")):
            fitted = edit.apply_face_safe_layout([self.cue], video_path="fixture", clips=[[0,120,0,120,1]],
                                                 fps=30, width=1920, height=1080)[0][0]
        self.assertFalse(fitted.get("review_blocked"), fitted.get("review_blocked_reason"))
        self.assertEqual(fitted["layout"]["region"], "top-banner")
        self.assertGreater(fitted["layout"]["scale"], 50)
        x,y,w,h = fitted["layout"]["region_bbox"]
        self.assertLessEqual(y+h, subject[1]-edit.SUBJECT_CLEARANCE+.0001)
        self.assertGreaterEqual(fitted["native_typography_fit"]["slots"]["Title"]["screen_px_1080"],28)

    def test_native_geometry_never_claims_full_subject_has_free_space(self):
        for region in edit.REGION_SPECS:
            rect, scale, contained = edit._fit_native_glass_region(region, (0,0,1,1))
            self.assertEqual(scale, 0)
            self.assertFalse(contained)

    def test_only_opted_in_review8_discards_unknown_legacy_controls(self):
        self.cue["template_layers"][0]["controls"].update({"Primary Accent": [1, 0, 0, 1],
                                                         "Ambient Glow": 32, "Glow Radius": 200})
        self.fit()
        self.assertFalse(self.cue.get("review_blocked"))
        self.assertNotIn("Primary Accent", self.cue["controls"])
        self.assertNotIn("Ambient Glow", self.cue["template_layers"][0]["controls"])
        self.assertEqual(self.cue["controls"]["Glow Radius"], 200)
        self.assertEqual(set(self.cue["native_typography_fit"]["discarded_legacy_controls"]),
                         {"Ambient Glow", "Primary Accent"})
        self.assertTrue(set(self.cue["controls"]).issubset(edit.NATIVE_GLASS_CONTROLS))
        self.assertEqual(len(edit.NATIVE_GLASS_CONTROLS), 21)


class NativeGlassGroundedCopyTests(unittest.TestCase):
    def select(self, body, *, source=None, changes=None):
        item = {"headline_fa": body, "copy_segment_ids": [3],
                "copy_provenance": {"source_text": body if source is None else source,
                                    "grounding": {"supported": True}}}
        item.update(changes or {})
        controls = {"Title": "ORIGINAL TITLE", "Body": body, "Unrelated Color": [1, 0, 0, 1]}
        original = copy.deepcopy((item, controls))
        result, metadata = edit._native_glass_concise_copy(item, controls)
        self.assertEqual((item, controls), original)
        self.assertEqual(result["Unrelated Color"], controls["Unrelated Color"])
        return result, metadata

    def test_definition_extracts_only_exact_term_and_preserves_full_clause_provenance(self):
        body = "به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی."
        source = body[:-1] + "؛ ادامهٔ صحبت در فایل اصلی وجود دارد."
        result, metadata = self.select(body, source=source)
        self.assertEqual(result["Title"], "ANALYSIS PARALYSIS")
        self.assertEqual(result["Body"], "فلج تحلیلی")
        self.assertEqual(metadata["display_kind"], "term-label")
        self.assertEqual(metadata["complete_clause"], body)
        self.assertEqual(metadata["source_text"], source)
        self.assertEqual(metadata["original_controls"]["Body"], body)
        start, end = metadata["source_term_span"]
        self.assertEqual(source[start:end], result["Body"])
        self.assertEqual(metadata["source_segment_ids"], [3])
        self.assertFalse(metadata["applied"])

    def test_nondefinition_changes_only_english_term_label_never_persian_assertion(self):
        body = "تریدینگ‌ویو یک بخش کامیونیتی داره."
        result, metadata = self.select(body, source=body[:-1] + " که ادامه دارد.")
        self.assertEqual(result["Title"], "COMMUNITY")
        self.assertEqual(result["Body"], body)
        self.assertEqual(metadata["display_kind"], "term-topic-with-complete-source-clause")

    def test_definition_with_extra_tail_is_not_compressed(self):
        body = "به این وضعیت می‌گن فلج تحلیلی و این موضوع مهم است."
        result, metadata = self.select(body)
        self.assertEqual(result["Body"], body)
        self.assertEqual(metadata["display_kind"], "term-topic-with-complete-source-clause")

    def test_negative_conditional_and_reported_uncertainty_are_not_selected(self):
        bodies = ["این بخش کامیونیتی ندارد.", "این بخش کامیونیتی نداره.",
                  "این بخش کامیونیتی نداشت.", "شاید این بخش کامیونیتی داره.",
                  "اگر این بخش کامیونیتی داره، باید آن را ببینیم.",
                  "به این وضعیت فلج تحلیلی نمی‌گویند.",
                  "فلانی گفت به این وضعیت می‌گن فلج تحلیلی.",
                  "فکر می‌کنم به این وضعیت می‌گن فلج تحلیلی.",
                  "به این وضعیت می‌گن فلج تحلیلی؟"]
        for body in bodies:
            with self.subTest(body=body):
                result, metadata = self.select(body)
                self.assertIsNone(metadata)
                self.assertEqual(result["Title"], "ORIGINAL TITLE")
                self.assertEqual(result["Body"], body)

    def test_same_clause_source_qualification_cannot_be_dropped(self):
        body = "به این وضعیت می‌گن فلج تحلیلی."
        for prefix in ("شاید ", "فلانی گفت ", "به نظرم ", "اگر "):
            with self.subTest(prefix=prefix):
                _, metadata = self.select(body, source=prefix + body)
                self.assertIsNone(metadata)

    def test_multiple_terms_and_repeated_same_term_are_ambiguous(self):
        for body in ("این کامیونیتی یک اسکرینر دارد.", "این کامیونیتی از کامیونیتی قبلی بهتر است."):
            _, metadata = self.select(body)
            self.assertIsNone(metadata)

    def test_incomplete_blocked_ungrounded_and_changed_headline_remain_untouched(self):
        for body in ("فلج تحلیلی", "به این وضعیت می‌گن فلج تحلیلی که", "…"):
            _, metadata = self.select(body)
            self.assertIsNone(metadata)
        body = "به این وضعیت می‌گن فلج تحلیلی."
        for change in ({"review_blocked": True}, {"needs_manual_copy": True},
                       {"headline_fa": "متن متفاوت"}, {"copy_provenance": {}},
                       {"copy_provenance": {"source_text": body, "grounding": {"supported": False}}}):
            _, metadata = self.select(body, changes=change)
            self.assertIsNone(metadata)

    def test_term_substrings_and_attached_half_space_suffixes_are_not_matches(self):
        for body in ("این بخش کامیونیتیها دارد.", "این بخش کامیونیتی‌ها دارد.",
                     "این بخش پیش‌کامیونیتی دارد.", "این بخش اسکرینرها دارد."):
            _, metadata = self.select(body)
            self.assertIsNone(metadata)

    def test_diacritics_arabic_letters_and_half_space_keep_exact_source_spans(self):
        for exact in ("فَلَج تَحلیلی", "فلج تحليلي"):
            source = "به این وضعیت می‌گن " + exact + "."
            result, metadata = self.select(source)
            self.assertEqual(result["Body"], exact)
            start, end = metadata["source_term_span"]
            self.assertEqual(source[start:end], exact)
        for exact in ("بک‌تست", "بک تست"):
            body = "به این روش می‌گن " + exact + "."
            result, metadata = self.select(body)
            self.assertEqual(result["Title"], "BACKTEST")
            self.assertEqual(result["Body"], exact)

    def test_absent_or_repeated_anchor_and_invented_person_assertion_are_not_rewritten(self):
        body = "به این وضعیت می‌گن فلج تحلیلی."
        for source in ("متن دیگری اینجا وجود دارد.", body + " " + body):
            _, metadata = self.select(body, source=source)
            self.assertIsNone(metadata)
        body = "حافظ پیروی استراتژی مخصوص داره."
        result, metadata = self.select(body)
        self.assertIsNone(metadata)
        self.assertEqual(result["Body"], body)

    def test_casefold_expansion_preserves_mapping_to_original_source(self):
        normalized, offsets = edit._native_copy_index("ß فلج تحلیلی")
        self.assertEqual(len(normalized), len(offsets))
        self.assertEqual(offsets[:2], [0, 0])


if __name__ == "__main__":
    unittest.main()
