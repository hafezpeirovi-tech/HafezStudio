from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
import word_boundary_guard as guard

FPS = 30000/1001
MEDIA = {"sha256": "a"*64}


def word(text="آخرش", start=72.28, end=73.12, confidence=.989):
    return {"word_id": "source-run:3:0", "evidence_id": "source-run", "text": text,
            "acoustic_start": start, "acoustic_end": end, "confidence": confidence,
            "timing_origin": "asr-word-timestamps"}


def verification(raw):
    return {raw["word_id"]: {"verification_kind": "audio-reviewed", "verification_id": "test-review",
                             "source_sha256": MEDIA["sha256"], "text": raw["text"],
                             "acoustic_start": raw["acoustic_start"], "acoustic_end": raw["acoustic_end"]}}


def mapping(source_start, source_end, timeline_start):
    return {"orig_start_ms": source_start*1000, "orig_end_ms": source_end*1000,
            "tl_start_ms": timeline_start*1000,
            "tl_end_ms": (timeline_start+source_end-source_start)*1000}


class WordBoundaryGuardTests(unittest.TestCase):
    def assess(self, raw=None, keeps=None, **options):
        raw = raw or word()
        keeps = keeps or [[0, 224, 1949, 2173], [224, 289, 2177, 2242]]
        return guard.assess_word_boundary_gaps(keeps, [raw], fps=FPS,
                                               media_identity=options.pop("media_identity", MEDIA),
                                               gap_origin=options.pop("gap_origin", "vad_silence"), **options)

    def test_real_four_frame_opening_gap_is_report_only_for_original_asr(self):
        keeps = [[0, 224, 1949, 2173], [224, 289, 2177, 2242]]
        original = copy.deepcopy(keeps)
        result = self.assess(keeps=keeps)
        self.assertEqual(result["decisions"][0]["gap_source_frames"], [2173, 2177])
        self.assertIn("source-audio-verification-required", result["decisions"][0]["reasons"])
        self.assertEqual(result["eligible_candidates"], 0)
        self.assertEqual(result["restored_frames"], 0)
        self.assertFalse(result["cuts_changed"])
        self.assertEqual(keeps, original)

    def test_verified_four_and_five_frame_candidates_still_never_apply_cuts(self):
        fixtures = [(word(), [[0, 224, 1949, 2173], [224, 289, 2177, 2242]], 4),
                    (word("هزار", 74.66, 75.32, .923),
                     [[224, 289, 2177, 2242], [289, 520, 2247, 2478]], 5)]
        for raw, keeps, frames in fixtures:
            with self.subTest(frames=frames):
                result = self.assess(raw, keeps, verified_words=verification(raw))
                self.assertEqual(result["eligible_candidates"], 1)
                self.assertEqual(result["decisions"][0]["gap_frames"], frames)
                self.assertFalse(result["decisions"][0]["applied"])
                self.assertFalse(result["publication_ready"])

    def test_even_one_protected_frame_blocks_manual_phone_and_retake_candidates(self):
        for reason in ("manual_approved", "phone", "retake", "intentional_edit", "unknown"):
            with self.subTest(reason=reason):
                raw = word()
                result = self.assess(raw, verified_words=verification(raw),
                                     protected_removals=[{"start_frame": 2174, "end_frame": 2175, "reason": reason}])
                self.assertEqual(result["eligible_candidates"], 0)
                self.assertIn("protected-removal", result["decisions"][0]["reasons"])

    def test_targeted_asr_or_self_awarded_verified_flag_is_not_audio_review(self):
        raw = {**word(), "verified": True, "evidence_kind": "targeted-asr"}
        proof = verification(raw)
        proof[raw["word_id"]]["verification_kind"] = "targeted-asr"
        self.assertEqual(self.assess(raw, verified_words=proof)["eligible_candidates"], 0)
        self.assertEqual(self.assess(raw)["eligible_candidates"], 0)

    def test_media_mismatch_weak_stat_identity_and_wrong_reviewed_text_fail_closed(self):
        raw = word()
        for media in ({"sha256": "b"*64}, {"path": "source.mp4", "size_bytes": 1}):
            self.assertEqual(self.assess(raw, verified_words=verification(raw), media_identity=media)["eligible_candidates"], 0)
        proof = verification(raw)
        proof[raw["word_id"]]["text"] = "کلمه دیگر"
        self.assertEqual(self.assess(raw, verified_words=proof)["eligible_candidates"], 0)

    def test_legacy_clipped_only_words_are_not_acoustic_evidence(self):
        raw = {"word_id": "legacy", "text": "آخرش", "source_start": 72.64, "source_end": 73.12,
               "confidence": .99}
        result = self.assess(raw)
        self.assertEqual(result["eligible_candidates"], 0)
        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["invalid_word_evidence"][0]["reason"], "missing-or-invalid-raw-acoustic-evidence")

    def test_low_confidence_stretched_words_interpolation_and_unknown_origin_are_rejected(self):
        for raw in (word(confidence=.5), word(end=76), {**word(), "timing_origin": "segment-interpolation"}):
            self.assertEqual(self.assess(raw, verified_words=verification(raw))["eligible_candidates"], 0)
        raw = word()
        self.assertEqual(self.assess(raw, verified_words=verification(raw), gap_origin="unknown")["eligible_candidates"], 0)

    def test_large_gap_and_timeline_discontinuity_never_qualify(self):
        raw = word()
        for keeps in ([[0, 224, 1949, 2173], [224, 284, 2182, 2242]],
                      [[0, 224, 1949, 2173], [225, 290, 2177, 2242]]):
            self.assertEqual(self.assess(raw, keeps, verified_words=verification(raw))["eligible_candidates"], 0)

    def test_invalid_rates_frames_protected_ranges_and_reordered_sequences_fail_closed(self):
        for rate in (0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                guard.assess_word_boundary_gaps([], [], fps=rate)
        with self.assertRaises(ValueError):
            self.assess(keeps=[[0, 2, 10, 13]])
        with self.assertRaises(ValueError):
            self.assess(protected_removals=[{"start_frame": 2175, "end_frame": 2174}])
        raw = word()
        keeps = [[0, 20, 2500, 2520], [20, 244, 1949, 2173], [244, 309, 2177, 2242]]
        result = self.assess(raw, keeps, verified_words=verification(raw))
        self.assertFalse(result["source_and_timeline_order_valid"])
        self.assertEqual(result["eligible_candidates"], 0)

    def test_outer_take_edges_are_not_restoration_candidates(self):
        raw = word()
        self.assertEqual(self.assess(raw, [[0, 65, 2177, 2242]], verified_words=verification(raw))["decisions"], [])

    def test_exact_source_and_timeline_contiguous_fragments_map_one_word(self):
        raw = word("واژه", 1.5, 2.5)
        result = guard.map_source_words([raw], [mapping(1, 2, 0), mapping(2, 3, 1)])
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["start"], result[0]["end"]), (.5, 1.5))
        self.assertEqual(len(result[0]["source_fragments"]), 2)
        self.assertEqual(result[0]["source_coverage"], 1)
        self.assertFalse(result[0]["word_boundary_review_required"])

    def test_nonzero_source_gap_does_not_merge_or_resurrect_missing_audio(self):
        raw = word("واژه", 1.5, 2.5)
        result = guard.map_source_words([raw], [mapping(1, 2, 0), mapping(2.1, 3, 1)])
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["source_start"], result[0]["source_end"]), (1.5, 2))
        self.assertEqual(result[0]["acoustic_end"], 2.5)
        self.assertTrue(result[0]["word_boundary_review_required"])
        self.assertEqual(len(result[0]["source_fragments"]), 1)

    def test_timeline_gap_or_source_reorder_never_merges_word_fragments(self):
        raw = word("واژه", 1.5, 2.5)
        for maps in ([mapping(1, 2, 0), mapping(2, 3, 1.1)],
                     [mapping(2, 3, 0), mapping(1, 2, 1)]):
            result = guard.map_source_words([raw], maps)
            self.assertEqual(len(result), 1)
            self.assertEqual(len(result[0]["source_fragments"]), 1)
            self.assertTrue(result[0]["word_boundary_review_required"])

    def test_collection_preserves_raw_times_and_distinguishes_interpolation(self):
        segments = [{"words": [{"word": " واژه ", "start": 1.5, "end": 2.5, "probability": .99,
                                 "timing_origin": "asr-word-timestamps"},
                                {"word": "حدسی", "start": 2.5, "end": 3, "probability": None,
                                 "timing_origin": "segment-interpolation"}]}]
        raw = guard.collect_source_words(segments, "test-run")
        self.assertEqual(raw[0]["word_id"], "test-run:0:0")
        self.assertEqual(raw[0]["acoustic_start"], 1.5)
        self.assertIsNone(raw[1]["confidence"])
        self.assertEqual(raw[1]["timing_origin"], "segment-interpolation")

    def test_autocut_records_provenance_with_one_mocked_asr_run_and_no_media_rewrite(self):
        import autocut
        segment = SimpleNamespace(text="واژه", start=1.5, end=2.5, avg_logprob=-.1,
                                  words=[SimpleNamespace(word="واژه", start=1.5, end=2.5, probability=.99)])
        model = Mock()
        model.transcribe.return_value = ([segment], SimpleNamespace(language="fa", language_probability=1))
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory)/"fake-local-source.mp4"
            media.write_bytes(b"test fixture; model is mocked")
            original = media.read_bytes()
            evidence = {}
            with patch.object(autocut.ctranslate2, "get_cuda_device_count", return_value=0), patch.object(
                    autocut, "WhisperModel", return_value=model) as loader:
                mapped = autocut.transcribe_and_map(str(media), [mapping(2, 3, 0)], [], evidence_sink=evidence)
            loader.assert_called_once()
            model.transcribe.assert_called_once()
            self.assertEqual(media.read_bytes(), original)
            self.assertEqual(evidence["kind"], "original-asr-not-audio-verified")
            self.assertEqual(evidence["media_identity"]["strength"], "sha256-content-before-after-asr")
            import hashlib
            self.assertEqual(evidence["media_identity"]["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(mapped[0]["media_sha256"], evidence["media_identity"]["sha256"])
            self.assertEqual(evidence["words"][0]["acoustic_start"], 1.5)
            self.assertEqual(mapped[0]["source_start"], 2)
            self.assertEqual(mapped[0]["acoustic_start"], 1.5)
            self.assertEqual(mapped[0]["source_evidence_id"], evidence["evidence_id"])

    def test_media_replacement_during_mocked_asr_is_not_stamped_as_trusted_provenance(self):
        import autocut
        segment = SimpleNamespace(text="واژه", start=1.5, end=2.5, avg_logprob=-.1,
                                  words=[SimpleNamespace(word="واژه", start=1.5, end=2.5, probability=.99)])
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory)/"fake-local-source.mp4"
            media.write_bytes(b"before")
            def replace_during_fake_transcription(*args, **kwargs):
                media.write_bytes(b"after-with-different-size")
                return [segment], SimpleNamespace(language="fa", language_probability=1)
            model = Mock()
            model.transcribe.side_effect = replace_during_fake_transcription
            evidence = {}
            with patch.object(autocut.ctranslate2, "get_cuda_device_count", return_value=0), patch.object(
                    autocut, "WhisperModel", return_value=model), self.assertRaisesRegex(RuntimeError, "Source media changed"):
                autocut.transcribe_and_map(str(media), [mapping(1, 3, 0)], [], evidence_sink=evidence)
            self.assertEqual(evidence, {})


if __name__ == "__main__":
    unittest.main()
