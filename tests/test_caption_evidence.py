import copy
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from caption_evidence import merge_orphan_cues

MEDIA = "a" * 64
RUN = "unit-test-source-run"


def word(i, text, start, end, source_start=None, source_end=None):
    return {"source_word_id": f"w{i}", "source_evidence_id": RUN,
            "media_sha256": MEDIA, "text": text, "start": start, "end": end,
            "acoustic_start": source_start if source_start is not None else 10 + start,
            "acoustic_end": source_end if source_end is not None else 10 + end,
            "confidence": .95, "timing_origin": "asr-word-timestamps",
            "source_coverage": 1, "word_boundary_review_required": False}


def keep(a=0, b=4000, source_in=10000, source_out=14000, name="a1"):
    return {"id": name, "media_sha256": MEDIA, "start_frame": a, "end_frame": b,
            "source_in_frame": source_in, "source_out_frame": source_out}


def cue(i, text, start, end, word_ids):
    return {"id": i, "text": text, "start": start, "end": end,
            "source_word_ids": word_ids, "caption_boundary_before": True,
            "caption_boundary_before_reason": "segment-partition",
            "caption_boundary_after": True, "caption_boundary_after_reason": "segment-partition"}


def ordinary_fixture():
    words = [word(0, "روش", 0, .5), word(1, "روشن", .5, 1.5), word(2, "شد.", 1.5, 1.9)]
    cues = [cue(1, "روش روشن", 0, 1.5, ["w0", "w1"]), cue(2, "شد.", 1.5, 1.9, ["w2"])]
    return cues, words, [keep()]


