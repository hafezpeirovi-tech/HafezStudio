"""Read-only explanation of actual chapter rejections; no approval or mutation."""
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine/src/hermes_video'))
from caption_provenance import verify_fresh_caption_source, variant_caption_context
from chapter_timeline import xml_clock, xml_track_clips, picture_boundaries, can_insert_at
from glass_assembly import mapped_word_spans, read_srt


def main():
    job = ROOT / 'proof/glass-fresh-asr-20260913-01'
    source = job / 'F_Hafez_Youtube_8rdvid_C2963.glass-source'
    data = json.loads((source / 'source.edit.json').read_text(encoding='utf-8-sig'))
    sequence = ET.parse(source / 'Director-source.xml').find('sequence')
    rate = xml_clock(sequence)
    context, audit = verify_fresh_caption_source(data, timebase=int(sequence.findtext('rate/timebase')),
                                               ntsc=sequence.findtext('rate/ntsc'))
    context = variant_caption_context(context, xml_track_clips(sequence.find('media/audio/track')))
    spans = mapped_word_spans(context)
    captions = read_srt(source / 'Director-source.srt')
    result = []
    for segment in (s for s in data['review_segments'] if s['id'] in (6, 27, 32)):
        owned = segment['source_word_ids']
        first = next((w for w in spans if w['id'] == owned[0]), None)
        row = dict(segment_id=segment['id'], source_start=segment['source_start'],
                   first_word=first, boundary=segment.get('caption_boundary_before_reason'),
                   owned_words=[w for w in spans if w['id'] in owned], candidates=[])
        if first:
            previous = [w for w in spans if w['end'] <= first['start']]
            points = picture_boundaries(sequence)
            if previous:
                points += [round((max(w['end'] for w in previous)+first['start'])/2*float(rate))]
            for at in sorted(set(points)):
                t = at / float(rate)
                if not 0 <= first['start']-t <= 2:
                    continue
                margin = 2 / float(rate)
                row['candidates'].append(dict(frame=at, final_director_seconds=t,
                    static_picture_safe=can_insert_at(sequence, at),
                    blocking_words=[w for w in spans if w['start']-margin < t < w['end']+margin],
                    blocking_captions=[c for c in captions if c['start'] < t < c['end']],
                    previous_word=previous[-1] if previous else None))
        result.append(row)
    report = dict(audit=audit, candidates=result, gate_changed=False, publication_ready=False)
    out = ROOT / 'proof/glass-speech-probe-20260913-01/chapter-gap-audit.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
