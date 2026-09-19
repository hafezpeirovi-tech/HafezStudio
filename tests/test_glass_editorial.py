import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine/src/hermes_video'))
from glass_editorial import editorial_proposals, review_markdown
import test_glass_assembly as assembly_fixtures
from unittest.mock import patch
import os
import tempfile
import subtitle_pipeline


class GlassEditorialTests(unittest.TestCase):
    def proposal(self, text, **extra):
        return editorial_proposals([dict(id=25, source_text=text, **extra)])

    def test_explicit_transition_produces_literal_label_not_rewrite(self):
        r = self.proposal('مورد بعد، رفع مشکل نداشتن استراتژی.')
        self.assertEqual(r['chapters'][0]['quote_fa'], 'رفع مشکل نداشتن استراتژی')
        self.assertEqual(r['chapters'][0]['title_en'], '')
        self.assertFalse(r['policy']['source_rewrite'])
        self.assertFalse(r['policy']['publication_ready'])

    def test_named_feature_uses_only_spoken_name(self):
        r = self.proposal('این برنامه یک بخش گزارش هفتگی داره که مفیده.')
        self.assertEqual(r['chapters'][0]['quote_fa'], 'گزارش هفتگی')

    def test_named_concept_is_not_a_fixed_domain_dictionary(self):
        r = self.proposal('به این روش می‌گن یادگیری فعال، یعنی تمرین کنیم.')
        self.assertEqual(r['chapters'][0]['quote_fa'], 'یادگیری فعال')

    def test_long_or_unfinished_labels_are_not_truncated(self):
        for text in ['مورد بعد، راهی که با استفاده از آن همه کارها را انجام می دهیم.',
                     'مورد بعد، بررسی این که', 'مورد بعد، ابزار...', 'مورد بعد، ابزار…']:
            with self.subTest(text=text):
                self.assertEqual(self.proposal(text)['chapters'], [])

    def test_no_fixed_interval_or_generic_text_chapter(self):
        r = self.proposal('این یک جمله عادی است.', start=105, confidence=1)
        self.assertEqual(r['chapters'], [])

    def test_rewritten_text_cannot_replace_original(self):
        r = editorial_proposals([dict(id=1, text='مورد بعد، نتیجه قطعی.')])
        self.assertFalse(r['chapters'])
        self.assertEqual(r['review_items'][0]['status'], 'missing-original-source-text')

    def test_english_proposal_is_retained_but_never_auto_rendered(self):
        r = editorial_proposals([dict(id=1, source_text='گزارش هفتگی')],
              [dict(segment_id=1, quote_fa='گزارش هفتگی', title_en='GUARANTEED SUCCESS')])
        self.assertEqual(r['chapters'][0]['title_en'], '')
        self.assertEqual(r['chapters'][0]['proposed_translation'], 'GUARANTEED SUCCESS')

    def test_comments_are_never_promoted_to_copy(self):
        r = editorial_proposals([dict(id=1, source_text='متن ساده')],
              [dict(segment_id=1, comment='مورد بعد، نتیجه قطعی')])
        self.assertEqual(r['chapters'][0]['quote_fa'], '')

    def test_same_source_label_is_not_duplicated(self):
        text = 'مورد بعد، گزارش هفتگی.'
        r = editorial_proposals([dict(id=1, source_text=text)],
              [dict(segment_id=1, quote_fa='گزارش هفتگی')])
        self.assertEqual(len(r['chapters']), 1)

    def test_overlays_are_review_only_not_native_insertion(self):
        r = self.proposal('مقایسه ۳۰ و ۴۰ درصد؛ سابسکرایب کن؛ نکته مهم بعدی.')
        self.assertEqual({i['role'] for i in r['review_items']},
                         {'comparison', 'metric', 'subscribe', 'important-words'})
        self.assertTrue(all(i['status'] == 'review-only-not-inserted' for i in r['review_items']))
        self.assertIsNone(next(i for i in r['review_items'] if i['role']=='subscribe')['family'])
        self.assertFalse(r['policy']['overlay_insertion'])

    def test_invalid_and_duplicate_identities_fail_closed(self):
        for segments in [[dict(id=True)], [dict(id=1), dict(id=1)], 'wrong']:
            with self.assertRaises(ValueError): editorial_proposals(segments)
        for sid in [True, [], '1', None]:
            r = editorial_proposals([], [dict(segment_id=sid, quote_fa='الف')])
            self.assertFalse(r['chapters'])
            self.assertIn('blocked-invalid-copy',review_markdown(r,[],[],[]))

    def test_rule_proposal_still_requires_original_acoustic_gate(self):
        fixture = assembly_fixtures.GlassAssemblyTests()
        fixture.setUp()
        fixture.segments[0]['source_text']='مورد بعد، شروع موضوع.'
        fixture.requests=editorial_proposals(fixture.segments)['chapters']
        self.assertEqual(len(fixture.choose()[0]),1)
        fixture.context['words'][1]['confidence']=.7
        self.assertFalse(fixture.choose()[0])

    def test_review_has_source_clock_and_no_publication_claim(self):
        seg=dict(id=25,source_text='مورد بعد، گزارش هفتگی.',start=80,source_start=100,source_end=110)
        r=editorial_proposals([seg])
        text=review_markdown(r,[],[dict(request=r['chapters'][0],reason='unsafe-gap')],[seg])
        self.assertIn('unsafe-gap',text)
        self.assertIn('100 تا 110',text)
        self.assertIn('تأیید انتشار نیست',text)
        self.assertIn('تحلیل اولیه 80',text)
        self.assertIn('نه زمان سکانس نهایی Premiere',text)
        self.assertNotIn('تایم‌لاین 80',text)

    def test_glass_local_reviewer_has_explicit_short_chapter_contract(self):
        with patch.dict(os.environ, {'HERMES_STYLE_PACK':'glass'}):
            tasks=subtitle_pipeline.build_review_tasks([dict(id=1,text='مورد بعد، گزارش هفتگی.',start=30)],100)
            for task in (t for t in tasks if t['task_type']=='editor'):
                prompt=subtitle_pipeline._local_task_prompt(task)
                self.assertIn('"type":"CHAPTER"',prompt)
                self.assertIn('1-6 word',prompt)
                self.assertIn('title_en MUST be empty',prompt)
                self.assertNotIn('hermes-glass-insight',prompt)
                self.assertNotIn('6-18 words',prompt)

    def test_non_glass_editor_contract_is_unchanged(self):
        with patch.dict(os.environ, {'HERMES_STYLE_PACK':'signal-os'}):
            task=dict(task_type='editor',style_pack='signal-os',prompt='Transcript:\n[{"id":1,"text":"متن"}]')
            prompt=subtitle_pipeline._local_task_prompt(task)
            self.assertIn('6-18 words',prompt)
            self.assertNotIn('1-6 word',prompt)

    def test_old_local_prompt_answer_is_not_reused_after_contract_change(self):
        task=dict(task_id='visual-001',task_type='editor',style_pack='glass',prompt='saved task')
        response=dict(events=[],edits=[],markers=[])
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'HERMES_STYLE_PACK':'glass'}), \
             patch.object(subtitle_pipeline,'_call_local_json',return_value=(response,None)) as model:
            checkpoint=Path(tmp)/'checkpoint.json'
            with patch.object(subtitle_pipeline,'_local_task_prompt',return_value='contract A'):
                subtitle_pipeline.resolve_review_tasks(None,[task],checkpoint_path=checkpoint)
                subtitle_pipeline.resolve_review_tasks(None,[task],checkpoint_path=checkpoint)
                self.assertEqual(model.call_count,1)
            with patch.object(subtitle_pipeline,'_local_task_prompt',return_value='contract B'):
                subtitle_pipeline.resolve_review_tasks(None,[task],checkpoint_path=checkpoint)
                self.assertEqual(model.call_count,2)


if __name__ == '__main__':
    unittest.main()
