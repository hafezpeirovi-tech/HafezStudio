import copy
import os
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from glass_assembly import select_chapters, mapped_word_spans, srt_text, read_srt
from glass_pack import planning_catalog
import subtitle_pipeline


class GlassAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.seq=ET.fromstring('<sequence><duration>6000</duration><rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate><media><video/><audio/></media></sequence>')
        for _ in range(2):
            track=ET.SubElement(self.seq.find('media/video'),'track')
            for a,b in ((0,900),(900,6000)):
                clip=ET.SubElement(track,'clipitem')
                for k,v in (('start',a),('end',b),('in',a),('out',b)):ET.SubElement(clip,k).text=str(v)
        words=[]
        for wid,text,a,b in [('a','پایان',29,29.5),('b','شروع',30.2,30.5),('c','موضوع',30.6,31)]:
            words.append(dict(source_word_id=wid,text=text,acoustic_start=a,acoustic_end=b,
                              source_evidence_id='e',media_sha256='a'*64,confidence=.99,
                              word_boundary_review_required=False,source_coverage=1,timing_origin='asr-word-timestamps'))
        self.context=dict(words=words,media_sha256='a'*64,evidence_id='e',fps=(30,1),
                          keeps=[dict(start_frame=0,end_frame=6000,source_in_frame=0,source_out_frame=6000)])
        self.segments=[dict(id=1,text='شروع موضوع',source_word_ids=['b','c'],source_evidence_id='e',caption_boundary_before_reason='sentence-end')]
        self.requests=[dict(segment_id=1,quote_fa='موضوع',title_en='TOPIC')]
        self.captions=[dict(start=29,end=29.5,text='الف'),dict(start=30.2,end=31,text='ب')]

    def choose(self):return select_chapters(self.seq,self.segments,self.context,self.captions,self.requests)

    def test_safe_source_bound_boundary_selected(self):
        good,bad=self.choose();self.assertEqual(bad,[]);self.assertEqual(good[0]['at'],900)

    def test_plain_segment_partition_does_not_mean_sentence_end(self):
        self.segments[0]['caption_boundary_before_reason']='segment-partition'
        good,bad=self.choose();self.assertFalse(good);self.assertEqual(bad[0]['reason'],'not-a-sentence-or-pause-boundary')

    def test_invented_or_incomplete_quote_rejected(self):
        for quote in ('موضوع تازه','موضوع…'):
            self.requests[0]['quote_fa']=quote
            self.assertFalse(self.choose()[0])

    def test_word_and_caption_occupancy_block_chapter(self):
        self.context['words'][0]['acoustic_end']=30.1
        self.assertFalse(self.choose()[0])
        self.context['words'][0]['acoustic_end']=29.5
        self.captions[0]['end']=30.1
        self.assertFalse(self.choose()[0])

    def test_untrusted_or_missing_acoustic_context_never_fills_gap(self):
        self.context['words'][1]['confidence']=.7
        self.assertFalse(self.choose()[0])
        del self.context['words'][1]['acoustic_start']
        with self.assertRaisesRegex(ValueError,'acoustic'):self.choose()

    def test_duplicate_words_and_forged_identity_rejected(self):
        self.context['words'][1]['media_sha256']='b'*64
        self.assertFalse(self.choose()[0])
        self.context['words'].append(copy.deepcopy(self.context['words'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):self.choose()

    def test_editor_prompts_receive_real_glass_ids_not_legacy(self):
        with patch.dict(os.environ,{'HERMES_STYLE_PACK':'glass'}):
            tasks=subtitle_pipeline.build_review_tasks([{'id':1,'text':'شروع موضوع','start':0,'end':3}],3)
            for task in (t for t in tasks if t['task_type']=='editor'):
                self.assertEqual(task['style_pack'],'glass')
                for prompt in (task['prompt'],subtitle_pipeline._local_task_prompt(task)):
                    self.assertIn('foslight-saas-',prompt)
                    self.assertNotIn('hermes-glass-insight',prompt)
                    self.assertNotIn('hermes-title-hero-2',prompt)

    def test_real_catalog_has_only_known_review_candidates(self):
        catalog=planning_catalog()
        self.assertEqual(len(catalog),3)
        self.assertTrue(all(c['requires']['native_review'] for c in catalog))

    def test_ambiguous_segment_and_word_ownership_rejected(self):
        self.segments.append(copy.deepcopy(self.segments[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate segment'):self.choose()
        self.segments[-1]['id']=2
        with self.assertRaisesRegex(ValueError,'word ownership'):self.choose()

    def test_retimed_and_repeated_source_keeps_rejected(self):
        self.context['keeps'][0]['source_out_frame']=5999
        with self.assertRaisesRegex(ValueError,'source keeps'):self.choose()
        self.context['keeps'][0]['source_out_frame']=6000
        self.context['keeps'].append(copy.deepcopy(self.context['keeps'][0]))
        with self.assertRaisesRegex(ValueError,'source keeps'):self.choose()

    def test_malformed_requests_never_coerced_into_titles(self):
        self.requests={}
        with self.assertRaisesRegex(ValueError,'list of objects'):self.choose()
        self.requests=[dict(segment_id=1,quote_fa=['موضوع'],title_en='TOPIC')]
        self.assertEqual(self.choose()[1][0]['reason'],'invalid-title-fields')

    def test_caption_clock_and_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.srt'
            for source in ('1\n00:60:00,000 --> 00:61:00,000\nBad\n',
                           '1\n00:00:01,000 --> 00:00:03,000\nA\n\n2\n00:00:02,000 --> 00:00:04,000\nB\n'):
                path.write_text(source,encoding='utf-8')
                with self.assertRaises(ValueError):read_srt(path)


if __name__=='__main__':unittest.main()
