"""Build an isolated Glass review from a completed two-camera edit.

Reuses real source-word evidence. No ASR, fabricated chapter summaries, silent
style fallback, Premiere mutation, movie export or publication occurs here.
"""
from __future__ import annotations

import copy
import json
import math
import re
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from caption_provenance import verify_fresh_caption_source, variant_caption_context
from chapter_timeline import Insertion, InsertionMap, assert_source_preserved, can_insert_at, frame, picture_boundaries, rewrite_sequence, xml_clock, xml_track_clips
from glass_pack import DEFAULT_PALETTE, load_library, sha256, typed_layer, validate_plan
from glass_editorial import editorial_proposals, review_markdown
from runtime_paths import studio_root


def tokens(text):
    return re.findall(r'[^\W_]+', str(text).replace('ي','ی').replace('ك','ک'), re.UNICODE)


def read_srt(path):
    text = Path(path).read_text(encoding='utf-8-sig').replace('\r\n','\n')
    rows = []
    def time(value):
        h,m,s,ms = map(int,re.split('[:,]',value))
        if m >= 60 or s >= 60:
            raise ValueError('Malformed SRT clock')
        return h*3600+m*60+s+ms/1000
    for block in re.split(r'\n\s*\n',text.strip()):
        match = re.fullmatch(r'\d+\n(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})\n(.+)',block,re.S)
        if not match:
            raise ValueError('Unsupported/malformed SRT cue')
        a,b = time(match[1]),time(match[2])
        if b <= a:
            raise ValueError('Reversed SRT cue')
        if rows and a < rows[-1]['end']:
            raise ValueError('Overlapping or unsorted SRT cues')
        rows.append(dict(start=a,end=b,text=match[3]))
    return rows


def srt_text(cues):
    def stamp(value):
        total = round(value*1000); whole,ms=divmod(total,1000); minute,s=divmod(whole,60);h,m=divmod(minute,60)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    return '\n\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}'
                       for i,c in enumerate(cues,1))+'\n'


def mapped_word_spans(context):
    """All mapped acoustic spans block insertions, even untrusted ASR words."""
    rate = Fraction(*context['fps']); spans=[]
    previous_end = previous_source_end = 0
    if not context['keeps'] or rate <= 0:
        raise ValueError('Missing source keep clock')
    for keep in context['keeps']:
        a,b,c,d=[frame(keep[k]) for k in ('start_frame','end_frame','source_in_frame','source_out_frame')]
        if not a < b or b-a != d-c or a < previous_end or c < previous_source_end:
            raise ValueError('Overlapping, unordered or retimed source keeps')
        previous_end,previous_source_end=b,d
    ids=[w.get('source_word_id') for w in context['words']]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Missing/duplicate source word identities')
    for word in context['words']:
        sa,sb = word.get('acoustic_start'),word.get('acoustic_end')
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in (sa,sb)) or not 0 <= sa < sb:
            raise ValueError('Missing acoustic occupancy; cannot certify a gap')
        parts=[]
        for keep in context['keeps']:
            a,b,c,d=[keep[k] for k in ('start_frame','end_frame','source_in_frame','source_out_frame')]
            left,right=max(Fraction(str(sa)),Fraction(c)/rate),min(Fraction(str(sb)),Fraction(d)/rate)
            if left < right:
                parts.append((left,right,left+Fraction(a-c)/rate,right+Fraction(a-c)/rate))
        complete = bool(parts) and sum(p[1]-p[0] for p in parts) == Fraction(str(sb))-Fraction(str(sa))
        complete = complete and all(parts[i-1][3] == parts[i][2] for i in range(1,len(parts)))
        trusted = (complete and word.get('word_boundary_review_required') is False
                   and word.get('source_coverage') == 1 and 0.9 <= word.get('confidence',0) <= 1
                   and word.get('media_sha256') == context['media_sha256']
                   and word.get('source_evidence_id') == context['evidence_id']
                   and word.get('timing_origin') == 'asr-word-timestamps')
        for _,_,a,b in parts:
            spans.append(dict(start=float(a),end=float(b),id=word['source_word_id'],
                              trusted=bool(trusted),text=word.get('text','')))
    return sorted(spans,key=lambda x:(x['start'],x['end']))


