"""Re-run the real CLI finalizer on a scoped copy of the existing speech evidence.

No new ASR/model request, original outputs are never rewritten. This is not a
fresh camera-import test; it verifies real finalize routing and frame/audio QA.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/src/hermes_video'))
from glass_pack import sha256

source=ROOT/'proof/final-editorial-spoken-trigger-20260912-03/finalize/F_Hafez_Youtube_8rdvid_C2963.edit.json'
review=source.with_name('F_Hafez_Youtube_8rdvid_C2963.resolved-review.json')
output=ROOT/'proof/glass-finalize-20260913-03'
if output.exists():raise SystemExit('Existing proof; inspect instead of rerunning')
before={str(p):sha256(p) for p in (source,review)}
manifest=json.loads(source.read_text(encoding='utf-8-sig'))
output.mkdir()
manifest['outputs']={key:str(output/Path(value).name) for key,value in manifest['outputs'].items()}
target=output/source.name
manifest['outputs']['manifest']=str(target)
target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
environment=os.environ.copy()
environment['PYTHONUTF8']='1'
environment['HERMES_PRESERVE_CAMERA1_AUDIO']='1'
command=[sys.executable,str(ROOT/'engine/src/hermes_video/studio_cli.py'),'finalize',
         '--manifest',str(target),'--review',str(review),'--style','glass','--glass-review',
         '--performance','balanced','--job-id','HS-GLASS-REVIEW-03']
with (output/'finalize.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,encoding='utf-8',errors='replace',env=environment,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for line in process.stdout:
        log.write(line);log.flush();print(line,end='',flush=True)
    result=process.wait()
unchanged=all(sha256(Path(path))==value for path,value in before.items())
receipt=dict(exit_code=result,original_inputs_unchanged=unchanged,
             source_hashes=before,asr_rerun=False,fresh_ai_review=False,
             native_premiere_import_performed=False,publication_ready=False)
(output/'cli-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if not unchanged:raise RuntimeError('Original source artifact changed')
raise SystemExit(result)
