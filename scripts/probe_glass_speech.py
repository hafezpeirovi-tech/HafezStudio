"""Bounded, offline ASR comparison; never changes evidence/captions/Premiere.

Alternative decodes are hypotheses, not listening approval. No auto-selection.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine/src/hermes_video'))
from caption_provenance import hash_media_content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'proof'):
        raise ValueError('A new proof directory inside HafezStudio is required')
    data = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    media = Path(data['cam1_path'])
    original_hash = hash_media_content(media)
    if original_hash != data['source_word_evidence']['media_identity']['sha256']:
        raise ValueError('Camera differs from the fresh evidence')
    # Bounded source-clock windows selected from the recorded failed cases.
    windows = [('opening', 62, 78), ('concept', 96, 112), ('chapter', 392, 402)]
    model_path = ROOT / 'runtime/models/whisper-fa-ct2'
    ffmpeg = ROOT / 'runtime/tools/ffmpeg.exe'
    if not (model_path / 'model.bin').is_file() or not ffmpeg.is_file():
        raise ValueError('Local model/tools missing; no downloads permitted')
    output.mkdir()
    write = lambda name, value: (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    write('intent.json', dict(media=str(media), media_sha256=original_hash,
          evidence_id=data['source_word_evidence']['evidence_id'], windows=windows,
          model=str(model_path), offline=True, mutates_evidence=False,
          auto_select=False, publication_ready=False))
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import numpy as np
    from faster_whisper import WhisperModel
    samples = {}
    for name, start, end in windows:
        wav = output / (name + '.wav')
        subprocess.run([str(ffmpeg), '-nostdin', '-v', 'error', '-n', '-ss', str(start),
                        '-i', str(media), '-t', str(end-start), '-vn', '-ac', '1',
                        '-ar', '16000', '-c:a', 'pcm_s16le', str(wav)], check=True, timeout=45)
        import wave
        with wave.open(str(wav), 'rb') as stream:
            raw = stream.readframes(stream.getnframes())
        samples[name] = np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768
    rows = []
    for compute in ('int8', 'float32'):
        model = WhisperModel(str(model_path), device='cpu', compute_type=compute,
                             cpu_threads=min(8, os.cpu_count() or 1), num_workers=1,
                             local_files_only=True)
        for name, start, end in windows:
            then = time.monotonic()
            print(f'PROBE {compute} {name} {start}-{end}', flush=True)
            iterator, _ = model.transcribe(samples[name], language='fa', beam_size=5,
                    temperature=0.0, condition_on_previous_text=False, word_timestamps=True,
                    vad_filter=False, initial_prompt=None, hotwords=None)
            decoded = [dict(text=s.text, start=start+s.start, end=start+s.end,
                            avg_logprob=s.avg_logprob, words=[dict(text=w.word,
                            start=start+w.start, end=start+w.end, confidence=w.probability)
                            for w in s.words or []]) for s in iterator]
            baseline = [dict(text=w['text'], start=w['acoustic_start'], end=w['acoustic_end'],
                             confidence=w['confidence']) for w in data['mapped_words']
                        if start <= (w['acoustic_start']+w['acoustic_end'])/2 < end]
            row = dict(window=name, source_start=start, source_end=end, compute_type=compute,
                       seconds=round(time.monotonic()-then, 2), baseline=baseline,
                       hypothesis=decoded, authority='machine-comparison-only',
                       accepted_as_source=False, publication_ready=False)
            rows.append(row)
            write(f'{name}-{compute}.json', row)
            print(json.dumps(dict(window=name, compute=compute, seconds=row['seconds'],
                                  text=' '.join(s['text'] for s in decoded)), ensure_ascii=False), flush=True)
        del model
        gc.collect()
    if hash_media_content(media) != original_hash:
        raise ValueError('Camera changed during comparison')
    write('comparison.json', dict(results=rows, source_unchanged=True,
                                 automatic_correction=False, publication_ready=False))
    print('COMPARISON_COMPLETE no source/caption/project changes', flush=True)


if __name__ == '__main__':
    main()
