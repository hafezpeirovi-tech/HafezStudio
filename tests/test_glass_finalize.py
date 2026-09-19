import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from contextlib import redirect_stdout
from io import StringIO
from fractions import Fraction
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
import glass_audio
import glass_finalize
import studio_cli
from glass_pack import sha256


class GlassFinalizeTests(unittest.TestCase):
    def test_review_requires_explicit_opt_in_and_resets_environment(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{},clear=False):
            folder=Path(tmp)/'draft'
            studio_cli._configure_runtime(folder,style='glass',glass_review=True)
            self.assertEqual(os.environ['HERMES_GLASS_REVIEW_MODE'],'1')
            studio_cli._configure_runtime(folder,style='signal-os')
            self.assertEqual(os.environ['HERMES_GLASS_REVIEW_MODE'],'0')
            with self.assertRaises(ValueError):
                studio_cli._configure_runtime(folder,style='signal-os',glass_review=True)

    def test_run_and_finalize_parse_review_opt_in(self):
        p=studio_cli.build_parser()
        for args in (['run','--cam1','a','--cam2','b'],['finalize','--manifest','a']):
            result=p.parse_args(args+['--style','glass','--glass-review'])
            self.assertTrue(result.glass_review)

    def test_resume_validates_without_reimporting_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'review.edit.json'
            manifest.write_text(json.dumps(dict(glass_review=True,outputs={'xml':str(Path(tmp)/'a.xml')})))
            args=studio_cli.build_parser().parse_args(['finalize','--manifest',str(manifest),'--style','glass','--glass-review'])
            with patch.object(studio_cli,'_configure_job_runtime'), patch.object(studio_cli,'_import_autocut') as engine, \
                 patch.object(studio_cli,'validate_job_outputs',return_value={'xml':'a.xml','srt':'a.srt'}) as validate, redirect_stdout(StringIO()) as out:
                self.assertEqual(studio_cli.finalize_job(args),0)
                engine.assert_not_called(); validate.assert_called_once()
                self.assertIn('reusedVerifiedReview',out.getvalue())
            review=Path(tmp)/'changed.json';review.write_text('{}');args.review=str(review)
            with patch.object(studio_cli,'_configure_job_runtime'), self.assertRaisesRegex(ValueError,'immutable'):
                studio_cli.finalize_job(args)

    def test_prepare_still_calls_analysis_without_resume_path(self):
        args=studio_cli.build_parser().parse_args(['prepare','--cam1','a','--cam2','b','--style','glass'])
        engine=Mock();engine.prepare_edit.return_value='new.edit.json'
        with patch.object(studio_cli,'_video_paths',return_value=(Path('a'),Path('b'))), \
             patch.object(studio_cli,'_configure_job_runtime'),patch.object(studio_cli,'_import_autocut',return_value=engine),redirect_stdout(StringIO()):
            self.assertEqual(studio_cli.prepare_job(args),0)
            engine.prepare_edit.assert_called_once_with('a','b')

    def review_fixture(self, folder):
        from test_chapter_timeline import sequence
        from chapter_timeline import Insertion, InsertionMap, rewrite_sequence
        source=sequence();rate=Fraction(30000,1001)
        mapping=InsertionMap(60,[Insertion('intro',0,15)],rate)
        output=rewrite_sequence(source,mapping,'Glass')
        paths={key:folder/name for key,name in dict(xml='Glass.xml',professional_plan='Glass.plan.json',
               tight_srt='Glass.srt',audit='report.json',youtube='YouTube.md').items()}
        original=folder/'source.xml'; container=ET.Element('xmeml');container.append(source);ET.ElementTree(container).write(original)
        audio=folder/'entry.wav';audio.write_bytes(b'fixture')
        cue=dict(start_frame=0,end_frame=15,frames=15,asset_path=str(audio),sha256=sha256(audio),depth=24,sample_rate=48000,channels=2)
        output.findall('media/audio/track')[3].append(glass_audio.audio_clip(cue,rate,0))
        plan=dict(sequence='Glass',timeline_mapping=mapping.payload(),expected_project_path=str(folder/'review.prproj'),
                  graphics=[dict(start=0,end=float(15/rate),template_layers=[dict(track=2),dict(track=3)])],
                  camera_schedule=[dict(start=float(15/rate),end=float(75/rate),camera='cam1')],punch_ins=[],sfx_cues=[cue])
        container=ET.Element('xmeml');container.append(output);ET.ElementTree(container).write(paths['xml'])
        paths['professional_plan'].write_text(json.dumps(plan))
        paths['tight_srt'].write_text('1\n00:00:00,501 --> 00:00:02,502\nSource\n')
        paths['youtube'].write_text('Review only')
        report=dict(inputs_sha256={str(original):sha256(original)},outputs_sha256={p.name:sha256(p) for k,p in paths.items() if k in ('xml','professional_plan','tight_srt')})
        paths['audit'].write_text(json.dumps(report))
        return dict(outputs={k:str(p) for k,p in paths.items()}),paths,plan,output,report

    def test_independent_output_validation_detects_tampering(self):
        # Isolate the separately-tested vendor schema; source/audio/timing checks are real.
        for mutation,error in [('none',None),('file','Stale'),('voice','Source frame'),
                               ('gap','coverage'),('missing-sfx','entry SFX'),('xml-sfx','SFX XML'),('caption','Caption')]:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                manifest,paths,plan,seq,report=self.review_fixture(Path(tmp))
                if mutation=='file':paths['xml'].write_text(paths['xml'].read_text()+' ')
                if mutation=='voice':
                    clip=seq.find('media/audio/track/clipitem');clip.find('in').text='101';clip.find('out').text='131'
                if mutation=='gap':plan['camera_schedule'][0]['start']=float(16/Fraction(30000,1001))
                if mutation=='missing-sfx':plan['sfx_cues']=[]
                if mutation=='xml-sfx':seq.findall('media/audio/track')[3].find('clipitem/start').text='1'
                if mutation=='caption':paths['tight_srt'].write_text('1\n00:00:00,000 --> 00:00:01,000\nWrong\n')
                if mutation not in ('none','file'):
                    container=ET.Element('xmeml');container.append(seq);ET.ElementTree(container).write(paths['xml'])
                    paths['professional_plan'].write_text(json.dumps(plan))
                    report['outputs_sha256']={paths[k].name:sha256(paths[k]) for k in ('xml','professional_plan','tight_srt')}
                    paths['audit'].write_text(json.dumps(report))
                with patch.object(glass_finalize,'validate_plan'),patch.object(glass_finalize,'load_library'):
                    if error:
                        with self.assertRaisesRegex(ValueError,error):glass_finalize.validate_review_outputs(manifest)
                    else:
                        result=glass_finalize.validate_review_outputs(manifest)
                        self.assertEqual(result['sfxCues'],1);self.assertFalse(result['publicationReady'])

    def test_only_explicit_chapter_copy_is_forwarded(self):
        result=glass_finalize.chapter_proposals([
            {'type':'TEXT','segment_id':1,'headline_fa':'A'},
            {'type':'CHAPTER','segment_id':2,'headline_fa':'متن منبع'},
            {'type':'CHAPTER','segment_id':2,'headline_fa':'تکراری'},
            {'type':'CHAPTER','segment_id':True,'headline_fa':'bad'},
            {'type':'CHAPTER','segment_id':3,'comment':'Do not derive a title from instructions'},
        ])
        self.assertEqual(result,[{'segment_id':2,'quote_fa':'متن منبع','title_en':''},
                                 {'segment_id':3,'quote_fa':'','title_en':''}])

    def test_no_legacy_graphic_call_after_glass_return(self):
        # Validate the real branch wiring without importing GPU/ASR dependencies.
        import ast
        tree=ast.parse((ROOT/'engine/src/hermes_video/autocut.py').read_text(encoding='utf-8-sig'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='finalize_edit')
        branch=next(n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='glass_review')
        self.assertIsInstance(branch.body[-1],ast.Return)
        calls=[n.func.id for n in ast.walk(branch) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertIn('finalize_review',calls)
        self.assertNotIn('render_graphic_assets',calls)
        self.assertNotIn('build_graphic_cues',calls)

    def test_finalize_rejects_existing_output_and_unbound_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.edit.json'; path.write_text('{}')
            manifest={'outputs':{'xml':str(Path(tmp)/'test.xml')}}
            kw=dict(manifest_path=path,manifest=manifest,director_variant={},events=[],
                    camera_schedule=[],markers=[],caption_source=None,sequence_builder=None)
            with self.assertRaisesRegex(ValueError,'Fresh word'):glass_finalize.finalize_review(**kw)
            (Path(tmp)/'test.glass-review').mkdir()
            with self.assertRaisesRegex(ValueError,'already exists'):glass_finalize.finalize_review(**kw)
            self.assertEqual(path.read_text(),'{}')

    def test_real_audio_catalog_hash(self):
        path,item=glass_audio.vendor_sfx(ROOT)
        self.assertEqual(sha256(path),item['sha256'])
        self.assertEqual(item['gain_db'],-9)

    def test_missing_modified_and_escaping_audio_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'config').mkdir()
            data=json.loads((ROOT/'config/glass-audio.json').read_text())
            f=root/'outside.mp3'; f.write_bytes(b'x')
            data['chapter_entry'].update(path=str(f),sha256=sha256(f))
            (root/'config/glass-audio.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):glass_audio.vendor_sfx(root)

    def test_audio_clip_clock_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'audio.wav'; path.write_bytes(b'fixture')
            cue=dict(start_frame=180,end_frame=360,frames=180,asset_path=str(path),sha256=sha256(path),
                     depth=24,sample_rate=48000,channels=2)
            clip=glass_audio.audio_clip(cue,Fraction(30000,1001),0)
            self.assertEqual(clip.findtext('start'),'180')
            self.assertEqual(clip.findtext('file/rate/ntsc'),'TRUE')
            self.assertEqual(clip.findall('filter'),[])
            cue['end_frame']=359
            with self.assertRaises(ValueError):glass_audio.audio_clip(cue,Fraction(30),0)
            cue['end_frame']=360; path.write_bytes(b'changed')
            with self.assertRaises(ValueError):glass_audio.audio_clip(cue,Fraction(30),0)

    def test_shared_composite_gets_one_sfx_no_voice_mutation(self):
        seq=ET.fromstring('<sequence><rate><timebase>30</timebase><ntsc>FALSE</ntsc></rate><media><audio>'
                          '<track><clipitem><name>voice</name></clipitem></track><track/><track/><track/><track/>'
                          '</audio></media></sequence>')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'a.wav';path.write_bytes(b'a')
            cue=dict(asset_path=str(path),sha256=sha256(path),frames=180,depth=24,sample_rate=48000,channels=2)
            before=ET.tostring(seq.find('media/audio/track'))
            with patch.object(glass_audio,'render_entry',return_value=cue) as render:
                cues=glass_audio.attach_entries(seq,{'insertions':[
                    {'id':'intro','start_frame':0,'end_frame':180,'frames':180},
                    {'id':'chapter','start_frame':900,'end_frame':1080,'frames':180}]},tmp,ROOT)
            self.assertEqual(render.call_count,1)
            self.assertEqual(len(cues),2)
            self.assertEqual(len(seq.findall('media/audio/track')[3].findall('clipitem')),2)
            self.assertEqual(ET.tostring(seq.find('media/audio/track')),before)
            self.assertEqual(len(seq.findall('media/audio/track')[4]),0)


if __name__=='__main__':unittest.main()
