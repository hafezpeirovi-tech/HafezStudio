import copy
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from editorial_source import prepare_recipe, media_slices, split_heading, local_media_path, premiere_media_url


class EditorialSourceTests(unittest.TestCase):
    def fixture(self):
        seq = ET.fromstring('''<sequence><name>Edit</name><duration>600</duration>
          <rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate><media><audio><track>
          <clipitem><start>0</start><end>90</end><in>300</in><out>390</out><file id="cam">
          <pathurl>file://localhost/C%3A/current.mp4</pathurl><rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate>
          <media><video/></media></file></clipitem>
          <clipitem><start>90</start><end>600</end><in>600</in><out>1110</out><file id="cam"/></clipitem>
          </track></audio></media></sequence>''')
        words=['source:1','source:2']
        evidence=dict(start_frame=30,end_frame=210,quote_fa='بهترین استراتژی',display_text='بهترین استراتژی',copy_edits=[],source_word_ids=words,
          semantic_source=dict(quote_fa='بهترین استراتژی',source_word_ids=words,
              meaning_review=dict(standalone=True,faithful=True,important=True,spelling_clean=True)))
        plan=dict(protocol='hermes-professional-edit-v2',style_pack='glass',sequence='Edit',fps=30,
                  graphics=[dict(id='cue',start=1,end=7,semantic_source=evidence)])
        return plan,seq

    def test_source_changes_follow_cuts_not_demo_media(self):
        p,s=self.fixture(); r=prepare_recipe(p,s,'cue')
        self.assertEqual([(x['source_in_frame'],x['frames']) for x in r['slices']],[(330,60),(600,120)])
        self.assertEqual(r['inserted_pause_frames'],0)
        self.assertFalse(r['dialogue_processing'])
        self.assertFalse(r['publication_ready'])
        self.assertTrue(all(x['path'].endswith('current.mp4') for x in r['slices']))

    def test_inputs_not_mutated(self):
        p,s=self.fixture(); before=copy.deepcopy(p); xml=ET.tostring(s)
        prepare_recipe(p,s,'cue')
        self.assertEqual(p,before); self.assertEqual(ET.tostring(s),xml)

    def test_unreviewed_unlinked_or_rewritten_text_fails(self):
        for case in ('review','word','rewrite','duplicate','quote','duration','clock','sequence','time'):
            with self.subTest(case=case):
                p,s=self.fixture(); e=p['graphics'][0]['semantic_source']
                if case=='review':e['semantic_source']['meaning_review']['faithful']=False
                if case=='word':e['source_word_ids']=['other']
                if case=='rewrite':e['display_text']='یک ادعای تازه'
                if case=='duplicate':p['graphics']*=2
                if case=='quote':e['semantic_source']['quote_fa']='متن دیگر'
                if case=='duration':e['end_frame']=300;p['graphics'][0]['end']=10
                if case=='clock':p['fps']=25
                if case=='sequence':p['sequence']='Other'
                if case=='time':p['graphics'][0]['start']=float('nan')
                with self.assertRaises(ValueError):prepare_recipe(p,s,'cue')

    def test_gaps_overlap_retime_filter_disabled_rejected(self):
        for case in ('gap','overlap','retime','filter','disabled','missing','mixed','transition'):
            with self.subTest(case=case):
                _,s=self.fixture(); track=s.find('media/audio/track'); a,b=track.findall('clipitem')
                if case=='gap':b.find('start').text='91';b.find('out').text='1109'
                if case=='overlap':b.find('start').text='89';b.find('out').text='1111'
                if case=='retime':b.find('out').text='1200'
                if case=='filter':ET.SubElement(a,'filter')
                if case=='disabled':ET.SubElement(a,'enabled').text='FALSE'
                if case=='missing':b.find('file').set('id','missing')
                if case=='mixed':a.find('file/rate/timebase').text='25'
                if case=='transition':ET.SubElement(track,'transitionitem')
                with self.assertRaises(ValueError):media_slices(s,30,210)

    def test_no_network_media_or_placeholder(self):
        for url in ('https://example.com/a.mp4','file://server/private.mp4'):
            with self.assertRaises(ValueError):local_media_path(url)
        for text in ('','…','یک دو سه چهار پنج شش هفت'):
            with self.assertRaises(ValueError):split_heading(text)
        self.assertEqual(' '.join(split_heading('فقط داشتن استراتژی کافی نیست')).split(), 'فقط داشتن استراتژی کافی نیست'.split())

    def test_premiere_windows_url_normalization(self):
        expected='file://localhost/C%3A/Media/a%20b.wav'
        self.assertEqual(premiere_media_url('file:///C:/Media/a%20b.wav'), expected)
        self.assertEqual(premiere_media_url(expected), expected)
        self.assertEqual(local_media_path(expected), local_media_path('file:///C:/Media/a%20b.wav'))


if __name__=='__main__':unittest.main()
