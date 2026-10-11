"""Separate native template QA. All copy is explicitly demo, not ASR evidence."""
import argparse
import copy
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from glass_assembly import chapter_layers
from glass_motion_roles import role_layers, PROTOCOL
from glass_pack import load_library, validate_plan, sha256, palette_values
from editorial_contract import PALETTE

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    out=args.output.resolve()
    if out.exists(): raise ValueError('Use a fresh isolated QA folder')
    source=ROOT/'proof/glass-pack-20260913-01/Glass-Pack-Native-QA.xml'
    tree=ET.parse(source)
    seq='Hafez-FX - Motion Roles - DEMO ONLY'
    tree.getroot().find('sequence/name').text=seq
    # The shared native finisher requires the same V1/V2 + graphics and
    # dialogue/muted-camera2/music/SFX layout as production. Only normalize
    # empty tracks in this throwaway fixture; never mutate source clips.
    for kind,count in (('video',4),('audio',5)):
        section=tree.getroot().find('sequence/media/'+kind)
        tracks=section.findall('track')
        for track in tracks[count:]:
            if track.findall('clipitem'): raise ValueError('Refuse to drop QA media')
            section.remove(track)
        while len(section.findall('track')) < count:
            track=ET.SubElement(section,'track')
            ET.SubElement(track,'enabled').text='TRUE'
            ET.SubElement(track,'locked').text='FALSE'
    tree.getroot().findall('sequence/media/audio/track')[1].find('enabled').text='FALSE'
    library=load_library(ROOT)
    cards=[dict(id='demo-chapter',start=0,end=6,motion_role='chapter',
                template_layers=chapter_layers(library,'فقط استراتژی کافی نیست','HAFEZ-FX',ROOT))]
    for cue_id,start,role,label,text in [
        ('demo-numbered',6,'numbered-point','تست اول','فقط به سود نگاه نکن'),
        ('demo-emphasis',20,'emphasis','','مدیریت ریسک')]:
        card=dict(id=cue_id,start=start,end=start+6,motion_role=role,label=label,display_text=text)
        card['template_layers']=role_layers(library,card,ROOT)
        cards.append(card)
    plan=dict(protocol='hermes-professional-edit-v2',style_pack='glass',purpose='isolated-native-qa',
        motion_role_policy=PROTOCOL,expected_project_path=str(out/'Hafez-Motion-Roles-Demo.prproj'),
        sequence=seq,fps=30,palette=copy.deepcopy(PALETTE),graphics=cards,sfx_cues=[],
        video_tracks=dict(cam1=0,cam2=1,mogrt_background=2,mogrt=3),
        publication_ready=False,speech_verified=False,
        notes=['DEMO ONLY: user example copy, not an automatic edit or a spoken quotation.'])
    colors=palette_values(PALETTE)
    for cue in cards:
        for layer in cue['template_layers']:
            layer['palette_id']=PALETTE['id']
            for c in layer['typed_controls']:
                if c['kind']=='color': c['value']=colors[c['paletteToken']]
    validate_plan(plan,library,qa=True,root=ROOT)
    out.mkdir(parents=True)
    xml=out/'Demo.xml'; plan_path=out/'Demo.plan.json'; srt=out/'Demo.srt'
    tree.write(xml,encoding='utf-8',xml_declaration=True)
    srt.write_text('1\n00:00:00,000 --> 00:00:28,000\nآزمون قالب — متن نمایشی\n',encoding='utf-8')
    def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    dump(plan_path,plan)
    dump(out/'assembly-report.json',dict(demo_only=True,publication_ready=False,
        source_xml_sha256=sha256(source),outputs_sha256={p.name:sha256(p) for p in (xml,plan_path,srt)}))
    dump(out/'engine-validation.json',dict(style='glass',publicationReady=False,pngTimelineAssets=0,
        xml=str(xml),plan=str(plan_path),srt=str(srt),expectedProject=plan['expected_project_path'],
        editableMogrtLayers=sum(len(c['template_layers']) for c in cards),demoOnly=True))
    print('Separate 28-second template gallery prepared; no native mutations or release approval.')

if __name__=='__main__':main()
