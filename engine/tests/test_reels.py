import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'hermes_video'))
import reels


class ReelsTests(unittest.TestCase):
    def setUp(self):
        self.media = {'fps': [30000, 1001], 'duration': 90, 'width': 1920, 'height': 1080, 'audio_channels': 2}
        self.segments = reels.validate_segments([
            {'start': 0, 'end': 10, 'text': 'چرا این نکته مهم است؟'},
            {'start': 10, 'end': 21, 'text': 'پاسخ کامل اینجاست.'},
            {'start': 21.05, 'end': 31, 'text': 'یک موضوع مستقل.'},
            {'start': 31, 'end': 43, 'text': 'پایان موضوع دوم.'}], 90)
    def bind(self, candidates):
        return reels.bind_candidates(candidates, self.segments, self.media, 20, 60, 6)
    def test_adjacent_clips_share_frame_without_duplicate_speech(self):
        clips = self.bind([{'first_segment': 0, 'last_segment': 1}, {'first_segment': 2, 'last_segment': 3}])
        self.assertLessEqual(clips[0]['end_frame'], clips[1]['start_frame'])
        self.assertIn('پاسخ کامل', clips[0]['text'])
        self.assertAlmostEqual(clips[0]['end'] * 30000 / 1001, clips[0]['end_frame'])
    def test_invented_or_overlapping_selection_is_rejected(self):
        for candidates in ([{'first_segment': False, 'last_segment': 2}],
                           [{'first_segment': 0, 'last_segment': 99}],
                           [{'first_segment': 0, 'last_segment': 2}, {'first_segment': 1, 'last_segment': 3}]):
            with self.assertRaises(ValueError): self.bind(candidates)
    def test_empty_selection_is_valid(self):
        self.assertEqual(self.bind([]), [])
    def test_bad_transcript_rejected(self):
        for data in ([{'start': 0, 'end': float('nan'), 'text': 'bad'}],
                     [{'start': 0, 'end': 5, 'text': 'one'}, {'start': 3, 'end': 9, 'text': 'two'}]):
            with self.assertRaises(ValueError): reels.validate_segments(data, 90)
    def test_captions_and_xml_keep_source_clock(self):
        clip = self.bind([{'first_segment': 2, 'last_segment': 3}])[0]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); srt = root / 'captions.srt'; xml = root / 'reels.xml'
            reels.write_captions(srt, self.segments, clip)
            parsed = reels.parse_srt(srt.read_text(encoding='utf8'))
            self.assertGreaterEqual(parsed[0]['start'], 0)
            self.assertLessEqual(parsed[-1]['end'], clip['end']-clip['start']+.001)
            reels.build_xml(root / 'finished & color.mp4', self.media, [clip], xml)
            tree = ET.parse(xml)
            self.assertEqual(tree.findtext('.//sequence/rate/ntsc'), 'TRUE')
            self.assertEqual(int(tree.findtext('.//video/track/clipitem/in')), clip['start_frame'])
            self.assertEqual(tree.findtext('.//video/format/samplecharacteristics/height'), '1920')
    def test_motion_is_source_bound(self):
        segments = reels.validate_segments([{'start': 0, 'end': 4, 'text': 'کمی مکث کن.'}], 30)
        cue = reels.motion_cues({'first_segment': 0, 'last_segment': 0, 'start': 0}, segments, 'editorial-3d')[0]
        self.assertEqual(cue['text'], segments[0]['text'])
        self.assertEqual(cue['template'], 'pause-card')
        self.assertEqual(cue['source_segment'], 0)

    def test_offline_selection_keeps_complete_chapter_instead_of_shorter_fragment(self):
        rows = reels.validate_segments([
            {'start': 0, 'end': 5, 'text': 'مشکل شماره یک شروع موضوع'},
            {'start': 5, 'end': 24, 'text': 'این توضیح اول بود'},
            {'start': 24, 'end': 35, 'text': 'پاسخ فقط توی تحلیل نیست'},
            {'start': 35, 'end': 42, 'text': 'توی احتمالاته'},
            {'start': 42, 'end': 52, 'text': 'پس باید ببینی نتیجه درست میشه یا نه'},
            {'start': 52, 'end': 57, 'text': 'مشکل شماره دو موضوع بعدی'}], 90)
        clips = reels.local_candidates(rows, 20, 60, 6)
        self.assertEqual([(x['first_segment'],x['last_segment']) for x in clips], [(0,4)])

    def test_wrong_media_cache_is_rejected_before_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); media=root/'analysis.wav';media.write_bytes(b'new source')
            plan=root/'plan.json';reels.save_json(plan,{'protocol':reels.PROTOCOL,'source':{'sha256':'wrong'}})
            with self.assertRaisesRegex(ValueError,'different source'):
                reels.transcript(media,self.media,root,reuse_plan=plan)

if __name__ == '__main__': unittest.main()
