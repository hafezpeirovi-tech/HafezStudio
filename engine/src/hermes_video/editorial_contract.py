"""Job-local compiled MOGRT identity, distinct from the static vendor inventory."""
from pathlib import Path
import json
from xml.etree import ElementTree as ET

from editorial_source import prepare_recipe
from glass_pack import read_mogrt, sha256

PALETTE = dict(id='editorial-smoked-sage', background='#0A1110', surface='#335944',
               accent='#80E9B0', accentLight='#B8C9BF', text='#F3F7F4', muted='#B8C9BF',
               glassDeep='#192E2E', glassShade='#0C1712', glassEdge='#101E19', panel='#14291F')
COLOR_TOKENS = {'Background Color 1':'background', 'Background Color 2':'surface',
                'Background Color 3':'glassDeep', 'Background Color 4':'glassShade',
                'Background Color 5':'glassEdge', 'Panel Tint':'panel',
                'Secondary Text Color':'muted', 'Accent Color':'accent', 'Text Color':'text'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def validate_compiled_layer(layer, cue, plan, root):
    """Recompute provenance and controls from local files, never trust plan labels."""
    if root is None:
        raise ValueError('Compiled MOGRT requires physical job/source verification')
    folder = Path(plan['expected_project_path']).resolve().parent
    template = Path(layer['template_path']).resolve(strict=True)
    if not template.is_relative_to(folder/'compiled') or template.name != 'Editorial-Editable.mogrt':
        raise ValueError('Compiled template outside its exact job')
    binding = layer['compiled_binding']
    recipe_path = template.parent/'recipe.json'
    if binding != dict(protocol='hafez-editorial-compiled-v1', recipe_sha256=sha256(recipe_path)):
        raise ValueError('Compiled recipe identity mismatch')
    recipe = read(recipe_path)
    if recipe.get('output') != str(template.parent) or recipe.get('cue_id') != cue['id']:
        raise ValueError('Compiled cue/job mismatch')
    expected_sources = [Path(root)/'motion-pack/modules/01-editorial-intro'/name for name in
                        ('Hafez-FX-Editorial-Intro-v3.aep','Hafez-FX Editorial Intro v4.mogrt')]
    for source in expected_sources:
        if recipe.get('inputs_sha256',{}).get(str(source)) != sha256(source):
            raise ValueError('Compiled template authoring source changed')
    for filename, digest in {**recipe['inputs_sha256'], **recipe['media_sha256']}.items():
        if sha256(Path(filename)) != digest:
            raise ValueError('Compiled source evidence changed')
    original_plan = read(recipe['source_plan'])
    xmls = [Path(p) for p in recipe['inputs_sha256'] if p.endswith('.xml')]
    if len(xmls) != 1:
        raise ValueError('Ambiguous compiled XML evidence')
    expected = prepare_recipe(original_plan, ET.parse(xmls[0]).getroot().find('sequence'), cue['id'])
    for key,value in expected.items():
        if recipe.get(key) != value:
            raise ValueError('Compiled source mapping mismatch: '+key)
    original = next(c for c in original_plan['graphics'] if c['id']==cue['id'])
    if any(cue.get(k) != original.get(k) for k in ('start','end','semantic_source','layout_mode')):
        raise ValueError('Compiled cue timing/text evidence changed')
    receipt = read(template.parent/'ae-receipt.json')
    report = read(template.parent/'binding-report.json')
    if not receipt.get('ok') or receipt.get('job_id') != recipe['job_id'] or report.get('job_id') != recipe['job_id']:
        raise ValueError('Missing matching native export receipt')
    if (report.get('template_sha256') != sha256(template) or
            report.get('portrait_sha256') != sha256(template.parent/'portrait-current.mp4')):
        raise ValueError('Compiled media/template changed')
    asset = read_mogrt(template)
    if len(asset['controls']) != 20 or asset['fontLocked'] or not asset['hasMediaReplacement']:
        raise ValueError('Compiled control contract changed')
    actual = {c['name']:c['value'] for c in layer['typed_controls'] if c['kind']=='text'}
    expected_text = dict(zip(('Title Line 1','Title Line 2'),recipe['title_lines']))
    expected_text.update(Brand='HAFEZ-FX', Subtitle='', **{'Topic Label':'','English Eyebrow':''})
    if actual != expected_text:
        raise ValueError('Compiled text differs from reviewed source')
    asset.update(id='editorial-'+cue['id'], family='hafez-editorial', path=str(template))
    if layer.get('role') != 'editorial-source-bound' or layer.get('track') != 3:
        raise ValueError('Unexpected compiled layout/track')
    return asset
