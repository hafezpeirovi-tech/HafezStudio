"""Re-run the actual role compiler on cached, verified speech (no ASR rerun).

Creates a separate review; never changes the source or dispatches Premiere.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from glass_assembly import assemble_review
from glass_finalize import validate_review_outputs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--editorial',action='store_true',help='Compile eligible current-media portrait cards through AE')
    args=parser.parse_args()
    source=args.source.resolve(strict=True);out=args.output.resolve()
    manifest=json.loads((source/'source.edit.json').read_text(encoding='utf-8-sig'))
    storyboard=json.loads((source/'semantic-storyboard.json').read_text(encoding='utf-8-sig'))
    report=assemble_review(manifest_path=source/'source.edit.json',xml_path=source/'Director-source.xml',
        base_plan_path=source/'Director-source.plan.json',captions_path=source/'Director-source.srt',
        requests_path=source/'chapter-proposals.json',output_dir=out,
        project_path=out/'Hafez-Motion-Roles-Review.prproj',root=ROOT,include_audio=True,
        storyboard=storyboard,motion_roles=True)
    (out/'YouTube-review.md').write_text('Native motion role candidate: manual review required.\n',encoding='utf-8')
    manifest.update(style_pack='glass',glass_review=True,publication_ready=False,outputs=dict(
        xml=str(out/'Glass-Director.xml'),professional_plan=str(out/'Glass-Director.premiere-plan.json'),
        tight_srt=str(out/'Glass-Director.srt'),audit=str(out/'assembly-report.json'),
        youtube=str(out/'YouTube-review.md')))
    if args.editorial:
        from editorial_pipeline import compile_review
        plan=json.loads(Path(manifest['outputs']['professional_plan']).read_text(encoding='utf-8'))
        if any(c.get('layout_mode')=='fullscreen-voice-continuous' for c in plan['graphics']):
            manifest['outputs']=compile_review(manifest['outputs'],root=ROOT)
    summary=validate_review_outputs(manifest,root=ROOT)
    for name,data in [('motion-review.edit.json',manifest),('engine-validation.json',summary)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(roles=summary['motionRoleCounts'],mogrts=summary['editableMogrtLayers'],
        rejected_numbered=[r for r in report['rejected_cutaways'] if 'source_word_id' in r],
        project=summary['expectedProject']),ensure_ascii=True))

if __name__=='__main__':main()
