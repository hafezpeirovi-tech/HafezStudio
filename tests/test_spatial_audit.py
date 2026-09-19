import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
import spatial_audit as spatial


def transform():
    return {"kind": "normalized-scale-center-v1", "coordinate_space": "sequence-normalized",
            "verified": True, "evidence_id": "fixture-native-calibration", "mode": "curves", "scale": {"interpolation": "constant", "value": 1},
            "center": {"interpolation": "constant", "value": [0, 0]}}


class SpatialAuditTests(unittest.TestCase):
    def setUp(self):
        self.cue = {"id": "example", "start_frame": 10, "end_frame": 13,
                    "template_sha256": "a" * 64, "text_style_sha256": "b" * 64}
        self.clips = [{"id": "clip1", "camera_id": "cam1", "media_id": "media1", "start_frame": 0,
                       "end_frame": 20, "source_in": 100, "source_out": 120, "visible": True,
                       "transform": transform()}]
        self.observations = {"media1": {frame: {"decoded": True, "face_verified": True,
            "face_box": [0.42, 0.15, 0.15, 0.2], "body_verified": True,
            "body_box": [0.35, 0.10, 0.4, 0.85], "body_method": "human-segmentation",
            "body_evidence_id": "fixture-model-and-mask-sha"} for frame in (110, 111, 112)}}
        self.footprint = {"verified": True, "coordinate_space": "sequence-normalized",
                          "placement_transform_verified": True, "includes_glow_and_motion": True,
                          "start_frame": 10, "end_frame": 13, "observed_frame_count": 3,
                          "frame_ids": [10, 11, 12],
                          "authored_size": [3840, 2160], "bounds_union": [0.06, 0.4, 0.20, 0.15],
                          "template_sha256": "a" * 64, "text_style_sha256": "b" * 64}
        self.refresh_footprint_context()

    def refresh_footprint_context(self):
        self.footprint["render_context_sha256"] = spatial.render_context_sha256(self.cue, self.clips)

    def audit(self):
        before = copy.deepcopy((self.cue, self.clips, self.observations, self.footprint))
        report = spatial.audit_spatial_cue(self.cue, self.clips, self.observations, self.footprint, profile=spatial.PROFILE)
        self.assertEqual((self.cue, self.clips, self.observations, self.footprint), before)
        self.assertFalse(report["timeline_mutated"])
        return report

    def assertBlocked(self):
        report = self.audit()
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["strict_spatial_verified"])
        self.assertFalse(report["allow_sfx"])
        self.assertTrue(report["issues"])
        return report

    def test_explicit_opt_in_only(self):
        report = spatial.audit_spatial_cue(self.cue, self.clips, {}, None)
        self.assertEqual(report["status"], "not-requested")

    def test_exact_half_open_frames_and_complete_independent_evidence_pass(self):
        report = self.audit()
        self.assertEqual(report["status"], "verified", report["issues"])
        self.assertEqual([row["source_frame"] for row in report["frame_mappings"]], [110, 111, 112])
        self.assertEqual(report["per_camera_coverage"]["cam1"],
                         {"expected": 3, "decoded": 3, "face_observed": 3, "body_observed": 3, "transformed": 3})

    def test_missing_one_decoded_frame_blocks_without_interpolation(self):
        del self.observations["media1"][111]
        report = self.assertBlocked()
        self.assertEqual(report["per_camera_coverage"]["cam1"]["decoded"], 2)

    def test_face_envelope_or_optical_flow_is_not_independent_body_evidence(self):
        for method in ("conservative-face-derived-envelope", "optical-flow", "", "background-subtraction"):
            self.observations["media1"][111]["body_method"] = method
            self.assertBlocked()

    def test_missing_body_model_remains_blocked_with_perfect_face_coverage(self):
        for observation in self.observations["media1"].values():
            observation["body_verified"] = False
        report = self.assertBlocked()
        self.assertEqual(report["per_camera_coverage"]["cam1"]["face_observed"], 3)
        self.assertEqual(report["per_camera_coverage"]["cam1"]["body_observed"], 0)

    def test_missing_face_or_invalid_body_mask_blocks(self):
        self.observations["media1"][111]["face_verified"] = False
        self.assertBlocked()
        self.observations["media1"][111]["face_verified"] = True
        for box in ([0, 0, 0, 0], [0, 0, float("nan"), 1], [0.9, 0.1, 0.5, 0.4]):
            self.observations["media1"][111]["body_box"] = box
            # NaN equality is not suitable for the no-mutation tuple assertion.
            if any(isinstance(value, float) and value != value for value in box):
                report = spatial.audit_spatial_cue(self.cue, self.clips, self.observations, self.footprint, profile=spatial.PROFILE)
                self.assertFalse(report["strict_spatial_verified"])
            else:
                self.assertBlocked()

    def test_arm_between_former_sparse_samples_is_in_full_union(self):
        self.observations["media1"][111]["body_box"] = [0.1, 0.1, 0.65, 0.85]
        report = self.assertBlocked()
        self.assertAlmostEqual(report["independent_body_union"][0], 0.1)

    def test_zoom_and_center_are_applied_before_union(self):
        self.clips[0]["transform"]["scale"]["value"] = 1.16
        self.clips[0]["transform"]["center"]["value"] = [-0.09, 0]
        self.refresh_footprint_context()
        report = self.assertBlocked()
        self.assertAlmostEqual(report["independent_body_union"][0], 0.236)

    def test_unknown_easing_crop_rotation_or_unverified_transform_is_blocked(self):
        changes = [{"verified": False}, {"rotation": 3}, {"crop": [0, 0, 1, 1]},
                   {"anchor": [0, 0]}, {"mode": "unknown"}]
        for change in changes:
            self.clips[0]["transform"] = {**transform(), **change}
            self.assertBlocked()
        self.clips[0]["transform"] = transform()
        self.clips[0]["transform"]["scale"] = {"interpolation": "FCPCurve", "value": 1.16}
        self.assertBlocked()

    def test_verified_linear_transform_and_exact_key_edges(self):
        self.clips[0]["transform"]["scale"] = {"interpolation": "linear", "keyframes": [
            {"frame": 10, "value": 1}, {"frame": 12, "value": 1.10}]}
        self.refresh_footprint_context()
        report = self.audit()
        self.assertTrue(report["strict_spatial_verified"], report["issues"])
        self.assertAlmostEqual(report["independent_body_union"][0], 0.335)

    def test_linear_easing_tangents_and_unbracketed_keys_not_approximated(self):
        self.clips[0]["transform"]["scale"] = {"interpolation": "linear", "keyframes": [
            {"frame": 11, "value": 1}, {"frame": 12, "value": 1.1}]}
        self.assertBlocked()
        self.clips[0]["transform"]["scale"]["keyframes"][0].update(frame=10, tangent=0.5)
        self.assertBlocked()

    def test_verified_per_frame_transform_requires_every_sample(self):
        self.clips[0]["transform"] = {"kind": "normalized-scale-center-v1", "coordinate_space": "sequence-normalized",
            "verified": True, "evidence_id": "fixture-native-calibration", "mode": "per-frame", "frames": {frame: {"scale": 1, "center": [0, 0]} for frame in (10, 11, 12)}}
        self.refresh_footprint_context()
        self.assertTrue(self.audit()["strict_spatial_verified"])
        del self.clips[0]["transform"]["frames"][11]
        self.assertBlocked()

    def test_footprint_missing_or_partial_or_changed_asset_style_never_passes(self):
        original = copy.deepcopy(self.footprint)
        for changes in ({"verified": False}, {"observed_frame_count": 2}, {"end_frame": 14},
                        {"template_sha256": "c" * 64}, {"text_style_sha256": "c" * 64},
                        {"includes_glow_and_motion": False}, {"coordinate_space": "3840-native"},
                        {"placement_transform_verified": False}, {"authored_size": []}):
            self.footprint = {**original, **changes}
            self.assertBlocked()
        self.footprint = None
        self.assertBlocked()

    def test_footprint_safe_area_and_entry_glow_extent_are_checked(self):
        self.footprint["bounds_union"] = [0.02, 0.3, 0.2, 0.2]
        self.assertBlocked()
        self.footprint["bounds_union"] = [0.06, 0.3, 0.29, 0.2]
        self.assertBlocked()

    def test_camera_cut_maps_both_edges_and_single_visible_frame(self):
        first = {**self.clips[0], "end_frame": 11, "source_out": 111}
        second = {**self.clips[0], "id": "clip2", "camera_id": "cam2", "media_id": "media2",
                  "start_frame": 11, "end_frame": 13, "source_in": 30, "source_out": 32}
        self.clips = [first, second]
        observation = self.observations["media1"][110]
        self.observations["media2"] = {30: copy.deepcopy(observation), 31: copy.deepcopy(observation)}
        self.refresh_footprint_context()
        report = self.audit()
        self.assertTrue(report["strict_spatial_verified"], report["issues"])
        self.assertEqual([(row["camera_id"], row["source_frame"]) for row in report["frame_mappings"]],
                         [("cam1", 110), ("cam2", 30), ("cam2", 31)])

    def test_disabled_camera_does_not_demand_evidence_but_unknown_visibility_blocks(self):
        self.clips.append({**self.clips[0], "id": "hidden", "media_id": "absent", "visible": False})
        self.refresh_footprint_context()
        self.assertTrue(self.audit()["strict_spatial_verified"])
        self.clips[1]["visible"] = None
        self.assertBlocked()

    def test_declared_simultaneously_visible_camera_also_needs_every_frame(self):
        self.clips.append({**self.clips[0], "id": "clip2", "camera_id": "cam2", "media_id": "media2"})
        report = self.assertBlocked()
        self.assertEqual(report["per_camera_coverage"]["cam2"]["expected"], 3)

    def test_gap_duplicate_identity_and_retimed_clip_block(self):
        original = copy.deepcopy(self.clips)
        for changes in ({"start_frame": 11, "source_in": 111}, {"source_out": 121},
                        {"speed": 2}, {"reverse": True}, {"time_remap": True}):
            self.clips = [{**original[0], **changes}]
            self.assertBlocked()
        self.clips = original + copy.deepcopy(original)
        self.assertBlocked()

    def test_integer_2997fps_mapping_has_no_rounding_or_outside_frame(self):
        rows, issues = spatial.exact_frame_map(525, 620, [{"id": "native", "camera_id": "cam1", "media_id": "media",
            "start_frame": 520, "end_frame": 630, "source_in": 2940, "source_out": 3050, "visible": True}])
        self.assertEqual(issues, [])
        self.assertEqual(len(rows), 95)
        self.assertEqual((rows[0]["source_frame"], rows[-1]["source_frame"]), (2945, 3039))
        self.assertEqual(rows[-1]["timeline_frame"], 619)

    def test_empty_fractional_or_negative_cue_interval_is_blocked(self):
        for start, end in ((10, 10), (10.5, 13), (-1, 13), (True, 13)):
            self.cue.update(start_frame=start, end_frame=end)
            self.assertBlocked()

    def test_hidden_or_out_of_range_duplicate_cannot_shadow_visible_zoom(self):
        self.clips[0]["transform"]["scale"]["value"] = 1.16
        self.clips[0]["transform"]["center"]["value"] = [-0.09, 0]
        original = copy.deepcopy(self.clips)
        self.assertBlocked()
        for hidden in ({"visible": False}, {"start_frame": 30, "end_frame": 40, "source_in": 0, "source_out": 10}):
            self.clips = original + [{**copy.deepcopy(original[0]), **hidden, "transform": transform()}]
            self.refresh_footprint_context()
            report = self.assertBlocked()
            self.assertTrue(any("INVALID_CLIP_IDENTITY" in issue for issue in report["issues"]))
            self.assertEqual(report["frame_mappings"], [])

    def test_malformed_hidden_global_ids_block_without_unhashable_exception(self):
        original = copy.deepcopy(self.clips)
        for identifier in ([], {}, 7, None, ""):
            self.clips = original + [{**original[0], "id": identifier, "visible": False}]
            report = self.assertBlocked()
            self.assertTrue(any("INVALID_CLIP_IDENTITY" in issue for issue in report["issues"]))

    def test_per_frame_sample_rejects_rotation_crop_warp_and_conflicting_modes(self):
        calibrated = {"kind": "normalized-scale-center-v1", "coordinate_space": "sequence-normalized",
                      "verified": True, "evidence_id": "fixture-native-calibration", "mode": "per-frame",
                      "frames": {frame: {"scale": 1, "center": [0, 0]} for frame in (10, 11, 12)}}
        self.clips[0]["transform"] = copy.deepcopy(calibrated)
        self.refresh_footprint_context()
        self.assertTrue(self.audit()["strict_spatial_verified"])
        for unknown in ({"rotation": 45}, {"crop": [0, 0, .5, 1]}, {"unqualified_warp": True}):
            self.clips[0]["transform"] = copy.deepcopy(calibrated)
            self.clips[0]["transform"]["frames"][11].update(unknown)
            self.refresh_footprint_context()
            report = self.assertBlocked()
            self.assertTrue(any("Per-frame sample must contain exactly" in issue for issue in report["issues"]))
        self.clips[0]["transform"] = {**calibrated, "scale": {"interpolation": "constant", "value": 1}}
        self.assertBlocked()
        self.clips[0]["transform"] = {**transform(), "frames": calibrated["frames"]}
        self.assertBlocked()

    def test_per_frame_integer_and_string_alias_cannot_hide_conflicting_sample(self):
        self.clips[0]["transform"] = {"kind": "normalized-scale-center-v1", "coordinate_space": "sequence-normalized",
            "verified": True, "evidence_id": "fixture-native-calibration", "mode": "per-frame",
            "frames": {frame: {"scale": 1, "center": [0, 0]} for frame in (10, 11, 12)}}
        self.clips[0]["transform"]["frames"]["11"] = {"scale": 1.16, "center": [-0.09, 0]}
        self.assertBlocked()

    def test_asset_style_or_transform_evidence_missing_is_not_self_verified(self):
        original_cue, original_footprint = copy.deepcopy(self.cue), copy.deepcopy(self.footprint)
        for key in ("template_sha256", "text_style_sha256"):
            for target in ("cue", "footprint"):
                self.cue, self.footprint = copy.deepcopy(original_cue), copy.deepcopy(original_footprint)
                (self.cue if target == "cue" else self.footprint).pop(key)
                self.assertBlocked()
        self.cue, self.footprint = original_cue, original_footprint
        for evidence in (None, "", " ", True):
            self.clips[0]["transform"] = {**transform(), "evidence_id": evidence}
            self.assertBlocked()

    def test_stale_footprint_context_rejects_placement_scale_effects_or_camera_schedule(self):
        original = copy.deepcopy((self.cue, self.clips))
        for change in ({"layout_position": [0.5, 0.5]}, {"layout_scale": 170},
                       {"controls": {"Glow Radius": 1000}}, {"duration": 7}):
            self.cue, self.clips = copy.deepcopy(original)
            self.cue.update(change)
            report = self.assertBlocked()
            self.assertTrue(any("render context is missing or stale" in issue for issue in report["issues"]))
        self.cue, self.clips = copy.deepcopy(original)
        self.clips[0]["camera_id"] = "changed-visible-camera"
        report = self.assertBlocked()
        self.assertTrue(any("render context is missing or stale" in issue for issue in report["issues"]))

    def test_footprint_count_cannot_replace_exact_unique_frame_evidence(self):
        for frames in ([10, 10, 10], [10, 11], [10, 11, 13], [True, 11, 12], None):
            self.footprint["frame_ids"] = frames
            self.assertBlocked()
        self.footprint["frame_ids"] = [12, 10, 11]
        self.assertTrue(self.audit()["strict_spatial_verified"])
        self.footprint.pop("render_context_sha256")
        self.assertBlocked()


if __name__ == "__main__":
    unittest.main()
