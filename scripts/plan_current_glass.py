"""Source-bound Glass cutaway planning for a copied, manually edited sequence.

Read-only native snapshot is the timing authority, not an old generated XML.
This script plans; it never claims that a plan is a rendered or saved MOGRT.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine/src/hermes_video'))
from glass_assembly import chapter_layers
from glass_pack import load_library, DEFAULT_PALETTE, validate_plan

TICKS = 254016000000


def normalize(text):
    return re.findall(r'[^\W_]+', text.replace('ي', 'ی').replace('ك', 'ک'), re.UNICODE)


def mapped_words(words, clips):
    result = []
    for word in words:
        left, right = word['acoustic_start'], word['acoustic_end']
        parts = []
        for clip in clips:
            a, b, c, d = [int(clip[k]) / TICKS for k in ('startTicks', 'endTicks', 'inTicks', 'outTicks')]
            if abs((b-a)-(d-c)) > 1/TICKS:
                raise ValueError('Retimed media requires a separate mapping')
            l, r = max(c, left), min(d, right)
            if l < r:
                parts.append((l, r, a+l-c, a+r-c))
        complete = bool(parts) and abs(sum(r-l for l, r, _, _ in parts)-(right-left)) < 1e-6
        continuous = all(abs(parts[i-1][3]-parts[i][2]) < 1e-6 for i in range(1, len(parts)))
        if complete and continuous:
            result.append(dict(word, timeline_start=parts[0][2], timeline_end=parts[-1][3]))
    return result


def main():
    folder = ROOT / 'proof/current-project-glass-20260923-01'
    snapshot = json.loads((folder / 'inspect.result.json').read_text(encoding='utf-8-sig'))['result']
    manifest = json.loads((ROOT / 'proof/c3009-vendor-glass-20260923-01/F_Hafez_Youtube_9thvid_C3009.edit.json').read_text(encoding='utf-8'))
    clips = next(t['clips'] for t in snapshot['sourceTracks'] if t['kind']=='video' and t['index']==0)
    if any(Path(c['mediaPath']) != Path(manifest['cam1_path']) for c in clips):
        raise ValueError('Different camera source')
    original = manifest['source_word_evidence']['words']
    mapped = {w['word_id']: w for w in mapped_words(original, clips)}
    tokens = [(token, i) for i, word in enumerate(original) for token in normalize(word['text'])]
    phrases = ['قانون احتمالات', 'نداشتن دیتا', 'احساسات', 'سیستم ندارند',
               'یک سیستم', 'تصمیم گیری', 'آیا سیستم داری', 'ریاضی و احتمالات']
    existing = [c for t in snapshot['sourceTracks'] if t['kind']=='video' and t['index']>=2 for c in t['clips']]
    fps = TICKS / int(snapshot['timebase'])
    candidates = []
    for phrase in phrases:
        wanted = normalize(phrase)
        for start in range(len(tokens)-len(wanted)+1):
            if [t for t, _ in tokens[start:start+len(wanted)]] != wanted:
                continue
            ids = sorted(set(i for _, i in tokens[start:start+len(wanted)]))
            words = [original[i] for i in ids]
            reason = None
            if any(w['word_id'] not in mapped or w['confidence'] < .9 for w in words):
                reason = 'incomplete-or-low-confidence-source'
            retained = [mapped[w['word_id']] for w in words if w['word_id'] in mapped]
            at = round(retained[0]['timeline_start']*fps)/fps if retained else None
            end = at + 180/fps if at is not None else None
            if at is not None and any(at < int(c['endTicks'])/TICKS and end > int(c['startTicks'])/TICKS for c in existing):
                reason = 'owner-graphic-overlap'
            candidates.append(dict(quote_fa=phrase, start=at, end=end, reason=reason,
                                   source_start=words[0]['acoustic_start'], source_end=words[-1]['acoustic_end'],
                                   source_word_ids=[w['word_id'] for w in words],
                                   confidence=min(w['confidence'] for w in words)))
    target = folder/'source-mapped-candidates.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(candidates, stream, ensure_ascii=False, indent=2)
    print(json.dumps(candidates, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
