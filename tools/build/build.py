"""Build the San Marino law repository from the retrieved "Testi coordinati" (unpack.py, parse.py).

    python -X utf8 scripts/san-marino-law/build.py ../san-marino-law-build --today YYYY-MM-DD [--limit N]

The Consiglio Grande e Generale publishes, under "Testi coordinati", consolidated texts of the main laws, grouped by
subject: a "testo coordinato" (one law with its amendments worked in) or a "raccolta coordinata" (several laws and
decrees on one subject). Each is a PDF made by the Segreteria Istituzionale, "aggiornato al" a stated date, with the
earlier wording and the amending provisions in footnotes. Only the current edition is published, so:

1. Each testo coordinato is one folder (`<subject>/`), each act in it a subfolder (`<kind>-<year>-<number>/`, or
   `<kind>-<year>-<mm>-<dd>/` for an unnumbered act), each
   article one file (`art-<n>.md`), one paragraph per line. Headings of Titles, Chapters and Sections go on the
   line(s) before the article they precede, as `## ...`. The cover (title, "aggiornato al", list of acts cited) is
   `title.md`; an act's heading and preamble are its `intro.md`; `index.txt` lists the files in reading order.
2. Footnotes stay in the file that calls them: the call is `[^n]` where the PDF has the superscript number, and the
   note text follows at the end of the file as `[^n]: ...` (further paragraphs indented four spaces). Notes nothing
   calls are in `notes-uncalled.md`. Each note's references to amending acts are listed in data/amendments.csv.
3. Each testo coordinato is one commit, `Kind: consolidated`, authored by the Segreteria Istituzionale, dated noon
   San Marino time on its "aggiornato al" date, which is also its `In-force:` date. Nobody is credited with single
   lines: the earlier text exists only as footnotes, not as an edition one could diff against.
4. One git fast-import, sorted, fixed dates: the same cache always gives the same hashes.
"""
import argparse
import csv
import io
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
SITE = 'https://www.consigliograndeegenerale.sm'
COMMITTER = 'Lexifina <san-marino@lexifina.com>'
PUBLISHER = ('Segreteria Istituzionale (Consiglio Grande e Generale)', 'segreteria-istituzionale@consigliograndeegenerale-sm.invalid')
MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre',
          'novembre', 'dicembre']
MONTH_RE = '|'.join(MONTHS)


def fix_title(t: str) -> str:
    """index.json was read as Latin-1; the site writes Windows-1252 (dashes, quotes)."""
    try:
        t = t.encode('latin-1').decode('cp1252')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return re.sub(r'\s+', ' ', t).strip()


def update_date(title: str, pdf: Path, fetched_on: str) -> tuple[str, str]:
    """(day, source): the latest "aggiornato al" date that the title or the PDF's first two pages give (a cover
    is sometimes left at an earlier date than the page after it); a month alone gives its first day; with none,
    the retrieval date."""
    def full(s: str) -> list[str]:
        out = []
        for m in re.finditer(rf"aggiornat\w*\s+(?:al\s+|all['’]\s*|a\s+)?(\d{{1,2}})[º°]?\s+({MONTH_RE})\s+(\d{{4}})", s, re.I):
            out.append(f'{int(m.group(3)):04d}-{MONTHS.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}')
        for m in re.finditer(r'aggiornat\w*\s+(?:al\s+)?(\d{1,2})/(\d{1,2})/(\d{4})', s, re.I):
            out.append(f'{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}')
        return out
    import pymupdf
    first = re.sub(r'\s+', ' ', ' '.join(p.get_text() for p in list(pymupdf.open(pdf))[:2]))
    found = [(d, 'title') for d in full(title)] + [(d, 'pdf') for d in full(first)]
    if found:
        day = max(d for d, _ in found)
        return day, 'title' if (day, 'title') in found else 'pdf'
    m = re.search(rf'(?:vigente|aggiornat\w*)\s+(?:a|al)\s+({MONTH_RE})\s+(\d{{4}})', first + ' ' + title, re.I)
    if m:
        return f'{int(m.group(2)):04d}-{MONTHS.index(m.group(1).lower()) + 1:02d}-01', 'month'
    return fetched_on, 'retrieved'


