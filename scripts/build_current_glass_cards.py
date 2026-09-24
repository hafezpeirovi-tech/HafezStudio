"""Compile three source-bound vendor cards for the owner's COPIED current edit."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine/src/hermes_video'))
from glass_assembly import chapter_layers
from glass_pack import load_library, DEFAULT_PALETTE, typed_layer, validate_plan, sha256

folder=ROOT/'proof/current-project-glass-20260923-01'
snapshot=json.loads((folder/'inspect.result.json').read_text(encoding='utf-8-sig'))['result']
choices=json.loads((folder/'source-mapped-candidates.json').read_text(encoding='utf-8'))
library=load_library(ROOT)
graphics=[]
for phrase,after in [('یک سیستم',300),('ریاضی و احتمالات',370),('تصمیم گیری',400)]:
    matches=[c for c in choices if c['quote_fa']==phrase and not c['reason'] and c['start']>=after]
    if len(matches)!=1:raise ValueError('Ambiguous or unverified source quote')
    c=matches[0]
    layers=chapter_layers(library,phrase,'',ROOT)
    if phrase=='تصمیم گیری':
        asset=next(a for a in library['assets'] if a['name']=='Trendy Title 01' and a['width']>a['height'])
        # Keep Persian shaping within one editable text field, blank all vendor sample copy.
        layers[1]=typed_layer(asset,text={'Text 1':'تصمیم‌گیری','Text 2':'','Text 3':'','Text 4':''},
                              track=3,root=ROOT,font='Tahoma',sizes={'Text 1':170},values={'Accent Word':1})
        layers[1]['native_motion_scale']=65
    graphics.append(dict(id='current-glass-'+str(len(graphics)+1),start=c['start'],end=c['end'],
                         source_quote=c,layout_mode='fullscreen-voice-continuous',template_layers=layers))
plan=dict(protocol='hermes-professional-edit-v2',style_pack='glass',purpose='isolated-native-qa',
          expected_project_path=snapshot['project'],expected_sequence_id=snapshot['sequence_id'],
          sequence=snapshot['sequence'],fps=254016000000/int(snapshot['timebase']),
          video_tracks=dict(mogrt=3),graphics=graphics,palette=DEFAULT_PALETTE,
          preserve_existing_tracks=snapshot['sourceTracks'],publication_ready=False,
          fonts_provisional=True,selection_mode='source-bound-curated-current-review',
          scope='Three fullscreen vendor cards; original edit and manual graphics preserved',
          source_snapshot_sha256=sha256(folder/'inspect.result.json'))
validate_plan(plan,library,qa=True,root=ROOT)
with (folder/'current-glass.plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,ensure_ascii=False,indent=2)
request=dict(mode='apply',request_id='current-glass-apply-20260923-01',
             plan_path=str(folder/'current-glass.plan.json'),expected_project_path=snapshot['project'],
             expected_sequence_name=snapshot['sequence'],expected_sequence_id=snapshot['sequence_id'],mute_guide=False)
with (folder/'apply.request.json').open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
print(json.dumps(dict(cards=len(graphics),layers=sum(len(c['template_layers']) for c in graphics),
                     vendor_families=sorted({l['family_id'] for c in graphics for l in c['template_layers']}))))
