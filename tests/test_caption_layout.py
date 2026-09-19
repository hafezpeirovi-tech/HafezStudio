import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from caption_layout import caption_atoms, wrap_caption, regroup_short_cues, build_source_word_cues
import subtitle_pipeline


class CaptionLayoutTests(unittest.TestCase):
    def test_decimal_characters_and_spaces_preserved_on_one_line(self):
        self.assertEqual(caption_atoms("مبلغ 1 .7 و ۳ ٫ ۵ است"), ["مبلغ", "1 .7", "و", "۳ ٫ ۵", "است"])
        for text in ("این مبلغ حدود 1 .7 ملیون است", "مبلغ ۳ ٫ ۵ ملیون است"):
            wrapped = wrap_caption(text, 14)
            self.assertEqual(wrapped.split(), text.split())
            self.assertNotIn("1\n.7", wrapped)
            self.assertNotIn("۳\n٫", wrapped)
        self.assertEqual(wrap_caption("supercalifragilisticexpialidocious", 5), "supercalifragilisticexpialidocious")

    def test_regroup_orphan_preserves_metadata_and_input(self):
        cues = [{"start": 1, "end": 1.039, "text": "تو", "words": [{"text": "تو"}]},
                {"start": 1.2, "end": 5.3, "text": "با این کار", "words": [{"text": "با این کار"}]}]
        original = copy.deepcopy(cues)
        result = regroup_short_cues(cues)
        self.assertEqual(cues, original)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "تو با این کار")
        self.assertEqual((result[0]["start"], result[0]["end"]), (1, 5.3))
        self.assertEqual(len(result[0]["words"]), 2)
        self.assertEqual(result[0]["layout_source_cues"], original)

    def test_unmergeable_or_hard_boundary_is_flagged_not_extended(self):
        cues = [{"start": 0, "end": .039, "text": "تو"},
                {"start": .2, "end": 2, "text": "جمله بعد", "caption_boundary_before": True}]
        result = regroup_short_cues(cues)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["end"], .039)
        self.assertTrue(result[0]["layout_review"])
        cues[1].pop("caption_boundary_before")
        cues[1]["start"] = 1
        self.assertEqual(len(regroup_short_cues(cues)), 2)

    def test_long_single_word_regroups_without_shortening_acoustic_extent(self):
        cues = [{"start": 138.085, "end": 143, "text": "بدم"},
                {"start": 143, "end": 144.135, "text": "که برام پیدا بکنن."}]
        result = regroup_short_cues(cues)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["end"], 144.135)
        self.assertEqual(result[0]["text"], "بدم که برام پیدا بکنن.")

    def test_bad_times_rejected(self):
        for start, end in ((float("nan"), 1), (1, 0), (0, float("inf")), (-1, -.5)):
            with self.assertRaises(ValueError):
                regroup_short_cues([{"start": start, "end": end, "text": "الف"}])
        for text in (None, {}, [], " "):
            with self.assertRaises(ValueError):
                build_source_word_cues([{"start": 0, "end": 1, "text": text}])
            with self.assertRaises(ValueError):
                regroup_short_cues([{"start": 0, "end": 1, "text": text}])
        with self.assertRaises(ValueError):
            regroup_short_cues([{"start": 0, "end": 2, "text": "متن چپ"},
                               {"start": 1, "end": 3, "text": "متن راست"}])

    def test_word_hard_after_boundary_survives_decimal_and_regroup(self):
        words = [{"text": "1", "start": 0, "end": .3, "caption_boundary_after": True},
                 {"text": ".7", "start": .4, "end": .8}]
        result = build_source_word_cues(words)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["caption_boundary_after"])
        result = subtitle_pipeline.build_srt_cues([
            {"id": i, **row} for i, row in enumerate(words)])
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["caption_boundary_after"])

    def test_source_discontinuity_remains_nonmergeable(self):
        words = [{"text": "first", "start": 0, "end": .1, "source_start": 10, "source_end": 10.1},
                 {"text": "second", "start": .2, "end": 1.2, "source_start": 200, "source_end": 201}]
        result = build_source_word_cues(words)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[1]["caption_boundary_before"])

    def test_three_token_decimal_is_not_split_at_threshold(self):
        words = [{"text": text, "start": i*.2, "end": (i+1)*.2}
                 for i, text in enumerate(["abcdef", "1", ".", "7"])]
        result = build_source_word_cues(words, max_chars=8)
        self.assertTrue(any("1 . 7" in c["text"] for c in result))
        self.assertEqual(" ".join(c["text"] for c in result).split(), [w["text"] for w in words])

    def test_production_short_duration_floor_does_not_overlap(self):
        result = subtitle_pipeline.build_srt_cues([
            {"id": 0, "start": 0, "end": .05, "text": "تو", "caption_boundary_after": True},
            {"id": 1, "start": .1, "end": 1, "text": "با این کار"}])
        self.assertEqual(result[0]["end"], .1)
        self.assertLessEqual(result[0]["end"], result[1]["start"])

    def test_legacy_production_segments_do_not_self_authorize_regrouping(self):
        result = subtitle_pipeline.build_srt_cues([
            {"id": 0, "start": 0, "end": .05, "text": "تو"},
            {"id": 1, "start": .1, "end": 1, "text": "با این کار"}])
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["caption_boundary_after"])
        self.assertTrue(result[1]["caption_boundary_before"])

    def test_word_decimal_stays_atomic_across_char_duration_threshold(self):
        words = [{"text": "ماهی", "start": 0, "end": .5, "source_start": 10, "source_end": 10.5},
                 {"text": "1", "start": 4.4, "end": 4.6, "source_start": 14.4, "source_end": 14.6},
                 {"text": ".7", "start": 4.8, "end": 5, "source_start": 15.4, "source_end": 15.6},
                 {"text": "ملیون", "start": 5, "end": 6, "source_start": 15.6, "source_end": 16.6}]
        result = build_source_word_cues(words)
        self.assertTrue(any("1 .7" in cue["text"] for cue in result))
        self.assertEqual(" ".join(c["text"] for c in result).split(), [w["text"] for w in words])

    def test_production_split_keeps_numeric_fragments_atomic(self):
        chunks = subtitle_pipeline._split_text("مبلغ مورد نظر 1 .7 ملیون", max_chars=15)
        self.assertTrue(any("1 .7" in chunk for chunk in chunks))
        self.assertEqual(subtitle_pipeline.normalize_source_caption("عدد 1 .7 است ."), "عدد 1 .7 است.")
        self.assertFalse(subtitle_pipeline.source_equivalent_caption("عدد 1 .7", "عدد 1.7"))

    def test_owner_local_draft_preserves_every_existing_word(self):
        path = ROOT / "proof/publication-job-20260905/F_Hafez_Youtube_8rdvid_C2963.review-v2-failed-99-take.draft-subtitle-provenance.json"
        if not path.exists():
            self.skipTest("Owner-local draft unavailable")
        evidence = json.loads(path.read_text(encoding="utf-8-sig"))["tight"]
        words = [w for cue in evidence["cues"] for w in cue["words"]]
        result = build_source_word_cues(words)
        self.assertEqual([w for c in result for w in c["words"]], words)
        self.assertEqual(" ".join(c["text"] for c in result).split(),
                         " ".join(w["text"] for w in words).split())
        # This real orphan crosses a source take boundary. It must remain a
        # flagged draft instead of being silently joined to a different take.
        short = [c for c in result if c["end"]-c["start"] < .65]
        self.assertTrue(all(c.get("layout_review") for c in short))
        self.assertTrue(any("1 .7" in c["text"] for c in result))
        self.assertTrue(any("بدم که" in c["text"] for c in result))
        self.assertTrue(all(a["end"] <= b["start"] for a, b in zip(result, result[1:])))


if __name__ == "__main__":
    unittest.main()
