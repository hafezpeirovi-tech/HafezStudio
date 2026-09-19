"""Pure optional integration fixtures; hashes below identify synthetic media only."""
import copy
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from subtitle_pipeline import build_srt_cues, format_timestamp


class CaptionContextIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict("os.environ", {"HERMES_COPY_MODE": "source-faithful"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @staticmethod
    def word(index, text, start, end, **extra):
        return {"source_word_id": f"run:{index}", "source_evidence_id": "run",
                "media_sha256": "a" * 64, "text": text,
                "acoustic_start": start, "acoustic_end": end,
                "start": 500 + float(start), "end": 500 + float(end),
                "confidence": .95, "timing_origin": "asr-word-timestamps",
                "source_coverage": 1, "word_boundary_review_required": False, **extra}

    @staticmethod
    def context(words, keeps=None, fps=(25, 1)):
        return {"words": words, "fps": fps, "evidence_id": "run", "media_sha256": "a" * 64,
                "keeps": keeps if keeps is not None else [
                    {"id": "keep-1", "media_sha256": "a" * 64,
                     "start_frame": 0, "end_frame": 100, "source_in_frame": 250, "source_out_frame": 350}]}

    @staticmethod
    def segment(index, text, start, end, ids, **extra):
        return {"id": index, "text": text, "source_text": "PROVENANCE MUST NEVER BE REINSERTED",
                "start": start, "end": end, "source_word_ids": [f"run:{i}" for i in ids],
                "source_evidence_id": "run", "caption_boundary_before": True,
                "caption_boundary_after": True, "caption_boundary_before_reason": "segment-partition",
                "caption_boundary_after_reason": "segment-partition", **extra}

    def pair(self):
        words = [self.word(0, "روش", 10, 10.4), self.word(1, "روشن", 10.4, 11.2)]
        segments = [self.segment(0, "روش", 0, .4, [0]), self.segment(1, "روشن", .4, 1.2, [1])]
        return segments, self.context(words)

    @staticmethod
    def srt_bytes(cues):
        return "".join(f"{i}\n{format_timestamp(c['start'])} --> {format_timestamp(c['end'])}\n{c['text']}\n\n"
                       for i, c in enumerate(cues, 1)).encode("utf-8")

    def test_legacy_no_context_is_byte_identical_with_optional_audit(self):
        segments, _ = self.pair()
        for segment in segments:
            segment.pop("source_word_ids")
        expected = build_srt_cues(segments)
        audit = {}
        result = build_srt_cues(segments, layout_audit=audit)
        self.assertEqual(result, expected)
        self.assertEqual(self.srt_bytes(result), self.srt_bytes(expected))
        self.assertFalse(audit["applied"])
        self.assertIn("missing-caption-context", str(audit))

    def test_optional_complete_context_merges_exact_ids_and_preserves_inputs(self):
        segments, context = self.pair()
        original = copy.deepcopy((segments, context))
        audit = {}
        result = build_srt_cues(segments, caption_context=context, layout_audit=audit)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "روش روشن")
        self.assertEqual(result[0]["source_word_ids"], ["run:0", "run:1"])
        self.assertEqual((result[0]["start"], result[0]["end"]), (0, 1.2))
        self.assertEqual((segments, context), original)
        self.assertTrue(audit["applied"])
        self.assertFalse(audit["publication_ready"])
        self.assertFalse(audit["audio_or_cuts_changed"])
        json.dumps(audit)

    def test_f_style_only_existing_first_word_onset_can_move_start_later(self):
        words = [self.word(0, "اینجا", 10.5, 10.6), self.word(1, "چه", 10.6, 10.7),
                 self.word(2, "اتفاقی", 10.7, 10.9), self.word(3, "می‌افته؟", 10.9, 11.3)]
        segments = [self.segment(0, "اینجا چه اتفاقی", .98, 1.9, [0, 1, 2]),
                    self.segment(1, "می‌افته؟", 1.9, 2.3, [3])]
        keep = {"id": "keep", "media_sha256": "a" * 64, "start_frame": 25,
                "end_frame": 100, "source_in_frame": 250, "source_out_frame": 325}
        audit = {}
        result = build_srt_cues(segments, caption_context=self.context(words, [keep]), layout_audit=audit)
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["start"], result[0]["end"]), (1.5, 2.3))
        self.assertEqual(audit["decisions"][0]["action"], "merge-start-later-only")

    def test_missing_hash_stat_identity_and_float_fps_never_self_authorize(self):
        segments, context = self.pair()
        cases = [{}, {**context, "media_sha256": "path-size-mtime"}, {**context, "fps": 25.0},
                 {**context, "fps": [25, 1]}, {**context, "fps": (0, 1)}]
        missing_hash = copy.deepcopy(context)
        missing_hash.pop("media_sha256")
        cases.append(missing_hash)
        expected = build_srt_cues(segments)
        for candidate in cases:
            with self.subTest(context=candidate.get("fps")):
                audit = {}
                result = build_srt_cues(segments, caption_context=candidate, layout_audit=audit)
                self.assertEqual(result, expected)
                self.assertFalse(audit["applied"])
                self.assertTrue(audit["context_rejections"])

    def test_legacy_word_ownership_or_wrong_binding_is_a_reported_no_op(self):
        for mutation in ("missing-ids", "wrong-run", "duplicate-word", "wrong-hash"):
            segments, context = self.pair()
            if mutation == "missing-ids":
                segments[0].pop("source_word_ids")
            elif mutation == "wrong-run":
                segments[0]["source_evidence_id"] = "other"
            elif mutation == "duplicate-word":
                context["words"].append(copy.deepcopy(context["words"][0]))
            else:
                context["words"][0]["media_sha256"] = "b" * 64
            audit = {}
            result = build_srt_cues(segments, caption_context=context, layout_audit=audit)
            self.assertEqual(result, build_srt_cues(segments))
            self.assertTrue(audit["context_rejections"])

    def test_physically_removed_owned_word_is_never_reinserted(self):
        segments, context = self.pair()
        context["words"].insert(0, self.word(9, "حذف‌شده", 2, 2.4))
        segments[0]["source_word_ids"].insert(0, "run:9")
        result = build_srt_cues(segments, caption_context=context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "روش روشن")
        self.assertNotIn("run:9", result[0]["source_word_ids"])
        segments[0]["text"] = "حذف‌شده روش"
        audit = {}
        self.assertEqual(build_srt_cues(segments, caption_context=context, layout_audit=audit), build_srt_cues(segments))
        self.assertIn("selected-text-word-mismatch", str(audit))

    def test_partial_cut_and_one_frame_source_gap_cannot_be_restored(self):
        segments, context = self.pair()
        context["keeps"] = [
            {"id": "a", "media_sha256": "a" * 64, "start_frame": 0, "end_frame": 5,
             "source_in_frame": 250, "source_out_frame": 255},
            {"id": "b", "media_sha256": "a" * 64, "start_frame": 5, "end_frame": 80,
             "source_in_frame": 256, "source_out_frame": 331}]
        original = copy.deepcopy(context)
        audit = {}
        self.assertEqual(build_srt_cues(segments, caption_context=context, layout_audit=audit), build_srt_cues(segments))
        self.assertTrue(audit["context_rejections"])
        self.assertEqual(context, original)

    def test_extra_same_text_elsewhere_is_not_fuzzy_searched(self):
        segments, context = self.pair()
        context["words"][0]["text"] = "دیگر"
        context["words"].append(self.word(9, "روش", 10, 10.4))
        audit = {}
        self.assertEqual(build_srt_cues(segments, caption_context=context, layout_audit=audit), build_srt_cues(segments))
        self.assertIn("selected-text-word-mismatch", str(audit))

    def test_literal_formatting_mismatch_stays_unchanged_not_rewritten_to_fit(self):
        segments, context = self.pair()
        corrections = {0: "روش،"}
        expected = build_srt_cues(segments, corrections)
        audit = {}
        self.assertEqual(build_srt_cues(segments, corrections, caption_context=context, layout_audit=audit), expected)
        self.assertIn("selected-text-word-mismatch", str(audit))

    def test_existing_regroup_ownership_is_reconstructed_from_all_leaves(self):
        words = [self.word(0, "روش", 10, 10.2), self.word(1, "روشن", 10.2, 10.7),
                 self.word(2, "است", 10.7, 11.05)]
        segments = [self.segment(0, "روش", 0, .2, [0], caption_boundary_after=False),
                    self.segment(1, "روشن", .2, .7, [1], caption_boundary_before=False),
                    self.segment(2, "است", .7, 1.05, [2])]
        self.assertEqual(len(build_srt_cues(segments)), 2)
        result = build_srt_cues(segments, caption_context=self.context(words))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_word_ids"], ["run:0", "run:1", "run:2"])
        self.assertEqual(result[0]["text"], "روش روشن است")

    def test_hard_manual_pause_and_sentence_boundaries_survive(self):
        for reason in ("manual-approved", "source-cut", "phone", "pause", "sentence-end"):
            segments, context = self.pair()
            segments[1]["caption_boundary_before_reason"] = reason
            segments[1]["caption_boundary_before"] = False
            expected = build_srt_cues(segments)
            result = build_srt_cues(segments, caption_context=context)
            self.assertEqual(result, expected)

    def test_internal_protection_hidden_by_legacy_regroup_blocks_further_merge(self):
        words = [self.word(0, "روش", 10, 10.2), self.word(1, "روشن", 10.2, 10.7),
                 self.word(2, "است", 10.7, 11.05)]
        for reason in ("manual-approved", "pause", "source-cut", "sentence-end"):
            for side in ("left-after", "right-before"):
                with self.subTest(reason=reason, side=side):
                    segments = [self.segment(0, "روش", 0, .2, [0], caption_boundary_after=False),
                                self.segment(1, "روشن", .2, .7, [1], caption_boundary_before=False),
                                self.segment(2, "است", .7, 1.05, [2])]
                    index, key = (0, "caption_boundary_after_reason") if side == "left-after" else (1, "caption_boundary_before_reason")
                    segments[index][key] = reason
                    expected = build_srt_cues(segments)
                    self.assertEqual(len(expected), 2)
                    audit = {}
                    result = build_srt_cues(segments, caption_context=self.context(words), layout_audit=audit)
                    self.assertEqual(result, expected)
                    self.assertFalse(audit["applied"])
                    self.assertIn("protected-internal-regroup-boundary", str(audit))

    def test_partial_interpolated_and_low_confidence_machine_words_are_no_op(self):
        for field, value in (("source_coverage", .99), ("timing_origin", "segment-interpolation"),
                             ("word_boundary_review_required", True), ("confidence", .5)):
            segments, context = self.pair()
            context["words"][0][field] = value
            audit = {}
            self.assertEqual(build_srt_cues(segments, caption_context=context, layout_audit=audit), build_srt_cues(segments))
            self.assertFalse(audit["applied"])
            self.assertTrue(audit["review"])

    def test_numeric_fragments_and_order_are_literal(self):
        words = [self.word(0, "مبلغ", 10, 10.2), self.word(1, "1", 10.2, 10.4),
                 self.word(2, ".7", 10.4, 10.6), self.word(3, "است", 10.6, 11)]
        segments = [self.segment(0, "مبلغ 1 .7", 0, .6, [0, 1, 2]), self.segment(1, "است", .6, 1, [3])]
        result = build_srt_cues(segments, caption_context=self.context(words))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"].split(), ["مبلغ", "1", ".7", "است"])
        self.assertNotIn("1\n.7", result[0]["text"])

    def test_unsafe_srt_quantization_remains_a_no_op(self):
        words = [self.word(0, "روش", Fraction(31, 3), 11), self.word(1, "روشن", 11, Fraction(113, 10))]
        keep = {"id": "k", "media_sha256": "a" * 64, "start_frame": 10,
                "end_frame": 100, "source_in_frame": 310, "source_out_frame": 400}
        segments = [self.segment(0, "روش", 1 / 3, 1, [0]), self.segment(1, "روشن", 1, 1.3, [1])]
        audit = {}
        result = build_srt_cues(segments, caption_context=self.context(words, [keep], (30, 1)), layout_audit=audit)
        self.assertEqual(result, build_srt_cues(segments))
        self.assertFalse(audit["applied"])


if __name__ == "__main__":
    unittest.main()
