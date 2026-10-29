# Reproducing this repository

Built on {{TODAY}} from the Consiglio Grande e Generale's "Testi coordinati", retrieved on {{FETCHED}}, by the
scripts in `tools/build/` (copied there as run).

| Script | sha256 |
| --- | --- |
| fetch.py | `{{SHA_FETCH_PY}}` |
| parse.py | `{{SHA_PARSE_PY}}` |
| build.py | `{{SHA_BUILD_PY}}` |
| docs.py | `{{SHA_DOCS_PY}}` |
| check_repo.py | `{{SHA_CHECK_REPO_PY}}` |

## Steps

```sh
pip install pymupdf          # parse.py; check_repo.py also needs poppler's pdftotext on the PATH
# 1. The index page, the 37 subject pages and the 65 downloads (one request at a time, 1 s apart; resumable),
#    then each download unpacked into .cache/pdf/<id>/: note.pdf (with notes) and senza.pdf (the copy named
#    "SENZA NOTE" or "NO NOTE", where there is one). A few downloads are a bare PDF (note.pdf only).
python fetch.py
# 2. Build. --today dates the documentation commit and is the latest date allowed.
python build.py ../san-marino-law --today {{TODAY}}
# 3. Check the letters and digits against the PDFs.
python check_repo.py ../san-marino-law
```

## robots.txt and bulk data

Checked on 2026-10-28. `https://www.consigliograndeegenerale.sm/robots.txt` answers HTTP 403: no file is served.
RFC 9309 (section 2.3.1.3) treats a 4xx answer as "unavailable", so crawling is allowed; it names no AI crawler
download: each testo coordinato is one download from its page.

## Fetch rate

No Crawl-delay is set. `fetch.py` sends one request at a time and waits one second after each: 1 index page, 37
subject pages and 65 downloads, about 3 minutes in all. Every answer, including errors, is cached under `.cache/`
(git-ignored), so a rerun asks for nothing again. The scripts call `curl`.

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
python tools/build/check_repo.py .                  # letters and digits against the PDFs (needs the cache)
```

Rebuilding twice from the same files gives the same `git rev-parse HEAD`.
