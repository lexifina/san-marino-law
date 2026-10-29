# Reproducing this repository

Built on {{TODAY}} from the Consiglio Grande e Generale's "Testi coordinati", retrieved on {{FETCHED}}, by the
scripts in `tools/build/` (copied there as run). The sha256 of every file the build read (each download, and the
PDFs unpacked from it) is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those files can be
checked byte for byte before rebuilding. How the files were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| unpack.py | `{{SHA_UNPACK_PY}}` |
| parse.py | `{{SHA_PARSE_PY}}` |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_repo.py | `{{SHA_CHECK_REPO_PY}}` |

## Steps

With the retrieved downloads in place (`zip/<id>.bin`, each matching its sha256 in `data/source-sha256.tsv`), and
the retrieval day in `fetched_on.txt`:

```sh
pip install pymupdf          # parse.py; check_repo.py also needs poppler's pdftotext on the PATH
# 1. Unpack each download into pdf/<id>/: note.pdf (with notes) and senza.pdf (the copy named "SENZA NOTE" or
#    "NO NOTE", where there is one). A few downloads are a bare PDF (note.pdf only).
python unpack.py
# 2. Build. --today dates the documentation commit and is the latest date allowed.
python build.py ../san-marino-law --today {{TODAY}}
# 3. Check the letters and digits against the PDFs.
python check_repo.py ../san-marino-law
```

The site offers no bulk download: each testo coordinato is one download from its page.

## What the build produced

- {{TEXTS}} testi coordinati ({{PAGES}} PDF pages): {{ACTS}} acts, {{ARTICLES}} articles, {{NOTES}} notes.
- {{COMMITS}} commits: one per text (`Kind: consolidated`) and one documentation commit.
- Update dates from {{FIRST}} to {{LAST}}.
- {{AMENDMENT_ROWS}} rows in data/amendments.csv naming {{AMENDING_ACTS}} acts; {{MISSING_NOTES}} calls without a note
  and {{UNCALLED_NOTES}} notes without a call (data/issues.csv).

## Checks

```sh
git rev-list --merges --count main                  # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
python tools/in_force_on.py {{TODAY}} nuovo-codice-penale/legge-1974-17 art-1
python tools/build/check_repo.py .                  # letters and digits against the PDFs (needs the files)
```

Rebuilding twice from the same files gives the same `git rev-parse HEAD`.

## AI

The scripts, the README and these notes were written by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), working
for Lexifina. No AI model writes or changes legal text, and none runs when the repository is built or checked: the
build is the Python in `tools/build/`, run as recorded here.
