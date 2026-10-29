"""Print a San Marino testo coordinato, one act in it, or one article, as this repository has it on a date.

    python tools/in_force_on.py 2026-10-01 codice-di-procedura-penale-2-gennaio-1878                    # the whole text
    python tools/in_force_on.py 2026-10-01 patrocinio-gratuito/legge-1884-12-20                         # one act in it
    python tools/in_force_on.py 2026-10-01 nuovo-codice-penale/legge-1974-17 art-1                      # one article

Reads the `In-force:` trailers (the "aggiornato al" date of each edition). The Consiglio Grande e Generale keeps
only the current edition, so a date before a text's edition has no version here. Standard library only.
"""
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def commit_on(day: str, path: str) -> tuple[str | None, str | None]:
    """The last commit on or before `day` that touched `path`, and the earliest date known for it."""
    fmt = '%H%x1f%(trailers:key=In-force,valueonly,separator=)'
    earliest = None
    for line in git('log', '--first-parent', f'--format={fmt}', 'main', '--', path).splitlines():
        h, d = (line.split('\x1f') + [''])[:2]
        d = d.strip()
        if not d:
            continue
        earliest = d
        if d <= day:
            return h, d
    return None, earliest


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, where = sys.argv[1], sys.argv[2].strip('/')
    unit = sys.argv[3] if len(sys.argv) > 3 else None
    if unit and unit.endswith('.md'):
        unit = unit[:-3]
    path = f'{where}/{unit}.md' if unit else where
    h, earliest = commit_on(day, path)
    if not h:
        if earliest:
            sys.exit(f'{path}: no version on or before {day}; the record starts at {earliest}, the edition the '
                     'Consiglio Grande e Generale publishes (it keeps no earlier edition)')
        sys.exit(f'{path}: not found')
    if unit:
        sys.stdout.write(git('show', f'{h}:{path}'))
        return
    text, _, act = where.partition('/')
    names = [n for n in git('show', f'{h}:{text}/index.txt').splitlines() if n]
    if act:
        names = [n for n in names if n.startswith(act + '/')]
    for n in names:
        sys.stdout.write(git('show', f'{h}:{text}/{n}') + '\n')


if __name__ == '__main__':
    main()
