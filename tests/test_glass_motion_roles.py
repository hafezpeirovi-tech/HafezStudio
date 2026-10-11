import copy
import os
import sys
import unittest
from unittest.mock import patch
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from chapter_timeline import InsertionMap, Insertion
from glass_motion_roles import select_numbered, select_roles, role_layers, enabled, review_notes
from glass_pack import load_library, validate_plan, DEFAULT_PALETTE


class MotionRoleTests(unittest.TestCase):
    def test_default_and_explicit_legacy_rollback(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertTrue(enabled())
            os.environ['HAFEZ_GLASS_MOTION_ROLES_QA']='0'
            self.assertFalse(enabled())

    def test_review_notes_expose_uncertain_literal_labels(self):
        text=review_notes({'graphics':[dict(start=413.6,motion_role='numbered-point',
            semantic_source=dict(label='تست چهارم',display_text='',source_review_required=True))]})
        self.assertIn('06:53',text)
        self.assertIn('تست چهارم',text)
        self.assertIn('کم‌اطمینان',text)

    def fixture(self, text='مشکل اول فقط به سود نگاه نکن.'):
        words=[dict(id='w'+str(i), text=t, start=40+i*.3, end=40+i*.3+.25, trusted=True)
               for i,t in enumerate(text.split())]
        return words,InsertionMap(3000,[Insertion('intro',0,180)],Fraction(30))

    def test_numbered_literal_and_negation_preserved(self):
        words,mapping=self.fixture()
        cards,rejected=select_numbered(words,mapping)
        self.assertFalse(rejected)
        self.assertEqual(cards[0]['label'],'مشکل اول')
        self.assertEqual(cards[0]['display_text'],'فقط به سود نگاه نکن.')
        self.assertEqual(cards[0]['start_frame'],1380)
        self.assertEqual(cards[0]['source_word_ids'],[w['id'] for w in words])
        self.assertEqual(mapping.output_duration,3180) # No new pause.

    def test_numbered_number_word_and_digits(self):
        for text in ('نکته شماره دو ریسک را محدود کن.', 'تست ۳ فقط سود مهم نیست.'):
            words,mapping=self.fixture(text)
            self.assertEqual(len(select_numbered(words,mapping)[0]),1)

    def test_rejects_untrusted_split_missing_end_overlong_and_overlap(self):
        for case in ('trust','split','duplicate','unfinished','long','occupied','chapter'):
            with self.subTest(case=case):
                words,mapping=self.fixture();occupied=[]
                if case=='trust': words[-1]['trusted']=False
                if case=='split': words[1]['start']=words[0]['start']
                if case=='duplicate': words[-1]['id']=words[0]['id']
                if case=='unfinished': words[-1]['text']='نکن'
                if case=='long': words,mapping=self.fixture('مشکل اول '+' '.join(['متن']*14)+' نیست.')
                if case=='occupied': occupied=[(1380,1550)]
                if case=='chapter': mapping=InsertionMap(3000,[Insertion('chapter',1260,180)],Fraction(30))
                self.assertFalse(select_numbered(words,mapping,occupied=occupied)[0])

    def test_generic_number_is_not_a_numbered_point(self):
        words,mapping=self.fixture('سه معامله انجام دادم.')
        self.assertFalse(select_numbered(words,mapping)[0])

    def test_long_explanation_can_show_only_literal_ordinal_not_a_fake_summary(self):
        words,mapping=self.fixture('تست دوم '+' '.join(['توضیح']*14)+' نیست.')
        cards,rejected=select_numbered(words,mapping,allow_label_only=True)
        self.assertEqual(cards[0]['label'],'تست دوم')
        self.assertEqual(cards[0]['display_text'],'')
        self.assertTrue(cards[0]['label_only'])
        self.assertEqual(cards[0]['source_word_ids'],['w0','w1'])
        self.assertTrue(rejected)
        words[0]['trusted']=False
        self.assertFalse(select_numbered(words,mapping,allow_label_only=True)[0])

    def test_explicit_numbered_wins_over_overlapping_keyword(self):
        words,mapping=self.fixture()
        story={'proposals':[dict(segment_id=1,role='important-text',quote_fa='سود',
            source_word_ids=[w['id'] for w in words],meaning_review=dict.fromkeys(
                ('standalone','faithful','important','spelling_clean'),True))]}
        cards,_=select_roles(story,words,mapping)
        self.assertEqual([c['motion_role'] for c in cards],['numbered-point'])

    def test_real_vendor_contracts_are_editable_separate_and_one_palette(self):
        lib=load_library(ROOT)
        numbered=role_layers(lib,dict(motion_role='numbered-point',label='مشکل اول',display_text='فقط به سود نگاه نکن.'),ROOT)
        emphasis=role_layers(lib,dict(motion_role='emphasis',display_text='مدیریت ریسک'),ROOT)
        self.assertEqual(len(numbered),2)
        self.assertEqual(len(emphasis),2)
        self.assertNotEqual(numbered[-1]['asset_id'],emphasis[-1]['asset_id'])
        position=next(c for c in emphasis[-1]['typed_controls'] if c['name']=='Global Position')
        self.assertEqual(position['value'],[.5,.5])
        self.assertEqual([c['track'] for c in emphasis],[2,3])
        colors={c['name']:c['paletteToken'] for c in numbered[-1]['typed_controls'] if c['kind']=='color'}
        self.assertEqual(colors,{'Text 1':'text','Text 2':'accent'})
        plan=dict(protocol='hermes-professional-edit-v2',style_pack='glass',purpose='isolated-native-qa',
            expected_project_path=str(ROOT/'proof/unused-test.prproj'),palette=DEFAULT_PALETTE,
            graphics=[dict(id='numbered',start=0,end=6,template_layers=numbered),
                      dict(id='emphasis',start=10,end=16,template_layers=emphasis)])
        validate_plan(plan,lib,qa=True,root=ROOT)
        assets={a['id']:a for a in lib['assets']}
        for layer in numbered+emphasis:
            self.assertFalse(assets[layer['asset_id']]['hasMediaReplacement'])
            for c in layer['typed_controls']:
                if c['kind']=='text':self.assertTrue(c['font'].startswith('Abar'))

    def test_single_word_fragment_is_not_an_automatic_takeaway(self):
        words,mapping=self.fixture('اشتباهی')
        story={'proposals':[dict(segment_id=1,role='important-text',quote_fa='اشتباهی',
            source_word_ids=['w0'],meaning_review=dict.fromkeys(
                ('standalone','faithful','important','spelling_clean'),True))]}
        original=copy.deepcopy(story)
        cards,rejected=select_roles(story,words,mapping)
        self.assertFalse(cards)
        self.assertEqual(rejected[0]['reason'],'emphasis-fragment-needs-review')
        self.assertEqual(story,original)

    def test_uncertain_label_can_be_review_candidate_but_never_trusted_body(self):
        words,mapping=self.fixture()
        for i,w in enumerate(words): w.update(source_index=i,reviewable_label=True)
        words[0]['trusted']=False
        original=copy.deepcopy(words)
        self.assertFalse(select_numbered(words,mapping)[0])
        cards,_=select_numbered(words,mapping,allow_review_labels=True)
        self.assertEqual(cards[0]['label'],'مشکل اول')
        self.assertEqual(cards[0]['display_text'],'')
        self.assertTrue(cards[0]['source_review_required'])
        self.assertFalse(cards[0]['publication_ready'])
        self.assertEqual(words,original)
        words[1]['source_index']=3
        self.assertFalse(select_numbered(words,mapping,allow_review_labels=True)[0])
        words[1]['source_index']=1;words[0]['reviewable_label']=False
        self.assertFalse(select_numbered(words,mapping,allow_review_labels=True)[0])

    def test_longer_emphasis_keeps_source_bound_portrait_layout(self):
        for phrase,role,layout in (
                ('مدیریت ریسک','emphasis','emphasis-voice-continuous'),
                ('فقط سود کافی نیست','editorial-emphasis','fullscreen-voice-continuous')):
            with self.subTest(phrase=phrase):
                words,mapping=self.fixture(phrase)
                story={'proposals':[dict(segment_id=1,role='important-text',quote_fa=phrase,
                    source_word_ids=[w['id'] for w in words],meaning_review=dict.fromkeys(
                        ('standalone','faithful','important','spelling_clean'),True))]}
                cards,rejected=select_roles(story,words,mapping)
                self.assertFalse(rejected)
                self.assertEqual(len(cards),1)
                self.assertEqual(cards[0]['motion_role'],role)
                self.assertEqual(cards[0]['layout_mode'],layout)
                self.assertEqual(cards[0]['source_word_ids'],[w['id'] for w in words])


if __name__=='__main__':unittest.main()
