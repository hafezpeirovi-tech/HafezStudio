"""Prerequisite metadata only: no ASR, caption merging, or source-cut repair."""

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from subtitle_pipeline import build_review_segments


class ReviewSegmentProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict("os.environ", {"HERMES_COPY_MODE": "source-faithful"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @staticmethod
    def word(index, text, start, end, **metadata):
        return {
            "text": text, "start": start, "end": end,
            "source_start": start + 100, "source_end": end + 100,
            "confidence": .95,
            "source_word_id": f"run:0:{index}", "source_evidence_id": "run",
            **metadata,
        }

    @staticmethod
    def legacy(words):
        return [{key: value for key, value in word.items()
                 if key not in {"source_word_id", "source_evidence_id"}} for word in words]

    def assert_legacy_fields_equal(self, rows, legacy_rows):
        self.assertEqual(len(rows), len(legacy_rows))
        for row, old in zip(rows, legacy_rows):
            self.assertEqual({key: row[key] for key in old}, old)

    def test_exact_legacy_snapshot_and_shape_unchanged(self):
        words = self.legacy([
            self.word(0, "روش", 1.1234, 1.4),
            self.word(1, "روشن", 1.4, 1.7654),
        ])
        self.assertEqual(build_review_segments(words), [{
            "id": 0, "start": 1.123, "end": 1.765,
            "source_start": 101.123, "source_end": 101.765,
            "text": "روش روشن", "source_text": "روش روشن",
            "source_text_provenance": "original-aligned-asr-words", "confidence": .95,
        }])

    def test_literal_text_times_ownership_and_inputs_preserved(self):
        words = [self.word(0, "مبلغ", 0, .3), self.word(1, "1", .3, .5),
                 self.word(2, ".7", .5, .7), self.word(3, "میلیون", .7, 1)]
        original = copy.deepcopy(words)
        rows = build_review_segments(words)
        self.assert_legacy_fields_equal(rows, build_review_segments(self.legacy(words)))
        self.assertEqual(rows[0]["source_word_ids"], [word["source_word_id"] for word in words])
        self.assertEqual(rows[0]["source_evidence_id"], "run")
        self.assertEqual(rows[0]["text"].split(), ["مبلغ", "1", ".7", "میلیون"])
        self.assertEqual(words, original)
        rows[0]["source_word_ids"].append("not-an-input-word")
        self.assertEqual(words, original)

    def test_distinct_ids_for_repeated_literal_words_are_not_collapsed(self):
        words = [self.word(i, "روش", i * .2, (i + 1) * .2) for i in range(3)]
        row = build_review_segments(words)[0]
        self.assertEqual(row["source_word_ids"], ["run:0:0", "run:0:1", "run:0:2"])
        self.assertEqual(row["source_text"], "روش روش روش")

    def test_empty_words_neither_own_ids_nor_invalidate_real_ownership(self):
        words = [{"text": "  ", "start": 0, "end": .1}, self.word(0, "روش", .1, .5)]
        row = build_review_segments(words)[0]
        self.assertEqual(row["source_word_ids"], ["run:0:0"])
        self.assertEqual(build_review_segments([]), [])

    def test_partial_ambiguous_and_mixed_evidence_inputs_are_legacy_no_op(self):
        base = [self.word(0, "روش", 0, .3), self.word(1, "روشن", .3, .6)]
        for key, value in (("source_word_id", None), ("source_word_id", "run:0:0"),
                           ("source_word_id", []), ("source_evidence_id", "other-run"),
                           ("source_evidence_id", "")):
            with self.subTest(key=key, value=value):
                words = copy.deepcopy(base)
                words[1][key] = value
                self.assertEqual(build_review_segments(words), build_review_segments(self.legacy(words)))

    def test_duplicate_id_across_different_segments_is_not_authorized(self):
        words = [self.word(0, "روش", 0, .2), self.word(0, "روشن", 2, 2.2)]
        self.assertEqual(build_review_segments(words), build_review_segments(self.legacy(words)))

    def test_actual_max_duration_boundary_records_partition_and_exact_cause(self):
        words = [self.word(0, "روش", 0, .5), self.word(1, "روشن", .5, 1.1)]
        rows = build_review_segments(words, max_duration=1)
        self.assert_legacy_fields_equal(rows, build_review_segments(self.legacy(words), max_duration=1))
        self.assertEqual(rows[0]["caption_boundary_after_reason"], "segment-partition")
        self.assertEqual(rows[0]["caption_boundary_after_reasons"], ["max-duration"])
        self.assertEqual(rows[1]["caption_boundary_before_reasons"], ["max-duration"])
        self.assertTrue(rows[0]["caption_boundary_after"])
        self.assertTrue(rows[1]["caption_boundary_before"])

    def test_actual_max_chars_partition_and_all_simultaneous_causes(self):
        words = [self.word(0, "روش", 0, .5), self.word(1, "روشن", .5, 1.1)]
        chars = build_review_segments(words, max_chars=5)
        self.assertEqual(chars[0]["caption_boundary_after_reasons"], ["max-chars"])
        both = build_review_segments(words, max_chars=5, max_duration=1)
        self.assertEqual(both[0]["caption_boundary_after_reason"], "segment-partition")
        self.assertEqual(both[0]["caption_boundary_after_reasons"], ["max-duration", "max-chars"])

    def test_pause_dominates_coincident_mechanical_partition(self):
        words = [self.word(0, "روش", 0, .2), self.word(1, "روشن", 1, 1.2)]
        rows = build_review_segments(words, max_chars=5, max_duration=1)
        self.assertEqual(rows[0]["caption_boundary_after_reason"], "pause")
        self.assertEqual(rows[0]["caption_boundary_after_reasons"], ["pause", "max-duration", "max-chars"])
        self.assertEqual(rows[1]["caption_boundary_before_reason"], "pause")

    def test_sentence_end_dominates_coincident_mechanical_partition(self):
        words = [self.word(0, "روش.", 0, .5), self.word(1, "روشن", .5, 1.1)]
        rows = build_review_segments(words, max_chars=5, max_duration=1)
        self.assertEqual(rows[0]["caption_boundary_after_reason"], "sentence-end")
        self.assertIn("sentence-end", rows[1]["caption_boundary_before_reasons"])
        self.assert_legacy_fields_equal(rows, build_review_segments(self.legacy(words), max_chars=5, max_duration=1))

    def test_equal_threshold_is_not_claimed_as_a_grouping_decision(self):
        words = [self.word(0, "روش", 0, .5), self.word(1, "روشن", .5, 1)]
        row = build_review_segments(words, max_duration=1, max_chars=8)[0]
        self.assertEqual(row["source_word_ids"], ["run:0:0", "run:0:1"])
        self.assertEqual(row["caption_boundary_before_reason"], "stream-start")
        self.assertEqual(row["caption_boundary_after_reason"], "stream-end")

    def test_explicit_manual_and_source_boundaries_retained_only_on_new_contract(self):
        for reason in ("manual-approved", "source-cut", "phone", "explicit-boundary"):
            with self.subTest(reason=reason):
                words = [self.word(0, "روش", 0, .3),
                         self.word(1, "روشن", .3, .6, caption_boundary_before=True,
                                   caption_boundary_before_reason=reason)]
                rows = build_review_segments(words)
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["caption_boundary_after_reason"], reason)
                self.assertEqual(rows[1]["caption_boundary_before_reason"], reason)
                self.assertEqual([row["source_word_ids"] for row in rows], [["run:0:0"], ["run:0:1"]])
                self.assertEqual(len(build_review_segments(self.legacy(words))), 1)

    def test_explicit_after_boundary_and_both_different_reasons_are_preserved(self):
        words = [self.word(0, "روش", 0, .3, caption_boundary_after=True,
                           caption_boundary_after_reason="source-cut"),
                 self.word(1, "روشن", .3, .6, caption_boundary_before=True,
                           caption_boundary_before_reason="manual-approved")]
        rows = build_review_segments(words)
        self.assertEqual(rows[0]["caption_boundary_after_reason"], "protected-boundary")
        self.assertEqual(rows[1]["caption_boundary_before_reasons"], ["source-cut", "manual-approved"])

    def test_explicit_partition_label_cannot_authorize_soft_boundary(self):
        words = [self.word(0, "روش", 0, .3, caption_boundary_after=True,
                           caption_boundary_after_reason="segment-partition"),
                 self.word(1, "روشن", .3, .6)]
        rows = build_review_segments(words)
        self.assertEqual(rows[0]["caption_boundary_after_reason"], "explicit-boundary")
        self.assertEqual(rows[0]["caption_boundary_after_reasons"], ["segment-partition"])

    def test_false_or_missing_flag_cannot_discard_explicit_protected_reason(self):
        for reason in ("source-cut", "manual-approved", "phone"):
            for flag in (False, None):
                with self.subTest(reason=reason, flag=flag):
                    metadata = {"caption_boundary_before_reason": reason}
                    if flag is not None:
                        metadata["caption_boundary_before"] = flag
                    words = [self.word(0, "روش", 0, .3), self.word(1, "روشن", .3, .6, **metadata)]
                    rows = build_review_segments(words)
                    self.assertEqual(len(rows), 2)
                    self.assertEqual(rows[1]["caption_boundary_before_reason"], reason)
                    self.assertTrue(rows[1]["caption_boundary_before"])
                    self.assertEqual(len(build_review_segments(self.legacy(words))), 1)

    def test_protection_copy_review_and_outer_explicit_boundaries_survive(self):
        words = [self.word(0, "روش", 0, .3, protected=True, caption_boundary_before=True,
                           caption_boundary_before_reason="manual-start"),
                 self.word(1, "روشن", .3, .6, copy_review_required=True, caption_boundary_after=True,
                           caption_boundary_after_reason="source-end")]
        row = build_review_segments(words)[0]
        self.assertTrue(row["protected"])
        self.assertTrue(row["copy_review_required"])
        self.assertEqual(row["caption_boundary_before_reasons"], ["manual-start", "stream-start"])
        self.assertEqual(row["caption_boundary_after_reasons"], ["source-end", "stream-end"])

    def test_source_discontinuity_never_guessed_into_soft_permission(self):
        words = [self.word(0, "روش", 0, .3),
                 self.word(1, "روشن", .3, .6, source_start=300, source_end=300.3)]
        row = build_review_segments(words)[0]
        self.assertNotEqual(row["caption_boundary_before_reason"], "segment-partition")
        self.assertNotEqual(row["caption_boundary_after_reason"], "segment-partition")
        self.assert_legacy_fields_equal([row], build_review_segments(self.legacy(words)))


if __name__ == "__main__":
    unittest.main()
