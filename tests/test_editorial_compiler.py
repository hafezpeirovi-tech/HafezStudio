import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from compile_editorial_intro import finalize_definition


class EditorialCompilerTests(unittest.TestCase):
    def definition(self):
        names=['Brand','Title Line 1','Title Line 2','Subtitle','Topic Label','English Eyebrow']
        return dict(capsuleID='old', clientControls=[dict(type=6,uiName={'strDB':[{'str':n}]},
                    value={'strDB':[{'str':'OLD DEMO'}]},fonteditinfo={}) for n in names]+[
                    dict(type=3,uiName={'strDB':[{'str':'Title Line Spacing'}]},value=132,min=0,max=100)],
            sourceInfoLocalized={'en_US':{'capsuleparams':{'capParams':[
                dict(capPropType=0,capPropUIName=n,capPropDefault='OLD DEMO') for n in names]+[
                dict(capPropType=2,capPropUIName='Title Line Spacing',capPropMin=0,capPropMax=100)]}}})

    def test_editable_defaults_and_ranges_agree(self):
        data=finalize_definition(self.definition(),{'title_lines':['مشکل اول','نداشتن داده']})
        self.assertNotEqual(data['capsuleID'],'old')
        self.assertEqual(data['clientControls'][0]['value']['strDB'][0]['str'],'HAFEZ-FX')
        self.assertEqual(data['clientControls'][1]['value']['strDB'][0]['str'],'مشکل اول')
        self.assertEqual(data['clientControls'][3]['value']['strDB'][0]['str'],'')
        for text in data['clientControls'][:6]:
            self.assertTrue(text['fonteditinfo']['capPropFontEdit'])
            self.assertTrue(text['fonteditinfo']['capPropFontSizeEdit'])
        slider=data['clientControls'][-1]
        self.assertEqual((slider['min'],slider['max'],slider['value']),(80,220,132))
        nested=data['sourceInfoLocalized']['en_US']['capsuleparams']['capParams']
        self.assertEqual(nested[2]['textEditValue'],'نداشتن داده')
        self.assertEqual((nested[-1]['capPropMin'],nested[-1]['capPropMax']),(80,220))

    def test_changed_template_contract_is_not_silently_accepted(self):
        data=self.definition(); data['clientControls'].pop(0)
        with self.assertRaises(ValueError):finalize_definition(data,{'title_lines':['a','b']})


if __name__=='__main__':unittest.main()
