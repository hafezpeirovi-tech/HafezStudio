"""Read-only saved-project vs engine XML/SRT verification; writes only a new receipt.

No app control, no project edits. Native rendering and speech truth remain separate QA.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from verify_native_glass_audio import Project, TICKS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('review', type=Path)
    parser.add_argument('--receipt-name', default='saved-native-verification.json')
    args = parser.parse_args()
    folder = args.review.resolve()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]*\.json', args.receipt_name), 'Receipt must be a simple JSON basename'
    dispatch = json.loads((folder / 'native-dispatch.json').read_text())['request']
    native = json.loads((folder / 'native-receipt.json').read_text())['result']
    project_path = Path(dispatch['expected_project_path'])
    assert project_path.parent == folder and native['ok'] and native['saved']
    project = Project(project_path)
    xml = ET.parse(folder / 'Glass-Director.xml')
    sequences = project.root.findall('Sequence')
    assert len(sequences) == 1, 'Expected one independent review sequence'
    rate = xml.find('.//sequence/rate')
    assert rate.findtext('timebase') == '30' and rate.findtext('ntsc') == 'TRUE'
    ticks_per_frame = TICKS * 1001 // 30000
    counts = {}
    # Compare every imported camera/voice edit's start/end/source in/out, not just counts.
    for kind in ('Video', 'Audio'):
        tracks = xml.findall('.//sequence/media/' + kind.lower() + '/track')
        for index in range(2):
            expected = tracks[index].findall('clipitem')
            actual = project.fingerprints(kind, index)
            assert len(expected) == len(actual), (kind, index, 'count')
            for source, saved in zip(expected, actual):
                for xml_key, native_key in (('start', 'start'), ('end', 'end'), ('in', 'source_in'), ('out', 'source_out')):
                    assert int(saved[native_key]) == int(source.findtext(xml_key)) * ticks_per_frame, (kind, index, xml_key)
                assert saved['name'] == source.findtext('name'), 'Media name mismatch'
            counts[kind + str(index + 1)] = len(actual)
    plan = json.loads((folder / 'Glass-Director.premiere-plan.json').read_text(encoding='utf-8-sig'))
    for index in (2, 3):
        rows = project.fingerprints('Video', index)
        expected_layers = [(cue, layer_index) for cue in plan['graphics']
                           for layer_index, layer in enumerate(cue['template_layers'])
                           if layer['track'] == index]
        assert len(rows) == len(expected_layers), 'Saved graphics count differs from plan'
        for row, (cue, layer_index) in zip(rows, expected_layers):
            assert row['name'] == 'Hafez Glass ' + cue['id'] + ' L' + str(layer_index)
            assert row['start'] == round(cue['start'] * TICKS)
            assert abs(row['end'] - round(cue['end'] * TICKS)) <= 2
    sfx = project.fingerprints('Audio', 3)
    assert len(sfx) == len(plan['sfx_cues'])
    for row, cue in zip(sfx, plan['sfx_cues']):
        assert row['start'] == cue['start_frame'] * ticks_per_frame
        assert row['end'] == cue['end_frame'] * ticks_per_frame
        assert row['name'] == Path(cue['asset_path']).name
    assert not project.items('Audio', 2) and not project.items('Audio', 4)
    srt = (folder / 'Glass-Director.srt').read_text(encoding='utf-8-sig').strip()
    cues = re.split(r'\n\s*\n', srt)
    captions = project.root.findall('Caption')
    timeline = project.root.findall('CaptionDataClipTrackItem')
    assert cues and re.fullmatch(r'\d+', cues[0].splitlines()[0]), 'Empty or invalid SRT'
    assert len(cues) == len(captions) == len(timeline), 'Saved caption count differs from source SRT'
    def ticks(value):
        h, m, s, ms = map(int, re.split('[:,]', value))
        return ((h * 3600 + m * 60 + s) * 1000 + ms) * TICKS // 1000
    max_error = 0
    caption_timing_issues = []
    binary_payloads = {n.get('BinaryHash'): base64.b64decode(n.text)
                       for n in project.root.iter('FormattedTextData') if n.text and n.text.strip()}
    for cue, caption, item in zip(cues, captions, timeline):
        lines = cue.splitlines()
        start, end = lines[1].split(' --> ')
        for label, val in (('Start', start), ('End', end)):
            expected = ticks(val)
            assert int(caption.findtext('Time' + label)) == expected
            actual = int(item.findtext('DataClipTrackItem/ClipTrackItem/TrackItem/' + label))
            error = abs(actual - expected)
            if error > ticks_per_frame:
                caption_timing_issues.append(dict(cue=int(lines[0]), boundary=label,
                    expected_seconds=expected / TICKS, actual_seconds=actual / TICKS,
                    error_frames=error / ticks_per_frame))
            max_error = max(max_error, error)
        # Premiere stores formatted caption text in a FlatBuffer; verify the complete
        # exact UTF-8 caption is present, not merely an approximate text match.
        expected_text = '\r'.join(lines[2:]).encode('utf-8')
        for parent in (caption, item):
            blocks = [project.deref(n) for n in parent.findall('BlockVector/BlockVectorItem')]
            # Timeline copies may reference a deduplicated BinaryHash with empty text.
            payload = b''.join(binary_payloads[n.find('FormattedTextData').get('BinaryHash')] for n in blocks)
            assert expected_text in payload, 'Saved caption text differs from source SRT'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(status='saved-native-structure-verified', project=str(project_path), project_sha256=digest(project_path),
                  sequence_id=native['sequence_id'], source_edits_verified=counts, mogrt_instances=sum(len(c['template_layers']) for c in plan['graphics']),
                  native_caption_count=len(cues), source_srt_sha256=digest(folder / 'Glass-Director.srt'),
                  caption_text_exact=True, max_caption_quantization_frames=max_error / ticks_per_frame,
                  sfx=dict(track='A4', cues=len(sfx), all_frame_ranges_verified=True), source_audio_timing_exact=True,
                  png_graphic_count=0, publication_ready=False, asr_verified_by_this_script=False, full_playback_qa=False)
    report['caption_timing_issues'] = caption_timing_issues
    report['ok'] = not caption_timing_issues
    if caption_timing_issues:
        report['status'] = 'saved-native-caption-timing-review-required'
    with (folder / args.receipt_name).open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    if caption_timing_issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
