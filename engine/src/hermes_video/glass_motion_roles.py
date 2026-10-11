"""Three native editorial roles, using the owner's existing SaaS library.

Numbered cues use literal retained speech, never generated summaries. All
vendor titles are independent of camera media. Longer statements retain the
approved source-bound portrait compiler. Native visual QA remains mandatory.
"""
import re
import os
from fractions import Fraction

from glass_pack import typed_layer
from glass_semantic_cards import select_cutaways
from glass_editorial import tokens

PROTOCOL = 'hafez-glass-motion-roles-v1'
ORDINALS = 'اول دوم سوم چهارم پنجم ششم هفتم هشتم نهم دهم یک دو سه چهار پنج شش هفت هشت نه ده'.split()
STARTS = {'مشکل', 'نکته', 'اشتباه', 'تست', 'مرحله', 'دلیل'}
INCOMPLETE = {'و', 'یا', 'که', 'از', 'به', 'با', 'در', 'برای', 'تا', 'را', 'رو', 'اگر', 'چون', 'ولی'}


def enabled():
    """Native-tested review routing; retain an explicit legacy rollback switch."""
    return os.environ.get('HAFEZ_GLASS_MOTION_ROLES_QA', '1') != '0'


def review_notes(plan):
    """Human-readable cue list, including uncertain literal labels, never approval."""
    lines=['بازبینی موشن‌ها — پیش‌نویس قابل ویرایش، نه نسخهٔ تأییدشدهٔ انتشار', '']
    for cue in plan['graphics']:
        evidence=cue.get('semantic_source',{})
        chapter=cue.get('chapter_source',{})
        seconds=int(cue['start']); minutes,seconds=divmod(seconds,60)
        text=evidence.get('label') or evidence.get('display_text') or chapter.get('quote_fa','')
        if evidence.get('label') and evidence.get('display_text'):
            text+=': '+evidence['display_text']
        warning=' — متن کم‌اطمینان؛ با گفتار تطبیق بده' if evidence.get('source_review_required') else ''
        lines.append(f'{minutes:02}:{seconds:02} | {cue.get("motion_role","chapter")} | {text}{warning}')
    lines += ['', 'متن، رنگ و زمان هر MOGRT را در Premiere بازبینی کن. خروجی ویدیو خودکار گرفته نمی‌شود.']
    return '\n'.join(lines)+'\n'


def select_numbered(spans, mapping, *, occupied=(), max_cards=8, allow_label_only=False,
                    allow_review_labels=False):
    """Require explicit ordinal + a complete, bounded acoustic statement.

    Read up to a sentence boundary/pause, never cut off a negation or silently
    shorten an over-capacity sentence. A rejected cue is left for manual review.
    """
    rate = mapping.rate
    chosen, rejected = [], []
    counts = {}
    for word in spans:
        counts[word['id']] = counts.get(word['id'], 0) + 1
    for i, first in enumerate(spans):
        if tokens(first['text']) not in [[s] for s in STARTS]:
            continue
        j = i + 1
        if j < len(spans) and tokens(spans[j]['text']) == ['شماره']:
            j += 1
        if j >= len(spans):
            continue
        ordinal = tokens(spans[j]['text'])
        if len(ordinal) != 1 or ordinal[0] not in ORDINALS + list('123456789۱۲۳۴۵۶۷۸۹'):
            continue
        label = ' '.join(w['text'].strip(' :،؛-') for w in spans[i:j+1])
        words = spans[i:j+1]
        body, closed = [], False
        for word in spans[j+1:]:
            if word['start'] - words[-1]['end'] > .8:
                closed = bool(body)
                break
            body.append(word); words.append(word)
            if re.search(r'[.!?؟؛]\s*$', word['text']):
                closed = True
                break
            if sum(len(tokens(w['text'])) for w in body) > 12:
                break
        body_text = ' '.join(w['text'] for w in body).strip()
        reason = None
        label_only = False
        if not closed or not 2 <= len(tokens(body_text)) <= 12 or tokens(body_text)[-1] in INCOMPLETE:
            reason = 'numbered-copy-needs-review'
            if allow_label_only:
                # A long/unpunctuated explanation is not a safe short title.
                # Show only the explicitly spoken label; never invent its summary.
                rejected.append(dict(source_word_id=first['id'], label=label, reason=reason))
                words = spans[i:j+1]
                body_text = ''
                label_only = True
                reason = None
        source_review = False
        if allow_review_labels and not all(w['trusted'] for w in words):
            prefix=spans[i:j+1]
            # Literal ordinal only. Never promote uncertain words to trusted or
            # use them to generate a body, chart, claim, caption or chapter gap.
            # Unique contiguous original-word indices prevent skipping a cut word.
            if (all(w.get('trusted') or w.get('reviewable_label') for w in prefix)
                    and all(counts[w['id']]==1 for w in prefix)
                    and all(type(w.get('source_index')) is int for w in prefix)
                    and all(b['source_index']==a['source_index']+1 for a,b in zip(prefix,prefix[1:]))):
                words=prefix; body_text=''; label_only=True; source_review=True; reason=None
                rejected.append(dict(source_word_id=first['id'],label=label,
                                     reason='literal-label-added-with-source-review'))
        if not all((w['trusted'] or source_review) and counts[w['id']] == 1 for w in words):
            reason = 'numbered-untrusted-source'
        elif any(b['start'] < a['end']-1e-6 or b['start']-a['end'] > .8 for a,b in zip(words,words[1:])):
            reason = 'numbered-discontinuous-speech'
        start = round(Fraction(str(first['start'])) * rate)
        # Keep the entire spoken statement on screen, with no added timeline time.
        frames = max(round(4*rate), round(Fraction(str(words[-1]['end']))*rate)-start)
        end = start + frames
        if end > mapping.duration or frames > round(8*rate):
            reason = reason or 'numbered-duration-capacity'
        pieces = mapping.spans(start, min(end, mapping.duration)) if start < mapping.duration else []
        if len(pieces) != 1:
            reason = reason or 'numbered-chapter-intersection'
        if reason:
            rejected.append(dict(source_word_id=first['id'], label=label, reason=reason)); continue
        _, _, a, b = pieces[0]
        if (len(chosen) >= max_cards or any(a < y and b > x for x,y in occupied) or
                any(a < c['end_frame']+round(5*rate) and b > c['start_frame']-round(5*rate) for c in chosen)):
            rejected.append(dict(source_word_id=first['id'], label=label, reason='numbered-density')); continue
        chosen.append(dict(id='glass-numbered-'+str(len(chosen)+1), start_frame=a, end_frame=b,
            frames=b-a, source_frame=start, source_word_ids=[w['id'] for w in words],
            quote_fa=' '.join(w['text'] for w in words), display_text=body_text,
            label=label, motion_role='numbered-point', layout_mode='numbered-voice-continuous',
            source_review_required=source_review,
            label_only=label_only, selection_rule='explicit-ordinal-retained-speech', publication_ready=False))
    return chosen, rejected


