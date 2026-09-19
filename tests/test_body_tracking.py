import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine/src/hermes_video'))
import body_tracking as body
import professional_edit as edit


class BodyTrackingTests(unittest.TestCase):
    def test_all_person_components_including_far_hand_are_union(self):
        scores = np.zeros((1, 2, 192, 192), dtype=np.float32)
        scores[:, 0] = .95
        scores[0, 0, 50:180, 70:120] = .05
        scores[0, 1, 50:180, 70:120] = .95
        scores[0, 0, 70:76, 170:176] = .05
        scores[0, 1, 70:76, 170:176] = .95
        box = body.person_box(scores)
        self.assertGreaterEqual(box[0] + box[2], 178/192)

    def test_empty_uncertain_invalid_maps_are_not_safe(self):
        for score in (np.zeros((1,2,192,192)), np.full((1,2,192,192), np.nan),
                      np.zeros((1,1,192,192)), np.full((1,2,192,192), .5)):
            self.assertIsNone(body.person_box(score))

    def test_half_open_frame_mapping_uses_all_visible_frames_across_cuts(self):
        a=[[0,60,100,160,1],[60,120,160,220,0]]
        b=[[0,60,300,360,0],[60,120,360,420,1]]
        self.assertEqual(edit._visible_source_frames(a,0,4,30), list(range(100,160)))
        self.assertEqual(edit._visible_source_frames(b,0,4,30), list(range(360,420)))
        self.assertTrue(edit._timeline_coverage_complete([a,b],0,4,30))
        self.assertFalse(edit._timeline_coverage_complete([a],0,4,30))
        self.assertIn(-1, edit._visible_source_frames([[0,30,100,160,1]],0,1,30))

    def test_missing_model_never_falls_back_to_inferred_body(self):
        with patch.object(body, 'PersonSegmenter', side_effect=ValueError('missing')):
            result, backend = body.detect_subject_box_unions('none', [[0,1,2]], 'face')
        self.assertFalse(result[0]['body_complete'])
        self.assertEqual(result[0]['decoded_count'], 0)
        self.assertIsNone(result[0]['subject_union'])
        self.assertIn('unavailable', backend)

    def test_protected_union_has_explicit_clamped_margin(self):
        self.assertEqual(body.protected_union([(0,0,1,1)]), (0,0,1,1))
        self.assertIsNone(body.protected_union([]))
        box=body.protected_union([(.2,.3,.4,.6)])
        self.assertAlmostEqual(box[0],.14)
        self.assertAlmostEqual(box[1],.24)

    def test_actual_model_hash_is_required(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.onnx'
            path.write_bytes(b'not-approved-model')
            with self.assertRaisesRegex(ValueError,'SHA256'):
                body.PersonSegmenter(path)

    def test_every_frame_is_inferred_and_mid_interval_hand_is_not_missed(self):
        class Capture:
            def __init__(self,*args): self.pos=0
            def isOpened(self): return True
            def set(self,key,value): self.pos=value
            def get(self,key): return self.pos
            def read(self):
                frame=np.full((4,4,3), self.pos, dtype=np.uint8)
                self.pos+=1
                return True,frame
            def release(self): pass
        class Person:
            def detect(self,frame):
                return (.1,.1,.8,.8) if frame[0,0,0]==1 else (.4,.2,.2,.6)
        class Face:
            backend='test'
            def __init__(self,*args): pass
            def detect(self,frame): return []
        with patch.object(body,'PersonSegmenter',Person), patch.object(body,'FaceDetector',Face), patch.object(body.cv2,'VideoCapture',Capture):
            result,_=body.detect_subject_box_unions('fixture',[[0,1,2]],'face')
        self.assertTrue(result[0]['body_complete'])
        self.assertEqual(len(result[0]['frame_evidence']),3)
        self.assertEqual(result[0]['body_union'], (.1,.1,.8,.8))

    def test_missing_body_evidence_blocks_motion_and_sfx(self):
        cue={'id':'x','start':0,'end':1,'kind':'statement','text':'متن کامل است.',
             'sfx_cue':{'start':0},'controls':{}}
        tracking={'sample_frames':list(range(30)), 'sample_count':30,'detected_count':29,
                  'coverage':29/30,'body_complete':False,'subject_union':(.4,.2,.2,.7),'face_union':None}
        with patch.object(edit,'detect_subject_box_unions', return_value=([tracking],'fixture')):
            result,_=edit.apply_face_safe_layout([cue],video_path='fixture',clips=[[0,30,0,30,1]],fps=30,width=1920,height=1080)
        self.assertTrue(result[0]['review_blocked'])
        self.assertNotIn('sfx_cue',result[0])
        self.assertFalse(result[0]['layout']['collision_free'])

    def test_camera_transform_gate_includes_ramp_but_not_disabled_camera(self):
        events=[{'start':2,'end':3,'scale':116}]
        self.assertTrue(edit._unverified_motion_overlap([[0,150,0,150,1]],1.9,2,30,events))
        self.assertTrue(edit._unverified_motion_overlap([[0,150,0,150,1]],3,3.15,30,events))
        self.assertFalse(edit._unverified_motion_overlap([[0,150,0,150,1]],0,1,30,events))
        self.assertFalse(edit._unverified_motion_overlap([[0,150,0,150,0]],2,3,30,events))

    def test_tracking_complete_does_not_claim_transformed_source_is_safe(self):
        cue={'id':'x','start':0,'end':4,'kind':'statement','text':'متن کامل است.',
             'sfx_cue':{'start':0},'controls':{}}
        tracking={'sample_frames':list(range(120)), 'sample_count':120,'detected_count':120,
                  'coverage':1,'body_complete':True,'subject_union':(.4,.2,.2,.7),'face_union':None}
        with patch.object(edit,'detect_subject_box_unions', return_value=([tracking],'fixture')):
            result,_=edit.apply_face_safe_layout([cue],video_path='fixture',clips=[[0,120,0,120,1]],fps=30,
                                                 width=1920,height=1080,motion_events=[{'start':1,'end':2}])
        self.assertIn('CAMERA_TRANSFORM_REVIEW_REQUIRED',result[0]['qa_flags'])
        self.assertNotIn('BODY_TRACKING_REVIEW_REQUIRED',result[0]['qa_flags'])
        self.assertNotIn('sfx_cue',result[0])


if __name__=='__main__': unittest.main()
