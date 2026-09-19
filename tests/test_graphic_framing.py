import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine/src/hermes_video'))
import professional_edit as edit
from graphic_framing import override_camera_interval, coordinate_graphic_framing


class GraphicFramingTests(unittest.TestCase):
    def setUp(self):
        self.schedule = [{'start': 0, 'end': 24, 'camera': 'cam1'},
                         {'start': 24, 'end': 32, 'camera': 'cam2'},
                         {'start': 32, 'end': 60, 'camera': 'cam1'}]

    def test_frame_exact_override_has_no_gap_overlap_or_duration_change(self):
        for fps in (25, 30, 30000/1001):
            for start, end in ((2, 6), (23, 27), (30, 35), (54, 58), (0, 5), (56, 60)):
                with self.subTest(fps=fps, start=start):
                    frozen = copy.deepcopy(self.schedule)
                    got = override_camera_interval(self.schedule, start=start, end=end, camera='cam2', fps=fps, cue_id='x')
                    self.assertEqual(self.schedule, frozen)
                    for tick in range(round(60*fps)):
                        selected = [s for s in got if round(s['start']*fps) <= tick < round(s['end']*fps)]
                        self.assertEqual(len(selected), 1)
                        if round(start*fps) <= tick < round(end*fps):
                            self.assertEqual(selected[0]['camera'], 'cam2')

    def test_invalid_schedule_or_outside_cue_is_rejected(self):
        for schedule, start, end in (([], 1, 3), (self.schedule, -1, 3), (self.schedule, 1, 61),
                                    ([{'start': 0, 'end': 2, 'camera': 'cam1'}, {'start': 3, 'end': 6, 'camera': 'cam2'}], 1, 4)):
            with self.assertRaises(ValueError):
                override_camera_interval(schedule, start=start, end=end, camera='cam2', fps=30, cue_id='x')

    def test_topic_label_requires_explicit_policy_and_exact_complete_source(self):
        body = 'تریدر باهوش یه دسیار داره که براش این کارو می‌کنه.'
        cue = {'headline_fa': body, 'copy_segment_ids': [5], 'copy_provenance': {'source_text': body},
               'native_runtime_contract': {'allowExactTopicLabels': True},
               'controls': {'Title': 'BAD MODEL ENGLISH', 'Body': body}}
        controls, evidence = edit._native_glass_editorial_copy(cue, cue['controls'])
        self.assertEqual(controls, {'Title': 'SMART TRADER', 'Body': 'تریدر باهوش'})
        self.assertEqual(evidence['display_kind'], 'topic-label')
        self.assertEqual(evidence['original_controls']['Body'], body)
        self.assertFalse(evidence['assertion_displayed'])
        cue.update(controls=controls, native_copy_selection={**evidence, 'applied': True}, template_layers=[{'controls': dict(controls)}])
        self.assertFalse(edit.guard_automatic_graphic_copy([cue])[0].get('review_blocked', False))
        cue['controls']['Body'] = 'حافظ استراتژی مخصوص دارد'
        self.assertTrue(edit.guard_automatic_graphic_copy([cue])[0]['review_blocked'])

    def test_topic_policy_never_rescues_uncertain_negative_incomplete_or_ambiguous_copy(self):
        for body in ('شاید این بخش کامیونیتی داره.', 'این بخش کامیونیتی نداره.',
                     'این بخش کامیونیتی داره که', 'این کامیونیتی اسکرینر دارد.'):
            cue = {'headline_fa': body, 'copy_provenance': {'source_text': body},
                   'native_runtime_contract': {'allowExactTopicLabels': True}}
            result, evidence = edit._native_glass_editorial_copy(cue, {'Title': 'untouched', 'Body': body})
            self.assertIsNone(evidence)
            self.assertEqual(result['Body'], body)

    def test_unverified_copy_never_changes_cameras_or_punches(self):
        raw = {'id': 'bad', 'start': 10, 'end': 14, 'controls': {'Body': 'نامفهوم'},
               'element_id': 'hermes-glass-insight', 'native_runtime_contract': {'typography': {'profile': edit.NATIVE_GLASS_PROFILE}}}
        events = [{'start': 10, 'end': 14, 'scale': 115}]
        with patch.object(edit, 'apply_face_safe_layout') as track:
            result, kept, audit = coordinate_graphic_framing([raw], [{**raw, 'review_blocked': True}], self.schedule, events,
                paths={'cam1': '1.mp4', 'cam2': '2.mp4'}, clips={'cam1': [], 'cam2': []}, fps=30, width=1920, height=1080)
        self.assertEqual(result, self.schedule)
        self.assertEqual(kept, events)
        self.assertEqual(audit['changes'], [])
        track.assert_not_called()

    def test_qualified_label_selects_body_safe_angle_and_drops_only_competing_punch(self):
        body = 'به این وضعیت می‌گن فلج تحلیلی.'
        raw = {'id': 'good', 'start': 40, 'end': 44, 'headline_fa': body, 'copy_provenance': {'source_text': body},
               'controls': {'Title': 'ANALYSIS PARALYSIS', 'Body': body}, 'element_id': 'hermes-glass-insight',
               'native_runtime_contract': {'typography': {'profile': edit.NATIVE_GLASS_PROFILE}}}
        events = [{'start': 42, 'end': 43}, {'start': 50, 'end': 53}]
        def candidate(cues, **kwargs):
            return ([{**cues[0], 'review_blocked': kwargs['video_path']=='1.mp4',
                      'layout': {'scale': 70, 'tracking_sample_count': 120}}], 'all-frames-fixture')
        with patch.object(edit, 'apply_face_safe_layout', side_effect=candidate), \
             patch.object(edit, 'guard_automatic_graphic_copy', side_effect=lambda cues:cues):
            result, kept, audit = coordinate_graphic_framing([raw], [{**raw, 'review_blocked': True}], self.schedule, events,
                paths={'cam1': '1.mp4', 'cam2': '2.mp4'}, clips={'cam1': [[0,1800,0,1800]], 'cam2': [[0,1800,30,1830]]}, fps=30, width=1920, height=1080)
        self.assertEqual(kept, [events[1]])
        self.assertEqual(audit['changes'][0]['camera'], 'cam2')
        self.assertTrue(audit['final_visible_frames_require_recheck'])
        self.assertEqual(next(s['camera'] for s in result if s['start'] <= 41 < s['end']), 'cam2')
        self.assertEqual(events, [{'start': 42, 'end': 43}, {'start': 50, 'end': 53}])

    def test_short_shot_absorption_cannot_change_a_qualified_neighbours_camera(self):
        body = 'به این وضعیت می‌گن فلج تحلیلی.'
        raw = {'id': 'candidate', 'start': 34, 'end': 38, 'headline_fa': body,
               'copy_provenance': {'source_text': body},
               'controls': {'Title': 'ANALYSIS PARALYSIS', 'Body': body},
               'element_id': 'hermes-glass-insight',
               'native_runtime_contract': {'typography': {'profile': edit.NATIVE_GLASS_PROFILE}}}
        placed = [{'id': 'already-safe', 'start': 32.5, 'end': 33, 'review_blocked': False},
                  {**raw, 'review_blocked': True}]
        events = [{'start': 35, 'end': 37}]
        def candidate(cues, **kwargs):
            return ([{**cues[0], 'review_blocked': kwargs['video_path'] == '1.mp4',
                      'layout': {'scale': 70, 'tracking_sample_count': 120}}], 'all-frames-fixture')
        with patch.object(edit, 'apply_face_safe_layout', side_effect=candidate), \
             patch.object(edit, 'guard_automatic_graphic_copy', side_effect=lambda cues: cues):
            result, kept, audit = coordinate_graphic_framing([raw], placed, self.schedule, events,
                paths={'cam1': '1.mp4', 'cam2': '2.mp4'},
                clips={'cam1': [[0,1800,0,1800]], 'cam2': [[0,1800,30,1830]]},
                fps=30, width=1920, height=1080)
        self.assertEqual(result, self.schedule)
        self.assertEqual(kept, events)
        self.assertEqual(audit['changes'], [])
        self.assertIn('already-qualified', audit['deferred'][0]['reason'])


if __name__ == '__main__':
    unittest.main()
