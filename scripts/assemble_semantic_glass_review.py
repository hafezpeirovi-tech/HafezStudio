"""Exercise the real automatic compiler on an existing isolated source package."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from glass_assembly import assemble_review

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('storyboard',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
report=assemble_review(manifest_path=args.source/'source.edit.json',
    xml_path=args.source/'Director-source.xml',base_plan_path=args.source/'Director-source.plan.json',
    captions_path=args.source/'Director-source.srt',requests_path=args.source/'chapter-proposals.json',
    output_dir=args.output,project_path=args.output/'Hafez-Glass-Review.prproj',root=ROOT,
    include_audio=True,storyboard=json.loads(args.storyboard.read_text(encoding='utf-8')))
print(json.dumps(dict(cards=report['native_mogrt_instances_planned']//2,
    content_cards=len(report['selected_cutaways']),blocked=report['rejected_cutaways'],
    source_preserved=report['original_files_changed'] is False),ensure_ascii=True))
