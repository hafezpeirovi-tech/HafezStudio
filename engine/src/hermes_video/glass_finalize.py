"""Opt-in Glass review finalizer. No legacy graphics, native UI or publication."""
from __future__ import annotations

import copy
import json
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from caption_provenance import variant_caption_context
from caption_timing import build_timeline_word_cues
from chapter_timeline import Insertion, InsertionMap, assert_source_preserved, xml_clock
from glass_assembly import assemble_review, read_srt, srt_text
from glass_pack import load_library, sha256, validate_plan
from runtime_paths import studio_root


def chapter_proposals(markers):
    """Keep AI chapter suggestions as untrusted proposals, never auto-trusted copy."""
    proposals=[]; seen=set()
    for marker in markers:
        if not isinstance(marker,dict) or str(marker.get('type','')).upper()!='CHAPTER':
            continue
        sid=marker.get('segment_id')
        if type(sid) is not int or sid in seen:
            continue
        seen.add(sid)
        proposals.append(dict(segment_id=sid,quote_fa=marker.get('quote_fa',marker.get('headline_fa','')),
                              title_en=marker.get('title_en','')))
    return proposals


def finalize_review(*, manifest_path, manifest, director_variant, events, camera_schedule,
                    markers, caption_source, sequence_builder, root=None):
    """Use existing cuts/camera logic but bypass all legacy graphic/render functions."""
    root=Path(root or studio_root())
    original=Path(manifest_path).resolve()
    base=Path(manifest['outputs']['xml']).with_suffix('')
    stage=Path(str(base)+'.glass-source').resolve()
    output=Path(str(base)+'.glass-review').resolve()
    if stage.exists() or output.exists():
        raise ValueError('Glass review already exists; use a new job, never overwrite a review')
    if stage.parent != original.parent or output.parent != original.parent:
        raise ValueError('Glass review outputs must stay beside their job manifest')
    if caption_source is None:
        raise ValueError('Fresh word evidence required for Glass review')
    audio_keeps=[clip[:4] for clip in director_variant['clips']['cam1']]
    cues, timing_audit=build_timeline_word_cues(variant_caption_context(caption_source,audio_keeps))
    if not cues:
        raise ValueError('No retained word captions for Glass')
    stage.mkdir()
    staged=copy.deepcopy(manifest)
    staged['outputs']={'xml':str(stage/'Director-source.xml')}
    # Original camera audio is used: master_audio=None and graphics=[].
    lines, backend=sequence_builder(staged,'glass-source',director_variant,events,[],None,[])
    xml_path=stage/'Director-source.xml'
    xml_path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<xmeml version="5">\n'+'\n'.join(lines)+'\n</xmeml>',encoding='utf-8')
    source_manifest=stage/'source.edit.json'
    source_manifest.write_text(json.dumps(staged,ensure_ascii=False,indent=2),encoding='utf-8')
    base_plan=stage/'Director-source.plan.json'
    base_plan.write_text(json.dumps(dict(sequence=director_variant['name'],fps=manifest['fps'],
                                        camera_schedule=camera_schedule,punch_ins=events),ensure_ascii=False,indent=2),encoding='utf-8')
    captions=stage/'Director-source.srt'
    captions.write_text(srt_text(cues),encoding='utf-8')
    requests=stage/'chapter-proposals.json'
    from glass_storyboard import review_with_local_ai, review_meaning
    storyboard=review_with_local_ai(manifest['review_segments'],checkpoint=stage/'semantic-checkpoint.json')
    storyboard=review_meaning(storyboard,manifest['review_segments'])
    (stage/'semantic-storyboard.json').write_text(json.dumps(storyboard,ensure_ascii=False,indent=2),encoding='utf-8')
    requests.write_text(json.dumps(chapter_proposals(markers),ensure_ascii=False,indent=2),encoding='utf-8')
    report=assemble_review(manifest_path=source_manifest,xml_path=xml_path,base_plan_path=base_plan,
                           captions_path=captions,requests_path=requests,output_dir=output,
                           project_path=output/'Hafez-Glass-Review.prproj',root=root,include_audio=True,
                           storyboard=storyboard)
    # Fresh chapter timestamps only. Never copy stale timestamps from the old cut.
    chapter_lines=[]
    rate=Fraction(*report['insertions']['fps'])
    for chapter,slot in zip(report['selected_chapters'],report['insertions']['insertions']):
        seconds=int(Fraction(slot['start_frame'])/rate)
        minutes,sec=divmod(seconds,60)
        chapter_lines.append(f'{minutes:02}:{sec:02} {chapter["quote_fa"]}')
    youtube=output/'YouTube-review.md'
    youtube.write_text('# پیش‌نویس زمان فصل‌ها — نیازمند بازبینی\n\n'
                       'این فایل تأیید آماده‌بودن برای انتشار نیست. عنوان‌های محتوایی هنوز تأیید نشده‌اند.\n\n'
                       +'\n'.join(chapter_lines)+'\n',encoding='utf-8')
    outputs=dict(xml=str(output/'Glass-Director.xml'),professional_plan=str(output/'Glass-Director.premiere-plan.json'),
                 srt=str(output/'Glass-Director.srt'),
                 tight_srt=str(output/'Glass-Director.srt'),safe_srt=str(output/'Glass-Director.srt'),
                 youtube=str(youtube),audit=str(output/'assembly-report.json'))
    review_manifest=copy.deepcopy(manifest)
    review_manifest.update(style_pack='glass',publication_ready=False,glass_review=True)
    # Do not advertise stale legacy graphics, captions or edit-note paths.
    review_manifest['outputs']=outputs
    review_manifest['glass_source_manifest']=str(source_manifest)
    review_manifest['glass_caption_timing']=timing_audit
    review_manifest['glass_camera_backend']=backend
    review_manifest['glass_storyboard_path']=str(stage/'semantic-storyboard.json')
    review_manifest['glass_storyboard_counts']={
        'source_bound_proposals':len(storyboard['proposals']),
        'rejected':len(storyboard['rejected']),
        'compiled_cutaways':len(report['selected_cutaways']),
        'blocked_cutaways':len(report['rejected_cutaways']),
        'nonchapter_layout_pending':sum(p['role'] not in ('chapter','important-text') for p in storyboard['proposals'])}
    # Commit the routing manifest last. Failure leaves the old manifest intact.
    temporary=original.with_name(original.name+'.glass-new')
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(review_manifest,stream,ensure_ascii=False,indent=2)
    temporary.replace(original)
    return outputs['xml'],outputs['tight_srt']


