import copy
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine/src/hermes_video'))
import glass_pack as glass


class GlassPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'motion-pack/vendor/test.mogrt'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'local-template')
        self.asset = {'id':'a', 'name':'Example', 'family':'one', 'path':'motion-pack/vendor/test.mogrt',
                      'sha256':glass.sha256(self.path), 'width':3840, 'height':2160,
                      'controls':[{'name':'Text 1','kind':'text','occurrence':0,
                          'font':{'capPropFontEdit':True,'capPropFontSizeEdit':True}},
                          {'name':'Text 1','kind':'color','occurrence':0,'font':{}},
                          {'name':'Glow','kind':'scalar','occurrence':0,'font':{}}]}

    def layer(self, **kw):
        return glass.typed_layer(self.asset, text={'Text 1':'عنوان'}, track=3, root=self.root, **kw)

    def plan(self):
        return {'protocol':'hermes-professional-edit-v2','style_pack':'glass','purpose':'isolated-native-qa',
                'expected_project_path':'separate.prproj','palette':copy.deepcopy(glass.DEFAULT_PALETTE),
                'graphics':[{'id':'chapter-1','start':0,'end':6,'template_layers':[self.layer()]}]}

    def test_same_name_color_and_text_are_separate_typed_bindings(self):
        bindings = self.layer()['typed_controls']
        self.assertEqual([b['kind'] for b in bindings], ['text','color'])
        self.assertEqual(bindings[0]['value'], 'عنوان')
        self.assertEqual(bindings[1]['value'], glass.palette_values(glass.DEFAULT_PALETTE)['text'])

    def test_exact_fonteditinfo_key_is_parsed(self):
        p = self.root/'sample.mogrt'
        with zipfile.ZipFile(p,'w') as archive:
            archive.writestr('definition.json',json.dumps({'clientControls':[{'type':6,
                'uiName':{'strDB':[{'localeString':'en_US','str':'Title'}]},
                'fonteditinfo':{'capPropFontEdit':True},'value':{'strDB':[]}}]}))
        self.assertFalse(glass.read_mogrt(p)['fontLocked'])

    def test_missing_or_ellipsis_text_is_rejected(self):
        for text in ({}, {'Text 1':'…'}, {'Text 1':'half...'}, {'Text 1':5}):
            with self.subTest(text=text), self.assertRaises(ValueError):
                glass.typed_layer(self.asset,text=text,track=3,root=self.root)

    def test_locked_font_is_not_reported_as_editable(self):
        self.asset['controls'][0]['font']['capPropFontEdit']=False
        with self.assertRaisesRegex(ValueError,'locked'):self.layer()

    def test_modified_asset_rejected(self):
        self.path.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.layer()

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):self.layer(values={'Imaginary Leading':10})

    def test_font_size_must_be_positive_and_supported(self):
        for size in (0,-1,float('nan'),float('inf')):
            with self.subTest(size=size), self.assertRaises(ValueError):self.layer(sizes={'Text 1':size})

    def test_no_implicit_native_approval(self):
        with self.assertRaisesRegex(ValueError,'native QA'):glass.validate_plan(self.plan(),{'assets':[self.asset]})
        glass.validate_plan(self.plan(),{'assets':[self.asset]},qa=True)

    def test_qa_requires_isolated_target(self):
        plan=self.plan();plan.pop('expected_project_path')
        with self.assertRaises(ValueError):glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_mixed_palette_rejected(self):
        plan=self.plan();plan['graphics'][0]['template_layers'][0]['typed_controls'][1]['value']=[1,0,0,1]
        with self.assertRaisesRegex(ValueError,'Mixed palette'):glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_missing_color_rejected(self):
        plan=self.plan();plan['graphics'][0]['template_layers'][0]['typed_controls'].pop()
        with self.assertRaisesRegex(ValueError,'Unbound'):glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_no_grain_removal_requirement_for_new_package(self):
        library=glass.load_library(ROOT)
        self.assertTrue(library['grainAllowed'])
        self.assertEqual(len(library['assets']),114)
        self.assertEqual(len(library['packages']),7)

    def test_per_control_font_override(self):
        font='AbarHighFaNum-ExtraBold'
        self.assertEqual(self.layer(fonts={'Text 1':font})['typed_controls'][0]['font'],font)

    def test_non_abar_font_cannot_reach_native_plan(self):
        for font in ('Tahoma', 'ArialMT', '', 'Abar'):
            with self.assertRaisesRegex(ValueError,'ABAR'):
                self.layer(fonts={'Text 1':font})
        plan=self.plan()
        plan['graphics'][0]['template_layers'][0]['typed_controls'][0]['font']='Tahoma'
        with self.assertRaisesRegex(ValueError,'ABAR'):
            glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_duplicate_and_unbound_text_rejected(self):
        for duplicate in (True, False):
            plan=self.plan(); bindings=plan['graphics'][0]['template_layers'][0]['typed_controls']
            if duplicate:bindings.append(copy.deepcopy(bindings[0]))
            else:bindings.pop(0)
            with self.assertRaises(ValueError):glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_wrong_native_path_rejected(self):
        plan=self.plan();plan['graphics'][0]['template_layers'][0]['template_path']=str(self.root/'wrong.mogrt')
        with self.assertRaises((ValueError,FileNotFoundError)):
            glass.validate_plan(plan,{'assets':[self.asset]},qa=True,root=self.root)

    def test_nonfinite_and_wrong_kind_rejected(self):
        for value in (float('nan'), True, '500'):
            plan=self.plan();layer=plan['graphics'][0]['template_layers'][0]
            layer['typed_controls'].append({'name':'Glow','kind':'scalar','occurrence':0,'value':value})
            with self.assertRaises(ValueError):glass.validate_plan(plan,{'assets':[self.asset]},qa=True)

    def test_no_metadata_only_ready_claim(self):
        report=glass.capability_report(glass.load_library(ROOT))
        self.assertFalse(report['automaticEditingReady'])
        self.assertEqual(report['nativeApproved'],0)

    def test_glass_cannot_silently_fall_back_to_legacy_editing(self):
        import studio_cli
        output = self.root/'not-created'
        with self.assertRaisesRegex(ValueError, 'not released'):
            studio_cli._configure_runtime(output, style='Glass')
        self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