def select_chapters(sequence, segments, context, captions, requests, *, max_chapters=5):
    """Requests are proposals. Quote, sentence-boundary and full gap checks decide."""
    rate=xml_clock(sequence); spans=mapped_word_spans(context)
    if not isinstance(requests,list) or any(not isinstance(r,dict) for r in requests):
        raise ValueError('Chapter requests must be a list of objects')
    source_index={s['id']:s for s in segments}; selected=[]; rejected=[]
    if len(source_index) != len(segments):
        raise ValueError('Duplicate segment identity')
    all_owned=[wid for s in segments for wid in s.get('source_word_ids',[])]
    if len(all_owned) != len(set(all_owned)):
        raise ValueError('Ambiguous source word ownership')
    possible=picture_boundaries(sequence); used=set()
    for request in requests:
        reason=None
        segment=source_index.get(request.get('segment_id')) if type(request.get('segment_id')) is int else None
        if (type(request.get('segment_id')) is not int or not isinstance(request.get('quote_fa'),str) or
                not isinstance(request.get('title_en',''),str) or
                len(request.get('title_en','')) > 80 or len(request['quote_fa']) > 100):
            rejected.append(dict(request=request,reason='invalid-title-fields'));continue
        quote=request.get('quote_fa',''); qt=tokens(quote)
        st=tokens(segment.get('source_text',segment.get('text',''))) if segment else []
        if not segment or not 1 <= len(qt) <= 6 or not any(st[i:i+len(qt)] == qt for i in range(len(st))):
            reason='title-not-a-short-literal-source-quote'
        elif '…' in quote or '...' in quote:
            reason='unfinished-title'
        elif segment.get('caption_boundary_before_reason') not in ('sentence-end','pause','stream-start'):
            reason='not-a-sentence-or-pause-boundary'
        elif segment.get('source_evidence_id') != context['evidence_id']:
            reason='unbound-segment'
        if reason:
            rejected.append(dict(request=request,reason=reason));continue
        owned=segment.get('source_word_ids',[])
        first=next((w for w in spans if owned and w['id'] == owned[0] and w['trusted']),None)
        trusted_ids={w['id'] for w in spans if w['trusted']}
        original_words={w['source_word_id']:w for w in context['words']}
        positions={w['source_word_id']:i for i,w in enumerate(context['words'])}
        literal_ok=False
        for i in range(len(owned)):
            for j in range(i+1,min(len(owned),i+6)+1):
                ids=owned[i:j]
                if (all(wid in trusted_ids for wid in ids)
                        and all(positions[ids[k]] == positions[ids[k-1]]+1 for k in range(1,len(ids)))
                        and [t for wid in ids for t in tokens(original_words[wid]['text'])] == qt):
                    literal_ok=True
        if not first or not literal_ok:
            rejected.append(dict(request=request,reason='unreliable-or-removed-source-words'));continue
        candidates=[]
        previous=[w['end'] for w in spans if w['end'] <= first['start']]
        extra=[]
        if previous:
            extra=[round((max(previous)+first['start'])/2*float(rate))]
        for at in sorted(set(possible+extra)):
            t=float(Fraction(at)/rate)
            if not 0 <= first['start']-t <= 2 or t < 25 or at in used or not can_insert_at(sequence,at):
                continue
            # No acoustic word or caption may straddle the inserted card.
            margin=2/float(rate)
            previous=[w for w in spans if w['end'] <= t]
            following=[w for w in spans if w['start'] >= t]
            if (not previous or not following or not previous[-1]['trusted'] or not following[0]['trusted']
                    or following[0]['id'] != first['id']
                    or any(w['start']-margin < t < w['end']+margin for w in spans)
                    or any(c['start'] < t < c['end'] for c in captions)):
                continue
            if any(abs(at-c['at']) < round(60*rate) for c in selected):
                continue
            candidates.append(at)
        if not candidates or len(selected) >= max_chapters:
            rejected.append(dict(request=request,reason='no-safe-shared-picture-speech-caption-gap'));continue
        at=max(candidates);used.add(at)
        selected.append(dict(id=f'glass-chapter-{segment["id"]}',at=at,quote_fa=quote,
                             # English is optional and remains proposal copy, never a new claim.
                             title_en=request.get('title_en',''),segment_id=segment['id'],
                             source_word_ids=owned,boundary_status='source-bound-machine-gap-review-required'))
    return sorted(selected,key=lambda x:x['at']),rejected