def validate_review_outputs(manifest, *, root=None):
    """Recompute source preservation; reports/labels alone cannot certify the output."""
    root=Path(root or studio_root()); outputs=manifest['outputs']
    xml_path=Path(outputs['xml']); plan_path=Path(outputs['professional_plan'])
    srt_path=Path(outputs['tight_srt']); report_path=Path(outputs['audit'])
    plan=json.loads(plan_path.read_text(encoding='utf-8-sig'))
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    for path in (xml_path,plan_path,srt_path):
        if report.get('outputs_sha256',{}).get(path.name)!=sha256(path):
            raise ValueError('Stale Glass review artifact: '+path.name)
    validate_plan(plan,load_library(root),qa=True,root=root)
    sequences=ET.parse(xml_path).getroot().findall('sequence')
    if len(sequences)!=1 or sequences[0].findtext('name')!=plan['sequence']:
        raise ValueError('Expected one exact Glass review sequence')
    seq=sequences[0]; payload=plan['timeline_mapping']; rate=xml_clock(seq)
    if payload['fps']!=[rate.numerator,rate.denominator]:
        raise ValueError('Glass frame clock mismatch')
    mapping=InsertionMap(payload['source_duration_frames'],
                         [Insertion(i['id'],i['source_frame'],i['frames']) for i in payload['insertions']],rate)
    if mapping.payload()!=payload or int(seq.findtext('duration'))!=mapping.output_duration:
        raise ValueError('Glass insertion mapping mismatch')
    source_xml=[]
    for path,digest in report['inputs_sha256'].items():
        if sha256(Path(path))!=digest:
            raise ValueError('Glass source evidence changed')
        if Path(path).suffix.lower()=='.xml':source_xml.append(path)
    if len(source_xml)!=1:
        raise ValueError('Ambiguous source XML evidence')
    original_sequences=ET.parse(source_xml[0]).getroot().findall('sequence')
    matches=[]
    for original in original_sequences:
        try:
            assert_source_preserved(original,seq,mapping); matches.append(original)
        except (ValueError,IndexError,AttributeError):
            continue
    if len(matches)!=1:raise ValueError('Source frame preservation not independently verified')
    captions=read_srt(srt_path)
    ranges=[(s['start_frame'],s['end_frame']) for s in payload['insertions']]
    graphics=[(round(Fraction(str(c['start']))*rate),round(Fraction(str(c['end']))*rate))
              for c in plan['graphics']]
    chapter_graphics=[g for g,c in zip(graphics,plan['graphics']) if c.get('layout_mode')!='fullscreen-voice-continuous']
    if chapter_graphics!=ranges or any(sorted(layer['track'] for layer in c['template_layers'])!=[2,3]
                              for c in plan['graphics']):
        raise ValueError('Glass cards do not occupy exact standalone slots')
    for i,(a,b) in enumerate(graphics):
        if not 0<=a<b<=mapping.output_duration or (i and a<graphics[i-1][1]):
            raise ValueError('Overlapping/out-of-range Glass cards')
        card=plan['graphics'][i]
        if card.get('layout_mode')=='fullscreen-voice-continuous':
            evidence=card.get('semantic_source',{})
            if (evidence.get('start_frame'),evidence.get('end_frame'))!=(a,b) or not evidence.get('source_word_ids'):
                raise ValueError('Unbound semantic card')
    for cue in captions:
        a,b=round(Fraction(str(cue['start']))*rate),round(Fraction(str(cue['end']))*rate)
        if not 0<=a<b<=mapping.output_duration or any(a<d and b>c for c,d in ranges):
            raise ValueError('Caption intersects chapter or leaves sequence')
    # The camera schedule and fullscreen cards together cover every output frame.
    coverage=[*ranges]
    for shot in plan['camera_schedule']:
        if shot['camera'] not in ('cam1','cam2'):raise ValueError('Unknown camera')
        coverage.append((round(Fraction(str(shot['start']))*rate),round(Fraction(str(shot['end']))*rate)))
    last=0
    for a,b in sorted(coverage):
        if a!=last or b<=a:raise ValueError('Glass camera/chapter coverage gap or overlap')
        last=b
    if last!=mapping.output_duration:raise ValueError('Incomplete Glass camera coverage')
    cues=plan.get('sfx_cues',[])
    if [(c['start_frame'],c['end_frame']) for c in cues]!=graphics:
        raise ValueError('Missing/duplicate composite entry SFX')
    for cue in cues:
        if sha256(Path(cue['asset_path']))!=cue['sha256'] or (cue['start_frame'],cue['end_frame']) not in graphics:
            raise ValueError('SFX identity/sync mismatch')
    from glass_audio import validate_entries
    validate_entries(seq,plan)
    if not Path(outputs.get('youtube','')).is_file():
        raise ValueError('YouTube review sidecar missing')
    return dict(mappedWords=len(manifest.get('mapped_words',[])),subtitleCues=len(captions),
                graphics=len(plan['graphics']),plannedGraphics=len(plan['graphics']),blockedGraphics=0,
                editableMogrtLayers=sum(len(c['template_layers']) for c in plan['graphics']),pngTimelineAssets=0,
                sfxCues=len(plan.get('sfx_cues',[])),musicPresent=False,publicationReady=False,
                premiereFinisherRequired=True,style='glass',reviewStatus='isolated-native-review-required',
                cameraShots=len(plan['camera_schedule']),punchIns=len(plan['punch_ins']),
                xml=str(xml_path),plan=str(plan_path),srt=str(srt_path),youtube=outputs.get('youtube'),
                expectedProject=plan['expected_project_path'],
                finisher='Create the exact separate review project, import XML, bind its sequence ID and apply the typed Glass plan. Never export automatically.')
