import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine/src/hermes_video'))
import subtitle_pipeline as pipeline
import professional_edit


class ReviewRecoveryTests(unittest.TestCase):
    def test_exact_selected_clause_and_catalog_hint_survive_the_pipeline(self):
        from curation_rules import curate_complete_statement
        from rough_cut import validate_markers
        quote = 'تریدینگ‌ویو یک بخش کامیونیتی داره'
        source = [{'id': 0, 'start': 0, 'end': 8, 'text': quote + ' که کاربران در آن استراتژی منتشر می‌کنند'}]
        decision = curate_complete_statement(source, 0, [quote])
        self.assertEqual(decision['text'], quote + '.')
        self.assertEqual(decision['source'], 'speaker-exact-selection')
        marker = {'segment_id': 0, 'type': 'GRAPHIC', 'confidence': 0.95,
                  'element_id': 'hermes-glass-insight', 'title_en': 'COMMUNITY STRATEGIES'}
        validated = validate_markers([marker], source)[0]
        self.assertEqual(validated['element_id'], marker['element_id'])
        self.assertEqual(validated['title_en'], marker['title_en'])
        rejected = curate_complete_statement(source, 0, ['این ابزار سود تضمینی دارد'])
        self.assertNotIn('سود تضمینی', rejected['text'])
        self.assertEqual(rejected['source'], 'speaker-exact')

    def test_original_audio_report_keeps_camera1_active_without_master_file(self):
        import autocut
        import xml.etree.ElementTree as ET
        metadata = {'width': 1920, 'height': 1080, 'frame_count': 300}
        audio = {'depth': 24, 'sample_rate': 48000, 'channels': 2}
        manifest = {'cam1_path': 'cam1.mp4', 'cam2_path': 'cam2.mp4',
                    'cam1_metadata': metadata, 'cam2_metadata': metadata,
                    'audio_metadata': {'cam1': audio, 'cam2': audio}, 'fps': 30}
        variant = {'name': 'Director', 'timeline_frames': 30,
                   'clips': {'cam1': [[0, 30, 0, 30, 0]], 'cam2': [[0, 30, 0, 30, 1]]}}
        for report in ({'source_preserved': True}, {'output_path': ''}, {'output_path': '.'}):
            with patch.object(autocut, 'prepare_track_motion', return_value=({}, 'test')):
                lines, _ = autocut._sequence_xml(manifest, 'director', variant, [], [], report)
            root = ET.fromstring('\n'.join(lines))
            tracks = root.findall('./media/audio/track')
            self.assertEqual(tracks[0].findtext('enabled'), 'TRUE')
            self.assertEqual(tracks[0].findtext('clipitem/enabled'), 'TRUE')
            self.assertEqual(tracks[1].findtext('enabled'), 'FALSE')
            self.assertEqual(tracks[1].findtext('clipitem/enabled'), 'FALSE')
            self.assertFalse(root.findall('.//audio//filter'))

    def test_curated_hero_preserves_glow_and_tracks_both_visible_angles(self):
        cue = {'id': 'hero', 'start': 0, 'end': 4, 'text': 'عنوان کامل',
               'element_id': 'hermes-title-hero-3', 'kind': 'chapter',
               'template_layers': [{'role': 'catalog-curated-element', 'controls': {'Title': 'عنوان کامل'}}]}
        def detect(path, groups, model):
            face = (0.1, 0.2, 0.1, 0.2) if path == 'cam1' else (0.6, 0.2, 0.1, 0.2)
            return ([{'sample_frames': group, 'sample_count': len(group), 'detected_count': len(group),
                      'coverage': 1.0, 'face_union': face, 'subject_union': face,
                      'body_complete': True, 'body_tracking_method': 'pphumanseg-independent-person-union'} for group in groups], 'test')
        with patch.object(professional_edit, 'detect_subject_box_unions', side_effect=detect) as detector, patch.dict(professional_edit.os.environ, {'HERMES_GLOW_INTENSITY': '0.82'}):
            placed, _ = professional_edit.apply_face_safe_layout(
                [cue], video_path='cam1', clips=[[0, 60, 100, 160, 1], [60, 120, 160, 220, 0]],
                secondary_video_path='cam2', secondary_clips=[[0, 60, 300, 360, 0], [60, 120, 360, 420, 1]],
                fps=30, width=1920, height=1080)
        self.assertEqual(detector.call_count, 2)
        a, b = detector.call_args_list
        self.assertTrue(all(100 <= frame < 160 for frame in a.args[1][0]))
        self.assertTrue(all(360 <= frame < 420 for frame in b.args[1][0]))
        layout = placed[0]['layout']
        self.assertGreater(layout['tracking_sample_count'], 2)
        self.assertEqual(set(layout['tracking_cameras']), {'cam1', 'cam2'})
        self.assertEqual(layout['face_union_bbox'], [0.1, 0.2, 0.6, 0.2])
        controls = placed[0]['template_layers'][0]['controls']
        self.assertEqual(controls['Layout Position'], [960, 540])
        self.assertEqual(controls['Layout Scale'], 100)
        self.assertEqual(controls['Show Background'], 1)
        self.assertEqual(controls['Glow Radius'], 200)
        self.assertEqual(controls['Glow Intensity'], 20)

    def test_short_title_is_an_exact_source_label_not_an_invented_sentence(self):
        element = {'textSlots': ['Title']}
        args = {'persian_text': 'به این وضعیت می‌گن فلج تحلیلی.', 'english_title': 'ANALYSIS PARALYSIS'}
        safe = professional_edit._catalog_control_values(element, **args, short_title_fa='فلج تحلیلی')
        self.assertEqual(safe['Title'], 'فلج تحلیلی')
        unsafe = professional_edit._catalog_control_values(element, **args, short_title_fa='حافظ پیروی استراتژی دارد')
        self.assertEqual(unsafe['Title'], args['persian_text'])

    def test_approved_glass_uses_physical_plate_size_at_hd_and_4k(self):
        cue = {'id': 'glass', 'start': 0, 'end': 4, 'text': 'متن کامل است.',
               'element_id': 'hermes-glass-insight', 'kind': 'statement',
               'template_layers': [{'role': 'catalog-curated-element', 'controls': {}}]}
        def detect(path, groups, model):
            return ([{'sample_frames': group, 'sample_count': len(group),
                      'detected_count': len(group), 'coverage': 1.0,
                      'body_complete': True, 'body_tracking_method': 'pphumanseg-independent-person-union',
                      'face_union': (0.4, 0.15, 0.2, 0.3),
                      'subject_union': (0.2491, 0.0574, 0.5276, 0.9426)}
                     for group in groups], 'test')
        scales = []
        for width, height in ((1920, 1080), (3840, 2160)):
            with self.subTest(width=width), patch.object(professional_edit, 'detect_subject_box_unions', side_effect=detect):
                placed, _ = professional_edit.apply_face_safe_layout(
                    [cue], video_path='cam1', clips=[[0, 120, 0, 120, 1]],
                    fps=30, width=width, height=height)
                layout = placed[0]['layout']
                scale = layout['scale']
                scales.append(scale)
                self.assertGreater(scale, 0)
                self.assertLessEqual(720 * scale / 100 + 24, layout['max_width'] * 1920 / width + 0.1)
                self.assertLessEqual(380 * scale / 100 + 24, layout['max_height'] * 1080 / height + 0.1)
                controls = placed[0]['template_layers'][0]['controls']
                self.assertEqual(controls['Layout Position'], layout['mogrt_layout_position'])
                self.assertEqual(controls['Layout Scale'], scale)
        self.assertEqual(scales[0], scales[1])

    def test_resume_reuses_only_matching_successful_task(self):
        task = {'task_id': 'subtitle-001', 'task_type': 'subtitle', 'prompt': 'original', 'segment_ids': [0]}
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / 'checkpoint.json'
            with patch.object(pipeline, '_call_local_json', return_value=({'segments': []}, None)) as call:
                pipeline.resolve_review_tasks(None, [task], checkpoint_path=checkpoint)
                self.assertEqual(call.call_count, 1)
                pipeline.resolve_review_tasks(None, [task], checkpoint_path=checkpoint)
                self.assertEqual(call.call_count, 1)
                pipeline.resolve_review_tasks(None, [{**task, 'prompt': 'changed'}], checkpoint_path=checkpoint)
                self.assertEqual(call.call_count, 2)

    def test_invalid_result_is_not_saved_as_a_success(self):
        task = {'task_id': 'subtitle-001', 'task_type': 'subtitle', 'prompt': 'original'}
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / 'checkpoint.json'
            with patch.object(pipeline, '_call_local_json', return_value=(None, 'timeout')):
                merged, audit, warnings = pipeline.resolve_review_tasks(None, [task], checkpoint_path=checkpoint)
            self.assertFalse(checkpoint.exists())
            self.assertFalse(audit['tasks'][0]['valid'])
            self.assertTrue(warnings)
            self.assertEqual(merged['segments'], [])

    def test_stream_assembles_fragments_and_requires_done(self):
        packets = [{'response': '{"segments":', 'done': False}, {'response': '[]}', 'done': True}]
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b'\n'.join(json.dumps(p).encode() for p in packets))
        with patch.object(pipeline.urllib.request, 'build_opener', return_value=Opener()):
            result, error = pipeline._call_local_json('test')
            self.assertEqual(result, {'segments': []})
            self.assertIsNone(error)
            packets[-1]['done'] = False
            result, error = pipeline._call_local_json('test')
            self.assertIsNone(result)
            self.assertIn('incomplete', error)

    def test_stream_deadline_does_not_accept_partial_copy(self):
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b'{"response":"{}","done":true}\n')
        with patch.object(pipeline.urllib.request, 'build_opener', return_value=Opener()), patch.object(pipeline.time, 'monotonic', side_effect=[0, 151]):
            result, error = pipeline._call_local_json('test', timeout=150)
        self.assertIsNone(result)
        self.assertIn('deadline', error)
