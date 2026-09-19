"""Conservative, source-literal Glass proposals, never ASR correction or approval.

Design selection is rule based. Existing acoustic/caption/retained-word gates
still decide whether a proposed chapter can be inserted. Overlay ideas stay in
the review queue until native geometry and full-interval tracking are verified.
"""
from __future__ import annotations

import re


def tokens(text):
    return re.findall(r"[^\W_]+", str(text).replace("ي", "ی").replace("ك", "ک"), re.UNICODE)


_CHAPTER_RULES = [
    ("explicit-topic-transition", re.compile(
        r"(?:^|[.!?؟؛،]\s*)(?:مورد|موضوع|بخش|نکته)\s+"
        r"(?:بعدی|بعد|اول|دوم|سوم|چهارم)\s*[،:؛-]\s*(?P<title>[^.!?؟؛،\n]+)")),
    ("named-feature", re.compile(
        r"(?:یک|یه)\s+(?:بخش|قابلیت|ابزار)\s+(?P<title>[^.!?؟؛،\n]{2,70}?)\s+(?:داره|دارد)(?=\W|$)")),
    ("named-concept", re.compile(
        r"(?:بهش|به\s+این\s+[^.!?؟؛،\n]{1,45}?)\s+می[‌ ]?گن\s+"
        r"(?P<title>[^.!?؟؛،\n]{2,60}?)(?=\s+(?:یعنی|تو|که|و)\s|[.!?؟؛،]|$)")),
]
_DANGLING = {"و", "یا", "که", "از", "به", "با", "در", "برای", "تا", "این", "اون", "رو", "را", "یک", "یه"}
_NEEDS_REVIEW = [
    ("subscribe", re.compile(r"سابسکرایب\s+کن(?:ید)?(?=\W|$)"), None, "Glass subscribe asset not selected"),
    ("metric", re.compile(r"\d|[۰-۹]"), "motionstate-liquid", "Verify numeric meaning, units and full-interval placement"),
    ("comparison", re.compile(r"تفاوت|مقایسه|در مقابل|برخلاف"), "motionstate-liquid", "Verify both compared claims and native layout"),
    ("important-words", re.compile(r"نکته[ٔ‌ ]+مهم|هشدار|حواست|مراقب"), "foslight-trendy", "Verify concise copy and full-interval placement"),
]


def editorial_proposals(segments, requests=()):
    """All titles remain proposals. No guessed translation or fixed-time chapters."""
    if not isinstance(segments, list) or any(not isinstance(s, dict) for s in segments):
        raise ValueError("Expected source segments")
    if not isinstance(requests, (list, tuple)) or any(not isinstance(r, dict) for r in requests):
        raise ValueError("Expected chapter proposals")
    by_id = {}
    for segment in segments:
        sid = segment.get("id")
        if type(sid) is not int or sid in by_id:
            raise ValueError("Invalid/duplicate segment identity")
        by_id[sid] = segment
    chapters, review, seen = [], [], set()

    def offer(sid, quote, rule, english=""):
        # Never promote editor comments/instructions into visible title copy.
        if type(sid) is not int or not isinstance(quote, str):
            review.append(dict(segment_id=sid if type(sid) is int else None,
                               role="chapter", status="blocked-invalid-copy"))
            return
        key = (sid, tuple(tokens(quote)))
        if key in seen:
            return
        seen.add(key)
        item = dict(segment_id=sid, quote_fa=quote, title_en="", proposal_origin=rule,
                    copy_role="literal-topic-label-not-complete-sentence", publication_ready=False)
        if english:
            item["proposed_translation"] = english if isinstance(english, str) else ""
            item["translation_status"] = "withheld-unverified-translation"
        chapters.append(item)

    for request in requests:
        # Invalid requests are retained for rejection, not silently blessed.
        offer(request.get("segment_id"), request.get("quote_fa", ""), "editor-proposal", request.get("title_en", ""))
    for segment in segments:
        sid = segment["id"]
        text = segment.get("source_text")
        if not isinstance(text, str) or not text.strip():
            review.append(dict(segment_id=sid, role="source", status="missing-original-source-text"))
            continue
        for rule, pattern in _CHAPTER_RULES:
            for match in pattern.finditer(text):
                quote = match.group("title").strip()
                words = tokens(quote)
                unfinished = text[match.end("title"):].lstrip().startswith(("...", "…"))
                if not 1 <= len(words) <= 6 or len(quote) > 100 or "…" in quote or "..." in quote or unfinished or words[-1] in _DANGLING:
                    review.append(dict(segment_id=sid, role="chapter", quote_fa=quote,
                                       status="not-a-short-complete-topic-label", proposal_origin=rule))
                    continue
                offer(sid, quote, rule)
        for role, pattern, family, reason in _NEEDS_REVIEW:
            if pattern.search(text):
                review.append(dict(segment_id=sid, role=role, source_quote=text,
                                   family=family, status="review-only-not-inserted", reason=reason,
                                   source_word_ids=segment.get("source_word_ids", [])))
    return dict(protocol="hafez-glass-editorial-proposals-v1", chapters=chapters, review_items=review,
                policy=dict(source_rewrite=False, translation_automatic=False,
                            chapter_gate="retained-source-words-and-acoustic-caption-gap",
                            overlay_insertion=False, publication_ready=False))


def review_markdown(editorial, selected, rejected, segments):
    """Review sidecar: analysis clock is not the final retake-edited sequence."""
    index = {s["id"]: s for s in segments}
    lines = ["# بازبینی محتوای Glass", "",
             "این فهرست تأیید انتشار نیست. زمان تحلیل اولیه، پیش از حذف برداشت‌های تکراری است؛ نه زمان سکانس نهایی Premiere.",
             "شروع/پایان منبع برای مراجعه به فایل دوربین اول است. ASR با شنیدن تأیید نشده است.", "",
             "تیترها عبارت کوتاه عین منبع‌اند، نه بازنویسی محاوره‌ای یا جملهٔ کاملِ ساختگی.",
             "ترجمهٔ تأییدنشده نمایش داده نمی‌شود. پیشنهادهای عدد/مقایسه/سابسکرایب هنوز درج نمی‌شوند.", ""]
    for label, items in (("فصل‌های عبورکرده از کنترل زمان و منبع", selected),
                         ("فصل‌های کنارگذاشته‌شده", rejected), ("صف بازبینی گرافیک", editorial["review_items"])):
        lines.extend(["## " + label, ""])
        for item in items:
            entry = item.get("request", item)
            segment = index.get(entry.get("segment_id"), {})
            at = segment.get("start", "—")
            quote = entry.get("quote_fa", entry.get("source_quote", "—")).replace("\n", " ")
            lines.append(f'- بخش {segment.get("id", "—")} | تحلیل اولیه {at} ثانیه | '
                         f'منبع {segment.get("source_start", "—")} تا {segment.get("source_end", "—")} | '
                         f'{quote} | {item.get("reason", item.get("status", "نیازمند شنیدن و تأیید"))}')
        if not items:
            lines.append("- موردی ثبت نشد.")
        lines.append("")
    return "\n".join(lines)
