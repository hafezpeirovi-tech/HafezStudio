"""Retain font A/B evidence and create the final visual-review plan (not release)."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'engine/src/hermes_video'))
from glass_pack import load_library, validate_plan

out = root / 'proof/glass-pack-20260913-01'
plan = json.loads((out / 'review-layout.plan.json').read_text(encoding='utf-8'))
plan['native_sequence_requirements'] = {'composite_in_linear_color': False,
                                        'verification': 'QA sequence UI observed and unchecked 2026-09-13'}
for cue in plan['graphics']:
    for layer in cue['template_layers']:
        if layer['role'] != 'vendor-background' and cue['id'] != 'glass-data-qa':
            layer['native_motion_scale'] = 65
validate_plan(plan, load_library(root), qa=True, root=root)

def save(name, data):
    with (out/name).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)

save('visual-review.plan.json', plan)
for mode in ('apply','inspect'):
    save(f'visual-review-{mode}.request.json', {
        'mode': mode, 'request_id': f'glass-visual-{mode}-20260913-01',
        'plan_path': str(out/'visual-review.plan.json'),
        'expected_project_path': plan['expected_project_path'],
        'expected_sequence_name': plan['sequence'],
        'expected_sequence_id': plan['expected_sequence_id'], 'mute_guide': False,
    })
print('Visual-review plan validated. Final fonts, audio and production route remain pending.')
