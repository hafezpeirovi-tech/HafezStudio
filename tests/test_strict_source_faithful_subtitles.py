from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
import rough_cut
import subtitle_pipeline as subtitles


class StrictSourceFaithfulSubtitleTests(unittest.TestCase):
    def setUp(self):
        self.mode = patch.dict(os.environ, {"HERMES_COPY_MODE": "source-faithful"})
        self.mode.start()
        self.addCleanup(self.mode.stop)

    def review(self, source, candidate):
        audit = []
        corrections, _, warnings = subtitles.parse_ai_review(
            {"segments": [{"id": 7, "text": candidate}]},
            [{"id": 7, "text": source, "source_text": source}], review_metadata=audit)
        return corrections, warnings, audit

    def test_default_and_unknown_mode_are_strict_only_explicit_opt_in_is_legacy(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(subtitles.source_faithful_subtitles())
        with patch.dict(os.environ, {"HERMES_COPY_MODE": "typo"}):
            self.assertTrue(subtitles.source_faithful_subtitles())
        with patch.dict(os.environ, {"HERMES_COPY_MODE": "grounded-summary"}):
            self.assertFalse(subtitles.source_faithful_subtitles())
            corrections, _, _ = self.review("معامله رو می‌زنی و ضرر میکنی", "معامله رو می‌زنم و ضرر می‌کنم")
            self.assertIn(7, corrections)

    def test_person_tense_negation_name_and_neighbor_changes_are_rejected(self):
        pairs = [
            ("معامله رو می‌زنی و ضرر میکنی", "معامله رو می‌زنم و ضرر می‌کنم"),
            ("این روش کار می‌کرد", "این روش کار می‌کند"),
            ("این روش سود نمی‌دهد", "این روش سود می‌دهد"),
            ("من حافظ پیروی هستم", "من حافظ فیوچرز هستم"),
            ("هدیه دارم بران", "هدیه دارم برادران"),
            ("خاصی بهت معرفی", "خاصی بهت معرفی می‌کنم"),
            ("فقط باز میکنین که یک تحلیلی", "فقط باز می‌کنین که یک تحلیل رو انجام بدین. اوه، سلام چطوری؟"),
            ("مهم دیگه‌ای رو می‌خوام بهت بگم", "دیگه‌ای رو می‌خوام بهت بگم"),
        ]
        for source, candidate in pairs:
            with self.subTest(source=source):
                corrections, warnings, audit = self.review(source, candidate)
                self.assertEqual(corrections, {})
                self.assertTrue(warnings)
                self.assertEqual(audit[0]["source_text"], source)
                self.assertFalse(audit[0]["applied"])
                self.assertEqual(audit[0]["status"], "draft-review-required")

    def test_safe_spacing_zwnj_ya_kaf_and_punctuation_are_allowed(self):
        source = "اين كار را مي کنم ، عدد 1.5 است"
        candidate = "این کار را می‌کنم، عدد 1.5 است."
        corrections, warnings, audit = self.review(source, candidate)
        self.assertEqual(corrections[7], candidate)
        self.assertFalse(warnings)
        self.assertEqual(audit[0]["status"], "accepted-formatting-only")

    def test_empty_deleted_or_wrong_type_copy_is_not_silently_accepted(self):
        for candidate in ("", None, ["متن"], {"text": "متن"}):
            corrections, warnings, audit = self.review("متن", candidate)
            self.assertFalse(corrections)
            self.assertTrue(warnings)
            self.assertFalse(audit[0]["applied"])
        self.assertFalse(subtitles.source_equivalent_caption("", "…"))

    def test_numbers_separators_signs_percentage_order_and_count_cannot_change(self):
        for source, candidate in [("عدد 1.5", "عدد 15"), ("عدد ۱٫۵", "عدد ۱۵"),
                                  ("عدد 1 5", "عدد 15"), ("عدد 60 و 30", "عدد 30 و 60"),
                                  ("عدد 30 و 30", "عدد 30"), ("عدد -5", "عدد 5"),
                                  ("عدد 5%", "عدد 5"), ("عدد 1,000", "عدد 1000"),
                                  ("عدد 30", "عدد ۳۰")]:
            with self.subTest(source=source):
                self.assertFalse(subtitles.source_equivalent_caption(source, candidate))

    def test_unicode_letter_changes_outside_allowlist_are_not_normalization(self):
        for source, candidate in [("مؤثر", "موثر"), ("مسألة", "مسأله"), ("ریستر برات بگم", "بذار برات بگم")]:
            self.assertFalse(subtitles.source_equivalent_caption(source, candidate))

    def test_review_units_preserve_raw_source_and_do_not_expand_vocabulary(self):
        words = [{"text": text, "start": i*0.3, "end": (i+1)*0.3}
                 for i, text in enumerate("ریستر برات بگم مؤثر".split())]
        segments = subtitles.build_review_segments(words)
        self.assertEqual(segments[0]["source_text"], "ریستر برات بگم مؤثر")
        self.assertEqual(segments[0]["text"], segments[0]["source_text"])
        cues = subtitles.build_srt_cues(segments, {0: "بذار برات بگم موثر"})
        self.assertEqual(cues[0]["text"], "ریستر برات بگم مؤثر")

    def test_legacy_cache_source_recovered_only_on_exact_aligned_boundaries(self):
        words = [{"text": "هفتی", "start": 0.9775, "end": 1.2775},
                 {"text": "مهم", "start": 1.2775, "end": 1.5775},
                 {"text": "همسایه", "start": 1.5775, "end": 2.0}]
        segments = [{"id": 8, "start": 0.978, "end": 1.578, "text": "حتی مهم"}]
        restored = subtitles.restore_source_segments(segments, words)
        self.assertEqual(restored[0]["id"], 8)
        self.assertEqual(restored[0]["source_text"], "هفتی مهم")
        self.assertEqual(restored[0]["text"], "هفتی مهم")
        self.assertEqual(restored[0]["source_word_indices"], [0, 1])
        self.assertEqual(segments[0]["text"], "حتی مهم")
        partial = subtitles.restore_source_segments([{**segments[0], "start": 1.0}], words)
        self.assertEqual(partial[0]["source_text_provenance"], "legacy-segment-source-unverified")
        self.assertEqual(partial[0]["source_text"], "حتی مهم")

    def test_srt_never_reintroduces_removed_take_from_original_provenance(self):
        original = "من این روش را ساختم من این روش را کامل ساختم"
        segment = {"id": 7, "start": 0, "end": 4, "text": original, "source_text": original}
        edits = [{"segment_id": 7, "action": "cut_tight", "confidence": 0.99,
                  "start": 0, "end": 1.5, "remove_text": "من این روش را ساختم", "matched_text": "من این روش را ساختم"}]
        mapping = [{"old_start": 1.5, "old_end": 4, "new_start": 0, "new_end": 2.5}]
        remapped = rough_cut.remap_segments([segment], mapping, edits, "tight")
        self.assertEqual(remapped[0]["source_text"], original)
        self.assertEqual(subtitles.build_srt_cues(remapped)[0]["text"], "من این روش را کامل ساختم")

    def test_real_cached_regressions_are_rejected_without_running_any_model(self):
        job = ROOT / "proof/publication-job-20260905"
        if not (job / "F_Hafez_Youtube_8rdvid_C2963.edit.json").exists():
            self.skipTest("Optional owner-local cached job is not present; generic source-boundary regressions still run.")
        manifest = json.loads((job / "F_Hafez_Youtube_8rdvid_C2963.edit.json").read_text(encoding="utf-8-sig"))
        review = json.loads((job / "F_Hafez_Youtube_8rdvid_C2963.resolved-review.json").read_text(encoding="utf-8-sig"))
        segments = subtitles.restore_source_segments(manifest["review_segments"], manifest["mapped_words"])
        audit = []
        corrections, _, _, _, _, warnings = subtitles.parse_full_review(review, segments, review_metadata=audit)
        for segment_id in (5, 11, 75, 83):
            self.assertNotIn(segment_id, corrections)
            self.assertTrue(any(d["segment_id"] == segment_id and not d["applied"] for d in audit))
        self.assertTrue(warnings)
        self.assertTrue(all("source_text" in s for s in segments))


if __name__ == "__main__":
    unittest.main()
