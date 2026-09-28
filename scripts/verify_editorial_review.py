"""Record a recomputed validation summary for an isolated compiled review."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from glass_finalize import validate_review_outputs

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True)
    folder=parser.parse_args().folder.resolve(strict=True)
    outputs={key:str(folder/name) for key,name in dict(xml='Glass-Director.xml',
        professional_plan='Glass-Director.premiere-plan.json',tight_srt='Glass-Director.srt',
        audit='assembly-report.json',youtube='YouTube-review.md').items()}
    summary=validate_review_outputs(dict(outputs=outputs))
    with (folder/'engine-validation.json').open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False))