def chapter_layers(library, fa, en, root):
    def asset(family,name):
        matches=[a for a in library['assets'] if a['family']==family and a['name']==name and a['width']>a['height']]
        if len(matches)!=1:raise ValueError('Ambiguous native Glass template')
        return matches[0]
    bg=typed_layer(asset('qss-gradient','SaaS Gradient Background 01'),text={},track=2,root=root,
        color_tokens={'BG Color 01':'accent','BG Color 02':'accentLight','BG Color 03':'surface',
                      'BG Color 04':'background','BG Color 05':'background','Dust Color 01':'background'})
    title=typed_layer(asset('foslight-saas','SaaS Pack Title 01'),
                     # This template animates Text 1 then Text 2, not two static
                     # lines. Blanking phase two leaves an empty title card.
                     text={'Text 1':en or fa,'Text 2':fa},track=3,root=root,
                     fonts={'Text 1':'AbarHighFaNum-ExtraBold','Text 2':'AbarHighFaNum-SemiBold'},
                     sizes={'Text 1':140,'Text 2':100},values={'Glow Radius':200})
    title['native_motion_scale']=65
    return [bg,title]


def assemble_review(*, manifest_path, xml_path, base_plan_path, captions_path, requests_path,
                    output_dir, project_path, source_sequence=None, root=None, include_audio=False,
                    storyboard=None):
    root=Path(root or studio_root()); output=Path(output_dir).resolve()
    project=Path(project_path).resolve()
    if output.exists() or project.parent != output or project.suffix.lower()!='.prproj':
        raise ValueError('A new isolated output directory/project is required')
    paths=[Path(p) for p in (manifest_path,xml_path,base_plan_path,captions_path,requests_path)]
    before={str(p):sha256(p) for p in paths}
    manifest=json.loads(paths[0].read_text(encoding='utf-8-sig'))
    base_plan=json.loads(paths[2].read_text(encoding='utf-8-sig'))
    xml=ET.parse(paths[1]).getroot()
    name=source_sequence or base_plan['sequence']
    if base_plan.get('sequence') != name:
        raise ValueError('Base plan belongs to a different sequence')
    sequences=[s for s in xml.findall('sequence') if s.findtext('name') == name]
    if len(sequences)!=1:raise ValueError('Ambiguous/missing Director sequence')
    original=sequences[0];rate=xml_clock(original)
    if abs(float(rate)-base_plan.get('fps',0)) > 1e-7:
        raise ValueError('Base plan clock differs from XML')
    source,audit=verify_fresh_caption_source(manifest,timebase=int(original.findtext('rate/timebase')),
                                            ntsc=original.findtext('rate/ntsc'))
    if source is None:raise ValueError('Fresh content-bound speech evidence required')
    a1=original.find('media/audio/track')
    if a1 is None or a1.findtext('enabled','TRUE')!='TRUE':raise ValueError('Original A1 must be active')
    expected=Path(manifest['cam1_path']).resolve()
    for clip in a1.findall('clipitem'):
        if clip.findtext('enabled','TRUE') != 'TRUE':
            raise ValueError('A1 source clip is disabled')
        uri=clip.findtext('file/pathurl','')
        parsed=urlparse(uri);native=unquote(parsed.path)
        if re.match(r'^/[a-zA-Z]:',native):native=native[1:]
        if parsed.scheme!='file' or parsed.netloc not in ('','localhost') or Path(native).resolve()!=expected:
            raise ValueError('XML A1 is not the verified source camera')
    context=variant_caption_context(source,xml_track_clips(a1))
    captions=read_srt(paths[3]);requests=json.loads(paths[4].read_text(encoding='utf-8-sig'))
    editorial=editorial_proposals(manifest['review_segments'],requests)
    chosen,rejected=select_chapters(original,manifest['review_segments'],context,captions,editorial['chapters'])
    intro=dict(id='glass-intro',at=0,quote_fa='شروع ویدیو',title_en='HAFEZ STUDIO',
               boundary_status='before-all-source-media',copy_role='navigation-label-not-speech')
    chosen=[intro,*chosen]
    mapping=InsertionMap(int(original.findtext('duration')), [Insertion(c['id'],c['at'],round(6*rate)) for c in chosen],rate)
    seq_name='Hafez Glass — Automatic Timeline Review'
    rewritten=rewrite_sequence(original,mapping,seq_name)
    preservation=assert_source_preserved(original,rewritten,mapping)
    mapped_captions=mapping.timed_items(captions,captions=True)
    library=load_library(root);graphics=[]
    for chapter,slot in zip(chosen,mapping.payload()['insertions']):
        graphics.append(dict(id=chapter['id'],start=float(Fraction(slot['start_frame'])/rate),
                             end=float(Fraction(slot['end_frame'])/rate),chapter_source=chapter,
                             template_layers=chapter_layers(library,chapter['quote_fa'],chapter['title_en'],root)))
    from glass_semantic_cards import select_cutaways, cutaway_layers
    cutaways, blocked_cutaways = select_cutaways(storyboard or {},mapped_word_spans(context),mapping,
        occupied=[(s['start_frame'],s['end_frame']) for s in mapping.payload()['insertions']])
    for card in cutaways:
        graphics.append(dict(id=card['id'],start=float(Fraction(card['start_frame'])/rate),
            end=float(Fraction(card['end_frame'])/rate),semantic_source=card,
            layout_mode='fullscreen-voice-continuous',
            template_layers=cutaway_layers(library,card['display_text'],root)))
    graphics.sort(key=lambda c:c['start'])
    plan=dict(protocol='hermes-professional-edit-v2',style_pack='glass',purpose='isolated-native-qa',
              expected_project_path=str(project),sequence=seq_name,fps=float(rate),palette=DEFAULT_PALETTE,
              video_tracks=dict(cam1=0,cam2=1,mogrt_background=2,mogrt=3),graphics=graphics,
              camera_schedule=mapping.timed_items(base_plan.get('camera_schedule',[])),
              punch_ins=mapping.timed_items(base_plan.get('punch_ins',[])),sfx_cues=[],
              timeline_mapping=mapping.payload(),publication_ready=False,
              native_sequence_requirements={'composite_in_linear_color':False,'verification':'requires-native-check'},
              font_selection='owner-approved-ABAR-High-FaNum',
              audio_policy=dict(voice_untouched_by_ducking=True,ducking_target='background-music-only',
                                background_music_present=False,ducking_applied=False),
              review_required=['ABAR native rendering','chapter listening/semantic review','native timing/compositing QA','curated music/SFX'])
    validate_plan(plan,library,qa=True,root=root)
    after={str(p):sha256(p) for p in paths}
    if before!=after:raise RuntimeError('Input changed during assembly')
    outxml=ET.Element('xmeml',version='5');outxml.append(rewritten);ET.indent(outxml)
    report=dict(status='editable-review-package-not-publication',source_identity=audit,
                frame_preservation=preservation,insertions=mapping.payload(),
                selected_chapters=chosen,rejected_chapters=rejected,inputs_sha256=before,
                selected_cutaways=cutaways,rejected_cutaways=blocked_cutaways,
                original_subtitle_cues=len(captions),output_subtitle_cues=len(mapped_captions),
                native_mogrt_instances_planned=len(graphics)*2,native_instances_inserted=0,
                original_files_changed=False,publication_ready=False)
    output.mkdir(parents=True)
    (output/'editorial-candidates.json').write_text(json.dumps(editorial,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'EDITORIAL_REVIEW_FA.md').write_text(review_markdown(editorial,chosen[1:],rejected,manifest['review_segments']),encoding='utf-8')
    report['editorial'] = dict(chapter_proposals=len(editorial['chapters']),content_chapters=len(chosen)-1,
                              review_only_items=len(editorial['review_items']),source_rewrite=False,
                              translations_withheld=sum(bool(c.get('proposed_translation')) for c in editorial['chapters']))
    if include_audio:
        from glass_audio import attach_entries
        entrances=sorted([*mapping.payload()['insertions'],*cutaways],key=lambda c:c['start_frame'])
        plan['sfx_cues'] = attach_entries(rewritten, {'insertions':entrances}, output, root)
        plan['audio_tracks'] = dict(cam1=0, cam2=1, reserved=2, sfx=3, music=4)
        plan['audio_policy'].update(sfx_source='local-FosLight-SaaS-vendor',
                                    sfx_count=len(plan['sfx_cues']), music_status='awaiting-local-choice')
        plan['review_required'][-1] = 'vendor SFX audition; curated music choice'
        report['audio'] = plan['audio_policy']
        # The audio adapter is never allowed to change camera/dialogue identity.
        assert_source_preserved(original, rewritten, mapping)
    report['outputs_sha256'] = {}
    (output/'Glass-Director.xml').write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE xmeml>\n'+ET.tostring(outxml,encoding='utf-8'))
    (output/'Glass-Director.srt').write_text(srt_text(mapped_captions),encoding='utf-8')
    for filename,value in (('Glass-Director.premiere-plan.json',plan),('assembly-report.json',report)):
        (output/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    report['outputs_sha256'] = {name:sha256(output/name) for name in
                               ('Glass-Director.xml','Glass-Director.srt','Glass-Director.premiere-plan.json')}
    (output/'assembly-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
