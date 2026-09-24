"""Run local models on identical source transcript, without editing Premiere."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from glass_storyboard import review_with_local_ai, review_meaning

parser = argparse.ArgumentParser()
parser.add_argument('manifest', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--model', action='append', required=True)
parser.add_argument('--limit', type=int, default=12)
parser.add_argument('--meaning-review', action='store_true')
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
segments = manifest['review_segments'][:args.limit]
if not segments:
    raise SystemExit('No original review segments')
args.output.mkdir(parents=True, exist_ok=True)
for model in args.model:
    name = model.replace(':','-').replace('/','-')
    started = time.monotonic()
    report = review_with_local_ai(segments, model=model,
        checkpoint=args.output/(name+'.checkpoint.json'))
    if args.meaning_review:
        report = review_meaning(report,segments,model=model)
    report['elapsed_seconds'] = round(time.monotonic()-started,2)
    report['evaluated_segments'] = len(segments)
    (args.output/(name+'.report.json')).write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(model=model,seconds=report['elapsed_seconds'],
        accepted=len(report['proposals']),rejected=len(report['rejected']),
        failures=report['model_failures']),ensure_ascii=True),flush=True)
