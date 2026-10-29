"""Unpack each retrieved download into pdf/<id>/ (under CACHE): note.pdf (the text with notes) and senza.pdf (the
copy whose name says "SENZA NOTE" or "NO NOTE", where there is one). A download that is a bare PDF is note.pdf.

    python -X utf8 unpack.py

Reads zip/<id>.bin (each matching its sha256 in data/source-sha256.tsv); build.py and check_repo.py read the
unpacked PDFs.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'


def unpack() -> None:
    """Each download into pdf/<id>/ (under CACHE): note.pdf (the text with notes) and senza.pdf (the copy whose name says
    "SENZA NOTE", where there is one). A download that is a bare PDF is note.pdf."""
    import zipfile
    for b in sorted((CACHE / 'zip').glob('*.bin')):
        out = CACHE / 'pdf' / b.stem
        out.mkdir(parents=True, exist_ok=True)
        if b.read_bytes()[:5] == b'%PDF-':
            (out / 'note.pdf').write_bytes(b.read_bytes())
            continue
        z = zipfile.ZipFile(b)
        pdfs = [i for i in z.infolist() if i.filename.lower().endswith('.pdf')]
        senza = [i for i in pdfs if re.search(r'senza note|\bno note', i.filename.lower())]
        note = [i for i in pdfs if i not in senza]
        if not senza and len(note) == 2 and sum('con note' in i.filename.lower() for i in note) == 1:
            # 17088418: "... con NOTE.pdf" and "... (2).pdf", the copy without notes
            senza = [i for i in note if 'con note' not in i.filename.lower()]
            note = [i for i in note if i not in senza]
        if len(note) != 1 or len(senza) > 1:
            sys.exit(f'{b.name}: expected one PDF with notes and at most one SENZA NOTE: {[i.filename for i in pdfs]}')
        (out / 'note.pdf').write_bytes(z.read(note[0]))
        if senza:
            (out / 'senza.pdf').write_bytes(z.read(senza[0]))


if __name__ == '__main__':
    unpack()
