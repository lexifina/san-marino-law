"""Independent check of the San Marino repository against the PDFs, with a different PDF reader (poppler's
pdftotext, not the PyMuPDF that parse.py uses) and nothing of parse.py.

    python -X utf8 scripts/san-marino-law/check_repo.py ../san-marino-law-build [--ref HEAD] [--show N]

Words are runs of letters and runs of digits (so a note number set against a word still counts as its own word).

1. In order, against the copy "SENZA NOTE" (without notes) where the Consiglio publishes one: the words of the
   text's files in index order, without the notes and the note calls, against the words of the PDF. Lines that
   hold only a page number are left out of the PDF's words. Reports every difference (difflib on the words).
2. As a multiset, for every text, against the PDF with notes: the words of all its files (text, calls, notes and
   their numbers) against the words of the PDF, page numbers left out. Reports recall (share of the PDF's words in
   the repository) and precision (share of the repository's words in the PDF).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
PDF = HERE / '.cache' / 'pdf'
WORD = re.compile(r'[^\W\d_]+|\d+')


def pdf_words(path: Path) -> list[str]:
    cached = path.with_suffix('.pdftotext.txt')  # pdftotext's output, kept beside the PDF (same PDF, same text)
    if not cached.exists() or cached.stat().st_mtime < path.stat().st_mtime:
        r = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(path), '-'], capture_output=True)
        cached.write_bytes(r.stdout)
    text = cached.read_bytes().decode('utf-8', 'replace')
    lines = [l for l in text.split('\n') if not re.fullmatch(r'\s*[-–]?\s*\d{1,4}\s*[-–]?\s*', l)]
    return words('\n'.join(lines))


def words(text: str) -> list[str]:
    text = text.replace('­', '')
    return WORD.findall(text)


def token_diff(a: list[str], b: list[str]) -> list[tuple[list[str], list[str]]]:
    """(PDF words, repository words) of each hunk where the two differ: git's diff (Myers), one word a line."""
    with tempfile.TemporaryDirectory() as tmp:
        pa, pb = Path(tmp) / 'pdf', Path(tmp) / 'repo'
        pa.write_text('\n'.join(a) + '\n', 'utf-8')
        pb.write_text('\n'.join(b) + '\n', 'utf-8')
        out = subprocess.run(['git', 'diff', '--no-index', '--no-color', '-U0', str(pa), str(pb)], capture_output=True).stdout
    hunks = []
    for line in out.decode('utf-8', 'replace').split('\n'):
        if line.startswith('@@'):
            hunks.append(([], []))
        elif hunks and line.startswith('-') and not line.startswith('---'):
            hunks[-1][0].append(line[1:])
        elif hunks and line.startswith('+') and not line.startswith('+++'):
            hunks[-1][1].append(line[1:])
    return hunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--ref', default='HEAD')
    ap.add_argument('--show', type=int, default=3, help='differences to print per text')
    ap.add_argument('--record', action='store_true', help='write the summary to verification.json')
    args = ap.parse_args()

    def git(*a: str) -> str:
        return subprocess.run(['git', '-C', str(args.repo), *a], capture_output=True, encoding='utf-8', errors='replace').stdout

    batch = subprocess.Popen(['git', '-C', str(args.repo), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def show(spec: str) -> str:
        """A file's text at the ref, read through one `git cat-file --batch`."""
        batch.stdin.write(spec.encode('utf-8') + b'\n')
        batch.stdin.flush()
        head = batch.stdout.readline().split()
        if len(head) < 3 or head[1] != b'blob':
            return ''
        data = batch.stdout.read(int(head[2]))
        batch.stdout.read(1)
        return data.decode('utf-8', 'replace')

    log = git('log', args.ref, '--format=%x1e%(trailers:key=Source,valueonly)%x1f%(trailers:key=Kind,valueonly)%x1f', '--name-only')
    texts = []
    for rec in log.split('\x1e'):
        p = rec.strip('\n').split('\x1f')
        if len(p) == 3 and p[1].strip() == 'consolidated':
            did = re.search(r'documento(\d+)', p[0]).group(1)
            folder = next(f.split('/')[0] for f in p[2].split('\n') if '/' in f)
            texts.append((did, folder))
    tot_words = tot_diff = tot_moved = 0
    ordered = 0
    low = []
    rec_all = []
    for did, folder in sorted(texts):
        names = [n for n in show(f'{args.ref}:{folder}/index.txt').split('\n') if n]
        body, full = [], []
        defs: dict[str, list[str]] = {}  # a note called from several files is written in each: count it once
        for n in names:
            t = show(f'{args.ref}:{folder}/{n}')
            keep, calls = [], []
            note = None
            for line in t.split('\n'):
                m = re.match(r'\[\^(\d+)\]: ?(.*)$', line)
                if m:
                    note = m.group(1)
                    first = note not in defs
                    defs.setdefault(note, [])
                    if first:
                        defs[note].append(m.group(2))
                    else:
                        note = '-'  # a copy: skip its lines
                    continue
                if note is not None and (line.startswith('    ') or not line):
                    if note != '-':
                        defs[note].append(line)
                    continue
                note = None
                calls.append(re.sub(r'\[\^(\d+)\]', r' \1 ', line))
                keep.append(re.sub(r'\[\^\d+\]', ' ', re.sub(r'^#+ ', '', line)))
            full.append('\n'.join(calls))
            if n != 'notes-uncalled.md':
                body.append('\n'.join(keep))
        full += [f'{k} ' + '\n'.join(v) for k, v in defs.items()]
        senza = PDF / did / 'senza.pdf'
        if senza.exists():
            a, b = pdf_words(senza), words('\n'.join(body))
            hunks = token_diff(a, b)
            # a word the PDF reader joins across a line-end hyphen ("nulla-osta" -> "nullaosta") has the same
            # letters and digits: not a difference
            real = [(d, i) for d, i in hunks if ''.join(d) != ''.join(i)]
            dels = Counter(w for d, _ in real for w in d)
            ins = Counter(w for _, i in real for w in i)
            moved = sum((dels & ins).values())  # the same words in another order (table cells)
            nd = sum((dels - ins).values()) + sum((ins - dels).values())
            tot_words += len(a)
            tot_diff += nd
            tot_moved += moved
            ordered += 1
            print(f'{did} {folder}: SENZA NOTE {len(a)} words; {nd} differ, {moved} in another order', flush=True)
            shown = 0
            both = dels & ins
            for d, i in real:
                if all(w in both for w in d) and all(w in both for w in i):
                    continue
                if shown < args.show:
                    print(f'    pdf {" ".join(d)[:150]!r} | repo {" ".join(i)[:150]!r}')
                shown += 1
        a, b = Counter(pdf_words(PDF / did / 'note.pdf')), Counter(words('\n'.join(full)))
        common = sum((a & b).values())
        recall, precision = common / max(1, sum(a.values())), common / max(1, sum(b.values()))
        rec_all.append((recall, precision, did, folder, sum(a.values())))
        if recall < 0.999 or precision < 0.999:
            low.append((recall, precision, did, folder, a - b, b - a))
    print()
    print(f'ordered check against SENZA NOTE: {ordered} texts, {tot_words} words, {tot_diff} differ '
          f'({100 * tot_diff / max(1, tot_words):.4f}%), {tot_moved} in another order')
    pw = sum(r[4] for r in rec_all)
    print(f'multiset check against the PDF with notes: {len(rec_all)} texts, {pw} words; '
          f'{len(rec_all) - len(low)} texts at recall and precision >= 99.9%')
    for recall, precision, did, folder, miss, extra in sorted(low):
        print(f'  {did} {folder}: recall {recall:.4f} precision {precision:.4f}; pdf only {sum(miss.values())} '
              f'{list(miss.most_common(8))}; repo only {sum(extra.values())} {list(extra.most_common(8))}')
    if args.record:
        # the summary the next build's README quotes
        cw = sum(r[4] * r[0] for r in rec_all)
        out = {'checked_head': git('rev-parse', args.ref).strip(), 'senza_texts': ordered, 'senza_words': tot_words,
               'senza_differ': tot_diff, 'senza_moved': tot_moved, 'notes_texts': len(rec_all), 'notes_words': pw,
               'notes_texts_999': len(rec_all) - len(low), 'notes_recall': round(cw / max(1, pw), 4),
               'notes_min_recall': round(min(r[0] for r in rec_all), 4)}
        (HERE / 'verification.json').write_text(json.dumps(out, indent=1) + '\n', 'utf-8')


if __name__ == '__main__':
    main()