class CaptionEvidenceTests(unittest.TestCase):
    def call(self, cues, words, keeps, **kwargs):
        return merge_orphan_cues(cues, words=words, keeps=keeps, fps=kwargs.pop("fps", (1000, 1)),
                                 media_sha256=MEDIA, evidence_id=RUN, **kwargs)

    def assert_refused(self, cues, words, keeps, **kwargs):
        before = copy.deepcopy((cues, words, keeps))
        result = self.call(cues, words, keeps, **kwargs)
        self.assertEqual(result["cues"], cues)
        self.assertFalse(result["decisions"])
        self.assertTrue(result["review"])
        self.assertEqual((cues, words, keeps), before)
        return result

    def test_d_e_style_adjacent_segments_merge_with_same_keep_and_literal_copy(self):
        for prefix, verb in (("استراتژی‌ها بک‌تست", "بگیری."), ("روشن بودن", "ببینی.")):
            cues, words, keeps = ordinary_fixture()
            words[0]["text"], words[1]["text"] = prefix.split()
            words[2]["text"] = verb
            cues[0]["text"], cues[1]["text"] = prefix, verb
            result = self.call(cues, words, keeps)
            self.assertEqual(len(result["cues"]), 1)
            self.assertEqual(result["cues"][0]["text"], prefix + " " + verb)
            self.assertEqual((result["cues"][0]["start"], result["cues"][0]["end"]), (0, 1.9))
            self.assertEqual(result["decisions"][0]["action"], "merge-preserve-endpoints")
            self.assertFalse(result["review"])

    def test_f_style_late_onset_is_generic_and_rational_fps_keep_bound(self):
        # Real F-shaped timing, synthetic source identity; this is not native/media QA.
        words = [word(0, "اینجا", 278.2753, 278.4953, 570.58, 570.8),
                 word(1, "چه", 278.4953, 278.6353, 570.8, 570.94),
                 word(2, "اتفاقی", 278.6353, 279.0353, 570.94, 571.34),
                 word(3, "می‌افته؟", 279.0353, 279.4753, 571.34, 571.78)]
        cues = [cue(63, "اینجا چه اتفاقی", 277.763, 279.035, ["w0", "w1", "w2"]),
                cue(64, "می‌افته؟", 279.035, 279.475, ["w3"])]
        result = self.call(cues, words, [keep(8330, 8602, 17090, 17362)], fps=(30000, 1001))
        self.assertEqual(result["cues"][0]["start"], words[0]["start"])
        self.assertEqual(result["cues"][0]["end"], cues[-1]["end"])
        self.assertEqual(result["decisions"][0]["action"], "merge-start-later-only")
        self.assertEqual(result["decisions"][0]["frame_envelope"], [8339, 8376])
        self.assertEqual(result["cues"][0]["caption_source_cue_ids"], [63, 64])

    def test_one_frame_source_jump_never_becomes_merge_permission(self):
        words = [word(0, "کلام", 0, 1.2, 10, 11.2), word(1, "بعدی", 1.2, 1.5, 11.201, 11.501)]
        cues = [cue(1, "کلام", 0, 1.2, ["w0"]), cue(2, "بعدی", 1.2, 1.5, ["w1"])]
        keeps = [keep(0, 1200, 10000, 11200, "a"), keep(1200, 2400, 11201, 12401, "b")]
        result = self.assert_refused(cues, words, keeps)
        self.assertIn("no-unique-whole-word-source-keep", result["review"][0]["reasons"])

    def test_removed_take_words_in_catalog_are_never_searched_or_reinserted(self):
        cues, words, keeps = ordinary_fixture()
        words += [word(99, "اشتباه", .1, .2), word(100, "حذف‌شده", .2, .3)]
        result = self.call(cues, words, keeps)
        self.assertEqual(result["cues"][0]["text"], "روش روشن شد.")
        self.assertEqual(result["cues"][0]["source_word_ids"], ["w0", "w1", "w2"])
        self.assertNotIn("w99", str(result))

    def test_missing_legacy_ownership_never_self_authorizes(self):
        cues, words, keeps = ordinary_fixture()
        cues[0].pop("source_word_ids")
        self.assert_refused(cues, words, keeps)
        cues, words, keeps = ordinary_fixture()
        words[0] = {k: words[0][k] for k in ("text", "start", "end", "source_word_id")}
        self.assert_refused(cues, words, keeps)

    def test_missing_duplicate_and_reused_word_ids_are_rejected(self):
        for kind in ("missing", "duplicate-catalog", "duplicate-cue", "cross-cue"):
            with self.subTest(kind=kind):
                cues, words, keeps = ordinary_fixture()
                if kind == "missing":
                    words.pop()
                elif kind == "duplicate-catalog":
                    words.append(copy.deepcopy(words[0]))
                elif kind == "duplicate-cue":
                    cues[0]["source_word_ids"] = ["w0", "w0"]
                else:
                    cues[1]["source_word_ids"] = ["w0"]
                self.assert_refused(cues, words, keeps)

    def test_literal_mapping_no_fuzzy_names_or_person_rewrite(self):
        cues, words, keeps = ordinary_fixture()
        for text in ("روش روشن‌تر", "روش، روشن", "روش می‌رود"):
            changed = copy.deepcopy(cues)
            changed[0]["text"] = text
            self.assert_refused(changed, words, keeps)

    def test_partial_interpolated_unreviewed_and_low_confidence_words_refuse(self):
        for key, value in (("source_coverage", .99), ("word_boundary_review_required", True),
                           ("word_boundary_review_required", None), ("timing_origin", "segment-interpolation"),
                           ("timing_origin", "unknown"), ("confidence", .59), ("confidence", None)):
            with self.subTest(key=key, value=value):
                cues, words, keeps = ordinary_fixture()
                words[1][key] = value
                self.assert_refused(cues, words, keeps)

    def test_wrong_source_fingerprint_or_asr_run_refuses(self):
        for key, value in (("media_sha256", "b"*64), ("source_evidence_id", "different-run")):
            cues, words, keeps = ordinary_fixture()
            words[0][key] = value
            self.assert_refused(cues, words, keeps)

    def test_complete_acoustic_extent_and_affine_mapping_required(self):
        for key, value in (("acoustic_start", None), ("acoustic_end", 11.8),
                           ("start", .1), ("end", float("nan")), ("confidence", True)):
            with self.subTest(key=key):
                cues, words, keeps = ordinary_fixture()
                words[0][key] = value
                self.assert_refused(cues, words, keeps)

    def test_unlabelled_and_explicit_protected_boundaries_never_relax(self):
        for side, key, value in ((0, "caption_boundary_after_reason", None),
                                  (0, "caption_boundary_after_reason", "manual"),
                                  (1, "caption_boundary_before_reason", "source-cut"),
                                  (0, "protected", True), (1, "copy_review_required", True)):
            cues, words, keeps = ordinary_fixture()
            cues[side][key] = value
            self.assert_refused(cues, words, keeps)

    def test_protected_reason_is_not_defeated_by_false_boundary_flag(self):
        cues, words, keeps = ordinary_fixture()
        cues[0]["caption_boundary_after"] = False
        cues[0]["caption_boundary_after_reason"] = "manual"
        self.assert_refused(cues, words, keeps)

    def test_numeric_atoms_and_all_characters_survive_without_lexical_normalization(self):
        for tokens in (["مبلغ", "1", ".7"], ["مبلغ", "۳", "٫", "۵"]):
            words = [word(i, token, i*.3, (i+1)*.3) for i, token in enumerate(tokens)]
            boundary = (len(tokens)-1)*.3
            cues = [cue(1, " ".join(tokens[:-1]), 0, boundary, [f"w{i}" for i in range(len(tokens)-1)]),
                    cue(2, tokens[-1], boundary, len(tokens)*.3, [f"w{len(tokens)-1}"])]
            result = self.call(cues, words, [keep()])
            self.assertEqual(len(result["cues"]), 1)
            self.assertEqual(result["cues"][0]["text"].split(), tokens)
            self.assertIn(" ".join(tokens[1:]), result["cues"][0]["text"])
            cues[0]["caption_boundary_after_reason"] = "protected"
            self.assert_refused(cues, words, [keep()])

    def test_no_end_extension_or_clamping_across_keep(self):
        cues, words, keeps = ordinary_fixture()
        keeps = [keep(0, 1900, 10000, 11900)]
        cues[-1]["end"] = 1.901  # A single millisecond beyond an actual keep.
        self.assert_refused(cues, words, keeps)

    def test_unsupported_old_last_end_never_gets_retimed(self):
        cues, words, keeps = ordinary_fixture()
        cues[-1]["end"] = 2.0
        self.assert_refused(cues, words, keeps)

    def test_existing_late_start_is_not_moved_earlier(self):
        cues, words, keeps = ordinary_fixture()
        cues[0]["start"] = .2
        result = self.call(cues, words, keeps)
        self.assertEqual(result["cues"][0]["start"], .2)

    def test_no_tail_rebalance_or_overlong_layout(self):
        cues, words, keeps = ordinary_fixture()
        self.assert_refused(cues, words, keeps, max_chars=5)
        self.assert_refused(cues, words, keeps, max_duration=1)

    def test_long_single_word_asr_duration_remains_review_not_shortened(self):
        words = [word(0, "عرض", 0, 3), word(1, "بعدی", 3, 3.4)]
        cues = [cue(1, "عرض", 0, 3, ["w0"]), cue(2, "بعدی", 3, 3.4, ["w1"])]
        self.assert_refused(cues, words, [keep()])

    def test_reordered_or_overlapping_raw_words_fail_closed(self):
        cues, words, keeps = ordinary_fixture()
        words[1]["acoustic_start"] = 10.4
        self.assert_refused(cues, words, keeps)
        cues, words, keeps = ordinary_fixture()
        words[1]["start"] = .4
        self.assert_refused(cues, words, keeps)

    def test_keeps_must_be_unique_ordered_source_bound_and_1x(self):
        for replacement in ([keep(), keep(name="b")], [keep(source_out=14001)],
                            [keep(), keep(4000, 5000, 14000, 15000)],
                            [{**keep(), "media_sha256": "b"*64}], [{**keep(), "start_frame": False}]):
            with self.subTest(replacement=replacement):
                cues, words, _ = ordinary_fixture()
                with self.assertRaises(ValueError):
                    self.call(cues, words, replacement)

    def test_repeated_source_in_distinct_final_keeps_is_ambiguous(self):
        cues, words, _ = ordinary_fixture()
        self.assert_refused(cues, words, [keep(0, 4000, 10000, 14000, "a"),
                                        keep(4000, 8000, 10000, 14000, "b")])

    def test_invalid_fps_and_cue_times_fail_before_result(self):
        cues, words, keeps = ordinary_fixture()
        for fps in (29.97, (30000, 0), (True, 1), (1.0, 1), [30000, 1001]):
            with self.assertRaises(ValueError):
                self.call(cues, words, keeps, fps=fps)
        for key, value in (("start", -.1), ("end", 0), ("end", float("inf"))):
            changed = copy.deepcopy(cues)
            changed[0][key] = value
            with self.assertRaises(ValueError):
                self.call(changed, words, keeps)
        changed = copy.deepcopy(cues)
        changed[1]["start"] = 1.4
        with self.assertRaises(ValueError):
            self.call(changed, words, keeps)

    def test_no_orphan_means_no_mutation_or_optimization(self):
        cues, words, keeps = ordinary_fixture()
        cues[-1]["end"] = 2.2
        words[-1]["end"], words[-1]["acoustic_end"] = 2.2, 12.2
        result = self.call(cues, words, keeps)
        self.assertEqual(result["cues"], cues)
        self.assertEqual(result["decisions"], [])

    def test_input_and_unrelated_cue_metadata_are_untouched(self):
        cues, words, keeps = ordinary_fixture()
        cues[0]["custom"] = {"keep": [1, 2]}
        words.append(word(3, "پایان", 2, 3))
        cues.append(cue(3, "پایان", 2, 3, ["w3"]))
        before = copy.deepcopy((cues, words, keeps))
        result = self.call(cues, words, keeps)
        self.assertEqual((cues, words, keeps), before)
        self.assertEqual(result["cues"][-1], cues[-1])
        self.assertEqual(result["cues"][0]["source_word_ids"], ["w0", "w1", "w2"])
        self.assertFalse(result["audio_or_cuts_changed"])
        self.assertFalse(result["publication_ready"])
        result["cues"][0]["custom"]["keep"].append(3)
        self.assertEqual(cues[0]["custom"]["keep"], [1, 2])

    def test_rational_start_safe_before_float_conversion_is_refused_after_conversion(self):
        a, mid, b = Fraction(1, 3), Fraction(1), Fraction(13, 10)
        cues = [cue(1, "روش", a, mid, ["w0"]), cue(2, "روشن", mid, b, ["w1"])]
        words = [word(0, "روش", a, mid, Fraction(31, 3), 11),
                 word(1, "روشن", mid, b, 11, Fraction(113, 10))]
        result = self.assert_refused(cues, words, [keep(10, 100, 310, 400)], fps=(30, 1))
        self.assertIn("returned-timing-crosses-source-keep", result["review"][0]["reasons"])

    def test_float_safe_at_boundary_but_unsafe_after_srt_rounding_is_refused(self):
        a, mid, b = .33333333333333337, 1, 1.3
        cues = [cue(1, "روش", a, mid, ["w0"]), cue(2, "روشن", mid, b, ["w1"])]
        words = [word(0, "روش", a, mid, Fraction(31, 3), 11), word(1, "روشن", mid, b, 11, 11.3)]
        result = self.assert_refused(cues, words, [keep(10, 100, 310, 400)], fps=(30, 1))
        self.assertIn("serialized-timing-crosses-source-keep", result["review"][0]["reasons"])

    def test_float_millisecond_inside_boundary_remains_valid(self):
        cues = [cue(1, "روش", .334, 1, ["w0"]), cue(2, "روشن", 1, 1.3, ["w1"])]
        words = [word(0, "روش", .334, 1, 10.334, 11), word(1, "روشن", 1, 1.3, 11, 11.3)]
        result = self.call(cues, words, [keep(10, 100, 310, 400)], fps=(30, 1))
        self.assertEqual(len(result["cues"]), 1)
        self.assertEqual(result["cues"][0]["start"], .334)
        self.assertEqual(result["decisions"][0]["frame_envelope"], [10, 39])
        self.assertEqual(result["decisions"][0]["serialized_frame_envelope"], [10, 39])

    def test_exact_representable_keep_boundary_and_normal_case_still_pass(self):
        a, mid, b = Fraction(2, 5), 1, Fraction(7, 5)
        cues = [cue(1, "روش", a, mid, ["w0"]), cue(2, "روشن", mid, b, ["w1"])]
        words = [word(0, "روش", a, mid, Fraction(52, 5), 11),
                 word(1, "روشن", mid, b, 11, Fraction(57, 5))]
        result = self.call(cues, words, [keep(10, 100, 260, 350)], fps=(25, 1))
        self.assertEqual(len(result["cues"]), 1)
        self.assertEqual(result["decisions"][0]["frame_envelope"], [10, 35])
        self.assertEqual(result["decisions"][0]["serialized_frame_envelope"], [10, 35])
        normal = self.call(*ordinary_fixture())
        self.assertEqual(len(normal["cues"]), 1)

    def test_srt_end_rounding_past_keep_is_refused_without_clamping(self):
        a, mid, b = Fraction(0), Fraction(3, 4), 1.1666666666666665
        cues = [cue(1, "روش", a, mid, ["w0"]), cue(2, "روشن", mid, b, ["w1"])]
        words = [word(0, "روش", a, mid, 10, Fraction(43, 4)),
                 word(1, "روشن", mid, b, Fraction(43, 4), Fraction(67, 6))]
        # Float end is just inside35/30, but SRT1.167s has outward ceil36.
        result = self.assert_refused(cues, words, [keep(0, 35, 300, 335)], fps=(30, 1))
        self.assertIn("serialized-timing-crosses-source-keep", result["review"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
