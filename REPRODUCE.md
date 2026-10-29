# Reproducing this repository

Built on 2026-10-29 from the Consiglio Grande e Generale's "Testi coordinati", retrieved on 2026-10-28, by the
scripts in `tools/build/` (copied there as run). The sha256 of every file the build read (each download, and the
PDFs unpacked from it) is in [`data/source-sha256.tsv`](data/source-sha256.tsv), so a copy of those files can be
checked byte for byte before rebuilding. How the files were retrieved is not part of this record.

| Script | sha256 |
| --- | --- |
| unpack.py | `b2afb0dfac6079d053724a56bdc38ab983b857ed6880b4d5218c5ff625772fae` |
| parse.py | `10a4a8adb9aaccf4714bca4324b4058726761d89f1a6a135321ff077302b74b3` |
| build.py | `6c33566754019f9cd141224651acb59e90f57928d5e84555016efced824a42d2` |
| docs.py | `16f2fa3e262868f60c2d041f8f264f739cefb0a91043731aa7543d1bafed5ad8` |
| check_repo.py | `74fecfb512e5b99729a032b72dee8487039cdc8c60b8fc930113fdccf4c63791` |

## Steps

With the retrieved downloads in place (`zip/<id>.bin`, each matching its sha256 in `data/source-sha256.tsv`), and
the retrieval day in `fetched_on.txt`:

```sh
pip install pymupdf          # parse.py; check_repo.py also needs poppler's pdftotext on the PATH
# 1. Unpack each download into pdf/<id>/: note.pdf (with notes) and senza.pdf (the copy named "SENZA NOTE" or
#    "NO NOTE", where there is one). A few downloads are a bare PDF (note.pdf only).
python unpack.py
# 2. Build. --today dates the documentation commit and is the latest date allowed.
python build.py ../san-marino-law --today 2026-10-29
# 3. Check the letters and digits against the PDFs.
python check_repo.py ../san-marino-law
```

The site offers no bulk download: each testo coordinato is one download from its page.

## What the build produced

- 65 testi coordinati (5276 PDF pages): 526 acts, 7535 articles, 2461 notes.
- 66 commits: one per text (`Kind: consolidated`) and one documentation commit.
- Update dates from 2012-01-20 to 2026-10-28.
- 3578 rows in data/amendments.csv naming 394 acts; 9 calls without a note
  and 30 notes without a call (data/issues.csv).

## Checks

```sh
git rev-list --merges --count main                  # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
python tools/in_force_on.py 2026-10-29 nuovo-codice-penale/legge-1974-17 art-1
python tools/build/check_repo.py .                  # letters and digits against the PDFs (needs the files)
```

Rebuilding twice from the same files gives the same `git rev-parse HEAD`.

## AI

The scripts, the README and these notes were written by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), working
for Lexifina. No AI model writes or changes legal text, and none runs when the repository is built or checked: the
build is the Python in `tools/build/`, run as recorded here.
