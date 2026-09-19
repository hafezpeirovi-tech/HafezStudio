import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
from spoken_trigger import exact_trigger_timing
from professional_edit import _catalog_subscribe_cue, load_editorial_catalog


class SpokenTriggerTests(unittest.TestCase):
    def fixture(self):
        words = [self.word("0", "سابسکرایب", 11.2, 11.65), self.word("1", "کن،", 11.65, 11.9)]
        segment = {"id": 7, "start": 0, "end": 8, "text": "لطفا سابسکرایب کن،",
                   "source_word_ids": ["run:0", "run:1"], "source_evidence_id": "run"}
        context = {"words": words, "fps": (25, 1), "media_sha256": "a"*64, "evidence_id": "run",
                   "keeps": [{"id": "keep", "start_frame": 0, "end_frame": 300,
                              "source_in_frame": 250, "source_out_frame": 550, "media_sha256": "a"*64}]}
        return [segment], context

    @staticmethod
    def word(index, text, start, end):
        return {"source_word_id": "run:"+index, "source_evidence_id": "run", "media_sha256": "a"*64,
                "text": text, "start": 999, "end": 1000, "source_start": start, "source_end": end,
                "acoustic_start": start, "acoustic_end": end, "timing_origin": "asr-word-timestamps",
                "source_coverage": 1, "word_boundary_review_required": False, "confidence": .99}

    def run_case(self, segments, context, **kwargs):
        original = copy.deepcopy((segments, context))
        report = exact_trigger_timing(segments, "سابسکرایب کن", context,
                                      fps=kwargs.get("fps", 25), timeline_duration=kwargs.get("duration", 12))
        self.assertEqual((segments, context), original)
        self.assertFalse(report["audio_verified"])
        self.assertFalse(report["cuts_changed"])
        self.assertFalse(report["native_placement_approved"])
        return report

    def test_uses_final_acoustic_map_not_segment_or_prepare_clock(self):
        segments, context = self.fixture()
        chosen = self.run_case(segments, context)["selected"]
        self.assertEqual(chosen["start_frame"], 30)
        self.assertEqual(chosen["end_frame"], 135)
        self.assertEqual(chosen["source_word_ids"], ["run:0", "run:1"])
        self.assertEqual(chosen["start"], 1.2)

    def test_missing_context_never_uses_segment_start_as_valid_timing(self):
        segments, _ = self.fixture()
        self.assertIsNone(self.run_case(segments, None)["selected"])

    def test_missing_owner_or_paraphrased_trigger_fails(self):
        for mutation in ("owner", "phrase", "literal"):
            segments, context = self.fixture()
            if mutation == "owner":
                segments[0].pop("source_word_ids")
            elif mutation == "phrase":
                segments[0]["text"] = "سابسکرایب یادت نره"
            else:
                context["words"][1]["text"] = "کنید"
            self.assertIsNone(self.run_case(segments, context)["selected"])

    def test_partial_low_confidence_nonfinite_or_boolean_evidence_fails(self):
        changes = [{"source_coverage": .99}, {"word_boundary_review_required": True},
                   {"confidence": .89}, {"confidence": float("inf")}, {"confidence": True},
                   {"timing_origin": "interpolated"}, {"media_sha256": "b"*64}]
        for change in changes:
            with self.subTest(change=change):
                segments, context = self.fixture()
                context["words"][0].update(change)
                self.assertIsNone(self.run_case(segments, context)["selected"])

    def test_duplicate_ids_or_segment_ownership_fail(self):
        for duplicate in ("word", "owner"):
            segments, context = self.fixture()
            if duplicate == "word":
                context["words"].append(copy.deepcopy(context["words"][0]))
            else:
                segments.append({**segments[0], "id": 8})
            self.assertIsNone(self.run_case(segments, context)["selected"])

    def test_final_cut_refuses_word_even_if_prepare_marked_it_complete(self):
        segments, context = self.fixture()
        context["keeps"][0].update(source_in_frame=282, source_out_frame=582)
        self.assertIsNone(self.run_case(segments, context)["selected"])

    def test_selected_words_cannot_skip_an_intervening_source_word(self):
        segments, context = self.fixture()
        context["words"][1].update(source_start=11.8, acoustic_start=11.8)
        context["words"].insert(1, self.word("middle", "نکن", 11.66, 11.78))
        result = self.run_case(segments, context)
        self.assertIsNone(result["selected"])
        self.assertEqual(result["rejections"][0]["reason"], "trigger-skips-intervening-source-word")

    def test_zero_gap_split_is_safe_but_removed_source_gap_is_not(self):
        for removed in (0, 1):
            segments, context = self.fixture()
            context["keeps"] = [
                {"id": "a", "start_frame": 0, "end_frame": 36, "source_in_frame": 250,
                 "source_out_frame": 286, "media_sha256": "a"*64},
                {"id": "b", "start_frame": 36, "end_frame": 300-removed,
                 "source_in_frame": 286+removed, "source_out_frame": 550, "media_sha256": "a"*64}]
            self.assertEqual(self.run_case(segments, context)["selected"] is not None, removed == 0)

    def test_wrong_clock_retime_and_source_reordering_fail(self):
        segments, context = self.fixture()
        self.assertIsNone(self.run_case(segments, context, fps=30)["selected"])
        context["keeps"][0]["source_out_frame"] = 551
        self.assertIsNone(self.run_case(segments, context)["selected"])

    def test_later_complete_occurrence_replaces_partial_first(self):
        segments, context = self.fixture()
        context["words"][0]["word_boundary_review_required"] = True
        context["words"].extend([self.word("2", "سابسکرایب", 15, 15.4), self.word("3", "کن", 15.4, 15.7)])
        segments.append({"id": 8, "start": 5, "end": 8, "text": "سابسکرایب کن",
                         "source_word_ids": ["run:2", "run:3"], "source_evidence_id": "run"})
        result = self.run_case(segments, context)
        self.assertEqual(result["selected"]["segment_id"], 8)
        self.assertEqual(result["selected"]["start_frame"], 125)
        self.assertEqual(len(result["rejections"]), 1)

    def test_insufficient_tail_does_not_truncate_authored_animation(self):
        segments, context = self.fixture()
        self.assertIsNone(self.run_case(segments, context, duration=4)["selected"])

    def test_timing_does_not_clear_native_failure_or_change_authored_text(self):
        segments, context = self.fixture()
        catalog = load_editorial_catalog()
        before = copy.deepcopy(catalog)
        cue = _catalog_subscribe_cue(segments, 12, catalog, word_context=context, fps=25)
        self.assertTrue(cue["review_blocked"])
        self.assertEqual(cue["start"], 1.2)
        self.assertIsNotNone(cue["trigger_timing"]["selected"])
        self.assertEqual(cue["controls"]["CTA Text"], "سابسکرایب کن")
        self.assertEqual(before, catalog)


if __name__ == "__main__":
    unittest.main()
