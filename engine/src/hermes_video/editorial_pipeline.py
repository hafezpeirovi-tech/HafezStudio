"""Compile source-bound editorial cues into a complete, isolated Glass review."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

from editorial_contract import PALETTE, COLOR_TOKENS
from editorial_source import prepare_recipe, premiere_media_url
from glass_pack import load_library, palette_values, read_mogrt, sha256, validate_plan
from runtime_paths import adobe_apps, studio_root


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def dump(path, value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)


def upgrade_manifest(path):
    """Preserve the previous review manifest; commit the new routing only last."""
    from glass_finalize import validate_review_outputs
    path=Path(path).resolve(strict=True)
    manifest=read(path)
    if manifest.get('style_pack')!='glass' or not manifest.get('glass_review'):
        raise ValueError('Expected an existing Glass review manifest')
    validate_review_outputs(manifest)
    existing=read(manifest['outputs']['professional_plan'])
    if existing.get('editorial_compilation'):
        return path
    target=path.with_name(path.stem+'.editorial.json')
    if target.exists():
        raise ValueError('Editorial manifest already exists; inspect the previous result')
    outputs=compile_review(manifest['outputs'])
    result=copy.deepcopy(manifest)
    result.update(outputs=outputs,publication_ready=False)
    validate_review_outputs(result)
    dump(target,result)
    return target


def compile_review(outputs, *, root=None, compiler=None, previous_project=None):
    """No stale cue reuse, silent legacy substitution or publication claim.

    Preserve the full assembly and compile all its eligible semantic title cues;
    retain independently selected vendor chapter/other families. AE job chaining
    may close only the exact clean project produced by the preceding iteration.
    """
    root=Path(root or studio_root())
    original={key:Path(outputs[key]).resolve(strict=True) for key in
              ('xml','professional_plan','tight_srt','audit','youtube')}
    source_folder=original['xml'].parent
    folder=source_folder/'editorial'
    if folder.exists():
        raise ValueError('Editorial job already exists; inspect it, never rerun native mutations blindly')
    plan=read(original['professional_plan']); report=read(original['audit'])
    for key in ('xml','professional_plan','tight_srt'):
        path=original[key]
        if report.get('outputs_sha256',{}).get(path.name)!=sha256(path):
            raise ValueError('Editorial assembly input changed')
    validate_plan(plan,load_library(root),qa=True,root=root)
    tree=ET.parse(original['xml']); sequence=tree.getroot().find('sequence')
    selected=[cue for cue in plan['graphics'] if cue.get('layout_mode')=='fullscreen-voice-continuous']
    if not selected:
        raise ValueError('No reviewed semantic title cues; editorial compilation cannot substitute invented titles')
    # Preflight every mapping before opening AE or starting an expensive render.
    for cue in selected:
        prepare_recipe(plan,sequence,cue['id'])
    if compiler is None:
        from editorial_compiler import compile_job
        compiler=compile_job
    ae=adobe_apps()['afterEffects']
    if not ae:
        raise ValueError('After Effects is required for current-media Editorial compilation')
    executable=ae/'Support Files/AfterFX.com'
    if not executable.is_file():
        raise ValueError('AfterFX.com unavailable')
    folder.mkdir()
    compiled=folder/'compiled'; compiled.mkdir()
    result=copy.deepcopy(plan)
    result['palette']=copy.deepcopy(PALETTE)
    result['expected_project_path']=str(folder/'Hafez-FX-Editorial-Review.prproj')
    result['editorial_compilation']=dict(protocol='hafez-editorial-pipeline-v1',
        source_plan=str(original['professional_plan']),source_plan_sha256=sha256(original['professional_plan']),
        compiled_cue_ids=[c['id'] for c in selected],publication_ready=False)
    colors=palette_values(PALETTE)
    for index,cue in enumerate(selected,1):
        print(f'HERMES_STAGE design 82 قالب Editorial {index}/{len(selected)} · {cue["id"]}',flush=True)
        job=compiled/cue['id']
        args=SimpleNamespace(plan=str(original['professional_plan']),xml=str(original['xml']),
            report=str(original['audit']),cue=cue['id'],output=str(job),preview=False,
            after_effects=str(executable),previous_project=previous_project)
        compiler(args)
        previous_project=str(job/'Editorial-Source.aep')
        native=read(job/'Editorial-Review.plan.json')['graphics'][0]['template_layers'][0]
        asset=read_mogrt(Path(native['template_path']))
        controls=[]
        for binding in native['typed_controls']:
            binding=dict(binding,occurrence=0)
            if binding['kind']=='color':
                token=COLOR_TOKENS[binding['name']]
                binding.update(value=colors[token],paletteToken=token)
            controls.append(binding)
        layer=dict(native,asset_id='editorial-'+cue['id'],family_id='hafez-editorial',
            palette_id=PALETTE['id'],coordinate_space=[asset['width'],asset['height']],
            typed_controls=controls,allow_no_text=False,
            compiled_binding=dict(protocol='hafez-editorial-compiled-v1',recipe_sha256=sha256(job/'recipe.json')))
        target=next(c for c in result['graphics'] if c['id']==cue['id'])
        target['template_layers']=[layer]
    # Every family shares the same palette. Keep its independently selected role.
    for cue in result['graphics']:
        for layer in cue['template_layers']:
            layer['palette_id']=PALETTE['id']
            for binding in layer['typed_controls']:
                if binding['kind']=='color':binding['value']=colors[binding['paletteToken']]
                if cue['id']=='glass-intro' and binding.get('value')=='HAFEZ STUDIO':
                    binding['value']='HAFEZ-FX'
    validate_plan(result,load_library(root),qa=True,root=root)
    for url in sequence.iter('pathurl'):
        url.text=premiere_media_url(url.text)
    xml=folder/'Glass-Director.xml'; plan_path=folder/'Glass-Director.premiere-plan.json'
    captions=folder/'Glass-Director.srt'; youtube=folder/'YouTube-review.md'
    tree.write(xml,encoding='utf-8',xml_declaration=True)
    captions.write_bytes(original['tight_srt'].read_bytes())
    youtube.write_bytes(original['youtube'].read_bytes())
    dump(plan_path,result)
    report=copy.deepcopy(report)
    report['editorial_compilation']=result['editorial_compilation']
    report['native_mogrt_instances_planned']=sum(len(c['template_layers']) for c in result['graphics'])
    report['outputs_sha256']={p.name:sha256(p) for p in (xml,plan_path,captions)}
    dump(folder/'assembly-report.json',report)
    return dict(outputs,xml=str(xml),professional_plan=str(plan_path),srt=str(captions),
                tight_srt=str(captions),safe_srt=str(captions),youtube=str(youtube),
                audit=str(folder/'assembly-report.json'))
