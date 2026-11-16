# Tools

The scripts behind this San Marino-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/san-marino-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only san-marino-law and its commit (language
`it`). `build_vulns.py`, `flags_chart.py`, `late_ext_select.py` and `late_ext_rebut.py` sit two folders above the scripts,
next to `config.json`.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps moved paths (`map_moved.py`; this repository has none), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `map_moved.py` | For a repository that moved its act folders (`data/paths.json`), rewrites the paths in the history table to each act's folder today; here it finds no `data/paths.json` and changes nothing |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods (here 40 lapsed time limits, the same 40 in both passes, and no empty periods) |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (there were none here) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Italian and English, light and dark |
| `config.json` | The repository, the Italian category names, the files that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`) |
| `patch_detectors_vi.py`, `patch_es.py`, `patch_ca.py`, `patch_en.py`, `patch_de.py`, `patch_en_et.py`, `patch_co.py`, `patch_sv.py`, `patch_pt.py`, `patch_ru.py`, `patch_r18.py`, `patch_xk.py`, `patch_mo.py`, `patch_lu.py`, `patch_li.py`, `patch_mx.py`, `patch_mn.py`, `patch_mt.py`, `patch_np.py`, `patch_en_nr.py`, `patch_dv.py`, `patch_az.py`, `patch_ar.py`, `patch_en_nz.py`, `patch_nb.py`, `patch_mk.py`, `patch_pa.py`, `patch_py.py`, `patch_pe.py`, `patch_en_ph.py` | The same for the blind spots that runs on other countries and languages found, one file each; this run's copy carries them all. Most apply only to their own language; those for every language (references, currencies, notes) apply here too |
| `patch_it.py` | The fixes for Italian, below (`python -X utf8 patch_it.py <scripts dir>`; each change carries a `patch_it` marker, and one already in place is skipped) |
| `apply_patches.py` | Applies every patch above once, in order, recording each in `.kit_patches.json` in the scripts folder (`python -X utf8 apply_patches.py <scripts dir>`); `patch_it.py` is last in its list |
| `redo.py` | Runs `apply_patches.py`, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`; `EMBED_FONTS` names the script that embeds the chart's fonts). Not needed here: every fix was in place before the run whose results are published |
| `notes_split.py` | Hand-check helper: for each flag, whether it stands in an article's text or in its notes, and, for a lapsed time limit, whether its date falls after the day to which its testo coordinato is updated (the counts in the READMEs) |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data/|tools/|README|REPRODUCE|SOURCES|LICENSE|corpus[.]json|laws[.]csv)'`; every
testo coordinato is law, so the review of lapsed time limits in law texts drew the same 40 flags as the review of all of
them, and `build_vulns.py` keeps the later review of each flag.

Changes made for this repository:

- `add_root.py` also counts `Kind: consolidated` as law: each of the 65 commits that make a version holds one edition of a
  testo coordinato, credited to the Segreteria Istituzionale (Consiglio Grande e Generale). The kit's list left them out,
  so the history table had no law at all. No flag was added or removed, as no text has a second edition (the scores of lapsed time limits changed, as they now see the day of each edition); the 10 documentation commits
  (no `In-force` trailer) stay out.
- `patch_it.py`, time limits (`ingest/textscan.py`): in an Italian text, "entro il 30 giugno 2021", "entro e non oltre il",
  "non oltre il", "fino alla data del", "sino alle ore 05.00 del", an extension's new end ("prorogato al 31 marzo 2015",
  also "differito", "posticipato", "rinviato") and the end of a period ("dal 1 luglio 2023 al 30 settembre 2023") are
  read; "fino al" and "sino al" were read already. "entro" and "non oltre" mark a deadline, which the empty-period search
  leaves out, and they count as deadline wording in the score (`detectors/text_detectors.py`). Lapsed time limits went
  from 69 to 314.
- `patch_it.py`, repeal placeholders (`detectors/placeholder_ref.py`): an Italian repeal clause ("È abrogato il Regolamento
  30 settembre 2015 n.13", "Sono abrogati: ...", "Sono abrogate tutte le norme in contrasto con la presente legge", "Il
  secondo comma dell'articolo 97 della Legge 70/2004 è abrogato") was taken for a repealed article, as "sont abrogés" and
  "quedan derogados" no longer are: 85 articles were read as placeholders, now 11. References to repealed placeholders
  went from 11 to 9.
- `patch_it.py`, references (`ingest/refscan.py`): in an Italian text, "articolo 14, comma 1 della Legge 16 dicembre 2013
  n.166" (a paragraph, letter or number, then another act) cites another act, not this act's Article 14.
- `patch_it.py`, currencies (`detectors/currency_scan.py`): in an Italian text, lire written "L.5.000.000" or "L. 10.000",
  in words ("lire sessantamila", "lire cento") and as "20 milioni di lire" are read; only "5.000 lire" and "lire 50" were.
  Dead currencies went from 26 to 135.
- `patch_it.py`, publisher notes (`detectors/notes_scan.py`, every language): the English note "So in original" is matched
  only as words of its own, not inside the Italian "trasmesso in originale" or "sia esso in originale". Publisher notes
  went from 2 to 0.
- `config.json` counts as not law `data/`, `tools/` and the root files; every testo coordinato is law.
- Not fixed: the notes at the end of each article's file (earlier wording, amending text) are read as text by every
  detector; months or years without a day ("entro il mese di dicembre 2020") and relative terms ("entro trenta giorni")
  are not read as time limits.
