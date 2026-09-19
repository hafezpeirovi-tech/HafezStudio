"""Independent checks of the measured initial-plan comparison. No UI mutation."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'engine/src/hermes_video'))
from caption_provenance import hash_media_content
from word_boundary_guard import map_source_words


def main():
    job = ROOT/'proof/glass-fresh-asr-20260913-01'
    folder = ROOT/'proof/glass-padding-probe-20260913-02'
    load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    source = load(job/'F_Hafez_Youtube_8rdvid_C2963.edit.json')
    candidate = load(folder/'candidate-planning.json')
    compare = load(folder/'comparison.json')
    words = source['source_word_evidence']['words']
    old = {w['source_word_id']: w for w in map_source_words(words, source['mapping'])}
    new = {w['source_word_id']: w for w in map_source_words(words, candidate['mapping'])}
    regressions = [key for key, word in old.items() if not word['word_boundary_review_required']
                   and (key not in new or new[key]['word_boundary_review_required'])]
    if regressions:
        raise ValueError('Previously complete word coverage regressed')
    old_frames = {i for clip in source['clips']['cam1'] for i in range(clip[2], clip[3])}
    new_frames = [i for clip in candidate['clips']['cam1'] for i in range(clip[2], clip[3])]
    if not old_frames.issubset(set(new_frames)) or len(new_frames) != len(set(new_frames)):
        raise ValueError('Lost or duplicated previously retained source frames')
    offset_frames = round(source['offset_ms']*source['fps']/1000)
    for first, second in zip(candidate['clips']['cam1'], candidate['clips']['cam2'], strict=True):
        if first[:2] != second[:2] or second[2] != max(0, first[2]-offset_frames):
            raise ValueError('Inconsistent fixed camera offset')
        if first[1]-first[0] != second[3]-second[2]:
            raise ValueError('Camera duration mismatch')
    project = job/'F_Hafez_Youtube_8rdvid_C2963.glass-review/Hafez-Glass-Review.prproj'
    expected = '8c5eea2808674f698ca630053accc2149e664d08b7967719a21817598020e67e'
    if hash_media_content(project) != expected:
        raise ValueError('Current native review differs from the saved pre-probe state')
    from autocut import build_initial_timeline
    previous_style = os.environ.get('HERMES_STYLE_PACK')
    try:
        os.environ['HERMES_STYLE_PACK'] = 'glass'
        wired, mapped, length, policy = build_initial_timeline(candidate['detector_ranges'], source['offset_ms'],
                                                             source['fps'], 1000000)
    finally:
        if previous_style is None:
            os.environ.pop('HERMES_STYLE_PACK', None)
        else:
            os.environ['HERMES_STYLE_PACK'] = previous_style
    if ({k: [list(c) for c in v] for k, v in wired.items()} != candidate['clips']
            or mapped != candidate['mapping'] or length != candidate['timeline_frames']
            or policy['id'] != compare['policy']['id']):
        raise ValueError('Actual Glass prepare selection differs from the measured candidate')
    result = dict(previous_complete_word_regressions=regressions,
                  new_partial_words_previously_absent=[key for key in compare['newly_partial'] if key not in old],
                  all_previous_source_frames_retained=True, duplicated_source_frames=0,
                  fixed_camera_offset_frames=offset_frames, current_native_project_unchanged=True,
                  source_engine_wired=True, packaged_candidate02_updated=False,
                  audio_listened=False, full_automatic_job_rerun=False, publication_ready=False)
    with (folder/'independent-verification-v2.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
