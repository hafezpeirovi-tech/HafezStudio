"""Finish review sidecars and independently validate an isolated test package."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from glass_finalize import validate_review_outputs

parser=argparse.ArgumentParser()
parser.add_argument('package',type=Path)
args=parser.parse_args()
p=args.package.resolve()
plan=json.loads((p/'Glass-Director.premiere-plan.json').read_text(encoding='utf-8'))
sidecar=p/'YouTube-review.md'
if not sidecar.exists():
    lines=['# Engine-only review; no Premiere import or publication approval',
           '', 'Voice-continuous content cutaways (not additional pauses):', '']
    for cue in plan['graphics']:
        evidence=cue.get('semantic_source')
        if evidence:
            lines.append(f"- {cue['start']:.3f}s: {evidence['display_text']}")
    sidecar.write_text('\n'.join(lines)+'\n',encoding='utf-8')
manifest={'outputs':{k:str(p/v) for k,v in dict(xml='Glass-Director.xml',
    professional_plan='Glass-Director.premiere-plan.json',tight_srt='Glass-Director.srt',
    audit='assembly-report.json',youtube='YouTube-review.md').items()}}
result=validate_review_outputs(manifest,root=ROOT)
result['nativeExecuted']=False
(p/'engine-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
