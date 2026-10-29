"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, laws.csv, data/ and tools for the San Marino law repository
(called by build.py)."""
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
# Published with the record. The retrieval script and its notes stay private (the user's rule of 2026-10-29), and
# publish_gate (gitlaw_common, private) checks every file before it is written.
BUILD_FILES = ('unpack.py', 'parse.py', 'build.py', 'docs.py', 'check_repo.py')
sys.path.insert(0, str(HERE.parent / 'gitlaw_common'))
try:
    from publish_gate import publish_gate
except ImportError:          # an outside reader rebuilding from the published tools: no private rule to apply
    if os.environ.get('GITLAW_PUBLIC_REBUILD') != '1':
        raise SystemExit('publish gate missing: run from lexifina/scripts, or set GITLAW_PUBLIC_REBUILD=1')

    def publish_gate(files): return files
CITATION = {'file': r'([a-z0-9-]+/[a-z-]+-[0-9]{4}-[0-9]+)/art-([0-9]+(?:-[a-z]+)?)(?:--[0-9]+)?\.md',
            'cites': r'(^|[^0-9A-Za-z])([Aa]rticol[oi]|[Aa]rt\.) ?{n}([^0-9]|$)'}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def source_sums() -> str:
    paths = sorted((CACHE / 'zip').glob('*.bin')) + sorted((CACHE / 'pdf').glob('*/*.pdf'))
    return ''.join(f"{p.relative_to(CACHE).as_posix()}\t{_sha(p)}\n" for p in paths)


def render(commits: list[tuple], today: str, fetched_on: str) -> dict[str, bytes]:
    items = [i for i, _ in commits]
    days = sorted(i['day'] for i in items)
    acts = sum(len(b['acts']) for _, b in commits)
    arts = sum(b['articles'] for _, b in commits)
    notes = sum(b['notes'] for _, b in commits)
    rows = [r for _, b in commits for r in b['rows']]
    amending = {r[4] for r in rows if r[4]}
    missing = sum(len(b['missing_notes']) for _, b in commits)
    uncalled = sum(len(b['uncalled']) for _, b in commits)
    src = Counter(i['date_source'] for i in items)
    stats = {
        'today': today, 'fetched': fetched_on, 'texts': len(items), 'acts': acts, 'articles': arts, 'notes': notes,
        'commits': len(commits) + 1, 'first': days[0], 'last': days[-1], 'amending_acts': len(amending),
        'amendment_rows': len(rows), 'missing_notes': missing, 'uncalled_notes': uncalled,
        'senza': sum(1 for i in items if i['senza']), 'pages': sum(b['pages'] for _, b in commits),
        'dated_title': src['title'] + src['pdf'], 'dated_month': src['month'], 'dated_retrieved': src['retrieved'],
    }

    vf = HERE / 'verification.json'
    ver = json.loads(vf.read_text('utf-8')) if vf.exists() else {}
    if ver:
        stats.update({
            'v_senza_texts': ver['senza_texts'], 'v_senza_words': f"{ver['senza_words']:,}",
            'v_senza_differ': f"{ver['senza_differ']:,}", 'v_senza_pct': f"{100 * ver['senza_differ'] / ver['senza_words']:.2f}",
            'v_senza_moved': f"{ver['senza_moved']:,}", 'v_notes_texts': ver['notes_texts'],
            'v_notes_words': f"{ver['notes_words']:,}", 'v_notes_999': ver['notes_texts_999'],
            'v_notes_recall': f"{100 * ver['notes_recall']:.2f}", 'v_notes_min': f"{100 * ver['notes_min_recall']:.2f}",
            'v_head': ver['checked_head'][:7]})

    def fill(t: str) -> str:
        for k, v in stats.items():
            t = t.replace('{{' + k.upper() + '}}', str(v))
        for name in BUILD_FILES:
            t = t.replace('{{SHA_' + name.upper().replace('.', '_') + '}}', _sha(HERE / name))
        return t

    laws_csv = _csv([['folder', 'title', 'updated', 'date_source', 'acts', 'articles', 'notes', 'senza_note_pdf',
                      'categories', 'source']] +
                    [[i['dir'] + '/', i['title'], i['day'], i['date_source'], len(b['acts']), b['articles'], b['notes'],
                      'yes' if i['senza'] else 'no', ' | '.join(i['categories']),
                      'https://www.consigliograndeegenerale.sm' + i['url']] for i, b in sorted(commits, key=lambda c: c[0]['dir'])])
    acts_csv = _csv([['folder', 'act', 'heading', 'date', 'articles']] +
                    [[i['dir'] + '/', a['key'], a['head'], a['date'], a['articles']] for i, b in commits for a in b['acts']])
    amend_csv = _csv([['text', 'file', 'note', 'section', 'act', 'act_date', 'line']] + sorted(rows))
    issues = []
    for i, b in commits:
        for n in b['missing_notes']:
            issues.append([i['dir'] + '/', n, 'called in the text, but the PDF has no note with this number'])
        for n in b['uncalled']:
            issues.append([i['dir'] + '/', n, 'a note nothing in the text calls (kept in notes-uncalled.md)'])
        if i['date_source'] in ('month', 'retrieved'):
            issues.append([i['dir'] + '/', '', f"no full update date; dated by {i['date_source']}: {i['day']}"])
    issues_csv = _csv([['text', 'note', 'issue']] + issues)

    corpus = {
        'corpus': 'sm/national/acts',
        'name': 'Testi coordinati of the Republic of San Marino (consolidated texts of the Consiglio Grande e Generale)',
        'label': 'San Marino',
        'language': 'it',
        'history': 'current-only',
        'texts': len(items),
        'history_from': days[0],
        'record_to': days[-1],
        'record_note': 'The Consiglio Grande e Generale publishes only the current edition of each testo coordinato, so '
                       'each has one version here, dated by its "aggiornato al" date. Earlier wording is kept as the '
                       "footnotes print it (Testo originario, Modifiche legislative) and the amending acts they name are "
                       'in data/amendments.csv. The texts cover the main subjects, not every San Marino law.',
        'built': today,
        'baseline_trailer': 'Consolidated',
        'in_force_trailer': 'In-force',
        'dates': {'commit': 'the "aggiornato al" date of each testo coordinato',
                  'baseline_trailer': 'Consolidated', 'other_trailers': ['Date-source'],
                  'time': '12:00 Europe/San_Marino (CET/CEST)'},
        'author': {'consolidated': 'Segreteria Istituzionale (Consiglio Grande e Generale)', 'amendment': 'none',
                   'unexplained': 'Segreteria Istituzionale (Consiglio Grande e Generale)'},
        'legal_basis': 'Legge 25 gennaio 1991 n.8 (diritto d\'autore), art. 98(f): free reproduction, even in full, of '
                       'the acts of the State and of public administrations',
        'citation': CITATION,
        'tool': 'tools/in_force_on.py',
    }
    files = {
        'corpus.json': (json.dumps(corpus, indent=2, ensure_ascii=False) + '\n').encode('utf-8'),
        'README.md': fill((REPO_FILES / 'README.md').read_text('utf-8')).encode('utf-8'),
        'REPRODUCE.md': fill((REPO_FILES / 'REPRODUCE.md').read_text('utf-8')).encode('utf-8'),
        'SOURCES.md': fill((REPO_FILES / 'SOURCES.md').read_text('utf-8')).encode('utf-8'),
        'LICENSE': (REPO_FILES / 'LICENSE').read_bytes(),
        'laws.csv': laws_csv,
        'data/acts.csv': acts_csv,
        'data/amendments.csv': amend_csv,
        'data/issues.csv': issues_csv,
        'data/stats.json': (json.dumps(stats, indent=1, sort_keys=True) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': source_sums().encode('utf-8'),
        **({'data/verification.json': vf.read_bytes()} if ver else {}),
        'tools/in_force_on.py': (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes(),
    }
    for name in BUILD_FILES:
        files[f'tools/build/{name}'] = (HERE / name).read_bytes()
    for name in ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE'):
        files[f'tools/build/repo/{name}'] = (REPO_FILES / name).read_bytes()
    files['tools/build/repo/tools/in_force_on.py'] = (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes()
    return publish_gate(files)
