"""Compare fresh detector planning on original audio; no ASR/project mutation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine/src/hermes_video'))
from caption_provenance import hash_media_content
from speech_padding import build_padded_timeline, POLICY
from word_boundary_guard import map_source_words
from pydub import AudioSegment
from pydub.silence import detect_nonsilent


def coverage(words, mapping):
    mapped = map_source_words(words, mapping)
    partial = [dict(id=w['source_word_id'], text=w['text'], start=w['acoustic_start'], end=w['acoustic_end'],
                    coverage=w['source_coverage']) for w in mapped if w['word_boundary_review_required']]
    return dict(retained=len(mapped), full=len(mapped)-len(partial), partial=partial)


def main():
    job = ROOT/'proof/glass-fresh-asr-20260913-01'
    manifest = job/'F_Hafez_Youtube_8rdvid_C2963.edit.json'
    data = json.loads(manifest.read_text(encoding='utf-8-sig'))
    media = Path(data['cam1_path'])
    media_hash = hash_media_content(media)
    if media_hash != data['source_word_evidence']['media_identity']['sha256']:
        raise ValueError('Source hash mismatch')
    out = ROOT/'proof/glass-padding-probe-20260913-02'
    out.mkdir()  # Exclusive new proof; never overwrite an earlier run.
    write = lambda name, obj: (out/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    write('intent.json', dict(media_sha256=media_hash, policy=POLICY, applies_to_existing_project=False,
                             fresh_asr=False, publication_ready=False))
    print('PADDING_PROBE extract original audio', flush=True)
    # Exactly the prepare path: pydub's original-rate decode, then its own mono
    # conversion/resampling. FFmpeg -ac/-ar is not sample-identical to this.
    os.environ['PATH'] = str(ROOT/'runtime/tools')+os.pathsep+os.environ.get('PATH', '')
    AudioSegment.converter = str(ROOT/'runtime/tools/ffmpeg.exe')
    audio = AudioSegment.from_file(str(media)).set_channels(1).set_frame_rate(16000)
    print('PADDING_PROBE fresh silence detection; no new ASR', flush=True)
    ranges = detect_nonsilent(audio, min_silence_len=500, silence_thresh=-40)
    from autocut import build_timeline
    legacy, legacy_map, legacy_length = build_timeline(ranges, data['offset_ms'], data['fps'], len(audio))
    baseline_matches = legacy['cam1'] == [tuple(c) for c in data['clips']['cam1']]
    if not baseline_matches:
        write('baseline-mismatch.json', dict(detector_ranges=ranges, clips=legacy,
                    existing_clips=data['clips'], duration_ms=len(audio)))
        raise ValueError('Detector baseline differs; cannot attribute changes to padding alone')
    clips, mapping, length = build_padded_timeline(ranges, data['offset_ms'], data['fps'], len(audio))
    words = data['source_word_evidence']['words']
    old = coverage(words, legacy_map)
    new = coverage(words, mapping)
    old_ids = {w['id'] for w in old['partial']}
    new_ids = {w['id'] for w in new['partial']}
    # Compact previews use original voice, no gain/filter/synthetic speech.
    samples = []
    for name, acoustic_start in [('chapter', 393.9), ('feature', 442.79)]:
        sample = dict(name=name, source_word_start=acoustic_start)
        for variant, spans in [('before', legacy['cam1']), ('after', clips['cam1'])]:
            # Locate the keep that contains the tail of the clipped word.
            keep = next(c for c in spans if c[2]/data['fps'] <= acoustic_start+.6 < c[3]/data['fps'])
            start = max(keep[2]/data['fps'], acoustic_start-.6)
            end = min(keep[3]/data['fps'], acoustic_start+4.0)
            video = out/f'{name}-{variant}.mp4'
            subprocess.run([str(ROOT/'runtime/tools/ffmpeg.exe'), '-nostdin', '-v', 'error', '-n',
                '-ss', str(start), '-i', str(media), '-t', str(end-start), '-map', '0:v:0', '-map', '0:a:0',
                '-vf', 'scale=960:-2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(video)], check=True, timeout=90)
            sample[variant] = dict(path=str(video), start=start, end=end, keep=list(keep))
        samples.append(sample)
        print('PADDING_PROBE preview '+name, flush=True)
    if hash_media_content(media) != media_hash:
        raise ValueError('Source changed during probe')
    report = dict(policy=POLICY, source_sha256=media_hash, baseline_matches=True, source_unchanged=True,
                  fresh_asr=False, changed_project=False, publication_ready=False,
                  before=dict(clips=len(legacy['cam1']), seconds=legacy_length/data['fps'], coverage=old),
                  after=dict(clips=len(clips['cam1']), seconds=length/data['fps'], coverage=new),
                  previously_partial_now_complete=sorted(old_ids-new_ids), newly_partial=sorted(new_ids-old_ids),
                  previews=samples, authority='machine-timestamp-coverage-not-listening-approval')
    write('comparison.json', report)
    write('candidate-planning.json', dict(clips=clips, mapping=mapping, timeline_frames=length, detector_ranges=ranges))
    print(json.dumps(dict(before_partial=len(old_ids), after_partial=len(new_ids),
            complete_gains=len(old_ids-new_ids), newly_partial=len(new_ids-old_ids),
            before_seconds=report['before']['seconds'], after_seconds=report['after']['seconds']), indent=2), flush=True)


if __name__ == '__main__':
    main()
