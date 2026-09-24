"""Compile contextual AI choices into real vendor MOGRT cutaways, never PNGs.

Cutaways cover the camera picture with the approved gradient while speech and
all source timing continue unchanged. They are not face-safe overlays.
"""
from fractions import Fraction
import re
from glass_pack import typed_layer
from glass_editorial import tokens


def display_copy(quote):
    """Explicit spelling-only glossary; source quote/evidence remains unchanged."""
    text = re.sub(r'(?<!\w)استراتیجی(?!\w)', 'استراتژی', quote)
    return text.strip().rstrip('،.؛'), ([dict(source=quote,display=text,
        reason='spelling-glossary:strategy')] if text != quote else [])


def select_cutaways(storyboard, spans, mapping, *, occupied=(), max_cards=8):
    rate = mapping.rate
    selected, rejected = [], []
    indexed = {}
    for word in spans:
        indexed.setdefault(word['id'], []).append(word)
    for proposal in storyboard.get('proposals', []):
        reason = None
        if proposal.get('role') != 'important-text':
            reason = 'role-requires-dedicated-layout'
        elif not all(proposal.get('meaning_review', {}).get(k) is True for k in
                     ('standalone','faithful','important','spelling_clean')):
            reason = 'contextual-review-required'
        wanted = tokens(proposal['quote_fa'])
        if not 1 <= len(wanted) <= 6:
            reason = 'keyword-template-capacity'
        owned = proposal.get('source_word_ids', [])
        sequence = [indexed[wid][0] for wid in owned if len(indexed.get(wid, [])) == 1]
        matches = []
        for i in range(len(sequence)):
            for j in range(i+1, min(i+6,len(sequence))+1):
                words = sequence[i:j]
                # Missing/untrusted source words must not disappear from a phrase.
                ids = [w['id'] for w in words]
                position = owned.index(ids[0])
                if owned[position:position+len(ids)] != ids: continue
                if [t for w in words for t in tokens(w['text'])] != wanted: continue
                if not all(w['trusted'] for w in words): continue
                if any(b['start'] < a['end']-1e-6 or b['start']-a['end'] > 1
                       for a,b in zip(words,words[1:])): continue
                matches.append(words)
        if len(matches) != 1:
            reason = reason or 'ambiguous-or-unretained-acoustic-quote'
        if reason:
            rejected.append(dict(segment_id=proposal['segment_id'],reason=reason)); continue
        words = matches[0]
        source_frame = round(Fraction(str(words[0]['start']))*rate)
        source_end = source_frame + round(6*rate)
        if source_end > mapping.duration:
            rejected.append(dict(segment_id=proposal['segment_id'],reason='insufficient-tail')); continue
        pieces = mapping.spans(source_frame,source_end)
        if len(pieces) != 1:
            rejected.append(dict(segment_id=proposal['segment_id'],reason='chapter-intersection')); continue
        _,_,start,end = pieces[0]
        blocked = any(start < b and end > a for a,b in occupied)
        blocked = blocked or any(abs(start-c['start_frame']) < round(30*rate) for c in selected)
        if blocked or len(selected) >= max_cards:
            rejected.append(dict(segment_id=proposal['segment_id'],reason='density-or-existing-graphic')); continue
        display,copy_edits=display_copy(proposal['quote_fa'])
        selected.append(dict(id='glass-semantic-'+str(proposal['segment_id']),
            start_frame=start,end_frame=end,frames=end-start,source_frame=source_frame,
            quote_fa=proposal['quote_fa'],display_text=display,copy_edits=copy_edits,
            source_word_ids=[w['id'] for w in words],
            semantic_source=proposal,layout_mode='fullscreen-voice-continuous'))
    return selected,rejected


def cutaway_layers(library, quote, root):
    from glass_assembly import chapter_layers
    layers = chapter_layers(library, quote, '', root)
    assets = [a for a in library['assets'] if a['family']=='foslight-trendy'
              and a['name']=='Trendy Title 01' and a['width']>a['height']]
    if len(assets)!=1: raise ValueError('Ambiguous approved keyword template')
    layers[1] = typed_layer(assets[0], text={'Text 1':quote,'Text 2':'','Text 3':'','Text 4':''},
        track=3,root=root,font='AbarHighFaNum-ExtraBold',sizes={'Text 1':170},values={'Accent Word':1})
    layers[1]['native_motion_scale']=65
    return layers
