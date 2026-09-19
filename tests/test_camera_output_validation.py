"""Final XML camera coverage, independent of original media duration."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import professional_edit
import studio_cli


def xml_for(frames, timebase=30, ntsc="FALSE", name="03 - Hafez Director Cut"):
    return (f"<xmeml><sequence><name>{name}</name><duration>{frames}</duration>"
            f"<rate><timebase>{timebase}</timebase><ntsc>{ntsc}</ntsc></rate>"
            "</sequence></xmeml>")


def plan_for(end, start=0.0):
    return {"sequence": "03 - Hafez Director Cut", "camera_schedule": [
        {"start": start, "end": end, "camera": "cam1"}]}


class CameraOutputValidationTests(unittest.TestCase):
    def test_actual_fresh_clock_accepts_complete_short_hero(self):
        self.assertEqual([], studio_cli._camera_schedule_failures(plan_for(11.712), xml_for(351, ntsc="TRUE")))

    def test_single_shot_threshold_is_derived_from_shared_existing_policy(self):
        limit = sum((professional_edit.CAMERA_INITIAL_HOLD_SECONDS,
                     professional_edit.CAMERA_BOUNDARY_WINDOW_SECONDS,
                     professional_edit.CAMERA_SCHEDULE_TAIL_SECONDS))
        self.assertEqual(31.05, limit)
        for seconds in (12, 26, 29, 31.05):
            with self.subTest(seconds=seconds):
                self.assertEqual([], studio_cli._camera_schedule_failures(plan_for(seconds), xml_for(round(seconds * 100), 100)))
        for seconds in (31.06, 32, 180):
            with self.subTest(seconds=seconds):
                self.assertEqual(["کات دوربین هوشمند کافی نیست"], studio_cli._camera_schedule_failures(plan_for(seconds), xml_for(round(seconds * 100), 100)))

    def test_scheduler_single_shots_up_to_late_boundary_remain_unchanged(self):
        for duration, segments in ((12, []), (26, []), (29, [{"start": 29, "text": "boundary"}])):
            schedule = professional_edit.build_camera_schedule(segments, duration)
            self.assertEqual(1, len(schedule))
            plan = plan_for(duration)
            plan["camera_schedule"] = schedule
            self.assertEqual([], studio_cli._camera_schedule_failures(plan, xml_for(duration * 30)))

    def test_actual_scheduler_long_sequences_cover_ntsc_final_grid(self):
        rate = Fraction(30000, 1001)
        for frames in (1800, 15260, 17952):
            duration = float(Fraction(frames, 1) / rate)
            plan = plan_for(duration)
            plan["camera_schedule"] = professional_edit.build_camera_schedule([], duration)
            self.assertGreaterEqual(len(plan["camera_schedule"]), 2)
            self.assertEqual([], studio_cli._camera_schedule_failures(plan, xml_for(frames, ntsc="TRUE")))

    def test_empty_invalid_names_and_nonfinite_or_nonpositive_times_rejected(self):
        baseline = plan_for(12)
        for value in ([], None, {}, [{"start": 0, "end": 12, "camera": "cam3"}],
                      [{"start": 0, "end": 0, "camera": "cam1"}],
                      [{"start": 0, "end": float("nan"), "camera": "cam1"}],
                      [{"start": 0, "end": float("inf"), "camera": "cam1"}],
                      [{"start": True, "end": 12, "camera": "cam1"}],
                      [{"start": -1, "end": 12, "camera": "cam1"}]):
            plan = dict(baseline, camera_schedule=value)
            with self.subTest(value=value):
                self.assertTrue(studio_cli._camera_schedule_failures(plan, xml_for(360)))

    def test_internal_gap_overlap_and_one_frame_holes_fail(self):
        for start in (5.0, 5.967, 6.002, 6.033, 7.0):
            plan = plan_for(12)
            plan["camera_schedule"] = [
                {"start": 0, "end": 6, "camera": "cam1"},
                {"start": start, "end": 12, "camera": "cam2"}]
            with self.subTest(start=start):
                self.assertTrue(studio_cli._camera_schedule_failures(plan, xml_for(360)))

    def test_valid_join_rounding_not_a_frame_gap(self):
        plan = plan_for(12)
        plan["camera_schedule"] = [
            {"start": 0, "end": 6, "camera": "cam1"},
            {"start": 6.001, "end": 12, "camera": "cam2"}]
        self.assertEqual([], studio_cli._camera_schedule_failures(plan, xml_for(360)))

    def test_outer_edges_and_missing_final_frame_rejected(self):
        for start, end in ((0.001, 12), (0.034, 12), (0, 11.966), (0, 12.034), (0, 10)):
            with self.subTest(start=start, end=end):
                self.assertTrue(studio_cli._camera_schedule_failures(plan_for(end, start), xml_for(360)))

    def test_missing_ambiguous_malformed_xml_or_clock_rejected(self):
        base = xml_for(360)
        examples = ("<broken", base.replace("360", "0"), base.replace("360", "360.0"),
                    base.replace("FALSE", "unknown"), base.replace("<timebase>30", "<timebase>0"),
                    base.replace("03 - Hafez Director Cut", "other"),
                    base.replace("</xmeml>", base[7:]), "<xmeml/>")
        for xml in examples:
            with self.subTest(xml=xml):
                self.assertTrue(studio_cli._camera_schedule_failures(plan_for(12), xml))

    def test_zero_name_never_falls_back_to_first_sequence(self):
        plan = plan_for(12)
        plan.pop("sequence")
        self.assertTrue(studio_cli._camera_schedule_failures(plan, xml_for(360)))

    def test_single_final_short_passes_even_with_long_original_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {key: root / name for key, name in {
                "professional_plan": "plan.json", "xml": "cut.xml", "tight_srt": "cut.srt",
                "youtube": "youtube.md"}.items()}
            template = root / "fixture.mogrt"
            template.write_bytes(b"fixture exists only; no native MOGRT QA claimed")
            plan = plan_for(12)
            plan.update(graphics=[{"kind": "hook", "template_path": str(template)}], punch_ins=[{"start": 1}])
            files["professional_plan"].write_text(json.dumps(plan), encoding="utf-8")
            files["xml"].write_text(xml_for(360), encoding="utf-8")
            files["tight_srt"].write_text("1\n00:00:00,000 --> 00:00:01,000\nLiteral source\n", encoding="utf-8")
            files["youtube"].write_text("# Fixture description only\n", encoding="utf-8")
            manifest = root / "edit.json"
            manifest.write_text(json.dumps({"timeline_duration": 180, "mapped_words": [{"text": "word"}],
                                            "outputs": {k: str(v) for k, v in files.items()}}), encoding="utf-8")
            result = studio_cli.validate_job_outputs(manifest)
            self.assertEqual(1, result["cameraShots"])
            self.assertEqual(0, result["cameraSwitches"])
            self.assertFalse(result["publicationReady"])

    def test_inputs_are_never_changed(self):
        plan = plan_for(12)
        before = copy.deepcopy(plan)
        xml = xml_for(360)
        studio_cli._camera_schedule_failures(plan, xml)
        self.assertEqual(before, plan)


if __name__ == "__main__":
    unittest.main()
