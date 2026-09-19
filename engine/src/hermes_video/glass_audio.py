"""Local vendor audio on dedicated tracks; this module never opens voice media."""
from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from chapter_timeline import frame, xml_clock
from glass_pack import sha256


def vendor_sfx(root):
    root = Path(root)
    catalog = json.loads((root / 'config/glass-audio.json').read_text(encoding='utf-8-sig'))
    item = catalog['chapter_entry']
    relative = Path(item['path'])
    path = (root / relative).resolve(strict=True)
    if (relative.is_absolute() or not path.is_relative_to((root / 'personal-assets/Glass Audio').resolve())
            or sha256(path) != item['sha256']):
        raise ValueError('Unbound/modified curated Glass SFX')
    return path, item


def render_entry(root, output, frames, rate):
    """Render a bounded derivative, never loop/stretch audio or synthesize SFX."""
    source, item = vendor_sfx(root)
    frame(frames)
    if frames <= 0 or rate <= 0:
        raise ValueError('Invalid entry duration')
    target = Path(output)
    if target.exists():
        raise ValueError('Audio output already exists')
    duration = float(Fraction(frames) / rate)
    if duration > item['duration_seconds']:
        raise ValueError('Vendor SFX too short; no implicit loop')
    gain = item['gain_db']
    if type(gain) not in (int, float) or not math.isfinite(gain) or not -30 <= gain <= 0:
        raise ValueError('Unsafe SFX gain')
    # Smooth audible tail, no dialogue processing or automatic normalization.
    fade = min(.35, duration / 4)
    sample_count = round(Fraction(frames) / rate * 48000)
    filters = (f'atrim=duration={duration:.9f},asetpts=PTS-STARTPTS,volume={gain}dB,'
               f'afade=t=out:st={duration-fade:.9f}:d={fade:.9f}:curve=qsin,'
               f'apad=whole_len={sample_count},atrim=end_sample={sample_count}')
    result = subprocess.run([str(Path(root) / 'runtime/tools/ffmpeg.exe'), '-nostdin', '-v', 'error',
                             '-n', '-i', str(source), '-map', '0:a:0', '-map_metadata', '-1',
                             '-af', filters, '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(target)],
                            capture_output=True, text=True, timeout=60,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Vendor SFX conversion failed: ' + result.stderr[-800:])
    # PCM data duration is checked by ffprobe (Python 3.11 wave cannot read extensible PCM).
    probe = subprocess.run([str(Path(root) / 'runtime/tools/ffprobe.exe'), '-v', 'error',
                            '-show_entries', 'stream=sample_rate,channels,duration_ts,time_base',
                            '-of', 'json', str(target)], capture_output=True, text=True, timeout=15,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    streams = json.loads(probe.stdout)['streams'] if probe.returncode == 0 else []
    if (len(streams) != 1 or streams[0]['sample_rate'] != '48000' or streams[0]['channels'] != 2
            or Fraction(streams[0]['duration_ts']) * Fraction(streams[0]['time_base']) != Fraction(sample_count,48000)):
        raise ValueError('Rendered SFX sample clock mismatch')
    if sha256(source) != item['sha256']:
        raise ValueError('Vendor source changed during conversion')
    return dict(asset_path=str(target.resolve()), sha256=sha256(target),
                source_sha256=item['sha256'], source_asset=item['id'], frames=frames,
                duration=float(Fraction(sample_count,48000)), sample_rate=48000,
                channels=2, depth=24, gain_db=gain, curve='qsin',
                audition_status='requires-listening-review', music=False)


def audio_clip(cue, rate, index):
    a, b, length = (frame(cue[k]) for k in ('start_frame','end_frame','frames'))
    if b-a != length or not length:
        raise ValueError('SFX clock mismatch')
    clip = ET.Element('clipitem', id=f'glass-vendor-entry-{index}')
    path = Path(cue['asset_path']).resolve(strict=True)
    if sha256(path) != cue['sha256']:
        raise ValueError('Rendered SFX changed')
    def node(parent, name, value):
        ET.SubElement(parent, name).text = str(value)
    for name, value in (('name',path.name),('duration',length),('enabled','TRUE'),
                        ('start',a),('end',b),('in',0),('out',length)):
        node(clip,name,value)
    file = ET.SubElement(clip,'file',id=f'glass-vendor-audio-file-{index}')
    node(file,'name',path.name); node(file,'pathurl',path.as_uri()); node(file,'duration',length)
    clock = ET.SubElement(file,'rate')
    if rate.denominator == 1001:
        node(clock,'timebase',rate.numerator//1000); node(clock,'ntsc','TRUE')
    elif rate.denominator == 1:
        node(clock,'timebase',rate.numerator); node(clock,'ntsc','FALSE')
    else:
        raise ValueError('Unsupported XML audio clock')
    media=ET.SubElement(file,'media'); audio=ET.SubElement(media,'audio')
    sample=ET.SubElement(audio,'samplecharacteristics')
    node(sample,'depth',cue['depth']); node(sample,'samplerate',cue['sample_rate'])
    node(audio,'channelcount',cue['channels'])
    source=ET.SubElement(clip,'sourcetrack')
    node(source,'mediatype','audio'); node(source,'trackindex',1)
    return clip


def attach_entries(sequence, mapping, output, root):
    """One vendor cue per composite entrance on A4, not one stacked cue per layer."""
    rate=xml_clock(sequence); tracks=sequence.findall('media/audio/track')
    if len(tracks)!=5 or tracks[3].findall('clipitem') or tracks[4].findall('clipitem'):
        raise ValueError('Expected reserved clean SFX/music tracks')
    voice_before=[ET.tostring(t) for t in tracks[:2]]
    rendered={}; cues=[]
    for slot in mapping['insertions']:
        length=frame(slot['frames'])
        if length not in rendered:
            rendered[length]=render_entry(root,Path(output)/f'Glass-SaaS-entry-{length}f.wav',length,rate)
        cue={**rendered[length], 'id':slot['id']+'-vendor-entry',
             'start_frame':slot['start_frame'],'end_frame':slot['end_frame'],
             'start':float(Fraction(slot['start_frame'])/rate),'track':3,
             'sync':'composite-mogrt-first-frame', 'ducking_applied':False}
        tracks[3].append(audio_clip(cue,rate,len(cues))); cues.append(cue)
    if voice_before != [ET.tostring(t) for t in tracks[:2]]:
        raise RuntimeError('Voice tracks changed')
    return cues


def validate_entries(sequence, plan):
    """Validate real XML entries, not only planned SFX counts or metadata."""
    tracks=sequence.findall('media/audio/track'); cues=plan.get('sfx_cues',[])
    if len(tracks)!=5 or any(tracks[i].findall('clipitem') for i in (2,4)):
        raise ValueError('Unexpected reserved audio/music content')
    clips=tracks[3].findall('clipitem')
    if len(clips)!=len(cues) or (clips and tracks[3].findtext('enabled')!='TRUE'):
        raise ValueError('SFX XML count/track state mismatch')
    def signature(node):
        return (node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),
                tuple(signature(c) for c in node))
    for i,(clip,cue) in enumerate(zip(clips,cues)):
        if signature(clip)!=signature(audio_clip(cue,xml_clock(sequence),i)):
            raise ValueError('SFX XML path, timing or processing differs from plan')
