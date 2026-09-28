"""Compile one source-bound, editable Editorial Glass MOGRT for native QA.

Two explicit stages: prepare renders ONLY a silent primary-camera insert and
produces an AE script; finish verifies AE success and produces a Premiere plan.
Neither stage controls Premiere or changes the installed application.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
import uuid
import zipfile
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from runtime_paths import studio_root
ROOT = studio_root()
from editorial_source import prepare_recipe, local_media_path, premiere_media_url
from glass_pack import sha256, read_mogrt
from mogrt_font_controls import enable_definition

MODULE = ROOT/'motion-pack/modules/01-editorial-intro'
AEP = MODULE/'Hafez-FX-Editorial-Intro-v3.aep'
REFERENCE = MODULE/'Hafez-FX Editorial Intro v4.mogrt'


def dump(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run(args, log):
    with log.open('ab') as stream:
        subprocess.run([str(x) for x in args], check=True, stdin=subprocess.DEVNULL,
                       stdout=stream, stderr=stream, timeout=600)


def frame_count(path):
    raw = subprocess.check_output([str(ROOT/'runtime/tools/ffprobe.exe'), '-v', 'error',
        '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames',
        '-of', 'json', str(path)], timeout=120)
    return int(json.loads(raw)['streams'][0]['nb_read_frames'])


def prepare(args):
    plan_path, xml_path, report_path = (Path(p).resolve(strict=True) for p in (args.plan, args.xml, args.report))
    report = read(report_path)
    captions_path = xml_path.with_suffix('.srt')
    for path in (plan_path, xml_path, captions_path):
        if report.get('outputs_sha256', {}).get(path.name) != sha256(path):
            raise ValueError('Assembly receipt does not match input: '+path.name)
    plan = read(plan_path)
    tree = ET.parse(xml_path)
    sequences = tree.getroot().findall('sequence')
    if len(sequences) != 1:
        raise ValueError('Exactly one input sequence required')
    recipe = prepare_recipe(plan, sequences[0], args.cue)
    for url in sequences[0].iter('pathurl'):
        local_media_path(url.text).resolve(strict=True)
        premiere_media_url(url.text)
    for piece in recipe['slices']:
        Path(piece['path']).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError('Use a new output folder; previous jobs are never overwritten')
    # Capture all identities BEFORE running external applications.
    recipe['inputs_sha256'] = {str(p): sha256(p) for p in (plan_path, xml_path, report_path, captions_path, AEP, REFERENCE)}
    recipe['media_sha256'] = {p['path']: sha256(Path(p['path'])) for p in recipe['slices']}
    recipe['job_id'] = 'Editorial-'+uuid.uuid4().hex[:12]
    recipe['source_plan'] = str(plan_path)
    recipe['output'] = str(output)
    output.mkdir(parents=True)
    dump(output/'recipe.json', recipe)
    ffmpeg = ROOT/'runtime/tools/ffmpeg.exe'
    rate = Fraction(*recipe['fps'])
    parts = []
    for index, piece in enumerate(recipe['slices']):
        part = output/f'portrait-part-{index:03}.mp4'
        run([ffmpeg, '-v', 'warning', '-nostdin', '-n', '-ss', str(float(Fraction(piece['source_in_frame'])/rate)),
             '-i', piece['path'], '-map', '0:v:0', '-an', '-sn', '-dn', '-vf',
             f'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps={rate.numerator}/{rate.denominator}',
             '-frames:v', piece['frames'], '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', part], output/'media.log')
        if frame_count(part) != piece['frames']:
            raise ValueError('Source ended early; refusing freeze-frame fallback')
        parts.append(part)
    concat = output/'portrait-parts.txt'
    concat.write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
    portrait = output/'portrait-current.mp4'
    run([ffmpeg, '-v', 'warning', '-nostdin', '-n', '-f', 'concat', '-safe', '1', '-i', concat,
         '-map', '0:v:0', '-an', '-c', 'copy', portrait], output/'media.log')
    if frame_count(portrait) != recipe['end_frame']-recipe['start_frame']:
        raise ValueError('Composed portrait frame count mismatch')
    request = dict(recipe, source_aep=str(AEP), portrait=str(portrait),
                   project=str(output/'Editorial-Source.aep'), preview=bool(args.preview),
                   previous_project=getattr(args, 'previous_project', None))
    template = Path(__file__).with_name('editorial_source_export.jsx').read_text(encoding='utf-8')
    (output/'export.jsx').write_text('var HAFEZ_EDITORIAL_JOB = '+json.dumps(request, ensure_ascii=True)+';\n'+template, encoding='utf-8')
    print(json.dumps(dict(status='media-prepared-awaiting-AE', job_id=recipe['job_id'],
                         output=str(output), frames=frame_count(portrait)), ensure_ascii=False))


def finalize_definition(definition, recipe):
    """Normalize the same exported controls validated in module v4."""
    result = enable_definition(definition)
    if result != {'client_controls': 6, 'capsule_controls': 6}:
        raise ValueError('Unexpected source-text contract')
    definition['capsuleID'] = str(uuid.uuid4())
    texts = {'Brand':'HAFEZ-FX', 'Title Line 1':recipe['title_lines'][0],
             'Title Line 2':recipe['title_lines'][1], 'Subtitle':'', 'Topic Label':'', 'English Eyebrow':''}
    ranges = {'Title Line Spacing':(80,220), 'Title Scale':(50,140), 'Portrait Zoom':(100,160)}
    for control in definition['clientControls']:
        label = control['uiName']['strDB'][0]['str']
        if label in texts:
            for localized in control['value']['strDB']:
                localized['str'] = texts[label]
        if label in ranges:
            control['min'], control['max'] = ranges[label]
    for locale in definition['sourceInfoLocalized'].values():
        for control in locale.get('capsuleparams', {}).get('capParams', []):
            label = control.get('capPropUIName')
            if label in texts:
                control.update(capPropDefault=texts[label], textEditValue=texts[label], fontTextRunLength=[len(texts[label])])
            if label in ranges:
                control['capPropMin'], control['capPropMax'] = ranges[label]
    return definition


def finish(args):
    output = Path(args.output).resolve(strict=True)
    recipe = read(output/'recipe.json')
    if recipe['output'] != str(output):
        raise ValueError('Job relocated; re-prepare rather than reuse stale absolute paths')
    for name, digest in {**recipe['inputs_sha256'], **recipe['media_sha256']}.items():
        if sha256(Path(name)) != digest:
            raise ValueError('Input changed after preparation')
    receipt = read(output/'ae-receipt.json')
    portrait = output/'portrait-current.mp4'
    if not receipt.get('ok') or receipt.get('job_id') != recipe['job_id'] or receipt.get('portrait') != str(portrait).replace('\\','/'):
        raise ValueError('No matching successful AE export receipt')
    raw = output/(recipe['job_id']+'.mogrt')
    destination = output/'Editorial-Editable.mogrt'
    with zipfile.ZipFile(raw) as source, destination.open('xb') as stream, zipfile.ZipFile(stream, 'w') as target:
        definition = finalize_definition(json.loads(source.read('definition.json').decode('utf-8-sig')), recipe)
        for info in source.infolist():
            target.writestr(info, json.dumps(definition, ensure_ascii=False).encode('utf-8') if info.filename == 'definition.json' else source.read(info))
    asset = read_mogrt(destination)
    if asset['fontLocked'] or len(asset['controls']) != 20 or not asset['hasMediaReplacement']:
        raise ValueError('Editable MOGRT contract failed')
    controls = [{'name':c['name'], 'kind':c['kind'], 'value':c['default']} for c in asset['controls'] if c['kind'] in ('text','color','scalar')]
    for control in controls:
        if control['kind'] == 'text':
            control.update(font='AbarHighFaNum-ExtraBold' if control['name'].startswith('Title Line') else 'AbarHighFaNum-SemiBold',
                           fontSize=102 if control['name'].startswith('Title Line') else 28)
    rate = Fraction(*recipe['fps'])
    project = output/'Hafez-FX-Source-Bound-Review.prproj'
    sequence_name = recipe['job_id']+' — Source-bound review'
    # The original full edit is retained: only its sequence name is changed.
    xml_path = next(Path(p) for p in recipe['inputs_sha256'] if p.endswith('.xml'))
    tree = ET.parse(xml_path)
    sequence = tree.getroot().find('sequence')
    sequence.find('name').text = sequence_name
    # Canonicalize local URLs, not media identity, edit timing, or dialogue gain.
    for url in sequence.iter('pathurl'):
        url.text = premiere_media_url(url.text)
    tree.write(output/'Editorial-Review.xml', encoding='utf-8', xml_declaration=True)
    source_plan = read(recipe['source_plan'])
    plan = dict(protocol='hermes-professional-edit-v2', style_pack='glass', purpose='isolated-native-qa',
                expected_project_path=str(project), sequence=sequence_name, fps=float(rate),
                sfx_cues=copy.deepcopy(source_plan.get('sfx_cues', [])),
                timeline_mapping=copy.deepcopy(source_plan.get('timeline_mapping', {})),
                publication_ready=False, video_tracks={'mogrt':3}, graphics=[dict(id=recipe['job_id'],
                start=float(Fraction(recipe['start_frame'])/rate), end=float(Fraction(recipe['end_frame'])/rate),
                semantic_source=recipe, template_layers=[dict(template_path=str(destination),
                template_sha256=sha256(destination), track=3, role='editorial-source-bound', typed_controls=controls)])])
    dump(output/'Editorial-Review.plan.json', plan)
    captions = next(Path(p) for p in recipe['inputs_sha256'] if p.endswith('.srt'))
    (output/'Editorial-Review.srt').write_bytes(captions.read_bytes())
    dump(output/'premiere-request.json', dict(protocol='hafez-glass-finish-v1',mode='finish_glass',
        request_id=recipe['job_id'], expected_project_path=str(project),
        expected_sequence_name=sequence_name, expected_mogrt_count=1,
        expected_sfx_count=len(plan['sfx_cues']), plan_path=str(output/'Editorial-Review.plan.json'),
        xml_path=str(output/'Editorial-Review.xml'), captions_path=str(output/'Editorial-Review.srt'),
        allow_create_project=True,save_review_project=True,export_movie=False))
    dump(output/'binding-report.json', dict(status='compiled-awaiting-native-qa', job_id=recipe['job_id'],
        original_audio_timing_and_processing_unchanged=True, local_media_urls_normalized=True,
        original_duration_frames=int(sequence.findtext('duration')),
        added_pause_frames=0, png_title_count=0, editable_text_controls=6,
        portrait_sha256=sha256(portrait), template_sha256=sha256(destination),
        app_routing_enabled=False, publication_ready=False))
    print(json.dumps(dict(status='compiled-awaiting-native-qa', plan=str(output/'Editorial-Review.plan.json')), ensure_ascii=False))


def compile_job(args):
    """Single opt-in compiler command, with bounded native wait and progress.

    Native script refuses unrelated/unsaved AE projects. Never force-close AE or
    Premiere, and never consume a Premiere queue on behalf of this command.
    """
    # Only a clean, byte-identical project created by this compiler may be
    # chained across jobs. Never close an unrelated or edited AE project.
    owner_file=ROOT/'runtime/editorial/last-project.json'
    if not getattr(args,'previous_project',None) and owner_file.is_file():
        owner=read(owner_file)
        previous=Path(owner.get('project',''))
        if previous.name=='Editorial-Source.aep' and previous.is_file() and sha256(previous)==owner.get('sha256'):
            args.previous_project=str(previous)
    prepare(args)
    output = Path(args.output).resolve()
    executable = Path(args.after_effects).resolve(strict=True)
    if executable.name.lower() != 'afterfx.com':
        raise ValueError('Expected the installed Adobe AfterFX.com')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    subprocess.Popen([str(executable), '-r', str(output/'export.jsx')],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     startupinfo=startup)
    deadline = time.monotonic()+900
    while not (output/'ae-receipt.json').exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('AE export not confirmed in 15 minutes. Inspect the preserved job; do not repeat automatically.')
        print('EDITORIAL_STAGE native-export waiting-for-AE', flush=True)
        time.sleep(10)
    finish(args)
    project=output/'Editorial-Source.aep'
    owner_file.parent.mkdir(parents=True,exist_ok=True)
    pending=owner_file.with_name('last-project.'+uuid.uuid4().hex+'.tmp')
    dump(pending,dict(project=str(project),sha256=sha256(project)))
    pending.replace(owner_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('prepare','compile'):
        prep = sub.add_parser(command)
        for name in ('plan','xml','report','cue','output'):
            prep.add_argument('--'+name, required=True)
        prep.add_argument('--preview', action='store_true', help='Render a silent six-second QA preview, never the final movie')
        if command == 'compile':
            prep.add_argument('--after-effects', default=r'C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.com')
    done = sub.add_parser('finish'); done.add_argument('--output', required=True)
    arguments = parser.parse_args()
    {'prepare':prepare,'compile':compile_job,'finish':finish}[arguments.command](arguments)



if __name__ == '__main__':
    main()
