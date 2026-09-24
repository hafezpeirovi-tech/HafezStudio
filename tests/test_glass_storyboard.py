import sys
import unittest
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from glass_storyboard import semantic_proposals, review_with_local_ai


class StoryboardTests(unittest.TestCase):
    def test_words_are_copied_by_index_not_generated_quote(self):
        result=review_with_local_ai([dict(id=7,source_text='این قانون احتمالات است')],
            generate=lambda *a,**k: ({'markers':[dict(candidate_id='s7w1n2',confidence=.9,
                quote_fa='متن جعلی')]},None))
        self.assertEqual(result['proposals'][0]['quote_fa'],'قانون احتمالات')

    def test_checkpoint_is_model_specific(self):
        calls=[]
        def generate(prompt, **kwargs):
            calls.append(prompt)
            return {'markers':[]}, None
        with tempfile.TemporaryDirectory() as directory:
            checkpoint=Path(directory)/'cache.json'
            for model in ('first','first','second'):
                review_with_local_ai([dict(id=1,source_text='گزارش هفتگی')],
                    generate=generate,checkpoint=checkpoint,model=model)
        self.assertEqual(len(calls),2)

    def test_foreign_segment_not_accepted(self):
        result=review_with_local_ai([dict(id=1,source_text='گزارش هفتگی')],
            generate=lambda *a,**k: ({'markers':[{'segment_id':99}]},None))
        self.assertFalse(result['model_review_complete'])
        self.assertFalse(result['proposals'])

    def run_marker(self, **changes):
        marker=dict(segment_id=1, confidence=.95, visual_kind='kinetic', headline_fa='ریاضی و احتمالات')
        marker.update(changes)
        source=[dict(id=1, source_text='این سیستم بر اساس ریاضی و احتمالات است.', source_word_ids=['a','b'])]
        return semantic_proposals([marker], source)

    def test_source_bound_text_has_no_model_times_or_paths(self):
        result=self.run_marker(start=99, template_path='evil.png', approved=True)
        item=result['proposals'][0]
        self.assertEqual(item['role'], 'important-text')
        self.assertNotIn('start', item)
        self.assertNotIn('template_path', item)
        self.assertFalse(result['automatic_native_ready'])
        self.assertFalse(result['png_fallback_allowed'])

    def test_invention_and_bad_confidence_rejected(self):
        for changes in ({'headline_fa':'تضمین سود'}, {'confidence':True},
                        {'confidence':float('nan')}, {'segment_id':True},
                        {'headline_fa':'ریاضی و'}):
            self.assertFalse(self.run_marker(**changes)['proposals'])

    def test_chart_requires_real_data(self):
        self.assertFalse(self.run_marker(visual_kind='chart', data=['۹۰ درصد'])['proposals'])
        self.assertFalse(self.run_marker(visual_kind='chart')['proposals'])

    def test_duplicate_proposals_deduplicated(self):
        source=[dict(id=1, source_text='گزارش هفتگی')]
        marker=dict(segment_id=1, type='CHAPTER', quote_fa='گزارش هفتگی', confidence=.9)
        self.assertEqual(len(semantic_proposals([marker, marker], source)['proposals']),1)


if __name__ == '__main__': unittest.main()
