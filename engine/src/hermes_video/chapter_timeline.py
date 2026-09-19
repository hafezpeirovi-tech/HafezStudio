"""Integer-frame insertions shared by picture, dialogue, captions and markers.

This module never cuts source material, changes source speed, invents silence
evidence or approves a graphic. Intervals are half open: an insertion at b is
AFTER a clip ending at b and BEFORE a clip starting at b.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any
from xml.etree import ElementTree as ET


def frame(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Expected a non-negative integer frame")
    return value


def seconds(value: Any) -> Fraction:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid timeline seconds")
    return Fraction(str(value))


@dataclass(frozen=True)
class Insertion:
    id: str
    at: int
    length: int


class InsertionMap:
    def __init__(self, duration: int, insertions: list[Insertion], rate: Fraction):
        self.duration = frame(duration)
        if not self.duration or not isinstance(rate, Fraction) or rate <= 0:
            raise ValueError("Missing duration/exact frame clock")
        self.rate = rate
        self.insertions = tuple(sorted(insertions, key=lambda i: i.at))
        ids, positions = set(), set()
        for i in self.insertions:
            frame(i.at); frame(i.length)
            if (not isinstance(i.id, str) or not i.id or i.id in ids or i.at in positions
                    or not i.length or i.at >= duration):
                raise ValueError("Duplicate or invalid insertion")
            ids.add(i.id); positions.add(i.at)
        self.output_duration = duration + sum(i.length for i in self.insertions)

    def point(self, value: int, *, side: str = "after") -> int:
        frame(value)
        if value > self.duration or side not in {"before", "after"}:
            raise ValueError("Out-of-range/ambiguous point")
        return value + sum(i.length for i in self.insertions
                           if i.at < value or (side == "after" and i.at == value))

    def spans(self, start: int, end: int) -> list[tuple[int, int, int, int]]:
        frame(start); frame(end)
        if not start < end <= self.duration:
            raise ValueError("Invalid half-open interval")
        boundaries = [start] + [i.at for i in self.insertions if start < i.at < end] + [end]
        return [(a, b, self.point(a), self.point(b, side="before"))
                for a, b in zip(boundaries, boundaries[1:])]

    def clip(self, raw: list[int]) -> list[list[int]]:
        if len(raw) not in (4, 5):
            raise ValueError("Unsupported clip tuple")
        a, b, c, d = [frame(v) for v in raw[:4]]
        if b-a != d-c:
            raise ValueError("Retimed source is not supported")
        return [[na, nb, c+oa-a, c+ob-a, *raw[4:]] for oa, ob, na, nb in self.spans(a, b)]

    def timed_items(self, rows: list[dict], *, captions: bool = False) -> list[dict]:
        result = []
        for row in rows:
            a = round(seconds(row['start']) * self.rate)
            b = round(seconds(row.get('end', row['start'])) * self.rate)
            b = min(self.duration, max(a+1, b))
            pieces = self.spans(a, b)
            if captions and len(pieces) != 1:
                raise ValueError("A chapter would interrupt a caption/sentence")
            for index, (_, _, na, nb) in enumerate(pieces):
                item = copy.deepcopy(row)
                item.update(start=float(Fraction(na)/self.rate), end=float(Fraction(nb)/self.rate))
                if len(pieces) > 1:
                    item['chapter_fragment'] = index
                result.append(item)
        return result

    def payload(self) -> dict:
        return {'protocol': 'hafez-chapter-insertions-v1',
                'fps': [self.rate.numerator, self.rate.denominator],
                'source_duration_frames': self.duration, 'output_duration_frames': self.output_duration,
                'insertions': [dict(id=i.id, source_frame=i.at,
                                    start_frame=self.point(i.at, side='before'),
                                    end_frame=self.point(i.at), frames=i.length) for i in self.insertions]}


def xml_clock(sequence: ET.Element) -> Fraction:
    base = int(sequence.findtext('rate/timebase', '0'))
    ntsc = sequence.findtext('rate/ntsc')
    if base <= 0 or ntsc not in ('TRUE', 'FALSE'):
        raise ValueError('Missing declared XML clock')
    return Fraction(base*1000, 1001) if ntsc == 'TRUE' else Fraction(base)


def xml_track_clips(track: ET.Element) -> list[list[int]]:
    if track.findall('transitionitem'):
        raise ValueError('Transitions require a separate timing adapter')
    return [[int(c.findtext(k, '-1')) for k in ('start', 'end', 'in', 'out')]
            for c in track.findall('clipitem')]


def picture_boundaries(sequence: ET.Element) -> list[int]:
    """Only shared picture boundaries: never rebase local animation keyframes."""
    clips = [c for track in sequence.findall('media/video/track')[:2] for c in xml_track_clips(track)]
    points = {p for c in clips for p in c[:2]}
    return sorted(p for p in points if not any(c[0] < p < c[1] for c in clips))


def static_motion_only(clip: ET.Element) -> bool:
    for f in clip.findall('filter'):
        if f.findtext('effect/effectid') != 'basic' or f.findtext('start') != '-1' or f.findtext('end') != '-1':
            return False
        for parameter in f.findall('effect/parameter'):
            if parameter.findtext('parameterid') not in ('scale','center','anchorpoint'):
                return False
            keys=parameter.findall('keyframe')
            if any(k.find('value') is None or k.find('when') is None for k in keys):
                return False
            values=[tuple((v.tag,(v.text or '').strip()) for v in k.find('value').iter())
                    for k in keys]
            if not values or any(value != values[0] for value in values):
                return False
    return True


def can_insert_at(sequence: ET.Element, at: int) -> bool:
    for track in sequence.findall('media/video/track')[:2]:
        for clip in track.findall('clipitem'):
            a,b=int(clip.findtext('start','-1')),int(clip.findtext('end','-1'))
            if a < at < b and not static_motion_only(clip):
                return False
    return True


def rewrite_sequence(sequence: ET.Element, mapping: InsertionMap, name: str) -> ET.Element:
    if xml_clock(sequence) != mapping.rate or int(sequence.findtext('duration', '-1')) != mapping.duration:
        raise ValueError('Sequence identity/clock mismatch')
    output = copy.deepcopy(sequence)
    output.set('id', 'hafez-glass-review')
    output.find('name').text = name
    output.find('duration').text = str(mapping.output_duration)
    if any(not can_insert_at(sequence,i.at) for i in mapping.insertions):
        raise ValueError('Chapter inside an animated picture clip')
    # Only this NEW sequence drops legacy graphic/SFX tracks. Input is immutable.
    # A1/A2 are remapped, including disabled angle audio; no voice filter added.
    for kind in ('video', 'audio'):
        section = output.find('media/'+kind)
        if section is None:
            raise ValueError('Missing camera media section')
        tracks = section.findall('track')
        if len(tracks) < 2:
            raise ValueError('Expected the two-camera export contract')
        for extra in tracks[2:]:
            if kind == 'video' and extra.findall('clipitem'):
                raise ValueError('Unexpected existing graphic media; cannot silently replace')
            section.remove(extra)
        for ti, track in enumerate(tracks[:2]):
            if track.findall('transitionitem'):
                raise ValueError('Unsupported source transition')
            original_clips = track.findall('clipitem')
            for ci, clip in enumerate(original_clips):
                if clip.findall('link') or clip.findall('timeRemap'):
                    raise ValueError('Linked/retimed input requires explicit adapter')
                raw = [int(clip.findtext(k, '-1')) for k in ('start', 'end', 'in', 'out')]
                pieces = mapping.clip(raw)
                if kind == 'audio' and clip.findall('filter'):
                    raise ValueError('Processed dialogue not supported by raw-audio contract')
                if len(pieces) > 1 and not static_motion_only(clip):
                    raise ValueError('Cannot split local animated filters')
                track.remove(clip)
                for pi, (a, b, c, d) in enumerate(pieces):
                    item = copy.deepcopy(clip)
                    item.set('id', f'glass-{kind}-{ti}-{ci}-{pi}')
                    for key, value in (('start',a),('end',b),('in',c),('out',d),('duration',b-a)):
                        item.find(key).text = str(value)
                    if len(pieces) > 1:
                        # Only equal-valued Basic Motion keys reach here. One
                        # constant local key preserves that exact static pose.
                        for parameter in item.findall('filter/effect/parameter'):
                            keys=parameter.findall('keyframe')
                            for extra in keys[1:]:parameter.remove(extra)
                            if keys:keys[0].find('when').text='0'
                    track.append(item)
        # V3 background, V4 text. A3 reserved, A4 SFX, A5 music.
        for _ in range((4 if kind == 'video' else 5)-2):
            empty = ET.SubElement(section, 'track')
            ET.SubElement(empty, 'enabled').text = 'TRUE'
            ET.SubElement(empty, 'locked').text = 'FALSE'
    for marker in output.findall('marker'):
        a, b = int(marker.findtext('in', '-1')), int(marker.findtext('out', '-1'))
        marker.find('in').text = str(mapping.point(a))
        if b >= 0:
            marker.find('out').text = str(mapping.point(b, side='before') if b > a else mapping.point(a))
    for insertion in mapping.payload()['insertions']:
        marker = ET.SubElement(output, 'marker')
        ET.SubElement(marker, 'name').text = 'GLASS CHAPTER — REVIEW'
        ET.SubElement(marker, 'in').text = str(insertion['start_frame'])
        ET.SubElement(marker, 'out').text = str(insertion['end_frame'])
        ET.SubElement(marker, 'comment').text = insertion['id']
    return output


def assert_source_preserved(original: ET.Element, rewritten: ET.Element, mapping: InsertionMap) -> dict:
    """Independent per-frame source identity, not only equal durations/counts."""
    checked = {}
    for kind in ('video', 'audio'):
        left, right = original.findall(f'media/{kind}/track'), rewritten.findall(f'media/{kind}/track')
        for ti in range(2):
            expected, actual = {}, {}
            for target, track, shifted in ((expected,left[ti],True),(actual,right[ti],False)):
                for clip in track.findall('clipitem'):
                    a,b,c,d = [int(clip.findtext(k,'-1')) for k in ('start','end','in','out')]
                    if b-a != d-c or b <= a:
                        raise ValueError('Retimed/invalid source clip')
                    identity = clip.findtext('file/pathurl') or clip.find('file').get('id')
                    enabled = (track.findtext('enabled','TRUE'),clip.findtext('enabled','TRUE'))
                    for offset in range(b-a):
                        t = mapping.point(a+offset) if shifted else a+offset
                        if t in target:
                            raise ValueError('Overlapping source frames')
                        target[t] = (identity, c+offset, enabled)
            if expected != actual:
                raise ValueError(f'{kind} track {ti+1} source frame identity changed')
            checked[f'{kind}{ti+1}'] = len(actual)
    return {'status':'exact-per-frame-source-preserved','tracks':checked,
            'source_speed_changed':False,'voice_processing_added':False}
