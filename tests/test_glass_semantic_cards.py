import sys
import unittest
from pathlib import Path
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from chapter_timeline import InsertionMap, Insertion
from glass_semantic_cards import select_cutaways, display_copy
from glass_storyboard import review_meaning


class SemanticCardsTests(unittest.TestCase):
    def test_display_spelling_is_explicit_not_a_rewrite(self):
        text,changes=display_copy('بهترین استراتیجی')
        self.assertEqual(text,'بهترین استراتژی')
        self.assertEqual(changes[0]['source'],'بهترین استراتیجی')
        self.assertEqual(display_copy('ریاضی و احتمالات.')[0],'ریاضی و احتمالات')
        self.assertEqual(display_copy('حافظ پیروی')[0],'حافظ پیروی')
    def fixture(self):
        proposal=dict(segment_id=1,role='important-text',quote_fa='ریاضی و احتمالات',
            source_word_ids=['a','b','c'],meaning_review=dict(standalone=True,faithful=True,important=True,spelling_clean=True))
        spans=[dict(id=wid,text=text,start=at,end=at+.2,trusted=True)
               for wid,text,at in [('a','ریاضی',40),('b','و',40.2),('c','احتمالات',40.4)]]
        return {'proposals':[proposal]},spans,InsertionMap(3000,[Insertion('intro',0,180)],Fraction(30))

    def test_maps_real_quote_without_adding_pause(self):
        report,spans,mapping=self.fixture()
        chosen,rejected=select_cutaways(report,spans,mapping)
        self.assertFalse(rejected)
        self.assertEqual(chosen[0]['start_frame'],1380)
        self.assertEqual(chosen[0]['end_frame'],1560)
        self.assertEqual(mapping.output_duration,3180)

    def test_untrusted_or_missing_word_rejected(self):
        for mutation in ('untrusted','missing','meaning','capacity','overlap'):
            with self.subTest(mutation=mutation):
                report,spans,mapping=self.fixture()
                occupied=[]
                if mutation=='untrusted':spans[1]['trusted']=False
                if mutation=='missing':spans.pop(1)
                if mutation=='meaning':report['proposals'][0]['meaning_review']['faithful']=False
                if mutation=='capacity':report['proposals'][0]['quote_fa']='یک دو سه چهار پنج شش هفت'
                if mutation=='overlap':occupied=[(1380,1400)]
                chosen,rejected=select_cutaways(report,spans,mapping,occupied=occupied)
                self.assertFalse(chosen)
                self.assertTrue(rejected)

    def test_cannot_span_inserted_chapter(self):
        report,spans,_=self.fixture()
        chosen,rejected=select_cutaways(report,spans,InsertionMap(3000,[Insertion('chapter',1260,180)],Fraction(30)))
        self.assertFalse(chosen)
        self.assertEqual(rejected[0]['reason'],'chapter-intersection')

    def test_meaning_rejection_is_not_promoted(self):
        report,_,_=self.fixture()
        result=review_meaning(report,[dict(id=1,source_text='ریاضی و احتمالات')],
            generate=lambda *a,**k: ({'standalone':True,'faithful':False,'important':True},None))
        self.assertFalse(result['proposals'])
        self.assertEqual(len(result['meaning_rejected']),1)

if __name__=='__main__':unittest.main()
