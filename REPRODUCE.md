# Reproducing this repository

Built on 2026-10-29 from the Consiglio Grande e Generale's "Testi coordinati", retrieved on 2026-10-28, by the
scripts in `tools/build/` (copied there as run).

| Script | sha256 |
| --- | --- |
| fetch.py | `901d07560a351cb55c70b0abddb9b42e3346827125c3f284dea89d70dcf83b8c` |
| parse.py | `dee888b18c5397f6d64f4bcd4bd870894cb618ef8b03927dd47a6ee892acacd2` |
| build.py | `1b9fd7ed70b523be3596deae3e3a5663c90e77a2a3be47da97932d122d5a1ef3` |
| docs.py | `f057d9e41c12a4353d7689f757311349f4c1e71064889810dd09f2c02e8b66cd` |
| check_repo.py | `74fecfb512e5b99729a032b72dee8487039cdc8c60b8fc930113fdccf4c63791` |

## Steps

```sh
pip install pymupdf          # parse.py; check_repo.py also needs poppler's pdftotext on the PATH
# 1. The index page, the 37 subject pages and the 65 downloads (one request at a time, 1 s apart; resumable),
#    then each download unpacked into .cache/pdf/<id>/: note.pdf (with notes) and senza.pdf (the copy named
#    "SENZA NOTE" or "NO NOTE", where there is one). A few downloads are a bare PDF (note.pdf only).
python fetch.py
# 2. Build. --today dates the documentation commit and is the latest date allowed.
python build.py ../san-marino-law --today 2026-10-29
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

- 65 testi coordinati (5276 PDF pages): 517 acts, 7520 articles, 2461 notes.
- 66 commits: one per text (`Kind: consolidated`) and one documentation commit.
- Update dates from 2012-01-20 to 2026-10-28.
- 3578 rows in data/amendments.csv naming 394 acts; 9 calls without a note
  and 30 notes without a call (data/issues.csv).

## Checks

```sh
git rev-list --merges --count main                  # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
python tools/in_force_on.py 2026-10-29 nuovo-codice-penale/legge-1974-17 art-1
python tools/build/check_repo.py .                  # letters and digits against the PDFs (needs the cache)
```

Rebuilding twice from the same files gives the same `git rev-parse HEAD`.
