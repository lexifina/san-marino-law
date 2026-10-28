# How this repository was made (San Marino)

This file is written by the build on 2026-10-28, the day the source data was retrieved. Everything below is enough to rebuild this repository hash for hash.

## Sources

| Source | Address | Retrieved | Requests | Licence |
| --- | --- | --- | ---: | --- |
| Consiglio Grande e Generale: Archivio Leggi and Testi Coordinati | <https://www.consigliograndeegenerale.sm/on-line/home/testi-coordinati.html> | 2026-10-28 | 85 | No licence stated; © Segreteria Istituzionale. Not authentic texts (site disclaimer). |

Every response is cached by the sha256 of its URL, and the table above lists every source with its retrieval date. Lexifina keeps its fetch scripts privately; `tools/parse.py` reads only the cache and writes `corpus.json`, so the same cache always gives the same corpus.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `dichiarazione-dei-diritti` | Dichiarazione dei diritti dei cittadini e dei principi fondamentali dell'ordinamento sammarinese (Legge 8 luglio 1974 n.59) | 1 | 2025-10-11 to 2025-10-11 |

The build made 1 commits:

| Commits | Kind |
| ---: | --- |
| 1 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `futuro`: laws not yet in force on 2026-10-28.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 8 laws in the record.
- 1 tags.

## Dates

Each commit is dated at noon (Europe/San_Marino) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: Each law used here states its own entry into force ("entra in vigore il quinto/quindicesimo giorno successivo a quello della sua legale pubblicazione"); no general default rule was sourced. https://www.consigliograndeegenerale.sm/on-line/home/archivio-leggi-decreti-e-regolamenti.html

## Commands, in order

```sh
# fill the cache from the sources listed above (network; Lexifina's fetch scripts are kept privately)
python -X utf8 tools/parse.py                  # cache -> corpus.json (no network)
python -X utf8 tools/build.py <folder> --repo <empty folder> --docs-date 2026-10-28
python -X utf8 tools/check_repo.py <repo> --corpus <folder>/corpus.json --write
python -X utf8 tools/build.py <folder> --repo <another empty folder> --docs-date 2026-10-28 --compare <repo>
```

In the main Lexifina repository these files live as follows:
- `fetch.py`, `parse.py` and `repo/`: in `scripts/san-marino-law/`.
- `build.py`, `check_repo.py` (`check.py` there) and `on.py`: in `scripts/gitlaw_common/`, with the corpus format in `SCHEMA.md`.

## Exact inputs

- `corpus.json` sha256 `bac2ce8850d378b13f02598a56c13d93ac23c4ad88e8e1e1f70727dcf4539439` (22051 bytes)
- Script blob hashes (`git hash-object`):

| Script | Blob |
| --- | --- |
| build.py | `2bfc4ac9df193a7be844556d7f69cdb9d93ec3f2` |
| check.py | `cd346c7ff9996d450240e3bab52bcae03b2bc865` |
| on.py | `644a6c0857fbcc72562032b58d57aa113fee0641` |
| fetch.py | `dadae9e429c9fdf0e3f23fa16611218f5642cd96` |
| parse.py | `85277cd5236cf01380fd51193d24fecffae4e8fa` |

- Tools:
  - Python 3.14.0
  - git version 2.52.0.windows.1
  - curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP

## Checks

1 versions of 1 acts read back from git on the day each took effect and on the day before: 0 mismatches. Trailers: 0 commits whose trailers git cannot parse. Health: 0 merge commits on main, 0 commit dates that go backwards, 0 commits dated after the build.

Not yet run for this build.

These results are from the check run on the build before this one, from the same corpus.

## Decisions made by hand

- First cut: the Dichiarazione dei Diritti is one "oldest version available" version (the current testo coordinato), credited to the publisher; the earlier laws are listed but not yet replayed.
- The version is dated 2025-10-11, when Legge Costituzionale 26 settembre 2025 n.2 (the latest change in the text, Art. 2-bis) took effect, not the testo coordinato date of 26 September 2025, so no text precedes its law.
- The "Norma Transitoria" heading refers to Legge 26 febbraio 2002 n.36 art. 9 and is left out of the act.

## What AI did and did not do

The fetch, parse and check scripts were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above, through code that anyone can rerun.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: the text is parsed by code from the source PDF; no model wrote or classified legal text.
