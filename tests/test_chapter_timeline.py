import copy
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/src/hermes_video'))
from chapter_timeline import Insertion, InsertionMap, rewrite_sequence, assert_source_preserved, static_motion_only


def sequence():
    seq = ET.fromstring('<sequence><name>Base</name><duration>60</duration><rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate><media><video/><audio/></media></sequence>')
    for kind in ('video', 'audio'):
        for track_id in range(2):
            track=ET.SubElement(seq.find('media/'+kind),'track')
            ET.SubElement(track,'enabled').text='TRUE' if track_id == 0 else 'FALSE'
            for index,(a,b) in enumerate(((0,30),(30,60))):
                clip=ET.SubElement(track,'clipitem',id=f'{kind}{track_id}{index}')
                for k,v in dict(name='source.mp4',start=a,end=b,**{'in':100+a,'out':100+b},duration=b-a,enabled='TRUE').items():
                    ET.SubElement(clip,k).text=str(v)
                file=ET.SubElement(clip,'file',id=f'file-{track_id}')
                ET.SubElement(file,'pathurl').text=f'file:///camera{track_id}.mp4'
    return seq


class ChapterTimelineTests(unittest.TestCase):
    def setUp(self):
        self.m=InsertionMap(60,[Insertion('intro',0,15),Insertion('next',30,20)],Fraction(30000,1001))

    def test_boundary_has_distinct_before_and_after(self):
        self.assertEqual(self.m.point(30,side='before'),45)
        self.assertEqual(self.m.point(30),65)
        self.assertEqual(self.m.spans(0,30),[(0,30,15,45)])
        self.assertEqual(self.m.spans(30,60),[(30,60,65,95)])

    def test_splitting_preserves_every_source_frame(self):
        self.assertEqual(self.m.clip([10,50,110,150]),[[25,45,110,130],[65,85,130,150]])

    def test_xml_all_four_source_tracks_preserved(self):
        source=sequence(); before=ET.tostring(source)
        output=rewrite_sequence(source,self.m,'Glass')
        report=assert_source_preserved(source,output,self.m)
        self.assertEqual(report['tracks'],dict(video1=60,video2=60,audio1=60,audio2=60))
        self.assertEqual(ET.tostring(source),before)
        self.assertEqual(output.findtext('duration'),'95')
        self.assertEqual(len(output.findall('media/video/track')),4)
        self.assertEqual(len(output.findall('media/audio/track')),5)

    def test_caption_at_boundary_not_stretched_across_card(self):
        rate=float(self.m.rate)
        rows=[dict(start=0,end=30/rate,text='الف'),dict(start=30/rate,end=60/rate,text='ب')]
        mapped=self.m.timed_items(rows,captions=True)
        self.assertAlmostEqual(mapped[0]['end'],45/rate)
        self.assertAlmostEqual(mapped[1]['start'],65/rate)
        with self.assertRaisesRegex(ValueError,'interrupt'):
            self.m.timed_items([dict(start=0,end=2,text='Do not interrupt')],captions=True)

    def test_ambiguous_invalid_and_retimed_values_rejected(self):
        for items in ([Insertion('a',0,10),Insertion('a',30,10)],
                      [Insertion('a',0,10),Insertion('b',0,10)],
                      [Insertion('a',60,10)],[Insertion('a',True,10)],[Insertion('a',0,0)]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                InsertionMap(60,items,Fraction(30))
        with self.assertRaises(ValueError):self.m.clip([0,30,0,40])

    def test_source_mutation_detected_not_only_duration(self):
        source=sequence(); output=rewrite_sequence(source,self.m,'Glass')
        first=output.find('media/audio/track/clipitem')
        first.find('in').text='101'; first.find('out').text='131'
        with self.assertRaisesRegex(ValueError,'source frame identity'):
            assert_source_preserved(source,output,self.m)

    def test_animated_clip_split_and_processed_voice_rejected(self):
        animated=sequence()
        ET.SubElement(animated.find('media/video/track/clipitem'),'filter')
        with self.assertRaisesRegex(ValueError,'animated picture'):
            rewrite_sequence(animated,InsertionMap(60,[Insertion('a',20,10)],self.m.rate),'Glass')
        source=sequence(); ET.SubElement(source.find('media/audio/track/clipitem'),'filter')
        with self.assertRaisesRegex(ValueError,'Processed dialogue'):
            rewrite_sequence(source,self.m,'Glass')

    def test_static_picture_can_split_without_losing_source(self):
        source=sequence()
        mapping=InsertionMap(60,[Insertion('a',20,10)],self.m.rate)
        output=rewrite_sequence(source,mapping,'Glass')
        self.assertEqual(assert_source_preserved(source,output,mapping)['tracks']['video1'],60)

    def test_malformed_static_keyframes_are_not_silently_dropped(self):
        clip=ET.fromstring('<clipitem><filter><start>-1</start><end>-1</end><effect><effectid>basic</effectid><parameter><parameterid>scale</parameterid><keyframe><when>0</when><value>100</value></keyframe><keyframe><when>10</when></keyframe></parameter></effect></filter></clipitem>')
        self.assertFalse(static_motion_only(clip))
        ET.SubElement(clip.findall('.//keyframe')[1],'value').text='100'
        self.assertTrue(static_motion_only(clip))


if __name__=='__main__':unittest.main()
