"""Reads only the cache and writes scripts/san-marino-law/corpus.json (atomically).

    python -X utf8 scripts/san-marino-law/parse.py

First cut (2026-10-29, wind-down): the Dichiarazione dei Diritti (Legge 8 luglio 1974 n.59) as ONE "oldest version
available" version: the current testo coordinato ("SENZA NOTE" PDF in the ZIP served at documento17085085.html,
aggiornato al 26 settembre 2025). History replay from the annotated PDF's notes is the next step (see PROGRESS.md).
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / '.cache'
DICH_URL = ('https://www.consigliograndeegenerale.sm/on-line/home/archivio-leggi-decreti-e-regolamenti/'
            'documento17085085.html')


def cached(url: str) -> bytes:
    return (CACHE / hashlib.sha256(url.encode()).hexdigest()).read_bytes()


def pdf_from_zip(data: bytes, want_plain: bool) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    for inf in z.infolist():
        name = inf.filename.encode('cp437').decode('utf-8', 'replace')
        if ('SENZA NOTE' in name) == want_plain:
            out = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', '-', '-'], input=z.read(inf),
                                 capture_output=True)
            if not out.stdout:
                tmp = CACHE / 'tmp-parse.pdf'
                tmp.write_bytes(z.read(inf))
                out = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(tmp), '-'], capture_output=True)
                tmp.unlink()
            return out.stdout.decode('utf-8', 'replace')
    raise KeyError('pdf not in zip')


def norm(s: str) -> str:
    s = s.replace('\xa0', ' ').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace('–', '-').replace('—', '-')
    return re.sub(r'[ \t]+', ' ', s).strip()


def paragraphs(lines: list[str]) -> str:
    """Rejoin layout lines: a new paragraph starts at an indented line or a numbered/lettered item."""
    paras: list[str] = []
    for raw in lines:
        if not raw.strip():
            continue
        line = norm(raw)
        indented = raw.startswith('    ')
        item = re.match(r'^(\d+\.|[a-z]\)|[a-z]\.)\s', line)
        if not paras or indented or item:
            paras.append(line)
        else:
            paras[-1] += ' ' + line
    return ''.join(p + '\n' for p in paras)


def parse_dichiarazione() -> dict:
    data = cached(DICH_URL)
    txt = pdf_from_zip(data, want_plain=True)
    lines = [l for l in txt.replace('\f', '\n').split('\n') if not re.fullmatch(r'\s*\d{1,3}\s*', l)]
    start = next(i for i, l in enumerate(lines) if l.strip() == 'Preambolo')
    units: dict[str, dict] = {}
    key, label, buf = 'preambolo', 'Preambolo', []

    def flush():
        if key and any(x.strip() for x in buf):
            body = buf
            head = f'# {label}\n'
            if body and re.fullmatch(r'\s*\(.*\)\s*', body[0]):
                head += norm(body[0]) + '\n'
                body = body[1:]
            units[key] = {'label': label, 'kind': 'preamble' if key == 'preambolo' else 'art',
                          'text': head + paragraphs(body)}

    for l in lines[start + 1:]:
        s = l.strip()
        if s.startswith('ALTRE NORME'):
            break
        m = re.fullmatch(r'Art\.\s*(\d+)(?:[ -]?(bis))?', s)
        if m:
            flush()
            n = int(m.group(1))
            key = f'art-{n:03d}' + ('-bis' if m.group(2) else '')
            label = f'Art. {n}' + (' bis' if m.group(2) else '')
            buf = []
            continue
        if s == 'Norma Transitoria':
            flush()
            key, buf = None, []    # the transitional norm is Legge 36/2002 art. 9, given only under ALTRE NORME
            continue
        buf.append(l)
    flush()
    return {
        'slug': 'dichiarazione-dei-diritti',
        'short': 'Dichiarazione',
        'title': "Dichiarazione dei diritti dei cittadini e dei principi fondamentali dell'ordinamento sammarinese "
                 '(Legge 8 luglio 1974 n.59)',
        'url': 'https://www.consigliograndeegenerale.sm/on-line/home/archivio-leggi-decreti-e-regolamenti/scheda17011763.html',
        'first_law': None,
        'earlier_laws': ['l-1974-059', 'l-2000-095', 'l-2002-036', 'lc-2005-061', 'lrc-2005-182', 'lc-2011-001',
                         'lrc-2019-001', 'lc-2025-002'],
        'versions': [{
            'from': '2025-10-11',
            'source_url': DICH_URL,
            'sha256': hashlib.sha256(data).hexdigest(),
            'units': units,
            'note': 'Oldest version available in this build: the testo coordinato aggiornato al 26 settembre 2025, '
                    'dated 11 October 2025, the day Legge Costituzionale 26 settembre 2025 n.2 took effect '
                    '(fifteenth day after its publication on 26 September 2025).',
        }],
    }


LAWS = {
    'l-1974-059': ('Legge 8 luglio 1974 n.59', "Dichiarazione dei diritti dei cittadini e dei principi fondamentali dell'ordinamento sammarinese", '1974-07-08', '1974-07-17'),
    'l-2000-095': ('Legge 19 settembre 2000 n.95', "Modifica dell'articolo 4 della Legge 8 luglio 1974 n.59", '2000-09-19', None),
    'l-2002-036': ('Legge 26 febbraio 2002 n.36', 'Revisione della Legge 8 luglio 1974 n.59', '2002-02-26', None),
    'lc-2005-061': ('Legge Costituzionale 28 aprile 2005 n.61', "Revisione dell'articolo 16 della Dichiarazione dei Diritti", '2005-04-28', None),
    'lrc-2005-182': ('Legge di Revisione Costituzionale 14 dicembre 2005 n.182', "Abrogazione del comma quarto dell'articolo 3 della Legge 8 luglio 1974 n.59", '2005-12-14', None),
    'lc-2011-001': ('Legge Costituzionale 22 luglio 2011 n.1', 'Bandiera e stemma ufficiale della Repubblica di San Marino', '2011-07-22', '2011-07-25'),
    'lrc-2019-001': ('Legge di Revisione Costituzionale 28 marzo 2019 n.1', "Modifica all'articolo 4 della Legge 8 luglio 1974 n.59", '2019-03-28', '2019-03-28'),
    'lc-2025-002': ('Legge Costituzionale 26 settembre 2025 n.2', 'Inno Ufficiale della Repubblica di San Marino', '2025-09-26', '2025-09-26'),
}


def main() -> None:
    acts = [parse_dichiarazione()]
    corpus = {
        'country': {
            'code': 'SM', 'name': 'San Marino', 'slug': 'san-marino', 'lang': 'it', 'tz': 'Europe/San_Marino',
            'future_branch': 'futuro',
            'publisher': {'name': 'Segreteria Istituzionale (Consiglio Grande e Generale)',
                          'email': 'segreteria@consigliograndeegenerale-sm.invalid'},
            'default_in_force_rule': {
                'text': 'Each law used here states its own entry into force ("entra in vigore il quinto/quindicesimo '
                        'giorno successivo a quello della sua legale pubblicazione"); no general default rule was sourced.',
                'source': 'https://www.consigliograndeegenerale.sm/on-line/home/archivio-leggi-decreti-e-regolamenti.html'},
            'licence_note': 'Testi dal sito del Consiglio Grande e Generale (Segreteria Istituzionale, Repubblica di San '
                            'Marino). I testi non hanno carattere di autenticità; il testo autentico è quello del '
                            'Bollettino Ufficiale.',
        },
        'sources': [{
            'name': 'Consiglio Grande e Generale: Archivio Leggi and Testi Coordinati',
            'url': 'https://www.consigliograndeegenerale.sm/on-line/home/testi-coordinati.html',
            'retrieved': '2026-10-28',
            'requests': sum(1 for _ in open(CACHE / 'requests.jsonl', encoding='utf-8')),
            'licence': 'No licence stated; © Segreteria Istituzionale. Not authentic texts (site disclaimer).',
            'notes': 'Testi coordinati are served as ZIPs of two PDFs with a text layer (with and without notes).',
        }],
        'laws': {k: {'label': v[0], 'title': v[1], 'kind': 'law', 'enacted': v[2], 'published': v[3],
                     'url': None, 'temporary_until': None, 'restores': None, 'note': None} for k, v in LAWS.items()},
        'acts': acts,
        'applies': [],
        'decisions': [
            'First cut: the Dichiarazione dei Diritti is one "oldest version available" version (the current testo '
            'coordinato), credited to the publisher; the earlier laws are listed but not yet replayed.',
            'The version is dated 2025-10-11, when Legge Costituzionale 26 settembre 2025 n.2 (the latest change in the '
            'text, Art. 2-bis) took effect, not the testo coordinato date of 26 September 2025, so no text precedes its law.',
            'The "Norma Transitoria" heading refers to Legge 26 febbraio 2002 n.36 art. 9 and is left out of the act.',
        ],
        'ai_use': ['none: the text is parsed by code from the source PDF; no model wrote or classified legal text.'],
    }
    out = HERE / 'corpus.json'
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    tmp.replace(out)
    for a in acts:
        print(a['slug'], len(a['versions'][0]['units']), 'units')


if __name__ == '__main__':
    main()
