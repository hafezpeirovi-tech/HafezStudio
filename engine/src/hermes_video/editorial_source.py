"""Source-bound Editorial Glass preparation; never mutates the production edit.

This adapter consumes an existing reviewed semantic cue. It does not invent a
headline, extend the timeline, replace dialogue, or approve the ASR itself.
"""
from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse, quote
from xml.etree import ElementTree as ET

from chapter_timeline import xml_clock
from glass_semantic_cards import display_copy


def split_heading(value: str) -> tuple[str, str]:
    words = value.split()
    if not 1 <= len(words) <= 6 or len(value) > 90 or '…' in value:
        raise ValueError('Heading needs a short reviewed phrase, not a paragraph/placeholder')
    if len(words) <= 2:
        return ' '.join(words), ''
    split = min(range(1, len(words)), key=lambda i: abs(len(' '.join(words[:i])) - len(' '.join(words[i:]))))
    return ' '.join(words[:split]), ' '.join(words[split:])


def local_media_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != 'file' or parsed.netloc not in ('', 'localhost'):
        raise ValueError('Only explicit local media is supported')
    value = unquote(parsed.path)
    if len(value) >= 3 and value[0] == '/' and value[2] == ':':
        value = value[1:]
    return Path(value)


def premiere_media_url(url: str) -> str:
    """Premiere FCP XML requires the localhost form for Windows drive paths."""
    path = local_media_path(url)
    value = str(path).replace('\\', '/')
    if not (len(value) > 2 and value[1:3] == ':/'):
        raise ValueError('Expected an absolute Windows drive media path')
    return 'file://localhost/'+quote(value, safe='/')


def media_slices(sequence: ET.Element, start: int, end: int) -> list[dict]:
    """Resolve the PRIMARY camera from A1's unretimed edit, across every cut.

    Using A1 is intentional: this portrait module chooses the primary talking
    head, not the alternate-camera or punch-in appearance. No audio is rendered
    into the MOGRT. Existing sequence audio continues untouched beneath it.
    """
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError('Invalid requested frame range')
    rate = xml_clock(sequence)
    tracks = sequence.findall('media/audio/track')
    if not tracks or tracks[0].findtext('enabled', 'TRUE') != 'TRUE':
        raise ValueError('Enabled primary dialogue track required')
    track = tracks[0]
    if track.findall('transitionitem'):
        raise ValueError('Transition-aware mapping not implemented')
    files = {}
    for item in sequence.iter('file'):
        if item.find('pathurl') is not None:
            key = item.get('id')
            if key in files and files[key].findtext('pathurl') != item.findtext('pathurl'):
                raise ValueError('Conflicting media identity')
            files[key] = item
    pieces, cursor = [], start
    for clip in sorted(track.findall('clipitem'), key=lambda c: int(c.findtext('start', '-1'))):
        a, b, c, d = [int(clip.findtext(k, '-1')) for k in ('start', 'end', 'in', 'out')]
        if b <= start or a >= end:
            continue
        if clip.findtext('enabled', 'TRUE') != 'TRUE' or a < 0 or c < 0 or b-a != d-c or clip.findall('filter'):
            raise ValueError('Disabled, filtered or retimed dialogue clip cannot bind a portrait')
        left, right = max(a, start), min(b, end)
        if left != cursor:
            raise ValueError('Gap/overlap in primary camera mapping')
        reference = clip.find('file')
        media = files.get(reference.get('id')) if reference is not None else None
        if media is None or media.find('media/video') is None or xml_clock(media) != rate:
            raise ValueError('Missing video media or unsupported mixed-rate mapping')
        pieces.append(dict(path=str(local_media_path(media.findtext('pathurl', ''))),
                           source_in_frame=c+left-a, frames=right-left,
                           timeline_start_frame=left))
        cursor = right
    if cursor != end:
        raise ValueError('Uncovered primary camera interval')
    return pieces


def prepare_recipe(plan: dict, sequence: ET.Element, cue_id: str) -> dict:
    if plan.get('protocol') != 'hermes-professional-edit-v2' or plan.get('style_pack') != 'glass':
        raise ValueError('Expected an existing Glass edit plan')
    if plan.get('sequence') != sequence.findtext('name'):
        raise ValueError('Plan/XML sequence mismatch')
    rate = xml_clock(sequence)
    if not math.isclose(float(plan.get('fps', 0)), float(rate), abs_tol=1e-7):
        raise ValueError('Plan/XML clock mismatch')
    matches = [g for g in plan.get('graphics', []) if g.get('id') == cue_id]
    if len(matches) != 1:
        raise ValueError('Missing/duplicate cue id')
    cue = matches[0]
    evidence = cue.get('semantic_source') or {}
    proposal = evidence.get('semantic_source') or {}
    checks = proposal.get('meaning_review') or {}
    if not all(checks.get(k) is True for k in ('standalone', 'faithful', 'important', 'spelling_clean')):
        raise ValueError('This module needs an already reviewed semantic phrase')
    word_ids = evidence.get('source_word_ids')
    if not word_ids or len(set(word_ids)) != len(word_ids) or not set(word_ids).issubset(proposal.get('source_word_ids', [])):
        raise ValueError('Missing source-word linkage')
    quote = evidence.get('quote_fa', '')
    display, edits = display_copy(quote)
    if quote != proposal.get('quote_fa') or display != evidence.get('display_text') or edits != evidence.get('copy_edits'):
        raise ValueError('Unrecorded text rewrite')
    start, end = evidence.get('start_frame'), evidence.get('end_frame')
    if any(type(x) is not int for x in (start, end)) or not 0 <= start < end <= int(sequence.findtext('duration', '0')):
        raise ValueError('Invalid cue frames')
    if any(type(cue.get(k)) not in (int, float) or not math.isfinite(cue[k]) for k in ('start', 'end')):
        raise ValueError('Invalid cue seconds')
    if round(cue['start']*rate) != start or round(cue['end']*rate) != end:
        raise ValueError('Cue time/evidence mismatch')
    # v4 has six-second protected animation. Do not silently freeze/stretch a
    # different duration until a separate responsive-duration native test exists.
    if abs(Fraction(end-start)/rate - 6) > 1/rate:
        raise ValueError('Only the verified six-second animation duration is supported')
    line1, line2 = split_heading(display)
    return dict(protocol='hafez-editorial-source-v1', cue_id=cue_id,
                start_frame=start, end_frame=end, fps=[rate.numerator, rate.denominator],
                duration=float(Fraction(end-start)/rate), source_word_ids=word_ids,
                quote_fa=quote, display_text=display, copy_edits=edits,
                title_lines=[line1, line2], source_role='primary-camera-from-A1-edit',
                slices=media_slices(sequence, start, end),
                inserted_pause_frames=0, dialogue_processing=False,
                publication_ready=False, native_qa_required=True)