def slug(t: str, n: int = 50) -> str:
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    t = re.sub(r"['’]", '', t)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    if len(t) > n:
        t = t[:n + 1].rsplit('-', 1)[0]  # whole words
    return t or 'testo'


def short_title(t: str) -> str:
    """The subject of a title: without "Testo coordinato", the update date, the act's designation or "norme in
    materia di"."""
    s = re.sub(r'\s*\((?:aggiornat|aggiornamento)[^)]*\)\s*$', '', t, flags=re.I)
    s = re.sub(r'\s*[-–—]?\s*testo coordinato con .*$', '', s, flags=re.I)
    for _ in range(3):
        s = re.sub(r'^(?:testo\s+coordinato|raccolta\s+coordinata)\s*[-–—]?\s*', '', s, flags=re.I)
        s = re.sub(rf'^(?:legge|decreto)[a-z ]*?\s\d{{1,2}}\s+(?:{MONTH_RE})\s+\d{{4}}\s*n\.\s*\d+\s*(?:[-–—]\s*)?', '', s, flags=re.I)
        s = re.sub(r'^(?:(?:delle?\s+)?norme\s+|disposizioni\s+)?(?:in\s+materia\s+(?:di\s+)?|che\s+disciplinano\s+|'
                   r'sull[ae]?\s*[\'’]?\s*|sul\s+|di\s+)', '', s, flags=re.I)
        s = re.sub(r'^(?:legge\s+(?:sulle?|sui)\s+)', '', s, flags=re.I)
    return s.strip(' -–—') or t


def art_name(num: str) -> str:
    return 'art-' + re.sub(r'[^0-9a-z-]+', '-', num.lower()).strip('-')


ACT_REF = re.compile(rf'^\s*(?P<kind>Legge(?:\s+(?:Costituzionale|Qualificata))?|Decreto(?:\s*[-–]\s*Legge|\s+Delegato|\s+Reggenziale|\s+Consiliare)?|'
                     rf'Regolamento(?:\s+Consiliare)?)\s+(?P<d>\d{{1,2}})[º°]?\s+(?P<m>{MONTH_RE})\s+(?P<y>\d{{4}})\s*,?\s*(?:n\.?|nr\.?)\s*(?P<n>\d+)'
                     rf'(?P<rest>.*)$', re.I)


def note_rows(coll: str, path: str, num: str, paras: list[str]) -> list[list[str]]:
    """One row per amending act a note names at the start of a paragraph (its heading lines), with the section of
    the note it is in: 'original' (Testo originario), 'amendment' (Modifiche legislative) or 'note'."""
    rows = []
    section = 'note'
    for p in paras:
        low = p.lower()
        if low.startswith('testo originario') or low.startswith('testo previgente'):
            section = 'original'
            rows.append([coll, path, num, section, '', '', p[:200]])
            continue
        if low.startswith('modifiche legislative') or low.startswith('modifica legislativa'):
            section = 'amendment'
            continue
        m = ACT_REF.match(p)
        if m and len(p) < 260:
            d = f"{int(m['y']):04d}-{MONTHS.index(m['m'].lower()) + 1:02d}-{int(m['d']):02d}"
            act = f"{re.sub(r'\s+', ' ', m['kind']).title()} {int(m['d'])} {m['m'].lower()} {m['y']} n.{m['n']}"
            rows.append([coll, path, num, section, act, d, p[:200]])
    return rows


