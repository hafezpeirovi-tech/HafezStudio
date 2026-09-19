"""Read-only source regression against the prior real two-camera cut plan."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine/src/hermes_video'))
from autocut import build_initial_timeline


def main():
    load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    original_path = ROOT/'proof/glass-fresh-asr-20260913-01/before-finalize/F_Hafez_Youtube_8rdvid_C2963.edit.json'
    detector_path = ROOT/'proof/glass-padding-probe-20260913-02/candidate-planning.json'
    original = load(original_path)
    detector = load(detector_path)
    previous_style = os.environ.get('HERMES_STYLE_PACK')
    try:
        os.environ['HERMES_STYLE_PACK'] = 'glass'
        clips, mapping, length, policy = build_initial_timeline(
            detector['detector_ranges'], original['offset_ms'], original['fps'],
            round(original['cam1_metadata']['duration']*1000))
    finally:
        if previous_style is None:
            os.environ.pop('HERMES_STYLE_PACK', None)
        else:
            os.environ['HERMES_STYLE_PACK'] = previous_style
    normalized = {key: [list(c) for c in values] for key, values in clips.items()}
    assert normalized == original['clips'], 'Original two-camera cuts changed'
    assert mapping == original['mapping'], 'Original word/source mapping changed'
    assert length == original['timeline_frames'], 'Additional duration introduced'
    assert policy == dict(id='legacy-silence-v1', head_ms=200, tail_ms=200)
    report = dict(policy=policy, source_manifest=str(original_path),
                  source_manifest_sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(),
                  detector_sha256=hashlib.sha256(detector_path.read_bytes()).hexdigest(),
                  cam1_clips=len(clips['cam1']), cam2_clips=len(clips['cam2']),
                  total_frames=length, added_frames=length-original['timeline_frames'],
                  exact_two_camera_clips_match=True, exact_source_mapping_match=True,
                  asr_rerun=False, premiere_mutated=False,
                  localized_word_repair_implemented=False, publication_ready=False)
    out = ROOT/'proof/glass-restore-pacing-20260914-01'
    out.mkdir()  # Do not overwrite a previous acceptance receipt.
    with (out/'verification.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
