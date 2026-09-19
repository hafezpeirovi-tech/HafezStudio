from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = PRODUCT_ROOT / "engine" / "src" / "hermes_video"
sys.path.insert(0, str(ENGINE_DIR))

import audio_master  # noqa: E402
import brand_tokens  # noqa: E402
import curation_rules  # noqa: E402
import editorial_elements  # noqa: E402
import motion_style  # noqa: E402
import professional_edit  # noqa: E402
import rough_cut  # noqa: E402
import runtime_paths  # noqa: E402
import smart_crop  # noqa: E402
import sound_design  # noqa: E402
import studio_cli  # noqa: E402
import subtitle_pipeline  # noqa: E402


class CompleteStatementTests(unittest.TestCase):
    def test_incomplete_transcript_is_joined_until_the_thought_finishes(self) -> None:
        segments = [
            {"id": 0, "start": 0.0, "end": 2.0, "text": "اومدم یک الگوریتمی روی تریدینگ ویو ساختم که سیگنال"},
            {"id": 1, "start": 2.1, "end": 4.0, "text": "تولید می‌کند و نتیجه را برای اجرای خودکار می‌فرستد"},
        ]
        statement = professional_edit._complete_statement(segments, 0, {})
        self.assertIn("تولید می‌کند", statement)
        self.assertNotEqual(statement.rstrip("."), segments[0]["text"])
        self.assertTrue(statement.endswith("."))

    def test_source_faithful_mode_rejects_an_unsupported_editorial_paraphrase(self) -> None:
        segments = [{"id": 0, "start": 0.0, "end": 2.0, "text": "متن خام و نامرتب"}]
        marker = {"headline_fa": "این الگوریتم سیگنال معاملاتی را به‌صورت خودکار تولید می‌کند"}
        with patch.dict(os.environ, {"HERMES_COPY_MODE": "source-faithful"}):
            decision = professional_edit._complete_statement_decision(segments, 0, marker)
        self.assertEqual(decision["text"], "…")
        self.assertEqual(decision["source"], "manual-placeholder")
        self.assertTrue(decision["needs_manual_copy"])

    def test_later_corrected_take_with_same_opening_wins(self) -> None:
        segments = [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "من این الگوریتم رو طوری ساختم که"},
            {"id": 1, "start": 1.0, "end": 2.0, "text": "نه بذار دوباره بگم"},
            {"id": 2, "start": 2.0, "end": 4.0, "text": "من این الگوریتم رو طوری ساختم که سیگنال رو سریع می‌فرسته"},
        ]
        decision = professional_edit._complete_statement_decision(segments, 0, {})
        self.assertEqual(decision["source"], "later-corrected-take")
        self.assertIn("سریع می‌فرسته", decision["text"])
        self.assertFalse(decision["needs_manual_copy"])

    def test_unresolved_fragment_becomes_explicit_editable_placeholder(self) -> None:
        segments = [{"id": 0, "start": 0.0, "end": 1.0, "text": "این سیستم برای"}]
        decision = professional_edit._complete_statement_decision(segments, 0, {})
        self.assertEqual(decision["text"], "…")
        self.assertEqual(decision["source"], "manual-placeholder")
        self.assertTrue(decision["needs_manual_copy"])


class SpeechRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segment = {"id": 7, "start": 0.0, "end": 4.0, "text": "من سیستم را چیدم من سیستم را کامل چیدم"}
        tokens = self.segment["text"].split()
        self.words = [
            {"text": token, "start": index * 0.32, "end": index * 0.32 + 0.25}
            for index, token in enumerate(tokens)
        ]

    def test_repeated_restart_cuts_first_attempt_and_keeps_correction(self) -> None:
        raw = [{
            "segment_id": 7,
            "action": "cut_tight",
            "confidence": 0.97,
            "remove_text": self.segment["text"],
            "reason": "تکرار و شروع ناقص که با بیان درست اصلاح شده است",
        }]
        edits, warnings = rough_cut.validate_edit_decisions(raw, [self.segment], self.words)
        self.assertFalse(warnings)
        self.assertEqual(len(edits), 1)
        self.assertLess(edits[0]["end"], self.words[4]["start"])
        remapped = rough_cut.remap_segments(
            [self.segment],
            [{"old_start": 0.0, "old_end": 4.0, "new_start": 0.0, "new_end": 4.0}],
            edits,
            "tight",
        )
        self.assertEqual(remapped[0]["text"], "من سیستم را کامل چیدم")

    def test_editorial_shortening_without_a_real_speech_error_is_rejected(self) -> None:
        raw = [{
            "segment_id": 7,
            "action": "cut_tight",
            "confidence": 0.99,
            "remove_text": "من سیستم را چیدم",
            "reason": "کوتاه‌سازی برای ریتم بهتر",
        }]
        edits, warnings = rough_cut.validate_edit_decisions(raw, [self.segment], self.words)
        self.assertEqual(edits, [])
        self.assertTrue(warnings)

    def test_overlapping_ai_and_deterministic_edits_do_not_delete_the_kept_repeat(self) -> None:
        raw = [
            {
                "segment_id": 7,
                "action": "cut_tight",
                "confidence": 0.97,
                "remove_text": self.segment["text"],
                "reason": "تکرار و شروع ناقص",
            },
            {
                "segment_id": 7,
                "action": "cut_tight",
                "confidence": 0.965,
                "remove_text": "من سیستم را چیدم",
                "reason": "تکرار فوری و شروع ناقص",
            },
        ]
        edits, _warnings = rough_cut.validate_edit_decisions(raw, [self.segment], self.words)
        remapped = rough_cut.remap_segments(
            [self.segment],
            [{"old_start": 0.0, "old_end": 4.0, "new_start": 0.0, "new_end": 4.0}],
            edits,
            "tight",
        )
        self.assertEqual(remapped[0]["text"], "من سیستم را کامل چیدم")

    def test_fuzzy_cleanup_handles_one_asr_token_corrected_into_two_words(self) -> None:
        text = "معاملات الگوریتمی تو به جای اینکه با چشم دنبال نقطه ورود بگردی"
        phrase = "تو به جایین که با چشم دنبال نقطه ورود بگردی"
        self.assertEqual(rough_cut._remove_first_fuzzy_phrase(text, phrase), "معاملات الگوریتمی")

    def test_span_text_uses_word_midpoints_and_does_not_eat_the_previous_word(self) -> None:
        words = [
            {"text": "الگوریتمی", "start": 0.0, "end": 1.2},
            {"text": "تو", "start": 1.0, "end": 1.3},
        ]
        self.assertEqual(rough_cut._matched_text_for_span(words, (1.05, 1.35)), "تو")

    def test_deterministic_restart_detector_marks_tight_only(self) -> None:
        edits = rough_cut.detect_repeated_speech_edits([self.segment], self.words)
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["action"], "cut_tight")
        self.assertIn("تکرار", edits[0]["reason"])
        self.assertIn("چیدم", edits[0]["remove_text"])

    def test_unique_nearby_phrase_repairs_a_small_ai_segment_id_drift(self) -> None:
        target = {**self.segment, "start": 1.1, "end": 5.1}
        target_words = [
            {**word, "start": word["start"] + 1.1, "end": word["end"] + 1.1}
            for word in self.words
        ]
        segments = [
            {"id": 6, "start": 0.0, "end": 1.0, "text": "بخش قبلی کامل است"},
            target,
        ]
        raw = [{
            "segment_id": 6,
            "action": "cut_tight",
            "confidence": 0.97,
            "remove_text": self.segment["text"],
            "reason": "تکرار و شروع ناقص که اصلاح شده است",
        }]
        edits, warnings = rough_cut.validate_edit_decisions(raw, segments, target_words)
        self.assertEqual(edits[0]["segment_id"], 7)
        self.assertTrue(any("منتقل شد" in warning for warning in warnings))

    def test_short_two_word_restart_keeps_the_corrected_sentence(self) -> None:
        segment = {"id": 9, "start": 0.0, "end": 3.0, "text": "بهت بگم که بهت بگم روش درست چیه"}
        words = [
            {"text": token, "start": index * 0.3, "end": index * 0.3 + 0.23}
            for index, token in enumerate(segment["text"].split())
        ]
        raw = [{
            "segment_id": 9,
            "action": "cut_safe",
            "confidence": 0.97,
            "remove_text": segment["text"],
            "reason": "تکرار قطعی و شروع ناقص",
        }]
        edits, _warnings = rough_cut.validate_edit_decisions(raw, [segment], words)
        self.assertLess(edits[0]["end"] - edits[0]["start"], 1.0)

    def test_cross_segment_false_start_keeps_only_the_later_complete_attempt(self) -> None:
        segments = [
            {"id": 0, "start": 0.0, "end": 3.0, "text": "تو به جای اینکه با چشم دنبال نقطه ورود بگردی به سیستم میگی"},
            {"id": 1, "start": 3.0, "end": 4.0, "text": "فلان شرایط نامفهوم"},
            {"id": 2, "start": 4.0, "end": 8.0, "text": "تو به جای اینکه با چشم دنبال نقطه ورود بگردی به الگوریتم میگی"},
        ]
        edits = rough_cut.detect_repeated_speech_edits(segments, [])
        edited_ids = {item["segment_id"] for item in edits if item["source"] == "deterministic-cross-segment-restart"}
        self.assertEqual(edited_ids, {0, 1})

    def test_restart_that_begins_on_previous_segment_removes_its_leading_word(self) -> None:
        segments = [
            {"id": 3, "start": 0.0, "end": 2.0, "text": "معامله را می‌سپاری دست ربات اجرا"},
            {"id": 4, "start": 2.0, "end": 5.0, "text": "را می‌سپاری به ماشین اجرا را می‌سپاری به ماشین"},
        ]
        words = []
        for segment in segments:
            for index, token in enumerate(segment["text"].split()):
                start = float(segment["start"]) + index * 0.25
                words.append({"text": token, "start": start, "end": start + 0.2})
        edits = rough_cut.detect_repeated_speech_edits(segments, words)
        boundary = [item for item in edits if item["source"] == "deterministic-boundary-restart"]
        self.assertEqual([(item["segment_id"], item["remove_text"]) for item in boundary], [(3, "اجرا")])

    def test_long_transcript_paragraph_is_not_used_as_graphic_copy(self) -> None:
        segments = [
            {
                "id": 0,
                "start": 0.0,
                "end": 8.0,
                "text": " ".join(["این توضیح خام طولانی برای گفتار مناسب است اما روی تصویر خوانایی کافی ندارد"] * 5),
            }
        ]
        self.assertEqual(professional_edit._complete_statement(segments, 0, {}), "…")

    def test_grounded_summary_accepts_only_transcript_supported_wording(self) -> None:
        segments = [{
            "id": 0,
            "start": 0.0,
            "end": 2.0,
            "text": "بانک‌ها با اختلاف پنج تا ده میلی‌ثانیه معامله می‌کنند اما",
        }]
        marker = {"headline_fa": "بانک‌ها با اختلاف پنج تا ده میلی‌ثانیه معامله می‌کنند"}
        with patch.dict(os.environ, {"HERMES_COPY_MODE": "grounded-summary"}):
            decision = professional_edit._complete_statement_decision(segments, 0, marker)
        self.assertEqual(decision["source"], "speaker-exact-selection")
        self.assertTrue(decision["grounding"]["supported"])

    def test_grounding_rejects_the_invented_hafez_following_phrase(self) -> None:
        source = "من حافظ پیروی‌ام و توی این ویدیو اومدم استراتژی رو معرفی کنم"
        candidate = "حافظ پیروی استراتژی مخصوص داره"
        grounding = curation_rules.copy_grounding(candidate, [source])
        self.assertFalse(grounding["supported"])
        self.assertLess(grounding["content_token_coverage"], 0.82)


class GraphicPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segments = [
            {
                "id": index,
                "start": index * 7.0,
                "end": index * 7.0 + 4.0,
                "text": f"این نکته مهم شماره {index} درباره سیستم هوشمند است.",
            }
            for index in range(36)
        ]

    def test_max_density_is_engaging_but_bounded(self) -> None:
        with patch.dict(os.environ, {"HERMES_GRAPHIC_DENSITY": "max"}):
            cues = professional_edit.build_graphic_cues(self.segments, 252.0)
        self.assertGreaterEqual(len(cues), 8)
        self.assertLessEqual(len(cues), 12)
        self.assertTrue(all(cue["headline_fa"].endswith((".", "!", "؟", "?")) for cue in cues))
        self.assertTrue(all(cue["font_family"] == "Abar High FaNum" for cue in cues))

    def test_flowchart_uses_real_nodes_and_custom_mogrt(self) -> None:
        markers = [
            {
                "segment_id": 5,
                "type": "FLOWCHART",
                "visual_kind": "flowchart",
                "headline_fa": "سیستم داده را در چهار مرحله به تصمیم تبدیل می‌کند.",
                "kicker_en": "AUTOMATION FLOW",
                "nodes": ["دریافت داده", "پاک‌سازی", "تحلیل", "اجرای تصمیم"],
            }
        ]
        cues = professional_edit.build_graphic_cues(self.segments, 252.0, markers)
        flow = next(cue for cue in cues if cue["segment_id"] == 5)
        self.assertEqual(flow["kind"], "flowchart")
        self.assertEqual(flow["nodes"], markers[0]["nodes"])
        self.assertEqual(flow["element_id"], "hermes-flowchart")
        self.assertEqual(Path(flow["template_path"]).name, "Hafez Hermes Flowchart.mogrt")
        self.assertEqual(flow["selection_trace"]["selected_id"], "hermes-flowchart")

    def test_source_faithful_mode_ignores_an_invented_semantic_subtitle(self) -> None:
        segments = [{
            "id": 0,
            "start": 0.0,
            "end": 3.0,
            "text": "من حافظ پیروی‌ام و این استراتژی را در ویدیو معرفی می‌کنم.",
        }]
        markers = [{
            "segment_id": 0,
            "visual_kind": "statement",
            "semantic_subtitle_fa": "حافظ پیروی استراتژی مخصوص داره.",
        }]
        with patch.dict(os.environ, {"HERMES_COPY_MODE": "source-faithful", "HERMES_GRAPHIC_DENSITY": "balanced"}):
            cues = professional_edit.build_graphic_cues(segments, 3.0, markers)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]["semantic_subtitle_source"], "speaker-copy")
        self.assertNotIn("مخصوص داره", cues[0]["headline_fa"])

    def test_preview_only_png_is_transparent_and_visually_nonempty(self) -> None:
        cue = {
            "id": "graphic-001",
            "segment_id": 0,
            "start": 0.0,
            "end": 4.0,
            "text": "این الگوریتم سیگنال معاملاتی را به‌صورت خودکار تولید می‌کند.",
            "headline_fa": "این الگوریتم سیگنال معاملاتی را به‌صورت خودکار تولید می‌کند.",
            "kicker_en": "SIGNAL GENERATION",
            "kind": "statement",
            "placement": "right",
            "font_family": "Auto Persian",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            rendered = professional_edit.render_graphic_assets([cue], temp_dir, 1280, 720)
            image = Image.open(rendered[0]["asset_path"]).convert("RGBA")
            self.assertEqual(image.size, (1280, 720))
            alpha = image.getchannel("A")
            self.assertIsNotNone(alpha.getbbox())
            self.assertLess(alpha.getbbox()[0], alpha.getbbox()[2])

    def test_multi_frame_union_layout_never_truncates_copy(self) -> None:
        original = "این جمله کامل و کمی طولانی است و بدون بریدگی روی تصویر باقی می‌ماند."
        cue = {
            "id": "graphic-001", "segment_id": 0, "start": 1.0, "end": 4.4,
            "text": original, "headline_fa": original, "kind": "statement", "controls": {},
        }
        tracked = [{
            "sample_frames": [30, 45, 60, 75, 90, 105, 120, 132],
            "sample_count": 8,
            "detected_count": 8,
            "coverage": 1.0,
            "face_union": (0.42, 0.20, 0.18, 0.22),
            "subject_union": (0.29, 0.08, 0.44, 0.82),
        }]
        with patch.object(professional_edit, "detect_subject_box_unions", return_value=(tracked, "yunet-cuda")):
            placed, backend = professional_edit.apply_face_safe_layout(
                [cue], video_path="camera.mp4", clips=[[0, 300, 0]], fps=30.0, width=1920, height=1080,
            )
        self.assertEqual(backend, "yunet-cuda")
        self.assertEqual(placed[0]["text"], original)
        self.assertNotIn("…", placed[0]["text"])
        self.assertEqual(placed[0]["layout"]["tracking_mode"], "every-visible-source-frame-union")
        self.assertGreater(placed[0]["layout"]["tracking_sample_count"], 1)

    def test_text_animation_title_emits_editable_bilingual_layers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / curation_rules.TEXT_ANIMATION_TITLE.template_name).write_bytes(b"test-template")
            with patch.dict(os.environ, {"HERMES_TEXT_ANIMATION_ROOT": str(root)}):
                cues = professional_edit.build_graphic_cues(
                    self.segments,
                    252.0,
                    [{"segment_id": 0, "type": "TITLE", "visual_kind": "chapter", "title_en": "SIGNAL ENGINE"}],
                )
        title = next(cue for cue in cues if cue["segment_id"] == 0)
        self.assertEqual(title["template"], curation_rules.TEXT_ANIMATION_TITLE.template_name)
        self.assertEqual(title["headline_en"], "SIGNAL ENGINE")
        self.assertEqual(title["bilingual_typography"]["english"]["font_family"], "Relaxe")
        self.assertFalse(title["bilingual_typography"]["motion"]["linear_allowed"])
        self.assertEqual(
            title["template_layers"][0]["controls"][curation_rules.TEXT_ANIMATION_TITLE.english_control],
            "SIGNAL ENGINE",
        )
        self.assertEqual(
            title["template_layers"][0]["controls"][curation_rules.TEXT_ANIMATION_TITLE.persian_control],
            title["headline_fa"],
        )
        self.assertEqual(len(title["template_layers"]), 1)

    def test_template_identity_prefers_history_and_never_exceeds_four_families(self) -> None:
        cues = [
            {
                "id": f"cue-{index}",
                "template_family": family,
                "priority": "high" if family == "hafez-flowchart" else "normal",
                "kind": "flowchart" if family == "hafez-flowchart" else "statement",
            }
            for index, family in enumerate(
                (
                    "hafez-statement",
                    "hafez-keyword",
                    "hafez-hud",
                    "hafez-number",
                    "hafez-flowchart",
                    "hafez-compare",
                )
            )
        ]
        curated, identity = curation_rules.select_template_families(
            cues,
            history=["hafez-keyword", "hafez-statement"],
            limit=4,
        )
        selected = {cue["template_family"] for cue in curated}
        self.assertLessEqual(len(selected), 4)
        self.assertIn("hafez-keyword", identity["selected"])
        self.assertIn("hafez-statement", identity["selected"])
        self.assertIn("hafez-flowchart", identity["selected"])

    def test_curated_sfx_is_locked_to_the_first_mogrt_frame(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rendered = root / "hafez-hero-glass.wav"
            rendered.write_bytes(b"layered-local-sfx")
            details = {
                "duration": 0.86,
                "layers": ["soft-body", "micro-transient", "glass-settle"],
                "transient_offset_ms": 0,
                "settle_offset_ms": 245,
            }
            with patch.object(professional_edit, "recipe_asset", return_value=(rendered, details)):
                cue = professional_edit.build_sfx_cue(
                    {"id": "title", "start": 1.013, "kind": "chapter", "template_family": "hafez-hero-highlight"},
                    30.0,
                )
        self.assertIsNotNone(cue)
        self.assertEqual(cue["start_frame"], 30)
        self.assertEqual(cue["start"], 1.0)
        self.assertEqual(cue["sync"], "mogrt-first-entry-frame")
        self.assertTrue(cue["voice_untouched"])
        self.assertEqual(cue["ducking_target"], "background-music-only")
        self.assertEqual(cue["sample_rate"], 48_000)
        self.assertEqual(cue["recipe"], "hero-glass")
        self.assertEqual(len(cue["layers"]), 3)
        self.assertFalse(cue["generated_audio"])

    def test_selected_real_mogrt_is_editable_and_has_no_grain_asset(self) -> None:
        mogrt = curation_rules.resolve_text_animation_title()
        self.assertIsNotNone(mogrt)
        inspection = curation_rules.inspect_mogrt_asset(mogrt)
        self.assertTrue(inspection["grain_free"])
        self.assertEqual(
            set(inspection["editable_controls"]),
            {
                curation_rules.TEXT_ANIMATION_TITLE.english_control,
                curation_rules.TEXT_ANIMATION_TITLE.persian_control,
                curation_rules.TEXT_ANIMATION_TITLE.position_control,
                curation_rules.TEXT_ANIMATION_TITLE.scale_control,
            },
        )
        for control in (
            curation_rules.TEXT_ANIMATION_TITLE.english_control,
            curation_rules.TEXT_ANIMATION_TITLE.persian_control,
        ):
            self.assertTrue(inspection["font_controls"][control]["font_family_editable"])
            self.assertTrue(inspection["font_controls"][control]["font_size_editable"])

    def test_fullscreen_glass_is_the_rule_based_hook_and_chapter_family(self) -> None:
        style = motion_style.load_motion_style()
        family = motion_style.family_for_kind("chapter", style)
        self.assertEqual(family["familyId"], "hafez-fullscreen-glass")
        self.assertEqual(len(family["variants"]), 3)
        self.assertEqual(curation_rules.TEXT_ANIMATION_TITLE.template_name, "Hafez Fullscreen Glass Focus.mogrt")
        for variant in family["variants"]:
            self.assertTrue((PRODUCT_ROOT / "motion-pack" / "dist" / variant["template"]).is_file())

    def test_every_fullscreen_glass_variant_is_grain_free_and_font_editable(self) -> None:
        variants = motion_style.load_motion_style()["families"]["fullscreen-glass"]["variants"]
        for variant in variants:
            path = PRODUCT_ROOT / "motion-pack" / "dist" / variant["template"]
            with zipfile.ZipFile(path) as archive:
                payloads = [archive.read(info) for info in archive.infolist() if info.file_size <= 64 * 1024 * 1024]
                self.assertFalse(any(b"grain" in payload.lower() for payload in payloads), path.name)
                definition_name = next(name for name in archive.namelist() if name.casefold().endswith("definition.json"))
                definition = json.loads(archive.read(definition_name).decode("utf-8-sig"))
            text_controls = [
                control for control in definition["clientControls"]
                if int(control.get("type", -1)) == 6
            ]
            self.assertGreaterEqual(len(text_controls), 3, path.name)
            for control in text_controls:
                font_info = control["fonteditinfo"]
                self.assertTrue(font_info["capPropFontEdit"], path.name)
                self.assertTrue(font_info["capPropFontSizeEdit"], path.name)

    def test_title_hero_deep_glow_controls_are_real_and_default_to_radius_200(self) -> None:
        path = PRODUCT_ROOT / "motion-pack" / "dist" / "Hafez Hermes Title Hero 3.mogrt"
        with zipfile.ZipFile(path) as archive:
            definition_name = next(
                name for name in archive.namelist()
                if name.casefold().endswith("definition.json")
            )
            definition = json.loads(archive.read(definition_name).decode("utf-8-sig"))

        controls = {
            control["uiName"]["strDB"][0]["str"]: control
            for control in definition["clientControls"]
        }
        self.assertEqual(controls["Glow Radius"]["value"], 200)
        self.assertEqual((controls["Glow Radius"]["min"], controls["Glow Radius"]["max"]), (0, 500))
        self.assertEqual(controls["Glow Intensity"]["value"], 20)
        self.assertEqual((controls["Glow Intensity"]["min"], controls["Glow Intensity"]["max"]), (0, 100))
        self.assertTrue(controls["Title"]["fonteditinfo"]["capPropFontEdit"])
        self.assertTrue(controls["Title"]["fonteditinfo"]["capPropFontSizeEdit"])

        builder = (
            PRODUCT_ROOT
            / "motion-pack"
            / "after-effects"
            / "build_title_hero_3_review_2_deepglow.jsx"
        ).read_text(encoding="utf-8")
        self.assertIn('effect(\\"Glow Radius\\")(\\"Slider\\")', builder)
        self.assertIn('effect(\\"Glow Intensity\\")(\\"Slider\\") / 100', builder)
        self.assertIn('radius.setValue(200)', builder)
        self.assertIn('exposure.setValue(0.2)', builder)

    def test_fullscreen_glass_takeover_tracks_subject_but_uses_centered_safe_card(self) -> None:
        cue = {
            "id": "hero-001",
            "segment_id": 0,
            "start": 0.0,
            "end": 4.8,
            "text": "این جمله کامل و مناسب عنوان اصلی است.",
            "headline_fa": "این جمله کامل و مناسب عنوان اصلی است.",
            "headline_en": "THE WORKFLOW",
            "kind": "chapter",
            "template": curation_rules.TEXT_ANIMATION_TITLE.template_name,
            "template_layers": [{"role": "bilingual-hero-title", "controls": {}}],
            "controls": {},
        }
        tracked = [{
            "sample_frames": list(range(144)),
            "sample_count": 144,
            "detected_count": 144,
            "body_complete": True,
            "body_tracking_method": "pphumanseg-independent-person-union",
            "coverage": 1.0,
            "face_union": (0.42, 0.20, 0.18, 0.22),
            "subject_union": (0.29, 0.08, 0.44, 0.82),
        }]
        with patch.object(professional_edit, "detect_subject_box_unions", return_value=(tracked, "yunet-cpu")):
            placed, _ = professional_edit.apply_face_safe_layout(
                [cue], video_path="camera.mp4", clips=[[0, 144, 0]], fps=30.0, width=1920, height=1080,
            )
        layout = placed[0]["layout"]
        self.assertEqual(layout["region"], "fullscreen-takeover")
        self.assertEqual(layout["collision_policy"], "intentional-fullframe-takeover")
        self.assertTrue(layout["collision_free"])
        self.assertEqual(layout["mogrt_layout_position"], [960.0, 540.0])
        self.assertEqual(layout["scale"], 100.0)
        self.assertAlmostEqual(layout["source_visibility"], 0.09, places=2)
        self.assertEqual(placed[0]["controls"]["Glass Opacity"], 72.0)

    def test_safe_layout_has_zero_subject_overlap_and_stays_inside_title_safe(self) -> None:
        cue = {
            "id": "graphic-001",
            "segment_id": 0,
            "start": 0.0,
            "end": 3.12,
            "text": "این جمله کامل و قابل‌ویرایش باقی می‌ماند.",
            "headline_fa": "این جمله کامل و قابل‌ویرایش باقی می‌ماند.",
            "kind": "chapter",
            "controls": {},
        }
        tracked = [{
            "sample_frames": list(range(94)),
            "sample_count": 94,
            "detected_count": 94,
            "body_complete": True,
            "body_tracking_method": "pphumanseg-independent-person-union",
            "coverage": 1.0,
            "face_union": (0.43, 0.19, 0.16, 0.21),
            "subject_union": (0.29, 0.08, 0.44, 0.84),
        }]
        with patch.object(professional_edit, "detect_subject_box_unions", return_value=(tracked, "yunet-cpu")):
            placed, _ = professional_edit.apply_face_safe_layout(
                [cue], video_path="camera.mp4", clips=[[0, 94, 0, 94]], fps=30.0, width=1920, height=1080,
            )
        layout = placed[0]["layout"]
        self.assertTrue(layout["collision_free"])
        self.assertTrue(layout["safe_area_contained"])
        self.assertEqual(layout["face_overlap_ratio"], 0.0)
        self.assertEqual(layout["safe_margin_overlap_ratio"], 0.0)
        self.assertGreater(layout["tracking_sample_count"], 1)
        self.assertEqual(layout["mogrt_coordinate_space"], [1920, 1080])

    def test_motion_style_is_the_ui_language_and_rejects_vendor_skin(self) -> None:
        contract = motion_style.load_motion_style()
        self.assertEqual(contract["brandTokenId"], "hafez-premium-neon")
        self.assertEqual(contract["motion"]["entryCurve"], [0.16, 0.84, 0.22, 1.0])
        self.assertEqual(contract["motion"]["exitCurve"], [0.4, 0.0, 0.2, 1.0])
        self.assertFalse(contract["motion"]["linearAllowed"])
        self.assertFalse(contract["material"]["grainAllowed"])
        self.assertFalse(contract["visualLimits"]["vendorTemplateSkinAllowed"])
        self.assertLessEqual(len(contract["families"]), 4)


class SpatialTrackingTests(unittest.TestCase):
    def test_face_and_body_union_cover_every_detected_sample(self) -> None:
        boxes = {
            10: (0.10, 0.20, 0.10, 0.12),
            20: (0.36, 0.18, 0.12, 0.14),
            30: (0.24, 0.22, 0.11, 0.13),
        }
        with patch.object(smart_crop, "detect_face_boxes", return_value=(boxes, "yunet-cuda")):
            unions, backend = smart_crop.detect_subject_box_unions("camera.mp4", [[10, 20, 30]])
        face = unions[0]["face_union"]
        subject = unions[0]["subject_union"]
        self.assertEqual(backend, "yunet-cuda")
        self.assertAlmostEqual(face[0], 0.10)
        self.assertGreaterEqual(face[0] + face[2], 0.48)
        self.assertLessEqual(subject[0], face[0])
        self.assertGreaterEqual(subject[2], face[2])
        self.assertEqual(unions[0]["coverage"], 1.0)

    def test_title_and_body_typography_are_independent_and_recorded(self) -> None:
        bundled = PRODUCT_ROOT / "app" / "assets" / "fonts" / "Estedad-VF.ttf"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            title_font = temp / "Display-Variable.ttf"
            body_font = temp / "Reading-Variable.ttf"
            title_font.write_bytes(bundled.read_bytes())
            body_font.write_bytes(bundled.read_bytes())
            environment = {
                "HERMES_TITLE_FONT_PATH": str(title_font),
                "HERMES_TITLE_FONT_FAMILY": "Display Variable",
                "HERMES_TITLE_FONT_WEIGHT": "900",
                "HERMES_BODY_FONT_PATH": str(body_font),
                "HERMES_BODY_FONT_FAMILY": "Reading Variable",
                "HERMES_BODY_FONT_WEIGHT": "400",
            }
            cues = [
                {"id": "graphic-001", "segment_id": 0, "start": 0.0, "end": 4.0, "duration": 4.0, "text": "این عنوان مهم و کامل است.", "headline_fa": "این عنوان مهم و کامل است.", "kicker_en": "CHAPTER", "kind": "chapter", "font_role": "title", "font_weight": 900, "placement": "center", "template": "Hafez Chapter Hero.mogrt", "font_family": "Display Variable"},
                {"id": "graphic-002", "segment_id": 1, "start": 5.0, "end": 9.0, "duration": 4.0, "text": "این متن توضیحی خوانا و کامل است.", "headline_fa": "این متن توضیحی خوانا و کامل است.", "kicker_en": "KEY INSIGHT", "kind": "statement", "font_role": "body", "font_weight": 400, "placement": "right", "template": "Hafez Neural Statement.mogrt", "font_family": "Reading Variable"},
            ]
            with patch.dict(os.environ, environment):
                rendered = professional_edit.render_graphic_assets(cues, temp / "graphics", 1280, 720)
                plan_path = temp / "professional-plan.json"
                professional_edit.write_professional_plan(
                    plan_path,
                    sequence_name="Typography Test",
                    fps=30.0,
                    camera_schedule=[],
                    events=[],
                    graphics=rendered,
                )
            self.assertEqual(Path(rendered[0]["font_path"]), title_font)
            self.assertEqual(Path(rendered[1]["font_path"]), body_font)
            payload = json.loads(plan_path.read_text(encoding="utf-8-sig"))
            self.assertEqual(payload["typography"]["title"]["family"], "Display Variable")
            self.assertEqual(payload["typography"]["title"]["weight"], 900)
            self.assertEqual(payload["typography"]["body"]["family"], "Reading Variable")
            self.assertEqual(payload["typography"]["body"]["weight"], 400)
            self.assertEqual(payload["typography"]["system"], "Hafez Adaptive Type 2026")


class ProductContractTests(unittest.TestCase):
    def test_premium_neon_tokens_drive_ui_python_and_mogrt(self) -> None:
        payload = json.loads((PRODUCT_ROOT / "config" / "brand-tokens.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["palette"]["canvas"], "#020303")
        self.assertEqual(payload["palette"]["primaryAccent"], "#55FF72")
        self.assertEqual(payload["palette"]["negativeAccent"], "#FF5964")
        self.assertFalse(payload["rules"]["grainAllowed"])
        controls = brand_tokens.mogrt_control_values(payload)
        self.assertEqual(controls["Corner Radius"], 40.0)
        self.assertEqual(controls["Primary Accent"][:3], [0.333333, 1.0, 0.447059])
        styles = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        preload = (PRODUCT_ROOT / "electron" / "preload.js").read_text(encoding="utf-8")
        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        builder = (PRODUCT_ROOT / "motion-pack" / "after-effects" / "build_hafez_motion_pack.jsx").read_text(encoding="utf-8")
        self.assertIn("--brand-positive", styles)
        self.assertIn("applyBrandTokens", renderer)
        self.assertIn("getBrandTokens", preload)
        self.assertIn('ipcMain.handle("brand:get-tokens"', main)
        for control in ("Canvas Color", "Primary Accent", "Negative Accent", "Surface Color", "Surface Elevated", "Text Primary", "Text Secondary", "Glow Radius", "Corner Radius"):
            self.assertIn(control, builder)

    def test_asr_is_fail_closed_and_final_xml_contains_no_png_graphic_clips(self) -> None:
        source = (ENGINE_DIR / "autocut.py").read_text(encoding="utf-8")
        self.assertNotIn("XML همچنان قابل ساخت است", source)
        self.assertIn("زیرنویس خالی است", source)
        self.assertIn("FCP XML cannot carry an editable After Effects MOGRT", source)
        self.assertNotIn("<stillframe>TRUE</stillframe>", source)
        self.assertNotIn("Hafez Graphic Motion", source)

    def test_semantic_director_requests_sparse_content_specific_beats(self) -> None:
        segments = [
            {"id": index, "start": index * 4.0, "end": index * 4.0 + 3.0, "text": f"نکته کامل شماره {index} برای تحلیل محتوا."}
            for index in range(30)
        ]
        tasks = subtitle_pipeline.build_review_tasks(segments, 120.0)
        visual_prompt = next(task["prompt"] for task in tasks if str(task["task_id"]).startswith("visual-"))
        director_prompt = next(task["prompt"] for task in tasks if task["task_id"] == "director-001")
        self.assertIn("Semantic Director", visual_prompt)
        self.assertIn("تا ۲ Marker", visual_prompt)
        self.assertIn("روش یا مراحل→FLOWCHART", visual_prompt)
        self.assertIn("تعداد حداقل اجباری وجود ندارد", director_prompt)
        self.assertIn("headline_fa", visual_prompt)
        self.assertIn("ترجمه، بازنویسی آزاد", visual_prompt)
        # The local default may reuse the fast model to avoid swapping several
        # GB of weights. Content constraints, not a different model tag, matter.
        compact = subtitle_pipeline._local_task_prompt(next(task for task in tasks if str(task["task_id"]).startswith("visual-")))
        self.assertIn("at most 3 important semantic events and 2 sparse graphics", compact)
        self.assertIn("exact contiguous COMPLETE clause", compact)
        self.assertIn(segments[0]["text"], compact)
        self.assertIn("hermes-glass", compact)

    def test_quality_gate_rejects_a_visually_empty_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            xml = root / "edit.xml"
            plan = root / "plan.json"
            srt = root / "edit.srt"
            youtube = root / "youtube.md"
            xml.write_text("<xmeml><sequence></sequence></xmeml>", encoding="utf-8")
            plan.write_text(json.dumps({"graphics": [], "punch_ins": [], "camera_schedule": []}), encoding="utf-8")
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nمتن\n", encoding="utf-8")
            youtube.write_text("# YouTube package\ncontent", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "timeline_duration": 120,
                        "mapped_words": [{"text": "متن"}],
                        "outputs": {
                            "xml": str(xml),
                            "professional_plan": str(plan),
                            "tight_srt": str(srt),
                            "youtube": str(youtube),
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "کنترل کیفیت خروجی رد شد"):
                studio_cli.validate_job_outputs(manifest)

    def test_cli_and_desktop_force_utf8_output(self) -> None:
        class ReconfigurableStream:
            def __init__(self) -> None:
                self.calls: list[dict[str, str]] = []

            def reconfigure(self, **kwargs: str) -> None:
                self.calls.append(kwargs)

        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()
        with patch.object(studio_cli.sys, "stdout", stdout), patch.object(studio_cli.sys, "stderr", stderr):
            studio_cli._configure_utf8_stdio()
        for stream in (stdout, stderr):
            self.assertEqual(stream.calls, [{"encoding": "utf-8", "errors": "backslashreplace"}])

        electron_main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(electron_main.count('PYTHONIOENCODING: "utf-8"'), 2)

    def test_motion_pack_contains_legacy_and_v2_templates(self) -> None:
        expected = {
            "Hafez Bilingual Hero Highlight.mogrt",
            "Hafez Neural Statement.mogrt",
            "Hafez Kinetic Keyword.mogrt",
            "Hafez HUD Metric.mogrt",
            "Hafez Flowchart 4 Step.mogrt",
            "Hafez Chapter Hero.mogrt",
            "Hafez Compare AB.mogrt",
            "Hafez Word Lift Statement.mogrt",
            "Hafez Face Safe Corner Note.mogrt",
            "Hafez Big Number Reveal.mogrt",
            "Hafez Compact Flowchart.mogrt",
            "Hafez Glass HUD Metric.mogrt",
            "Hafez Split Compare.mogrt",
            "Hafez Chapter Billboard.mogrt",
            "Hafez Decision Depth Typography.mogrt",
            "Hafez Subject Occlusion Keyword.mogrt",
        }
        actual = {path.name for path in (PRODUCT_ROOT / "motion-pack" / "dist").glob("*.mogrt")}
        self.assertTrue(expected.issubset(actual))
        builder = (PRODUCT_ROOT / "motion-pack" / "after-effects" / "build_hafez_motion_pack.jsx").read_text(encoding="utf-8")
        self.assertIn('addVariableFontAxis("wght")', builder)
        self.assertIn("2026 · Adaptive Tracking", builder)
        self.assertIn("Hafez · Word Lift Reveal", builder)
        self.assertIn("Hafez Bilingual Hero Highlight", builder)
        self.assertIn("EN Display Title", builder)
        self.assertIn("FA Semantic Subtitle", builder)
        self.assertIn("Arial-BoldMT", builder)
        self.assertIn("blocked-by-adobe-2026-font-crash", (PRODUCT_ROOT / "config" / "motion-style-contract.json").read_text(encoding="utf-8"))
        self.assertNotIn("addGrain", builder)
        self.assertNotIn("Grain Amount", builder)
        self.assertNotIn("Glass Grain", builder)
        studio_cli = (ENGINE_DIR / "studio_cli.py").read_text(encoding="utf-8")
        self.assertNotIn("HERMES_TEXTURE_INTENSITY", studio_cli)
        self.assertNotIn("--texture-intensity", studio_cli)

    def test_premiere_manifest_has_a_production_host_contract(self) -> None:
        manifest = json.loads((PRODUCT_ROOT / "premiere-plugin" / "manifest.json").read_text(encoding="utf-8"))
        finisher = (PRODUCT_ROOT / "premiere-plugin" / "main.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["id"], "ir.hafez.studio.premiere")
        self.assertIsInstance(manifest["host"], dict)
        self.assertEqual(manifest["host"]["app"], "premierepro")
        self.assertIn("getComponentCount", finisher)
        self.assertIn("getComponentAtIndex", finisher)
        self.assertIn("getParamCount", finisher)
        self.assertNotIn("getParamList", finisher)

    def test_audio_profile_targets_camera_one_external_microphone(self) -> None:
        report = {"noise_floor_dbfs": -52.0, "input_peak_dbfs": -2.0}
        chain = audio_master._base_filter(report)
        self.assertIn("deesser", chain)
        self.assertIn("acompressor", chain)
        self.assertEqual(report["source_role"], "camera1_external_microphone")
        self.assertEqual(
            Path(audio_master.find_ffmpeg()),
            PRODUCT_ROOT / "runtime" / "tools" / "ffmpeg.exe",
        )

    def test_runtime_paths_resolve_inside_portable_product(self) -> None:
        self.assertEqual(runtime_paths.studio_root(), PRODUCT_ROOT)
        self.assertTrue(runtime_paths.face_model_path().exists())

    def test_desktop_brand_themes_font_and_workspaces(self) -> None:
        package = json.loads((PRODUCT_ROOT / "package.json").read_text(encoding="utf-8"))
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        css = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        self.assertEqual(package["productName"], "Hafez Studio")
        self.assertEqual(package["build"]["appId"], "ir.hafez.studio")
        self.assertTrue((PRODUCT_ROOT / "build" / "icon.ico").exists())
        self.assertTrue((PRODUCT_ROOT / "app" / "assets" / "fonts" / "Estedad-VF.ttf").exists())
        for mode in ("youtube", "reels", "podcast"):
            self.assertIn(f'data-mode="{mode}"', html)
        for view in ("director", "motion", "audio", "integrations", "settings"):
            self.assertIn(f'data-youtube-view="{view}"', html)
        self.assertIn('data-theme="light"', css)
        self.assertIn("applyTheme", renderer)
        self.assertIn("selectView", renderer)
        self.assertIn("refreshIntegrations", renderer)

        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        preload = (PRODUCT_ROOT / "electron" / "preload.js").read_text(encoding="utf-8")
        self.assertIn('ipcMain.handle("resource:paths"', main)
        self.assertIn('ipcMain.handle("system:integrations"', main)
        self.assertIn("getResourcePaths", preload)
        self.assertIn("getIntegrations", preload)

    def test_preview_lab_and_font_picker_have_an_engine_contract(self) -> None:
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        preload = (PRODUCT_ROOT / "electron" / "preload.js").read_text(encoding="utf-8")
        for section in ("profiles", "motions", "rhythm", "typography"):
            self.assertIn(f'data-preview-section="{section}"', html)
        for motion in ("statement", "keyword", "metric", "flow", "chapter", "compare"):
            self.assertIn(f'data-motion="{motion}"', html)
        for field in ("titleFontPath", "titleFontWeight", "bodyFontPath", "bodyFontWeight"):
            self.assertIn(field, renderer)
            self.assertIn(field, main)
        self.assertIn('ipcMain.handle("file:font"', main)
        self.assertIn("selectFont", preload)
        parser = studio_cli.build_parser()
        args = parser.parse_args(["run", "--cam1", "one.mp4", "--cam2", "two.mp4", "--title-weight", "900", "--body-weight", "300"])
        self.assertEqual(args.title_weight, 900)
        self.assertEqual(args.body_weight, 300)

    def test_adaptive_slider_has_one_state_and_dynamic_track_progress(self) -> None:
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        css = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        self.assertIn('aria-label="Adaptive intensity"', html)
        self.assertIn("adaptiveValue: ADAPTIVE_DEFAULT", renderer)
        self.assertIn("function adaptiveProgress", renderer)
        self.assertIn('input.style.setProperty("--slider-progress"', renderer)
        self.assertIn("glowIntensity: state.adaptiveValue / 100", renderer)
        self.assertIn("adaptiveValue: 82", main)
        self.assertIn("safe.glowIntensity = safe.adaptiveValue / 100", main)
        self.assertIn("--slider-progress:82%", css)
        self.assertIn("var(--slider-progress)", css)
        self.assertNotIn("var(--director-green) 0 43%", css)

    def test_director_pipeline_has_real_stage_progress_and_separate_log_region(self) -> None:
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        css = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        preload = (PRODUCT_ROOT / "electron" / "preload.js").read_text(encoding="utf-8")
        for stage in ("analyze", "direct", "design", "finish"):
            self.assertIn(f'data-stage="{stage}"', html)
            self.assertIn(f'"{stage}"', renderer)
        self.assertIn('id="progressValue"', html)
        self.assertIn('id="currentStageLabel"', html)
        self.assertIn('class="console-wrap"', html)
        self.assertIn("function renderJobProgress", renderer)
        self.assertIn("onJobProgress", preload)
        self.assertIn('data-job-state="failed"', css)
        self.assertIn("position:static", css)

    def test_director_controls_are_functional_and_custom_styled(self) -> None:
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        css = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        self.assertIn('id="performanceProfile"', html)
        self.assertIn("پروفایل پردازش", html)
        self.assertIn("تراکم موشن", html)
        self.assertIn("زبان گفتار", html)
        self.assertIn("function setupCustomSelects", renderer)
        self.assertIn(".select-menu", css)
        self.assertIn("performanceEnvironment", main)
        parser = studio_cli.build_parser()
        args = parser.parse_args([
            "run", "--cam1", "one.mp4", "--cam2", "two.mp4",
            "--performance", "maximum", "--language", "auto",
        ])
        self.assertEqual(args.performance, "maximum")
        self.assertEqual(args.language, "auto")

    def test_maximum_profile_exposes_all_logical_cores_without_a_fixed_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(os.environ, {}, clear=False):
            studio_cli._configure_runtime(Path(temp_dir), performance="maximum")
            self.assertEqual(os.environ["HERMES_PERFORMANCE_PROFILE"], "maximum")
            self.assertEqual(int(os.environ["HERMES_CPU_THREADS"]), max(1, int(os.cpu_count() or 1)))
            self.assertEqual(os.environ["HERMES_FFMPEG_THREADS"], "0")
            self.assertEqual(os.environ["HERMES_CUDA_PREFERRED"], "1")

    def test_each_job_gets_a_unique_project_folder_contract(self) -> None:
        main = (PRODUCT_ROOT / "electron" / "main.js").read_text(encoding="utf-8")
        self.assertIn("function createProjectOutput", main)
        self.assertIn('path.join(outputDir, "project.json")', main)
        self.assertIn('"--output", outputDir', main)
        self.assertIn("return { pid: child.pid, jobId, outputDir }", main)

    def test_engine_emits_all_four_real_pipeline_stages(self) -> None:
        autocut_source = (ENGINE_DIR / "autocut.py").read_text(encoding="utf-8")
        cli_source = (ENGINE_DIR / "studio_cli.py").read_text(encoding="utf-8")
        combined = autocut_source + cli_source
        for stage in ("analyze", "direct", "design", "finish"):
            self.assertIn(f'report_stage("{stage}"', combined)
        for progress in (5, 28, 50, 62, 71, 81, 92, 98):
            self.assertIn(f", {progress},", combined)

    def test_light_theme_is_authored_for_director_and_toggle_is_not_language(self) -> None:
        html = (PRODUCT_ROOT / "app" / "index.html").read_text(encoding="utf-8")
        renderer = (PRODUCT_ROOT / "app" / "renderer.js").read_text(encoding="utf-8")
        css = (PRODUCT_ROOT / "app" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('<span class="theme-light">روشن</span>', html)
        self.assertNotIn('<span class="theme-light">فارسی</span>', html)
        self.assertIn('? "روشن" : "تیره"', renderer)
        self.assertIn(':root[data-theme="light"] body[data-view="director"] .director-group', css)
        self.assertIn(':root[data-theme="light"] body[data-view="director"] .select-menu', css)


class EditorialElementCatalogTests(unittest.TestCase):
    def test_catalog_contains_fourteen_grain_free_curated_elements(self) -> None:
        catalog = editorial_elements.load_editorial_catalog()
        self.assertEqual(catalog["id"], "hafez-hermes-elements-2026")
        self.assertEqual(len(catalog["elements"]), 14)
        self.assertFalse(catalog["rules"]["grainAllowed"])
        self.assertEqual(catalog["fontSystem"]["family"], "Abar High FaNum")
        self.assertTrue(all(not item["grainAllowed"] for item in catalog["elements"]))
        self.assertEqual(
            catalog["editableControlContract"]["nativePerText"],
            ["Source Text", "Font Family", "Font Style", "Font Size"],
        )
        self.assertEqual(
            catalog["editableControlContract"]["authoredPerText"],
            ["Text Color", "Line Spacing", "Tracking"],
        )

    def test_after_effects_curator_wires_real_text_and_layout_controls(self) -> None:
        source = (PRODUCT_ROOT / "motion-pack" / "after-effects" / "curate_hermes_elements.jsx").read_text(encoding="utf-8")
        for control in ("Text Color", "Line Spacing", "Tracking", "Background Color", "Layout Position", "Layout Scale"):
            self.assertIn(control, source)
        self.assertIn(".setLeading(", source)
        self.assertIn(".setTracking(", source)
        self.assertIn('layout.name = "HAFEZ · LAYOUT"', source)
        self.assertIn("child.parent = layout", source)
        self.assertIn("function isFullFrameSolid", source)
        self.assertNotIn("function isDarkSolid", source)
        self.assertIn("The authored optional plate below is the only full-frame background", source)

    def test_exact_subscribe_trigger_is_deterministic_and_not_fuzzy(self) -> None:
        segments = [
            {"id": 1, "start": 2.0, "end": 3.0, "text": "اگه دوست داشتی سابسکرایب کن تا ادامه بدیم"},
            {"id": 2, "start": 8.0, "end": 9.0, "text": "سابسکرایب یادت نره"},
        ]
        matches = editorial_elements.exact_subscribe_segments(segments)
        self.assertEqual([item["segment_id"] for item in matches], [1])
        self.assertEqual(matches[0]["matched_phrase"], "سابسکرایب کن")

    def test_metric_and_flowchart_selection_are_fact_gated(self) -> None:
        metric, metric_trace = editorial_elements.select_editorial_element(
            {"kind": "hud", "semantic_role": "percentage"},
            "عملکرد این بخش به هفتاد درصد می‌رسه.",
        )
        self.assertEqual(metric["id"], "hermes-user-growth")
        self.assertIn("percentage-fit", metric_trace["reasons"])
        flow, flow_trace = editorial_elements.select_editorial_element(
            {
                "kind": "flowchart",
                "semantic_role": "steps",
                "nodes": ["دریافت داده", "تحلیل", "ارسال نتیجه"],
            },
            "این فرایند داده را تحلیل می‌کند و نتیجه را می‌فرستد.",
        )
        self.assertEqual(flow["id"], "hermes-flowchart")
        self.assertIn("node-count-fit", flow_trace["reasons"])

    def test_invalid_model_hint_is_rejected_by_rules(self) -> None:
        selected, trace = editorial_elements.select_editorial_element(
            {"kind": "statement", "semantic_role": "claim", "element_id": "hermes-revenue-chart"},
            "این نتیجه مسیر اجرای سیستم را روشن می‌کند.",
        )
        self.assertNotEqual(selected["id"], "hermes-revenue-chart")
        revenue_rejection = next(item for item in trace["rejected"] if item["id"] == "hermes-revenue-chart")
        self.assertIn("requires-number", revenue_rejection["reasons"])

    def test_editor_prompts_receive_the_same_catalog_and_element_id_contract(self) -> None:
        segments = [{"id": 0, "start": 0.0, "end": 2.0, "text": "این نکته مهم درباره سیستم است."}]
        tasks = subtitle_pipeline.build_review_tasks(segments, 20.0)
        editor_prompts = [task["prompt"] for task in tasks if task["task_type"] == "editor"]
        self.assertTrue(editor_prompts)
        self.assertTrue(all("hafez-hermes-elements-2026" in prompt for prompt in editor_prompts))
        self.assertTrue(all("element_id" in prompt for prompt in editor_prompts))

    def test_graphic_planner_injects_one_subscribe_cue_and_selection_trace(self) -> None:
        segments = [
            {"id": 0, "start": 0.0, "end": 2.0, "text": "این نکته مهم درباره سیستم است."},
            {"id": 1, "start": 6.0, "end": 8.0, "text": "اگر مفید بود سابسکرایب کن تا ادامه بدیم."},
            {"id": 2, "start": 12.0, "end": 14.0, "text": "این نتیجه مهم درباره عملکرد سیستم است."},
        ]
        cues = professional_edit.build_graphic_cues(segments, 18.0)
        subscribe = [cue for cue in cues if cue.get("element_id") == "hermes-subscribe"]
        self.assertEqual(len(subscribe), 1)
        self.assertTrue(subscribe[0]["required_by_trigger"])
        self.assertEqual(subscribe[0]["controls"]["CTA Text"], "سابسکرایب کن")
        self.assertEqual(subscribe[0]["selection_trace"]["selected_id"], "hermes-subscribe")


class CameraContractTests(unittest.TestCase):
    def test_camera_enablement_is_mutually_exclusive(self) -> None:
        segments = [
            {"id": i, "start": i * 6.0, "end": i * 6.0 + 3.5, "text": f"نکته مهم شماره {i}"}
            for i in range(30)
        ]
        schedule = professional_edit.build_camera_schedule(segments, 180.0)
        cam1 = professional_edit.split_track_for_camera([[0, 5400, 0, 5400]], schedule, 30.0, "cam1")
        cam2 = professional_edit.split_track_for_camera([[0, 5400, 30, 5430]], schedule, 30.0, "cam2")
        self.assertEqual(len(cam1), len(cam2))
        self.assertTrue(all(bool(first[4]) != bool(second[4]) for first, second in zip(cam1, cam2)))


if __name__ == "__main__":
    unittest.main()
