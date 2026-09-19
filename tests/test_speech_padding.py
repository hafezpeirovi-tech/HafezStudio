import copy
import math
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from speech_padding import build_padded_timeline


class SpeechPaddingTests(unittest.TestCase):
    def test_outward_handles_and_exact_frame_mapping(self):
        clips, mapping, length = build_padded_timeline([[2000, 3000]], 100, 30, 5000)
        self.assertEqual(clips['cam1'], [(0, 59, 42, 101)])
        self.assertEqual(clips['cam2'], [(0, 59, 39, 98)])
        self.assertEqual(length, 59)
        self.assertEqual(mapping[0]['orig_end_ms'], 101/30*1000)
        self.assertAlmostEqual(mapping[0]['orig_end_ms']-mapping[0]['orig_start_ms'], mapping[0]['tl_end_ms'])

    def test_overlapping_handles_are_not_replayed(self):
        clips, _, length = build_padded_timeline([[2000, 3000], [3500, 4000]], 0, 30, 5000)
        self.assertEqual(clips['cam1'], [(0, 89, 42, 131)])
        self.assertEqual(length, 89)

    def test_long_silence_is_still_removed(self):
        clips, _, length = build_padded_timeline([[2000, 3000], [6000, 7000]], 0, 30, 9000)
        self.assertEqual(len(clips['cam1']), 2)
        self.assertLess(length, 7*30)
        self.assertEqual(clips['cam1'][0][1], clips['cam1'][1][0])

    def test_media_edges_and_zero_camera_clamp(self):
        clips, _, length = build_padded_timeline([[0, 100], [700, 999]], 7675.94, 30000/1001, 999)
        self.assertEqual(clips['cam1'], [(0, 29, 0, 29)])
        self.assertEqual(clips['cam2'], [(0, 29, 0, 29)])

    def test_ntsc_fixed_offset_and_no_duplicate_source_frames(self):
        rate = 30000/1001
        clips, mapping, _ = build_padded_timeline([[9500, 10700], [15000, 16000]], 7675.94, rate, 20000)
        for a, b, mapped in zip(clips['cam1'], clips['cam2'], mapping):
            self.assertEqual(a[2]-b[2], round(7.67594*rate))
            self.assertEqual(a[1]-a[0], b[3]-b[2])
            self.assertAlmostEqual(mapped['orig_start_ms']/1000*rate, a[2])
        self.assertLess(clips['cam1'][0][3], clips['cam1'][1][2])

    def test_inputs_are_immutable(self):
        ranges = [[1000, 2000], [2500, 3000]]
        before = copy.deepcopy(ranges)
        build_padded_timeline(ranges, 0, 30, 4000)
        self.assertEqual(ranges, before)

    def test_invalid_input_fails_closed(self):
        for ranges in ([[100, 100]], [[-1, 400]], [[0, 1001]], [[200, 500], [100, 200]], [[0, math.inf]]):
            with self.assertRaises(ValueError):
                build_padded_timeline(ranges, 0, 30, 1000)
        for rate in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                build_padded_timeline([], 0, rate, 1000)
        with self.assertRaises(ValueError):
            build_padded_timeline([], 0, 30, 1000, head_ms=-1)

    def test_empty_detector_does_not_fabricate_speech(self):
        self.assertEqual(build_padded_timeline([], 0, 30, 1000), ({'cam1': [], 'cam2': []}, [], 0))

    def test_glass_keeps_approved_pacing_not_experimental_handles(self):
        import autocut
        ranges = [[2000, 3000], [3600, 4200]]
        with patch.dict(os.environ, {'HERMES_STYLE_PACK': 'glass'}), patch(
                'speech_padding.build_padded_timeline', side_effect=AssertionError('Retired experiment')) as retired:
            result = autocut.build_initial_timeline(ranges, 0, 30, 5000)
        retired.assert_not_called()
        self.assertEqual(result[:3], autocut.build_timeline(ranges, 0, 30, 5000))
        self.assertEqual(result[3], dict(id='legacy-silence-v1', head_ms=200, tail_ms=200))

    def test_glass_review_environment_does_not_enable_extra_silence(self):
        import autocut
        ranges = [[2000, 3000], [3500, 4000]]
        expected = autocut.build_timeline(ranges, 7675.94, 30000/1001, 5000)
        with patch.dict(os.environ, {'HERMES_STYLE_PACK': ' GLASS ', 'HERMES_GLASS_REVIEW_MODE': '1'}):
            result = autocut.build_initial_timeline(ranges, 7675.94, 30000/1001, 5000)
        self.assertEqual(result[:3], expected)
        self.assertEqual(result[3]['head_ms'], 200)

    def test_other_styles_keep_previous_cut_and_sync_exactly(self):
        import autocut
        ranges = [[2000, 3000], [3600, 4200]]
        expected = autocut.build_timeline(ranges, 567.8, 30000/1001, 5000)
        for style in ('signal-os', 'grunge', ''):
            with patch.dict(os.environ, {'HERMES_STYLE_PACK': style}):
                result = autocut.build_initial_timeline(ranges, 567.8, 30000/1001, 5000)
            self.assertEqual(result[:3], expected)
            self.assertEqual(result[3]['id'], 'legacy-silence-v1')

    def test_previous_fully_retained_word_does_not_become_partial(self):
        from word_boundary_guard import map_source_words
        from autocut import build_timeline
        ranges = [[2000, 3000], [3600, 4200]]
        raw = [dict(word_id='test:0', evidence_id='test', text='واژه',
                    acoustic_start=2.1, acoustic_end=2.8, confidence=.99)]
        _, old, _ = build_timeline(ranges, 0, 30, 5000)
        _, new, _ = build_padded_timeline(ranges, 0, 30, 5000)
        for mapping in (old, new):
            self.assertFalse(map_source_words(raw, mapping)[0]['word_boundary_review_required'])


if __name__ == '__main__':
    unittest.main()
