"""Read one official "testo coordinato" PDF (the version WITH notes) into acts, articles and notes.

The Segreteria Istituzionale makes these PDFs in Word: the law text is set at the body size (10-12pt), the notes
("Testo originario", "Modifiche legislative") at the foot of each page in a smaller size, each starting with a
small note number, and each note is called from the text by a superscript number. So, per page:

- visual lines are spans on the same baseline, left to right;
- the note area starts at the first line that begins with a small digit span followed by small text (a note start)
  or, on a page where a note runs on from the page before, at the separator line (a run of spaces) above a run of
  small lines that ends the page;
- the page number (digits alone, top or bottom margin) is dropped;
- small digit spans inside the text are note calls, written [^n].

A collection ("raccolta coordinata") holds several acts; an act starts at a bold line naming it
("LEGGE 23 FEBBRAIO 2006 N.47", "DECRETO DELEGATO 7 marzo 2019 n.42"). Articles start at bold "Art. N" lines.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre',
          'novembre', 'dicembre']
MONTH_RE = '|'.join(MONTHS)
KIND_RE = (r'legge\s+costituzionale|legge\s+qualificata|legge\s+di\s+revisione\s+costituzionale|'
           r'decreto\s*[-–—]?\s*legge|decreto\s+delegato|decreto\s+reggenziale|decreto\s+consiliare|'
           r'decreto\s+legislativo|decreto|legge|regolamento\s+consiliare|regolamento|ordinanza|delibera|statuto')
ACT_HEAD = re.compile(rf'^\s*(?P<kind>{KIND_RE})\s+(?:n\.?\s*\d+\s+)?(?:del\s+)?(?P<d>\d{{1,2}})[º°]?\s*'
                      rf'(?P<m>{MONTH_RE})\s+(?P<y>\d{{4}})\s*[,\-–]?\s*(?:n\.?|nr\.?|numero)\s*°?\s*(?P<n>\d+)\b',
                      re.I)
# an act of the 19th century has no number: "Legge 20 dicembre 1884", standing alone on a bold line
ACT_HEAD_NONUM = re.compile(rf'^\s*(?P<kind>legge|decreto|regolamento)\s+(?P<d>\d{{1,2}})[º°]?\s*(?P<m>{MONTH_RE})\s+'
                            rf'(?P<y>1[89]\d\d)\s*\.?\s*$', re.I)
# what may follow an act's designation on its heading line: nothing, a full stop, a parenthesis ("(Capo I)",
# "(pubblicato il 23 dicembre 1991)") or a dash and its title
ACT_TAIL = re.compile(r'\s*\.?\s*(?:\([^()]{1,60}\)\s*)?(?:[-–—:]\s*\S.*)?')
# headings of the parts of an act (not its title)
STRUCT = re.compile(r'(?i)^(?:titolo|capo|capitolo|sezione|parte|libro|allegato|tabella)\b')
# an old-style article, numbered at the start of its first paragraph: "1. - E' accordato ..."
OLD_ART = re.compile(r'^\s*(?P<num>\d{1,3})\.\s*[-–—]\s*\S')
ART_HEAD = re.compile(r'^\s*Art(?:icolo|\.)?\s*(?P<num>\d+(?:\s*[-.]?\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|'
                      r'novies|nonies|decies|undecies|duodecies|terdecies|quaterdecies|quinquiesdecies|sexiesdecies)'
                      r"|-?[a-z](?![\w’']))?|unico)\b\s*(?:[\-–—.:]\s*)?(?P<rest>.*)$", re.I)
SPACES = '     ​­﻿'


def clean(s: str) -> str:
    s = s.replace('­', '').replace('​', '').replace('﻿', '')
    for c in SPACES:
        s = s.replace(c, ' ')
    s = s.replace('\t', ' ')
    return re.sub(r' +', ' ', s)


def visual_lines(page) -> list[dict]:
    """Spans grouped by baseline, left to right. Each line: y, x, x1, spans [(text, size, bold)]."""
    spans = []
    for b in page.get_text('dict', flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP)['blocks']:
        for l in b.get('lines', []):
            if abs(l['dir'][1]) > 0.01:
                continue  # rotated text (stamps, margins)
            for sp in l['spans']:
                if not sp['text']:
                    continue
                spans.append((sp['origin'][1], sp['bbox'][0], sp['bbox'][2], sp['text'], round(sp['size'], 1),
                              bool(sp['flags'] & 16) or 'Bold' in sp['font'], sp['bbox'][1], sp['bbox'][3]))
    spans.sort(key=lambda s: (s[0], s[1]))
    lines: list[dict] = []
    for s in spans:
        if lines and abs(lines[-1]['y'] - s[0]) < 2.0:
            ln = lines[-1]
            ln['spans'].append(s)
            ln['top'] = min(ln['top'], s[6])
            ln['bot'] = max(ln['bot'], s[7])
            if s[4] > ln['size']:
                ln['size'] = s[4]
        else:
            lines.append({'y': s[0], 'top': s[6], 'bot': s[7], 'spans': [s], 'size': s[4]})
    # superscripts (note calls, note numbers) sit above the baseline: fold a line of small digits into the line it
    # overlaps vertically (the next line first, since a superscript's baseline is higher than its line's)
    merged: list[dict] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        ink = [s for s in ln['spans'] if s[3].strip()]
        if ink and all(re.fullmatch(r'\d{1,4}', s[3].strip()) for s in ink):
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            prv = merged[-1] if merged else None
            if nxt is not None and nxt['size'] - ln['size'] >= 1.5 and ln['bot'] >= nxt['top'] - 0.5 and nxt['y'] - ln['y'] < nxt['size']:
                nxt['spans'] = ln['spans'] + nxt['spans']
                nxt['top'] = min(nxt['top'], ln['top'])
                i += 1
                continue
            if prv is not None and prv['size'] - ln['size'] >= 1.5 and ln['top'] <= prv['bot'] and ln['y'] - prv['y'] < prv['size']:
                prv['spans'] += ln['spans']
                prv['bot'] = max(prv['bot'], ln['bot'])
                i += 1
                continue
        merged.append(ln)
        i += 1
    lines = merged
    for ln in lines:
        ln['spans'].sort(key=lambda s: s[1])
        ink = [s for s in ln['spans'] if s[3].strip()]
        ln['x'] = ink[0][1] if ink else ln['spans'][0][1]
        ln['x1'] = ink[-1][2] if ink else ln['spans'][-1][2]
        ln['text'] = join_spans(ln['spans'], [s[3] for s in ln['spans']])
        ln['blank'] = not ink
        ln['tsize'] = max((s[4] for s in ink if not s[3].strip().isdigit()), default=max((s[4] for s in ink), default=0))
        w = Counter()
        for s in ink:
            if not (s[3].strip().isdigit() and s[4] < ln['tsize'] - 1.5):
                w[s[4]] += len(s[3].strip())
        ln['msize'] = w.most_common(1)[0][0] if w else ln['tsize']  # the size of most of its letters
        ln['bold'] = bool(ink) and all(s[5] for s in ink if s[3].strip() and not (s[3].strip().isdigit() and s[4] < ln['tsize'] - 1.5))
    lines.sort(key=lambda l: l['y'])
    return lines


def note_start_info(ln: dict) -> tuple[float, float, str] | None:
    """(x, text size, number) if the line begins with a superscript note number followed by text."""
    ink = [s for s in ln['spans'] if s[3].strip()]
    if len(ink) < 2:
        return None
    first = ink[0]
    if not re.fullmatch(r'\d{1,4}', first[3].strip()):
        return None
    w = Counter()
    for s in ink[1:]:
        w[s[4]] += len(s[3].strip())
    rest = w.most_common(1)[0][0]
    if rest - first[4] < 1.5:
        return None
    return first[1], rest, first[3].strip()


def layout(pages: list[list[dict]]) -> dict:
    """The note area's measures for one PDF, from its note starts: the left edge they start at (the most common x)
    and their text size(s). The notes may be smaller than the law text or (in a few texts) the same size."""
    cands = [i for lines in pages for l in lines if (i := note_start_info(l))]
    if not cands:
        return {'note_x': None, 'note_sizes': [], 'note_max': 0.0, 'small': False, 'body': 0.0, 'lim': 0.0}
    note_x = Counter(round(x) for x, _, _ in cands).most_common(1)[0][0]
    sizes = Counter(s for x, s, _ in cands if abs(x - note_x) <= 4)
    main = sizes.most_common(1)[0][0]
    note_sizes = sorted(s for s, c in sizes.items() if s == main or (c >= 2 and main - 3 <= s <= main + 0.6))
    chars = Counter()
    for lines in pages:
        for l in lines:
            for s in l['spans']:
                chars[s[4]] += len(s[3].strip())
    big = Counter({s: c for s, c in chars.items() if s > max(note_sizes) + 0.4})
    above = sum(big.values())
    at = sum(c for s, c in chars.items() if abs(s - main) <= 0.6)
    # notes are "small" when most of the law text is set larger than them; then anything below the middle of the
    # two sizes is note-sized
    small = above > 0.25 * at
    body = big.most_common(1)[0][0] if small else main
    lim = max(max(note_sizes) + 0.6, body - 0.5) if small else max(note_sizes) + 0.6
    return {'note_x': note_x, 'note_sizes': note_sizes, 'note_max': max(note_sizes), 'small': small, 'body': body,
            'lim': lim}


def is_note_start(ln: dict, lay: dict) -> bool:
    i = note_start_info(ln)
    return bool(i and lay['note_x'] is not None and abs(i[0] - lay['note_x']) <= 6
                and min(lay['note_sizes']) - 1.6 <= i[1] <= lay['lim'])


def page_number(ln: dict, h: float) -> bool:
    t = ln['text'].strip()
    return bool(re.fullmatch(r'[-– ]*\d{1,4}[-– ]*|(?:pag(?:ina)?\.?\s*)?\d{1,4}\s*(?:di|/)\s*\d{1,4}', t, re.I)) and (ln['y'] > h - 80 or ln['y'] < 60)


def separators(page, lay: dict) -> list[float]:
    """y of Word's footnote separators: a thin rule at the notes' left edge, 144pt long (the separator) or the
    width of the text (the continuation separator), standing alone (not a table border)."""
    if lay['note_x'] is None:
        return []
    rules = []
    for d in page.get_drawings():
        r = d['rect']
        rules.append(r)
    out = []
    for r in rules:
        if r.height >= 3 or abs(r.x0 - lay['note_x']) > 6:
            continue
        if not (abs(r.width - 144) <= 6 or r.width >= 400):
            continue
        # a table border meets other rules on its line or vertical rules at its ends
        alone = not any(o is not r and o.y0 - 3 <= r.y0 <= o.y1 + 3 and (o.x0 > r.x1 - 2 or o.x1 < r.x0 + 2 or o.height > 3)
                        and o.x0 <= r.x1 + 2 and o.x1 >= r.x0 - 2 for o in rules)
        if alone:
            out.append((r.y0 + r.y1) / 2)
    return out if len(out) <= 2 else []  # many: the rules of a list or table


def split_page(page, lines: list[dict], lay: dict) -> tuple[list[dict], list[dict]]:
    """Law text and note area of one page. The note area starts at the first line from which every line is
    note-sized, if that line starts a note or has a footnote separator (a drawn rule, or a line of spaces) above it."""
    h = page.rect.height
    lines = [l for l in lines if not page_number(l, h)]
    if lay['note_x'] is None:
        return lines, []
    lim = lay['lim']
    ok = [False] * (len(lines) + 1)
    ok[len(lines)] = True
    for i in range(len(lines) - 1, -1, -1):
        ok[i] = ok[i + 1] and (lines[i]['blank'] or lines[i]['msize'] <= lim)
    seps = separators(page, lay)
    prev_bot = 0.0
    text_sep = False
    called = set()  # note calls seen on this page so far
    for i, l in enumerate(lines):
        if l['blank']:
            # a line of spaces, as Word writes its separator into the text layer
            if lay['small'] and (l['x1'] - l['x'] > 60 or len(l['text']) > 20):
                text_sep = True
            continue
        drawn = any(prev_bot - 2 <= y <= l['top'] + 1 for y in seps)
        if drawn and not ok[i]:
            # below a drawn separator, a note may hold a stray line at the text size: most lines are enough
            below = [m for m in lines[i:] if not m['blank']]
            mostly = sum(m['msize'] <= lim for m in below) >= 0.85 * len(below)
        else:
            mostly = False
        if ok[i] or mostly:
            sized = min(lay['note_sizes']) - 0.6 <= l['msize'] <= lim
            sep = sized and (text_sep or any(prev_bot - 2 <= y <= l['top'] + 1 for y in seps))
            ink = [s for s in l['spans'] if s[3].strip()]
            # a note number set at (almost) the note size, which a call on this page asked for
            by_call = (sized and len(ink) > 1 and ink[0][3].strip() in called and abs(ink[0][1] - lay['note_x']) <= 6
                       and ink[0][4] <= ink[1][4] + 0.1)
            if is_note_start(l, lay) or sep or by_call:
                return lines[:i], lines[i:]
        for s in l['spans']:
            if re.fullmatch(r'\s*\d{1,4}\s*', s[3]) and s[4] < l['tsize'] - 1.5:
                called.add(s[3].strip())
        prev_bot = l['bot']
        text_sep = False
    return lines, []


def join_spans(spans: list, texts: list[str]) -> str:
    """The spans' texts left to right, with a space where the PDF leaves a visible gap and writes none (the cells
    of a table row)."""
    out = []
    for k, (s, t) in enumerate(zip(spans, texts)):
        if k and out and t and not out[-1][-1:].isspace() and not t[:1].isspace():
            p = spans[k - 1]
            if s[1] - p[2] > 0.3 * max(s[4], p[4]):
                out.append(' ')
        out.append(t)
    return ''.join(out)


def line_text(ln: dict, calls: bool) -> str:
    out = []
    for s in ln['spans']:
        t = s[3]
        if calls and t.strip() and re.fullmatch(r'\s*\d{1,4}\s*', t) and s[4] < ln['tsize'] - 1.5:
            out.append(f'[^{t.strip()}]')
        else:
            out.append(t)
    return clean(join_spans(ln['spans'], out)).strip()


def join_para(paras: list[str], prev_x1: float | None, ln_text: str, new: bool) -> None:
    if new or not paras:
        paras.append(ln_text)
        return
    p = paras[-1]
    if re.search(r'[A-Za-zÀ-ſ0-9]-$', p):
        paras[-1] = p + ln_text
    else:
        paras[-1] = p + ' ' + ln_text


LIST_START = re.compile(r'^(?:\d{1,3}[\)\.º°](?:\s|$)|\d{1,3}\s*[\-–]\s|[a-z]{1,2}\)\s|[a-z]\.\s|[ivx]{1,5}[\)\.]\s|[-–•●·—]\s|'
                        r'["“«‘\'](?=\S)|\(\s*\w)', re.I)


def title_end(act: dict) -> int:
    """How many lines of an act's intro are its heading and title: the lines after its designation that are
    headings other than a Titolo/Capo..., or capitals or a parenthesis (a title running over several lines, a
    "(Ratifica ...)" note). An act without a designation (the text's opening) keeps none back."""
    if 'head_at' not in act:
        return 0
    lines = act['intro']
    i = act['head_at']
    while i < len(lines):
        s = re.sub(r'\[\^\d+\]', '', lines[i]).strip()
        if s.startswith('## '):
            if STRUCT.match(s[3:].strip()):
                break
        elif not (s.startswith('(') or not re.search(r'[a-zà-ÿ]', s)):
            break
        i += 1
    return i


def parse(pdf: Path) -> dict:
    doc = pymupdf.open(pdf)
    pages = [visual_lines(page) for page in doc]
    lay = layout(pages)
    body_lines = []  # (page, line)
    note_lines = []
    left = Counter()
    right = Counter()
    for pi, page in enumerate(doc):
        b, n = split_page(page, pages[pi], lay)
        for l in b:
            if not l['blank']:
                body_lines.append((pi, l))
                left[round(l['x'])] += 1
                right[round(l['x1'] / 5) * 5] += 1
        for l in n:
            if not l['blank']:
                note_lines.append((pi, l))
    margin = left.most_common(1)[0][0] if left else 57
    right_edge = max((k for k, v in right.items() if v >= max(3, len(body_lines) // 50)), default=540)

    # ---- notes
    notes: dict[str, list[str]] = {}
    order: list[str] = []
    cur = None
    prev = None
    nmargin = Counter(round(l['x']) for _, l in note_lines).most_common(1)[0][0] if note_lines else margin
    last = 0
    for pi, l in note_lines:
        ink = [s for s in l['spans'] if s[3].strip()]
        # a note starts with its number: set superscript, or (in some texts) at the note size, as the next number
        start = is_note_start(l, lay) or (
            len(ink) > 1 and re.fullmatch(r'\d{1,4}', ink[0][3].strip()) is not None and int(ink[0][3]) == last + 1
            and abs(ink[0][1] - nmargin) <= 6)
        if start:
            num = ink[0][3].strip()
            last = int(num)
            tail = l['spans'][l['spans'].index(ink[0]) + 1:]
            rest = clean(join_spans(tail, [s[3] for s in tail])).strip()
            key = num
            k = 2
            while key in notes:
                key = f'{num}~{k}'
                k += 1
            cur = key
            notes[cur] = [rest] if rest else []
            order.append(cur)
            prev = l
            continue
        t = line_text(l, False)
        if cur is None:
            cur = '0'
            notes[cur] = []
            order.append(cur)
        ps = notes[cur]
        new = (not ps or l['bold'] != (prev or {}).get('bold') or LIST_START.match(t) is not None
               or (prev is not None and prev['x1'] < right_edge - 60 and re.search(r'[.:;"”»]\s*$', prev['text']))
               or l['x'] > nmargin + 25)
        join_para(ps, None, t, new)
        prev = l

    # ---- body: acts, headings, articles
    acts: list[dict] = []
    act = {'head': None, 'key': 'intro', 'intro': [], 'articles': []}
    acts.append(act)
    art = None
    prev = None
    for pi, l in body_lines:
        t = line_text(l, True)
        if not t:
            continue
        plain = re.sub(r'\[\^\d+\]', '', t).strip()
        m_act = ACT_HEAD.match(plain)
        m_old = None if m_act else ACT_HEAD_NONUM.match(plain)
        m_art = ART_HEAD.match(plain)
        if (m_act and l['bold'] and ACT_TAIL.fullmatch(plain[m_act.end():])
                and not re.search(r'(?i)\bart(?:icolo|\.)\s*\d', plain)) or (m_old and l['bold']):
            # a new act (a collection may also name it again just before its text: same key -> same act)
            m = m_act or m_old
            d, mo, y = int(m['d']), MONTHS.index(m['m'].lower()) + 1, m['y']
            kind = re.sub(r'[\s\-–—]+', '-', m['kind'].lower())
            n = int(m_act['n']) if m_act else None
            key = f'{kind}-{y}-{n}' if m_act else f'{kind}-{y}-{mo:02d}-{d:02d}'  # unnumbered: by its date
            if act['key'] != key or act['articles']:
                # "ALTRE NORME" ("other provisions") divides a collection's main act from the acts after it: it
                # heads the next act, not the end of the last article
                last = act['articles'][-1]['lines'] if act['articles'] else act['intro']
                carry = []
                while last and re.fullmatch(r'## ALTRE NORME\W*', re.sub(r'\[\^\d+\]', '', last[-1]).strip(), re.I):
                    carry.insert(0, last.pop())
                act = {'head': plain, 'key': key, 'date': f'{y}-{mo:02d}-{d:02d}', 'kind': kind, 'number': n,
                       'intro': carry, 'articles': []}
                acts.append(act)
            act['intro'].append(t)
            act['head_at'] = len(act['intro'])
            art = None
            prev = l
            continue
        # an unnumbered (19th-century) act numbers its articles at the start of their first paragraph: "1. - ...",
        # 1, 2, 3 in turn
        mo_ = OLD_ART.match(plain) if act.get('number', 0) is None else None
        if (mo_ and not l['bold'] and abs(l['x'] - margin) <= 12
                and int(mo_['num']) == (int(act['articles'][-1]['num']) + 1 if act['articles'] else 1)
                and all(a.get('old') for a in act['articles'])
                and (prev is None or re.search(r'[.:;!?"”»)\]]\s*(\[\^\d+\])*\s*$', line_text(prev, True)) is not None
                     or prev['bold'])):
            art = {'num': mo_['num'], 'lines': [t], 'inline': True, 'old': True}
            act['articles'].append(art)
            prev = l
            continue
        # an "Art. 2" line alone, not bold, at the margin, after a full stop or a bold line
        alone = (m_art is not None and not l['bold'] and not m_art['rest'].strip() and abs(l['x'] - margin) <= 12
                 and prev is not None and (prev['bold'] or re.search(r'[.:;!?"”»)]\s*(\[\^\d+\])*\s*$', line_text(prev, True))))
        # "Art. 2. - L'ufficio ...": an old-style article whose heading runs into its text, at the left margin,
        # starting a paragraph
        inline = (m_art is not None and not l['bold'] and abs(l['x'] - margin) <= 12
                  and re.match(r'(?i)^\s*art(?:icolo|\.)\s*\d+[^.\-–—]{0,20}?\.?\s*[-–—]\s+\S', plain) is not None
                  and (prev is None or re.search(r'[.:;!?"”»)]\s*(\[\^\d+\])?\s*$', prev['text'].strip()) is not None))
        if m_art and (inline or alone or l['bold'] or (l['x'] > margin + 60 and len(plain) < 40)) and (len(plain) < 200 or inline):
            num = re.sub(r'[\s.\-]+', '-', m_art['num'].strip().lower())
            moved = []
            src = art['lines'] if art else act['intro']
            # the headings just above go with the article (Titolo, Capo ...), but not the act's own title, which
            # stays in its intro
            keep = title_end(act) if art is None else 0
            while len(src) > keep and src[-1].startswith('## '):
                moved.insert(0, src.pop())
            if art is None:
                # still an act title: a heading before the act's first Titolo/Capo, or one naming a law
                def struct(h: str) -> bool:
                    return STRUCT.match(re.sub(r'\[\^\d+\]', '', h[3:]).strip()) is not None
                while moved and not struct(moved[0]) and (any(struct(h) for h in moved[1:]) or re.match(
                        r'## (?:LEGGE|DECRETO|REGOLAMENTO|RIFORMA|TESTO UNICO|CODICE)\b', moved[0])):
                    src.append(moved.pop(0))
            art = {'num': num, 'lines': moved + [t], 'inline': inline}
            act['articles'].append(art)
            prev = l
            continue
        target = art['lines'] if art else act['intro']
        heading = (l['bold'] and (plain.isupper() or re.match(r'(?i)^(titolo|capo|sezione|parte|libro|allegato)\b', plain))
                   and not LIST_START.match(plain) and len(plain) < 160) or re.fullmatch(r'ALTRE NORME\W*', plain) is not None
        if heading:
            divider = re.compile(r'(?:## )?ALTRE NORME\W*')
            if target and target[-1].startswith('## ') and prev is not None and prev['bold'] and l['y'] - prev['y'] < l['tsize'] * 1.9 \
                    and not divider.fullmatch(plain) and not divider.fullmatch(re.sub(r'\[\^\d+\]', '', target[-1]).strip()):
                target[-1] += ' ' + t
            else:
                target.append('## ' + t)
            prev = l
            continue
        new = (prev is None or not target or target[-1].startswith('## ') or
               (art is not None and not art.get('inline') and len(target) == 1 + sum(1 for x in target if x.startswith('## '))) or
               l['x'] > margin + 12 or LIST_START.match(plain) is not None or
               (prev['x1'] < right_edge - 50 and re.search(r'[.:;!?"”»)]\s*(\[\^\d+\])?\s*$', prev['text'].strip()))
               or prev['bold'] != l['bold'])
        join_para(target, None, t, new)
        prev = l
    return {'layout': lay, 'acts': [a for a in acts if a['intro'] or a['articles']], 'notes': notes,
            'note_order': order, 'pages': doc.page_count}


if __name__ == '__main__':
    r = parse(Path(sys.argv[1]))
    import json
    for a in r['acts']:
        print('ACT', a['key'], a.get('head'), len(a['articles']))
        for line in a['intro'][:6]:
            print('   intro:', line[:150])
        for x in a['articles'][: int(sys.argv[2]) if len(sys.argv) > 2 else 3]:
            print('  ART', x['num'])
            for line in x['lines']:
                print('     ', line[:200])
    print(len(r['notes']), 'notes')
    for k in r['note_order'][:3]:
        print('NOTE', k, r['notes'][k][:4])
