"""Looks up San Marino laws in the Consiglio Grande e Generale archive and caches their original texts.

    python -X utf8 scripts/san-marino-law/laws.py lookup N YEAR [N YEAR ...]   # fetch search + scheda + original PDF

For each (number, year) the archive search lists every document with that number and year (laws, decrees, ...);
each hit has a "scheda" page (type, number, date, link to the original text: a PDF under /contents/instance18/files/).
Everything goes through fetch.fetch (cached, logged). Offline use (parse.py) reads the same cache.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import zipfile
import io
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402

BASE = 'https://www.consigliograndeegenerale.sm'
ARCH = BASE + '/on-line/home/archivio-leggi-decreti-e-regolamenti'


def search_url(numero: str, anno: str) -> str:
    return (ARCH + '.html?P0_path=%2Fhome%2Ftomcat%2Findicizzazione%2Findexleggi&P0_paginazione=15&P0_pagina=1'
            '&P0_orderBy=index_lucene%2Cdata_ordered%2Cnumero&P0_order=asc%2Cdesc%2Cdesc&P0_operatorMustBe=yes'
            f'&P0_title=&P0_tipo=&P0_numero={numero}&P0_anno={anno}&annoiniziale=&annofinale=&P0_data_gg='
            '&P0_data_mm=&P0_data_aa=&P0_document=&P0_data_ordered=&indicericerca=-1')


def _text(b: bytes) -> str:
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b.decode('cp1252', errors='replace')


def search(numero: str, anno: str, offline: bool = False) -> list[dict]:
    t = _text(fetch.fetch(search_url(numero, anno), offline))
    hits = []
    for m in re.finditer(r'<div id="card_(\d+)"[^>]*><h3>(.*?)</h3>.*?href="([^"]*documento(\d+)\.html)".*?'
                         r'<div class="fl">(.*?)</div>', t, re.S):
        head = html.unescape(re.sub(r'\s+', ' ', m.group(2))).strip()
        hits.append({'card': m.group(1), 'head': head, 'doc': m.group(4),
                     'scheda': f'{ARCH}/scheda{m.group(1)}.html'})
    return hits


def scheda(url: str, offline: bool = False) -> dict:
    t = _text(fetch.fetch(url, offline))
    s = t[t.find('nav-path'):]
    pdf = re.search(r"filesize\('([^']+)'", s)
    plain = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)))
    out = {'pdf': BASE + pdf.group(1) if pdf else None}
    for k in ('tipo', 'anno', 'numero', 'data'):
        m = re.search(k + r':\s*(?:\xa0|\s)*([^\s]+(?:\s[A-Za-z]+)*)', plain)
        out[k] = m.group(1).strip() if m else None
    m = re.search(r'DETTAGLIO:\s*(.*?)\s*(?:\xa0|\s)*filesize', plain)
    out['title'] = m.group(1).strip(' \xa0') if m else None
    return out


def pdf_text(url: str, offline: bool = False) -> str:
    """Text layer of a cached PDF (pdftotext -layout). Empty string for a scan."""
    data = fetch.fetch(url, offline)
    path = fetch.cache_path(url)
    if data[:2] == b'PK':      # some documents are ZIPs of PDFs: take the first PDF
        z = zipfile.ZipFile(io.BytesIO(data))
        path = path.with_suffix('.pdf0')
        if not path.exists():
            path.write_bytes(z.read(z.infolist()[0]))
    out = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'], capture_output=True)
    return out.stdout.decode('utf-8', errors='replace')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == 'lookup':
        for n, y in zip(args[1::2], args[2::2]):
            for h in search(n, y):
                sc = scheda(h['scheda'])
                print(n, y, h['head'][:110], '|', sc.get('data'), sc.get('pdf'))