def build_text(item: dict) -> dict:
    import parse
    pdf = CACHE / 'pdf' / item['id'] / 'note.pdf'
    r = parse.parse(pdf)
    coll = item['dir']
    files: dict[str, list[str]] = {}
    order: list[str] = []
    calls_in: dict[str, list[str]] = {}
    used: dict[str, int] = {}

    def add(path: str, lines: list[str]) -> None:
        if path in files:
            files[path] += lines
            return
        files[path] = list(lines)
        order.append(path)

    acts = []
    for a in r['acts']:
        if a['key'] == 'intro':
            if a['intro']:
                add('title.md', a['intro'])
            base = None
        else:
            base = a['key']
        if a['key'] != 'intro':
            acts.append({'key': a['key'], 'head': a.get('head') or '', 'date': a.get('date', ''), 'articles': len(a['articles'])})
            if a['intro']:
                # an act named twice in one text (a code, then the law that enacts it): a second intro file
                p = f'{base}/intro'
                k = used.get(p, 0) + 1
                used[p] = k
                add(f'{p}.md' if k == 1 else f'{p}--{k}.md', a['intro'])
        for art in a['articles']:
            name = art_name(art['num'])
            p = f'{base}/{name}' if base else name
            k = used.get(p, 0) + 1
            used[p] = k
            add(f'{p}.md' if k == 1 else f'{p}--{k}.md', art['lines'])
    # notes into the files that call them
    out: dict[str, str] = {}
    rows: list[list[str]] = []
    called = set()
    for path in order:
        lines = files[path]
        nums = []
        for l in lines:
            for n in re.findall(r'\[\^(\d+)\]', l):
                if n not in nums:
                    nums.append(n)
        foot = []
        for n in nums:
            if n in r['notes']:
                called.add(n)
                paras = r['notes'][n] or ['']
                foot.append(f'[^{n}]: {paras[0]}'.rstrip())
                foot += [f'    {p}' for p in paras[1:]]
                rows += note_rows(coll, f'{coll}/{path}', n, paras)
        out[path] = '\n'.join(lines + ([''] + foot if foot else [])) + '\n'
    missing = sorted({n for path in order for l in files[path] for n in re.findall(r'\[\^(\d+)\]', l)} - set(r['notes']),
                     key=int)
    left = [k for k in r['note_order'] if k not in called]
    if left:
        lines = []
        for k in left:
            paras = r['notes'][k] or ['']
            lines.append(f'[^{k}]: {paras[0]}'.rstrip())
            lines += [f'    {p}' for p in paras[1:]]
            rows += note_rows(coll, f'{coll}/notes-uncalled.md', k, paras)
        out['notes-uncalled.md'] = '\n'.join(lines) + '\n'
        order.append('notes-uncalled.md')
    out['index.txt'] = '\n'.join(order) + '\n'
    files_full = {f'{coll}/{p}': t for p, t in out.items()}
    return {'files': files_full, 'rows': rows, 'acts': acts, 'missing_notes': missing, 'uncalled': left,
            'notes': len(r['notes']), 'articles': sum(len(a['articles']) for a in r['acts']), 'pages': r['pages']}


# ---------------------------------------------------------------------------------------------------- dates

