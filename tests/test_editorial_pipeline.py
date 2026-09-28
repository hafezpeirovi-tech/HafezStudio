import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
import editorial_contract as contract
import editorial_pipeline as pipeline
import studio_cli
from editorial_source import prepare_recipe
from glass_pack import sha256, palette_values
import test_editorial_source as source_fixture


class EditorialPipelineTests(unittest.TestCase):
    def test_cli_opt_in_is_explicit_and_resets(self):
        parser=studio_cli.build_parser()
        for args in (['run','--cam1','a','--cam2','b'],['finalize','--manifest','m']):
            parsed=parser.parse_args(args+['--style','glass','--glass-review','--editorial-glass'])
            self.assertTrue(parsed.editorial_glass)
        self.assertEqual(parser.parse_args(['glass-editorial','--manifest','m']).manifest,'m')
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ):
            studio_cli._configure_runtime(Path(tmp),style='glass',glass_review=True,editorial_glass=True)
            self.assertEqual(os.environ['HAFEZ_EDITORIAL_GLASS'],'1')
            studio_cli._configure_runtime(Path(tmp))
            self.assertEqual(os.environ['HAFEZ_EDITORIAL_GLASS'],'0')
            with self.assertRaisesRegex(ValueError,'requires'):
                studio_cli._configure_runtime(Path(tmp),editorial_glass=True)

    def test_shared_palette_includes_every_approved_gradient_color(self):
        values=palette_values(contract.PALETTE)
        self.assertTrue(set(contract.COLOR_TOKENS.values()).issubset(values))
        self.assertEqual(values['glassDeep'],[25/255,46/255,46/255,1])
        bad=dict(contract.PALETTE,glassDeep='not-a-color')
        with self.assertRaises(ValueError):palette_values(bad)

    def fixture(self,root):
        plan,seq=source_fixture.EditorialSourceTests().fixture()
        cue=plan['graphics'][0];cue['layout_mode']='fullscreen-voice-continuous'
        media=root/'current.mp4';media.write_bytes(b'source')
        seq.find('media/audio/track/clipitem/file/pathurl').text=media.as_uri()
        xml=root/'source.xml';container=ET.Element('xmeml');container.append(seq)
        ET.ElementTree(container).write(xml)
        original=root/'source.plan.json';original.write_text(json.dumps(plan),encoding='utf-8')
        sources=[]
        for name in ('Hafez-FX-Editorial-Intro-v3.aep','Hafez-FX Editorial Intro v4.mogrt'):
            p=root/'motion-pack/modules/01-editorial-intro'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(b'authoring-source');sources.append(p)
        folder=root/'job/compiled/cue';folder.mkdir(parents=True)
        template=folder/'Editorial-Editable.mogrt';template.write_bytes(b'mogrt')
        portrait=folder/'portrait-current.mp4';portrait.write_bytes(b'portrait')
        recipe=prepare_recipe(plan,seq,'cue')
        recipe.update(output=str(folder),source_plan=str(original),job_id='test-job',
                      inputs_sha256={str(p):sha256(p) for p in [*sources,xml,original]},
                      media_sha256={str(media):sha256(media)})
        for name,data in [('recipe.json',recipe),('ae-receipt.json',dict(ok=True,job_id='test-job')),
                          ('binding-report.json',dict(job_id='test-job',template_sha256=sha256(template),portrait_sha256=sha256(portrait)))]:
            (folder/name).write_text(json.dumps(data),encoding='utf-8')
        texts={'Title Line 1':recipe['title_lines'][0],'Title Line 2':recipe['title_lines'][1],
               'Brand':'HAFEZ-FX','Subtitle':'','Topic Label':'','English Eyebrow':''}
        layer=dict(template_path=str(template),track=3,role='editorial-source-bound',
                   typed_controls=[dict(name=k,kind='text',value=v) for k,v in texts.items()],
                   compiled_binding=dict(protocol='hafez-editorial-compiled-v1',recipe_sha256=sha256(folder/'recipe.json')))
        plan['expected_project_path']=str(root/'job/review.prproj')
        return layer,cue,plan,folder

    def test_compiled_contract_checks_actual_source_and_rejects_tampering(self):
        for mutation in ('none','text','time','evidence','outside','mogrt','media','recipe','receipt','track'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);layer,cue,plan,folder=self.fixture(root)
                if mutation=='text':layer['typed_controls'][0]['value']='invented'
                if mutation=='time':cue['start']+=1
                if mutation=='evidence':cue['semantic_source']['display_text']='invented'
                if mutation=='outside':layer['template_path']=str(root/'current.mp4')
                if mutation=='mogrt':(folder/'Editorial-Editable.mogrt').write_bytes(b'changed')
                if mutation=='media':(root/'current.mp4').write_bytes(b'changed')
                if mutation=='recipe':(folder/'recipe.json').write_text('{}')
                if mutation=='receipt':(folder/'ae-receipt.json').write_text('{"ok":false}')
                if mutation=='track':layer['track']=0
                asset=dict(controls=[{}]*20,fontLocked=[],hasMediaReplacement=True)
                with patch.object(contract,'read_mogrt',return_value=asset):
                    if mutation=='none':
                        result=contract.validate_compiled_layer(layer,cue,plan,root)
                        self.assertEqual(result['family'],'hafez-editorial')
                    else:
                        with self.assertRaises((ValueError,KeyError)):
                            contract.validate_compiled_layer(layer,cue,plan,root)

    def test_compilation_does_not_overwrite_existing_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'editorial').mkdir()
            file=root/'input';file.write_text('{}')
            outputs={k:str(file) for k in ('xml','professional_plan','tight_srt','audit','youtube')}
            with self.assertRaisesRegex(ValueError,'already exists'):
                pipeline.compile_review(outputs,root=root)

    def test_native_failure_never_promotes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan=root/'plan.json';plan.write_text('{}')
            source=root/'source.json'
            payload=dict(style_pack='glass',glass_review=True,outputs={'professional_plan':str(plan)})
            source.write_text(json.dumps(payload))
            before=source.read_bytes()
            with patch('glass_finalize.validate_review_outputs'),patch.object(pipeline,'compile_review',side_effect=RuntimeError('AE rejected')):
                with self.assertRaisesRegex(RuntimeError,'AE rejected'):pipeline.upgrade_manifest(source)
            self.assertEqual(source.read_bytes(),before)
            self.assertFalse((root/'source.editorial.json').exists())


if __name__=='__main__':unittest.main()
