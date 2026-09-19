"""Build an isolated native Glass reel; original movie/project are not edited.

The English/Persian labels and 83% chart are explicitly demo copy, not an
assertion about the speaker's content. Native QA does not approve editorial use.
"""
import copy
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
from glass_pack import DEFAULT_PALETTE, load_library, typed_layer, validate_plan

OUT = ROOT / "proof/glass-pack-20260913-01"
SEQ = "Glass Pack - Native Review - 20260913"
PROJECT = OUT / "Hafez-Glass-Pack-Review-20260913.prproj"


def write_json(name, payload):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)


def main():
    OUT.mkdir(exist_ok=True)
    library = load_library(ROOT)
    def asset(family, name, horizontal=False):
        candidates = [a for a in library["assets"] if a["family"] == family and a["name"] == name
                      and (not horizontal or a["width"] > a["height"])]
        assert len(candidates) == 1, (family, name)
        return candidates[0]
    def layer(family, name, text, track=3, **kwargs):
        return typed_layer(asset(family, name, family == "qss-gradient"), text=text, track=track, root=ROOT, **kwargs)
    background = lambda: layer("qss-gradient", "SaaS Gradient Background 01", {}, track=2,
        color_tokens={"BG Color 01":"accent", "BG Color 02":"accentLight", "BG Color 03":"surface",
                      "BG Color 04":"background", "BG Color 05":"background", "Dust Color 01":"background"})
    title = layer("foslight-saas", "SaaS Pack Title 01", {"Text 1":"SMART WORKFLOW", "Text 2":"گردش کار هوشمند"},
                  sizes={"Text 1":140,"Text 2":100}, values={"Glow Radius":200})
    words = layer("foslight-trendy", "Trendy Title 01", {"Text 1":"FOCUS", "Text 2":"ON", "Text 3":"WHAT", "Text 4":"MATTERS"},
                  sizes={"Text 1":180,"Text 2":180,"Text 3":180,"Text 4":180})
    data = layer("motionstate-liquid", "01 Progress Bar", {
        "Text 01 (Edit Font Only)":"83%", "Text 02":"پیشرفت پروژه", "Text 03":"دادهٔ نمایشی برای آزمون قالب",
        "Text 04":"این عدد از ویدیو استخراج نشده است", "Text 05":"DEMO"},
        values={"Animation Duration (0 - 60 sec)":8,"Progress Bar Value (0 - 100 %)":83,
                "Glass Darkness (0 - 100 %)":55},
        color_tokens={"BG Color 01":"background","BG Color 02":"surface"})
    plan = {"protocol":"hermes-professional-edit-v2", "style_pack":"glass", "purpose":"isolated-native-qa",
            "expected_project_path":str(PROJECT), "sequence":SEQ, "fps":30,
            "palette":copy.deepcopy(DEFAULT_PALETTE), "video_tracks":{"mogrt":3,"png_guide":1},
            "graphics":[
                {"id":"glass-chapter-qa","start":0,"end":6,"template_layers":[background(),title]},
                {"id":"glass-words-qa","start":14,"end":20,"template_layers":[background(),words]},
                {"id":"glass-data-qa","start":20,"end":28,"template_layers":[data]}],
            "publication_ready":False,"speech_verified":False,"notes":["QA-only demo labels, not generated speech summaries.",
              "The source excerpt plays between cards, so cards never conceal the speaker.",
              "No background music supplied; no music downloaded or invented."]}
    validate_plan(plan, library, qa=True)
    old_xml = ROOT / "proof/subscribe-horizontal-20260913-01/native-qa/Hafez-Horizontal-Native-QA.xml"
    source = ET.parse(old_xml).getroot().find("sequence")
    output = ET.Element("xmeml",version="4"); seq = ET.SubElement(output,"sequence",id="hafez-glass-qa-20260913")
    ET.SubElement(seq,"name").text=SEQ; ET.SubElement(seq,"duration").text="840"
    seq.append(copy.deepcopy(source.find("rate"))); media=ET.SubElement(seq,"media")
    for kind in ("video","audio"):
        section=ET.SubElement(media,kind); section.append(copy.deepcopy(source.find("media/"+kind+"/format")))
        track=ET.SubElement(section,"track")
        # First eight seconds of the already source-mapped isolated CAM2/A1 QA,
        # shifted intact after the six-second chapter, never generated stills.
        for original in source.findall("media/"+kind+"/track/clipitem"):
            a,b=[int(original.findtext(k)) for k in ("start","end")]
            if a>=240: continue
            end=min(b,240); clip=copy.deepcopy(original); clip.set("id","glass-"+clip.get("id"))
            for key,value in (("start",a+180),("end",end+180),("out",int(original.findtext("in"))+end-a),("duration",end-a)):
                clip.find(key).text=str(value)
            track.append(clip)
        ET.SubElement(track,"enabled").text="TRUE";ET.SubElement(track,"locked").text="FALSE"
        if kind == "video":
            for _ in range(4):
                empty=ET.SubElement(section,"track");ET.SubElement(empty,"enabled").text="TRUE";ET.SubElement(empty,"locked").text="FALSE"
    ET.indent(output)
    with (OUT/"Glass-Pack-Native-QA.xml").open("xb") as stream:
        stream.write(b'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE xmeml>\n'+ET.tostring(output,encoding="utf-8"))
    write_json("baseline.plan.json",plan)
    write_json("import.request.json",{"protocol":"hafez-native-import-v1","mode":"import_xml",
        "request_id":"glass-import-20260913-01","expected_project_path":str(PROJECT),
        "xml_path":str(OUT/"Glass-Pack-Native-QA.xml"),"bin_name":"Glass Pack Review",
        "expected_sequence_names":[SEQ],"expected_sequence_name":SEQ})
    for mode in ("apply","inspect"):
        write_json(mode+".request.json",{"mode":mode,"request_id":"glass-"+mode+"-20260913-01",
            "plan_path":str(OUT/"baseline.plan.json"),"expected_project_path":str(PROJECT),
            "expected_sequence_name":SEQ,"mute_guide":False})
    print(json.dumps({"sequence":SEQ,"seconds":28,"mogrtLayers":5,"publicationReady":False}))


if __name__ == "__main__":
    main()
