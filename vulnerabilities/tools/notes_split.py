"""For every flag in out/data/flags.csv: is it in a note (earlier wording, amending text, the Segreteria's remarks) or in the
article's text; and, for lapsed limits, is the date before or after the edition of its testo coordinato.
python -X utf8 notes_split.py <D>"""
import collections, csv, json, re, subprocess, sys
from pathlib import Path
D = Path(sys.argv[1]); S = D / "gl/vulnerabilities/scripts"
pin = json.load(open(S / "pins.json", encoding="utf-8"))["corpora"][0]
G = S / "sources/corpus" / (pin["repo"] + ".git")
show = lambda p: subprocess.run(["git", "show", f'{pin["sha"]}:{p}'], cwd=G, capture_output=True).stdout.decode("utf-8", "replace")
ed = {}
for r in csv.DictReader(show("laws.csv").splitlines()):
    ed[r.get("folder") or r.get("path") or list(r.values())[0]] = r
print("laws.csv columns:", list(next(iter(ed.values())).keys()))
rows = list(csv.DictReader(open(D / "out/data/flags.csv", encoding="utf-8")))
cache = {}
res = collections.Counter(); after = collections.Counter(); per = collections.defaultdict(list)
for r in rows:
    p = r["path"]
    t = cache.setdefault(p, show(p))
    first_note = t.find("\n[^")
    where = "text"
    if p.endswith("notes-uncalled.md"):
        where = "note"
    elif r["detector"] == "lapsed_limit":
        flat = t.replace("\n", " ")
        i = flat.find(r["summary"])
        pos = i + (200 if i > 0 else 0)
        if first_note >= 0 and pos > first_note:
            where = "note"
    else:
        ln = int(r["reference"]) if r["reference"].isdigit() and r["detector"] in ("dead_currency", "publisher_flag") else None
        if ln:
            off = sum(len(l) + 1 for l in t.split("\n")[:ln - 1])
            where = "note" if first_note >= 0 and off > first_note else "text"
        elif r["detector"] == "placeholder_ref":
            i = t.find(r["summary"][100:160].strip()[:40]) if r["summary"] else -1
            where = "note" if first_note >= 0 and i > first_note else "text"
        elif r["detector"] == "dup_label":
            where = "note"  # checked by hand: all three are indented note lines
    res[(r["detector"], where)] += 1
    per[(r["detector"], where)].append(r)
    if r["detector"] == "lapsed_limit":
        e = ed.get(p.split("/")[0] + "/") or ed.get(p.split("/")[0])
        edate = (e or {}).get("updated") or ""
        after[(where, "after edition" if edate and r["date"] > edate else "before edition")] += 1
        if where == "text" and edate and r["date"] > edate:
            print("AFTER", r["date"], edate, p, "|", r["summary"][170:300])
for k, v in sorted(res.items()):
    print(k, v)
for k, v in sorted(after.items()):
    print(k, v)
json.dump({f"{a}|{b}": [x["path"] + " " + x["date"] for x in v] for (a, b), v in per.items()}, open(D / "work/notes_split.json", "w", encoding="utf-8"), indent=0)