def select_roles(storyboard, spans, mapping, *, occupied=()):
    numbered, rejected = select_numbered(spans, mapping, occupied=occupied, allow_label_only=True,
                                         allow_review_labels=True)
    # A grammatical fragment such as "اشتباهی" is not a useful takeaway.
    # Filter before density selection so rejected fragments cannot crowd out
    # later complete phrases. Keep the original storyboard/evidence immutable.
    proposals = []
    for proposal in storyboard.get('proposals', []):
        if proposal.get('role') == 'important-text' and len(tokens(proposal.get('quote_fa', ''))) < 2:
            rejected.append(dict(segment_id=proposal.get('segment_id'), reason='emphasis-fragment-needs-review'))
        else:
            proposals.append(proposal)
    important, blocked = select_cutaways(dict(storyboard, proposals=proposals), spans, mapping,
        occupied=[*occupied, *((c['start_frame'],c['end_frame']) for c in numbered)])
    for cue in important:
        # No face-safe geometry has been certified for this source shot.
        # An opaque cutaway is deterministic; speech/timeline never pause.
        cue.update(motion_role='emphasis', layout_mode='emphasis-voice-continuous',
                   placement_policy='opaque-cutaway-no-face-overlap', publication_ready=False)
        if len(tokens(cue['display_text'])) >= 3:
            # Retain the approved source-bound portrait layout for longer
            # statements; do not replace the whole owner's style with titles.
            cue.update(motion_role='editorial-emphasis',layout_mode='fullscreen-voice-continuous',
                       placement_policy='source-bound-editorial-portrait')
    return sorted([*numbered,*important], key=lambda c:c['start_frame']), [*rejected,*blocked]


def role_layers(library, card, root):
    if card['motion_role']=='editorial-emphasis':
        from glass_semantic_cards import cutaway_layers
        return cutaway_layers(library,card['display_text'],root)
    def asset(name):
        found = [a for a in library['assets'] if a['family']=='foslight-saas'
                 and a['name']==name and a['width']>a['height']]
        if len(found)!=1: raise ValueError('Ambiguous approved SaaS asset: '+name)
        return found[0]
    if card['motion_role']=='numbered-point':
        from glass_assembly import chapter_layers
        bg = chapter_layers(library, card['label'], '', root)[0]
        heading, detail = card['label'], card['display_text']
        if card.get('label_only'):
            heading, detail = heading.rsplit(' ', 1)
        title = typed_layer(asset('SaaS Pack Title 03'), track=3, root=root,
            text={'Text 1':heading, 'Text 2':detail},
            font='AbarHighFaNum-ExtraBold', sizes={'Text 1':130,'Text 2':90},
            color_tokens={'Text 1':'text','Text 2':'accent'})
        title['native_motion_scale']=65
        return [bg,title]
    if card['motion_role']=='emphasis':
        from glass_assembly import chapter_layers
        bg = chapter_layers(library, '', '', root)[0]
        title = typed_layer(asset('SaaS Pack Title 07'), track=3, root=root,
            text={'Text 1':card['display_text']}, font='AbarHighFaNum-ExtraBold',
            # Premiere AE Point controls return normalized comp coordinates.
            # Pixel coordinates here push the title completely off screen.
            sizes={'Text 1':105}, values={'Global Position':[.5,.5]},
            color_tokens={'Text 1':'text'})
        title['native_motion_scale']=65
        return [bg,title]
    raise ValueError('Unsupported executable motion role')
