"""Read-only comparison of the saved Premiere review to its pre-audio backup.

Never writes a Premiere project or controls Premiere. Writes one verification receipt.
"""
import gzip
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BEFORE=ROOT/'backups/glass-finalize-audio-20260913-01/Hafez-Glass-Timeline-Review-before-audio.prproj'
AFTER=ROOT/'proof/glass-timeline-20260913-03/Hafez-Glass-Timeline-Review.prproj'
TICKS=254016000000


class Project:
    def __init__(self,path):
        self.root=ET.fromstring(gzip.decompress(path.read_bytes()))
        self.ids={n.get('ObjectID'):n for n in self.root if n.get('ObjectID')}
        self.uids={n.get('ObjectUID'):n for n in self.root if n.get('ObjectUID')}

    def deref(self,node):
        if node is None:return None
        if node.get('ObjectRef'):return self.ids[node.get('ObjectRef')]
        if node.get('ObjectURef'):return self.uids[node.get('ObjectURef')]
        return node

    def canonical(self,node,seen=()):
        if node is None:return None
        reference=node.get('ObjectRef') or node.get('ObjectURef')
        if reference:
            if reference in seen:raise ValueError('Unexpected component reference cycle')
            return self.canonical(self.deref(node),seen+(reference,))
        return (node.tag,tuple(sorted((k,v) for k,v in node.attrib.items() if k not in ('ObjectID','ObjectUID'))),
                (node.text or '').strip(),tuple(self.canonical(c,seen) for c in node))

    def track(self,kind,index):
        nodes=[n for n in self.root.findall(kind+'ClipTrack') if n.findtext('ClipTrack/Track/Index')==str(index)]
        if len(nodes)!=1:raise ValueError('Expected exact native track')
        return nodes[0]

    def items(self,kind,index):
        return [self.deref(n) for n in self.track(kind,index).findall('ClipTrack/ClipItems/TrackItems/TrackItem')]

    def clip(self,item):
        sub=self.deref(item.find('ClipTrackItem/SubClip'))
        clip=self.deref(sub.find('Clip'))
        return sub,clip

    def fingerprints(self,kind,index):
        result=[]
        for item in self.items(kind,index):
            sub,clip=self.clip(item)
            result.append(dict(id=item.findtext('ID'),name=sub.findtext('Name'),
                start=int(item.findtext('ClipTrackItem/TrackItem/Start','0')),
                end=int(item.findtext('ClipTrackItem/TrackItem/End','0')),
                source_id=clip.findtext('Clip/ClipID'),source_in=clip.findtext('Clip/InPoint'),source_out=clip.findtext('Clip/OutPoint'),
                effects=self.canonical(item.find('ClipTrackItem/ComponentOwner/Components'))))
        return result


def main():
    before=Project(BEFORE);after=Project(AFTER)
    counts={}
    for kind,number in (('Audio',2),('Video',4)):
        for index in range(number):
            old=before.fingerprints(kind,index);new=after.fingerprints(kind,index)
            if old!=new:raise ValueError(f'Native {kind}{index+1} changed')
            counts[f'{kind}{index+1}']=len(new)
            if kind=='Audio':
                for tag in ('Components','Panner'):
                    route='AudioTrack/'+('ComponentOwner/' if tag=='Components' else '')+tag
                    if before.canonical(before.track(kind,index).find(route))!=after.canonical(after.track(kind,index).find(route)):
                        raise ValueError('Native voice track processing changed')
    if before.items('Audio',3):raise ValueError('Pre-audio A4 was not empty')
    for index in (2,4):
        if after.items('Audio',index):raise ValueError('Unexpected A3/A5 audio')
    items=after.items('Audio',3)
    if len(items)!=1:raise ValueError('Expected one native SFX')
    sfx=after.fingerprints('Audio',3)[0]
    if (sfx['name']!='Glass-SaaS-entry-180f.wav' or sfx['start']!=0 or sfx['end']!=1525620096000
            or sfx['source_in']!='0' or sfx['source_out']!='1525620096000'):
        raise ValueError('Native SFX source or 180-frame sync mismatch')
    chain=after.deref(items[0].find('ClipTrackItem/ComponentOwner/Components'))
    if chain.findall('ComponentChain/Components/Component'):
        raise ValueError('Unexpected SFX processing in Premiere')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt=dict(status='saved-native-audio-placement-verified',project=str(AFTER),project_sha256=digest(AFTER),
                 backup_sha256=digest(BEFORE),unchanged_native_tracks=counts,
                 sfx=dict(track='A4',start_frame=0,end_frame=180,seconds=sfx['end']/TICKS,
                          asset='Glass-SaaS-entry-180f.wav',placement='manual-native-QA'),
                 full_playback_qa=False,fonts_provisional=True,music_present=False,
                 new_cli_xml_imported=False,publication_ready=False)
    out=AFTER.with_name('native-audio-verification.json')
    with out.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