def last_sunday(y: int, m: int) -> date:
    d = date(y, m, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def tz_hours(d: date) -> int:
    """Central European Time, EU summer time (since 1996: last Sunday of March to last Sunday of October); noon is
    always after the 01:00 UTC switch, so the switch days take the new offset. San Marino follows Italy."""
    return 2 if last_sunday(d.year, 3) <= d < last_sunday(d.year, 10) else 1


def git_date(day: str) -> str:
    d = datetime.strptime(day, '%Y-%m-%d').date()
    h = tz_hours(d)
    ts = int(datetime(d.year, d.month, d.day, 12 - h, 0, tzinfo=timezone.utc).timestamp())
    return f'{ts} +0{h}00'


def message(item: dict, built: dict) -> str:
    day, src = item['day'], item['date_source']
    title = item['title']
    how = {'title': f'"aggiornato al" {day}, as its title says',
           'pdf': f'"aggiornato al" {day}, as its first page says',
           'month': f'"vigente a" the month of {day[:7]} (no day is given; dated the first of the month)',
           'retrieved': f'retrieved {day} (the text gives no update date)'}[src]
    subject = f"{item['short']}: testo coordinato, {'aggiornato al ' + day if src in ('title', 'pdf') else ('vigente a ' + day[:7] if src == 'month' else 'retrieved ' + day)}"
    body = [f'The consolidated text "{title}" as the Consiglio Grande e Generale publishes it,',
            f'{how}.',
            '',
            'The site keeps only the current edition, so this commit holds the whole text and nobody is credited',
            'with single lines. Earlier wording and the amending provisions are in the footnotes, kept in the files',
            f"({built['notes']} notes); data/amendments.csv lists the acts they name."]
    acts = [a['head'] for a in built['acts']]
    trailers = ['Kind: consolidated', f'In-force: {day}', f'Consolidated: {day}', f'Date-source: {src}',
                f"Acts: {len(built['acts'])}", f"Articles: {built['articles']}", f"Notes: {built['notes']}",
                f"Source: {SITE}{item['url']}"]
    return '\n'.join([subject, '', *body, '', *trailers]) + '\n'


def fast_import(repo: Path, commits: list[tuple], docs: dict[str, bytes], today: str) -> None:
    buf = io.BytesIO()
    w = buf.write
    name, email = PUBLISHER
    for item, built in commits:
        when = git_date(item['day'])
        w(b'commit refs/heads/main\n')
        w(f'author {name} <{email}> {when}\ncommitter {COMMITTER} {when}\n'.encode())
        m = message(item, built).encode('utf-8')
        w(f'data {len(m)}\n'.encode() + m + b'\n')
        for path, text in sorted(built['files'].items()):
            t = text.encode('utf-8')
            w(f'M 100644 inline {path}\ndata {len(t)}\n'.encode() + t + b'\n')
        w(b'\n')
    when = git_date(today)
    msg = (f'Documentation: README, REPRODUCE, tools, laws.csv and data\n\n'
           f'Built on {today} from the retrieved files of the Consiglio Grande e Generale.\n\nKind: documentation\n').encode()
    w(b'commit refs/heads/main\n')
    w(f'author {COMMITTER} {when}\ncommitter {COMMITTER} {when}\n'.encode())
    w(f'data {len(msg)}\n'.encode() + msg + b'\n')
    for path, data in sorted(docs.items()):
        w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
    w(b'\n')
    r = subprocess.run(['git', '-C', str(repo), 'fast-import', '--quiet', '--force'], input=buf.getvalue(), capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode('utf-8', 'replace')[-3000:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=1)
    args = ap.parse_args()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    fetched_on = (CACHE / 'fetched_on.txt').read_text('utf-8').strip()
    if fetched_on > args.today:
        sys.exit(f'retrieval date {fetched_on} is after --today')
    index = json.loads((CACHE / 'index.json').read_text('utf-8'))
    items = []
    used = set()
    for d in sorted(index, key=lambda d: int(d['id'])):
        title = fix_title(d['title'])
        short = short_title(title)
        s = slug(short)
        k = 2
        while s in used:
            s = f'{slug(short)}-{k}'
            k += 1
        used.add(s)
        day, src = update_date(title, CACHE / 'pdf' / d['id'] / 'note.pdf', fetched_on)
        items.append({'id': d['id'], 'url': d['url'], 'title': title, 'short': short, 'dir': s, 'day': day,
                      'date_source': src, 'categories': d['categories'],
                      'senza': (CACHE / 'pdf' / d['id'] / 'senza.pdf').exists()})
    if args.limit:
        items = items[:args.limit]
    if args.workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(args.workers) as pool:
            results = list(pool.map(build_text, items))  # in order, so the result does not depend on timing
    else:
        results = [build_text(i) for i in items]
    commits = []
    for item, built in zip(items, results):
        if item['day'] > args.today:
            sys.exit(f"{item['id']}: date {item['day']} after --today")
        commits.append((item, built))
    commits.sort(key=lambda c: (c[0]['day'], int(c[0]['id'])))
    print(f"{len(commits)} texts, {sum(len(b['acts']) for _, b in commits)} acts, "
          f"{sum(b['articles'] for _, b in commits)} articles, {sum(b['notes'] for _, b in commits)} notes", flush=True)

    import docs as docmod
    docs = docmod.render(commits, args.today, fetched_on)

    repo = args.repo
    repo.mkdir(parents=True, exist_ok=True)
    if (repo / '.git').exists():
        import os
        import shutil
        import stat

        def onerr(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(repo / '.git', onerror=onerr)
        for child in repo.iterdir():
            shutil.rmtree(child, onerror=onerr) if child.is_dir() else child.unlink()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    for k, v in (('core.autocrlf', 'false'), ('core.longpaths', 'true'), ('core.quotepath', 'false')):
        subprocess.run(['git', '-C', str(repo), 'config', k, v], check=True)
    subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', 'https://github.com/lexifina/san-marino-law.git'], check=True)
    fast_import(repo, commits, docs, args.today)
    subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-f', 'main'], check=True)
    head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(repo), 'rev-list', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip()
    print(f'built {repo}: {count} commits, head {head}', flush=True)


if __name__ == '__main__':
    main()
