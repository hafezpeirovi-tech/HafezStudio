import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
from asr_recovery import recovery_windows, recover_alignment
from subtitle_pipeline import _local_task_prompt, _task_response_is_valid
from caption_timing import build_timeline_word_cues
from rough_cut import detect_short_setup_prefix, build_variants, guard_retained_retake
from rough_cut import bind_graphic_markers_to_source
from curation_rules import curate_complete_statement
from professional_edit import guard_automatic_graphic_copy, _native_glass_concise_copy


def segment(text, start, end, probability=.9):
    return {"text": text, "start": start, "end": end, "words": [
        {"word": text, "start": start, "end": end, "probability": probability, "timing_origin": "asr-word-timestamps"}]}


class AutomaticQualityTests(unittest.TestCase):
    def test_readable_garbled_asr_is_not_automatic_title(self):
        cue = {"text": "ست تا جوف عرض و بالپایی می‌کنم.", "review_blocked": False,
               "native_typography_fit": {"status": "measured-fit-native-render-review-required"},
               "controls": {"Body": "ست تا جوف عرض و بالپایی می‌کنم."}, "sfx_cue": {"start": 3}}
        result = guard_automatic_graphic_copy([cue])[0]
        self.assertTrue(result["review_blocked"])
        self.assertNotIn("sfx_cue", result)
        self.assertFalse(cue["review_blocked"])

    def test_automatic_curated_label_is_rederived_and_live_text_checked(self):
        body = "به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی."
        cue = {"headline_fa": body, "copy_provenance": {"source_text": body},
               "controls": {"Title": "ANALYSIS PARALYSIS", "Body": body}}
        controls, evidence = _native_glass_concise_copy(cue, cue["controls"])
        self.assertEqual(evidence["display_kind"], "term-label")
        cue.update(controls=controls, native_copy_selection={**evidence, "applied": True},
                   template_layers=[{"controls": dict(controls)}])
        result = guard_automatic_graphic_copy([cue])[0]
        self.assertFalse(result.get("review_blocked", False))
        for slot in ("Title", "Body"):
            broken = copy.deepcopy(cue)
            broken["controls"][slot] = "جملهٔ ساختگی"
            self.assertTrue(guard_automatic_graphic_copy([broken])[0]["review_blocked"])
        broken = copy.deepcopy(cue)
        broken["template_layers"][0]["controls"]["Body"] = "جملهٔ ساختگی"
        self.assertTrue(guard_automatic_graphic_copy([broken])[0]["review_blocked"])

    def test_copy_gate_keeps_existing_block_and_rejects_self_asserted_approval(self):
        blocked = {"review_blocked": True, "review_blocked_reason": "Native QA failed"}
        self.assertEqual(guard_automatic_graphic_copy([blocked])[0], blocked)
        claimed = {"audio_verified": True, "native_copy_selection": {"applied": True,
                   "display_kind": "term-label", "original_controls": {"Body": "حدس"}}}
        self.assertTrue(guard_automatic_graphic_copy([claimed])[0]["review_blocked"])

    def test_unpunctuated_definition_ends_before_new_subject(self):
        text = "به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی تو انقدر تایم فریم‌ها و چارت‌ها رو بالا پایین میکنی که"
        decision = curate_complete_statement([{"id": 4, "start": 30, "end": 38, "text": text}], 0)
        self.assertEqual(decision["text"], "به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی.")
        self.assertFalse(decision["needs_manual_copy"])
        self.assertEqual(decision["source_text"], text)

    def test_graphic_uses_unique_quote_time_not_wrong_model_id(self):
        words = [{"text": t, "start": i, "end": i+.5} for i, t in enumerate("این مقدمه است این روش روشن است".split())]
        segments = [{"id": 0, "start": 0, "end": 2.5}, {"id": 1, "start": 3, "end": 6.5}]
        marker = {"type": "GRAPHIC", "segment_id": 0, "start": 0, "end": 3, "headline_fa": "این روش روشن است"}
        bound, warnings = bind_graphic_markers_to_source([marker], segments, words)
        self.assertFalse(warnings)
        self.assertEqual(bound[0]["segment_id"], 1)
        self.assertEqual(bound[0]["start"], 3)
        marker["headline_fa"] = "من استراتژی مخصوص دارم"
        bound, warnings = bind_graphic_markers_to_source([marker], segments, words)
        self.assertEqual(bound, [])
        self.assertTrue(warnings)
    def test_a_model_reason_cannot_delete_unique_speech(self):
        edit = {"segment_id": 0, "action": "cut_tight", "start": 0, "end": 2,
                "remove_text": "این روش اصلی من است", "confidence": .99, "reason": "certain false start"}
        words = [{"text": t, "start": i, "end": i+.5} for i, t in enumerate("این روش اصلی من است متن دیگری اینجا هست".split())]
        guarded, warnings = guard_retained_retake([edit], words)
        self.assertEqual(guarded[0]["action"], "review")
        self.assertTrue(warnings)

    def test_two_proposed_takes_are_not_both_deleted(self):
        phrase = "ویدیو قبلی که دیدی درباره این روش بود"
        words = [{"text": t, "start": i*.3, "end": (i+1)*.3} for i, t in enumerate((phrase+" "+phrase).split())]
        edits = [{"segment_id": i, "action": "cut_tight", "start": i*2.4, "end": (i+1)*2.4,
                  "remove_text": phrase, "confidence": .99} for i in (0, 1)]
        guarded, _ = guard_retained_retake(edits, words)
        self.assertEqual([e["action"] for e in guarded], ["cut_tight", "review"])
        guarded, _ = guard_retained_retake(edits[:1], words)
        self.assertEqual(guarded[0]["action"], "cut_tight")
        self.assertIn("retained_retake", guarded[0])
    def test_short_setup_removal_is_tight_only(self):
        clips = [[0, 10, 250, 260], [10, 21, 1250, 1261], [21, 121, 1400, 1500]]
        edits = detect_short_setup_prefix(clips, [{"start": .95, "end": 2, "text": "شروع"}], 25)
        variants = build_variants({"cam1": clips, "cam2": clips}, edits, 25, 121/25)
        self.assertEqual(variants["safe"]["removed_seconds"], 0)
        self.assertEqual(variants["tight"]["removed_seconds"], .84)
        self.assertEqual(variants["tight"]["clips"]["cam1"][0][2], 1400)

    def test_setup_does_not_remove_spoken_or_long_lead_in(self):
        words = [{"start": .1, "end": 2, "text": "شروع"}]
        self.assertEqual(detect_short_setup_prefix([[0, 10, 250, 260], [10, 121, 1400, 1511]], words, 25), [])
        self.assertEqual(detect_short_setup_prefix([[0, 30, 250, 280], [30, 121, 1400, 1491]], [{"start": 2, "end": 3}], 25), [])

    def test_caption_float_noise_narrows_but_does_not_extend(self):
        word = self.word(1, "متن", 10.1, 10.5, acoustic_end=10.49999999999999)
        cues, _ = build_timeline_word_cues(self.context([word]))
        self.assertLessEqual(cues[0]["end"], .5)
        word["acoustic_end"] = 10.49
        with self.assertRaises(ValueError):
            build_timeline_word_cues(self.context([word]))
    @staticmethod
    def context(words, keeps=None):
        return {"fps": (25, 1), "media_sha256": "a"*64, "evidence_id": "run", "words": words,
                "keeps": keeps or [{"start_frame": 0, "end_frame": 100, "source_in_frame": 250,
                                     "source_out_frame": 350, "media_sha256": "a"*64}]}

    @staticmethod
    def word(i, text, start, end, **extra):
        return {"source_word_id": str(i), "source_evidence_id": "run", "media_sha256": "a"*64,
                "text": text, "source_start": start, "source_end": end, "acoustic_start": start,
                "acoustic_end": end, "timing_origin": "asr-word-timestamps", **extra}

    def test_caption_clock_uses_retained_word_times_not_character_lengths(self):
        words = [self.word(1, "روش", 10, 10.04), self.word(2, "روشن", 10.04, 11.2)]
        cues, audit = build_timeline_word_cues(self.context(words))
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]["start"], 0)
        self.assertEqual(cues[0]["end"], 1.2)
        self.assertEqual(cues[0]["text"], "روش روشن")
        self.assertFalse(audit["publication_ready"])

    def test_caption_does_not_restore_removed_word_or_partial_tail(self):
        words = [self.word(1, "حذف", 8, 9), self.word(2, "متن", 9.8, 10.8)]
        cues, audit = build_timeline_word_cues(self.context(words))
        self.assertEqual(cues[0]["text"], "متن")
        self.assertEqual(cues[0]["start"], 0)
        self.assertEqual(audit["removed_word_ids"], ["1"])
        self.assertIn("partial-machine", str(audit["word_review"]))

    def test_caption_refuses_duplicate_provenance_and_overlapping_keeps(self):
        word = self.word(1, "متن", 10, 11)
        with self.assertRaises(ValueError):
            build_timeline_word_cues(self.context([word, word]))
        ctx = self.context([word])
        ctx["keeps"].append(dict(ctx["keeps"][0]))
        with self.assertRaises(ValueError):
            build_timeline_word_cues(ctx)

    def test_local_edit_schema_has_all_required_fields(self):
        prompt = _local_task_prompt({"task_type": "editor", "prompt": 'input\n[{"id":0,"text":"روش"}]'})
        for token in ('"action":"cut_tight"', '"confidence":0.95', '"remove_text"', '"reason"'):
            self.assertIn(token, prompt)

    def test_missing_action_is_not_success(self):
        payload = {"events": [], "markers": [], "edits": [{"segment_id": 5, "remove_text": "روش"}]}
        self.assertFalse(_task_response_is_valid("editor", payload))
        payload["edits"][0].update(action="cut_tight", confidence=.95, reason="تکرار")
        self.assertTrue(_task_response_is_valid("editor", payload))
        for bad in (True, float("nan"), 2, None):
            payload["edits"][0]["confidence"] = bad
            self.assertFalse(_task_response_is_valid("editor", payload))

    def test_long_word_and_voiced_gap_create_bounded_windows(self):
        cores, deferred = recovery_windows([segment("الف", 0, 1), segment("ب", 4, 30)], [(1, 4)], duration=35)
        self.assertTrue(cores)
        self.assertTrue(all(w["end"] - w["start"] <= 40 for w in cores))
        self.assertFalse(deferred)

    def test_silent_gap_is_not_an_anomaly(self):
        self.assertEqual(recovery_windows([segment("الف", 0, 1), segment("ب", 9, 10)], [], duration=10), ([], []))

    def test_empty_or_low_confidence_recovery_preserves_original(self):
        original = [segment("خراب", 2, 10)]
        frozen = copy.deepcopy(original)
        for answer in ([], [segment("حدس", 4, 4.5, .1)]):
            recovered, audit = recover_alignment(original, [], duration=12, transcribe_window=lambda a, b: answer)
            self.assertEqual(recovered, original)
            self.assertFalse(audit["publication_ready"])
        self.assertEqual(frozen, original)

    def test_recovery_retains_other_words_and_source_clock(self):
        original = [segment("قبل", 0, .5), segment("خراب", 2, 6), segment("بعد", 9, 9.5)]
        result, audit = recover_alignment(original, [], duration=10, transcribe_window=lambda a, b: [
            segment("نسخه", 2, 2.5), segment("کامل", 2.5, 3)])
        self.assertEqual([s["text"] for s in result], ["قبل", "نسخه", "کامل", "بعد"])
        self.assertEqual(result[1]["start"], 2)
        self.assertEqual(audit["authority"], "machine-asr-only")

    def test_recovery_never_erases_intact_final_take_inside_context(self):
        original = [segment("خراب", 2, 6), segment("نسخه", 6.2, 6.5), segment("درست", 6.5, 7)]
        result, audit = recover_alignment(original, [], duration=9, transcribe_window=lambda a, b: [
            segment("جمله", 2, 2.5), segment("کامل", 2.5, 3)])
        self.assertEqual([s["text"] for s in result], ["جمله", "کامل", "نسخه", "درست"])
        self.assertTrue(audit["original_plausible_words_preserved"])

    def test_window_budget_reports_deferred_work(self):
        rows = [segment(str(i), i*10, i*10+4) for i in range(4)]
        cores, deferred = recovery_windows(rows, [], duration=40, maximum=2)
        self.assertEqual(len(cores), 2)
        self.assertEqual(len(deferred), 2)


if __name__ == "__main__":
    unittest.main()
