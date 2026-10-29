# The laws of San Marino, as a git repository

The consolidated texts ("testi coordinati") of the Republic of San Marino as a git repository: 65 texts on
the main subjects of San Marino law, holding 526 acts and 7535 articles, from the
[Consiglio Grande e Generale](https://www.consigliograndeegenerale.sm/on-line/home/testi-coordinati.html). Each
article is one file, with one paragraph per line, so `git blame` and `git diff` work line by line. The text is in
Italian, as published.

**What this repository is not, yet: a history.** The Consiglio Grande e Generale publishes only the current edition
of each testo coordinato and keeps no earlier ones. So each text is a single commit holding its whole current
wording ("current-only"), dated by the day the text says it is updated to. There is no line-by-line history before
that edition. Later editions will be added as later commits, so the history grows forward from here. What the
source does say about the past is kept: the footnotes print each provision's earlier wording ("Testo originario")
and the amending provisions ("Modifiche legislative"), and they are in the files and listed in
[`data/amendments.csv`](data/amendments.csv).

The record holds 65 texts, updated between 2012-01-20 and 2026-10-28, in 66 commits. It is not every San
Marino law: only the laws the Consiglio has brought into a testo coordinato (see [`laws.csv`](laws.csv)).

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does article 1 of the Codice Penale say? | `python tools/in_force_on.py 2026-10-29 nuovo-codice-penale/legge-1974-17 art-1` |
| The whole of one act in a text, in order | `python tools/in_force_on.py 2026-10-29 nuovo-codice-penale/legge-1974-17` |
| A whole testo coordinato | `python tools/in_force_on.py 2026-10-29 patrocinio-gratuito` |
| An article's earlier wording and the act that changed it | the `[^n]:` notes at the end of its file |
| Every provision an amending act touched, by the notes | `grep -i 'Legge 2 marzo 2022 n.24' data/amendments.csv` |
| Which texts hold an act | `grep 'legge-2011-160' data/acts.csv` |
| What changed in a text since this build (after later builds) | `git log -p -- nuovo-codice-penale` |
| The list of texts, with their dates | [`laws.csv`](laws.csv) |

## How a text is laid out

Each testo coordinato is a folder named after its subject. Its `title.md` is the cover: the title, the "aggiornato
al" line and, where the text has one, the list of the acts it cites. A "raccolta coordinata" holds several acts:
each is a subfolder named by kind, year and number (`legge-2011-160`, `decreto-delegato-2019-122`), or by kind and
date for a 19th-century act that has no number (`legge-1884-12-20`), with the act's heading, title and preamble in
`intro.md` and one file per article (`art-1.md`, `art-2-bis.md`). Such an old act numbers its articles at the start
of their first paragraph ("1. - E' accordato ..."); each is still one file. A text that prints the same act twice
keeps both copies (`art-1--2.md`, `intro--2.md`). Headings of Titles, Chapters and Sections (`## TITOLO I`) go at
the top of the article that follows them; "ALTRE NORME" (the divider before a collection's further acts) heads the
next act's `intro.md`. `index.txt` lists the files in reading order.

A superscript note number in the PDF is written `[^n]` where it stands, and the note follows at the end of the
same file, `[^n]: Testo originario ...`, with each further paragraph indented four spaces. Notes that nothing in the
text calls (30 of them) are in the text's `notes-uncalled.md`; 9 note numbers are
called but have no note in the PDF. Both are listed in [`data/issues.csv`](data/issues.csv).

## The dates, and which one we use

Each text states the date it is updated to ("aggiornato al 22 dicembre 2025"). **Each commit is dated by that date**,
at noon San Marino time (CET/CEST), in its `In-force:` and `Consolidated:` trailers: the text is the law as the
Consiglio consolidated it on that day. 63 texts give a full date. 1 gives only a month
("vigente a maggio 2026") and is dated the first of that month, and 1 gives none and is dated by the
day it was retrieved (2026-10-28); the `Date-source:` trailer says which. The date is not the date any amendment
took effect: those are in the amending acts, named in the notes.

`tools/in_force_on.py` answers for any date on or after a text's edition. For an earlier date it says there is no
version, because the source has none.

## What "author" means

Every law-text commit has the same author: `Segreteria Istituzionale (Consiglio Grande e Generale)
<segreteria-istituzionale@consigliograndeegenerale-sm.invalid>`, with the trailer `Kind: consolidated`. The address
cannot exist. The author is the office that prepares the consolidation, not a lawmaker. No line is credited to an
amending act, because without an earlier edition nobody can show which words an amendment wrote. When a later
edition changes the text, the change will be credited to an amending act only where the new notes name one;
otherwise it is labelled `Kind: unexplained` and authored by the Segreteria.

The notes name 394 distinct acts in 3578 rows of `data/amendments.csv`.

## What it does not show

- Any edition before the current one. The site has none.
- Laws not in a testo coordinato. The Consiglio's archive has every law and decree as enacted; they are not here.
- Pictures, tables drawn as graphics, page numbers, and the PDF's layout (indentation, bold).
- Text the PDF itself garbles: a few PDFs have letters with no Unicode mapping, shown as `�` as the PDF gives them.

The testi coordinati are an aid to reading: the official text of each law is the one in the Bollettino Ufficiale,
and the Consiglio says so. The same is true of this repository.

## How it is checked

`tools/build/` holds the build as it was run, and [`data/source-sha256.tsv`](data/source-sha256.tsv) the sha256 of
every downloaded file. The build is deterministic: from the same files it gives the same commit hashes. See
[`REPRODUCE.md`](REPRODUCE.md). Before publishing it was checked for these things:
- the letters and digits of every text, in order, against the Consiglio's own copy without notes ("SENZA NOTE",
  33 texts have one), read by a different PDF reader (poppler's `pdftotext`, not the PyMuPDF the build uses);
  and, for every text, the words of the repository against the words of the PDF with notes;
- every commit's trailers parse; there are no merges, no dates that go backwards and none after the build date;
- the on-date tool, for sample articles on several dates;
- two builds from the same files give the same HEAD.

The results ([`data/verification.json`](data/verification.json), for the law commits of this build): against the
copies without notes (33 texts, 925,721 words), 1,540 words (0.17%)
differ, and 10,412 more are only in another order (table cells, which the two readers take in a different
order). Most differences are where the two PDFs themselves differ: tables of contents with other page numbers, a
few copies without notes made on another day, notes printed in the copy without notes. The rest are where the
other reader joins a word split at a line end or two numbers that stand side by side. Against the PDFs with notes
(65 texts, 2,475,831 words), 99.98% of the PDF's words are in the repository
(the lowest text: 99.35%, a decree whose annexes are wide tables), and 50 texts reach 99.9% both
ways.

## How it is built

Each text's download is a zip with the PDF with notes and, for some, one "SENZA NOTE"; `unpack.py` takes the
PDFs out of it. `parse.py` reads the PDF with notes with PyMuPDF: lines by baseline, the
note area of each page (below Word's footnote separator, or from the first note number, at the notes' size and
margin), the note calls (superscript numbers in the text), act headings and articles. `build.py` writes one commit
per text with `git fast-import`. No AI model takes part in building or checking it.

## Licence

Source: Consiglio Grande e Generale, Repubblica di San Marino (https://www.consigliograndeegenerale.sm), Segreteria
Istituzionale. The texts are acts of the State, which Legge 25 gennaio 1991 n.8, article 98(f), allows anyone to
reproduce in full. The wording was not changed; it was only split into files and lines. Lexifina's own
contributions (the tools, the arrangement and the commit messages) are CC0. See [`LICENSE`](LICENSE) and
[`SOURCES.md`](SOURCES.md).
