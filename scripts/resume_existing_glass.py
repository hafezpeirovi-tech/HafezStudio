"""Finalize an existing analysis into a NEW Glass job, preserving original inputs.

Explicit saved review required: no fresh transcription or model review is requested.
Native Premiere dispatch is separate, through the regular desktop broker.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('review', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source, review, output = (p.resolve() for p in (args.manifest, args.review, args.output))
    root = Path(__file__).resolve().parents[1]
    if output.exists() or not output.is_relative_to(root / 'proof'):
        raise ValueError('A new isolated HafezStudio proof directory is required')
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    saved_review = json.loads(review.read_text(encoding='utf-8-sig'))
    if not isinstance(saved_review, dict) or not {'segments', 'edits', 'markers'} <= saved_review.keys():
        raise ValueError('A completed explicit review is required; no inference fallback')
    if not data.get('source_word_evidence', {}).get('evidence_id'):
        raise ValueError('Missing original speech evidence')
    before = {str(p): digest(p) for p in (source, review)}
    output.mkdir(parents=True)
    backup = output / 'original-inputs'
    backup.mkdir()
    for p in (source, review):
        shutil.copy2(p, backup / p.name)
    data['outputs'] = {k: str(output / Path(v).name) for k, v in data['outputs'].items()}
    target = output / source.name
    data['outputs']['manifest'] = str(target)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    command = [sys.executable, '-X', 'utf8', str(root / 'engine/src/hermes_video/studio_cli.py'),
               'finalize', '--manifest', str(target), '--review', str(backup / review.name),
               '--style', 'glass', '--glass-review', '--performance', 'balanced',
               '--job-id', output.name]
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1',
                       HERMES_PRESERVE_CAMERA1_AUDIO='1')
    with (output / 'finalize.log').open('x', encoding='utf-8') as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                 env=environment, cwd=root,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    unchanged = all(digest(Path(p)) == sha for p, sha in before.items())
    receipt = dict(exit_code=process.returncode, original_inputs_unchanged=unchanged,
                   source_hashes=before, asr_rerun=False, supplied_existing_review=True,
                   native_dispatch=False, publication_ready=False)
    (output / 'resume-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))
    if not unchanged:
        raise RuntimeError('Original inputs changed')
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
