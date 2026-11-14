# San Marino: la storia delle leggi in git

**Italiano** · **[Or read it in English](README.en.md)**

<picture>
<source media="(prefers-color-scheme: dark)" srcset="data/it/effort-dark.svg">
<img alt="Il diritto sammarinese in questo repository: che cosa contiene, le modifiche per anno di entrata in vigore, la completezza rispetto alle fonti ufficiali e la correttezza dei contenuti" src="data/it/effort-light.svg" width="880">
</picture>

Il diritto di San Marino come repository git: un file per articolo, un comma per riga e un commit per ogni testo coordinato, datato al giorno a cui il Consiglio Grande e Generale dichiara aggiornato il testo. Il Consiglio pubblica solo l'edizione vigente di ciascun testo, perciò per ora ognuno è un unico commit, attribuito all'ufficio che lo predispone; le edizioni successive saranno aggiunte come nuovi commit e `git log` le elencherà. Le note di ogni articolo conservano la formulazione precedente ("Testo originario") e l'atto che l'ha modificata; scegliendo una data si ottiene l'edizione vigente in quel giorno.

Fa parte di [lexifina/global-law](https://github.com/lexifina/global-law), un'unica storia git per il diritto di ogni Paese: questo è il diritto nazionale di San Marino, che global-law legge in `san-marino/national/acts/`.

**Che cosa contiene ora:** 65 testi coordinati sulle principali materie del diritto sammarinese, un'edizione ciascuno, aggiornati tra il 20 gennaio 2012 e il 28 ottobre 2026, che comprendono 526 atti (409 distinti; alcuni sono riportati in più di un testo) e 7.535 articoli, tra cui la Dichiarazione dei diritti dei cittadini (Legge 8 luglio 1974 n.59) con le modifiche fino al 2025; le loro note indicano 394 atti modificativi. [`laws.csv`](laws.csv) elenca ogni testo con la sua data; [`data/acts.csv`](data/acts.csv) elenca gli atti di ciascun testo.

Ogni testo è una cartella che prende il nome dalla sua materia, con una cartella per atto denominata per tipo, anno e numero e un file per articolo (`lavoro/legge-1961-7/art-23.md` è l'articolo 23 della Legge 17 febbraio 1961 n.7, Legge per la tutela del lavoro e dei lavoratori, nella raccolta in materia di lavoro); `index.txt` elenca i file di un testo in ordine di lettura.

Il testo è in italiano, la lingua ufficiale di San Marino, così come lo pubblica il Consiglio. Una traduzione in inglese non fa parte di questo archivio.

## Domande come comandi git

| Domanda | Comando |
| --- | --- |
| Ogni edizione dell'articolo 23 della Legge per la tutela del lavoro (una finora) | `git log -p --word-diff -- lavoro/legge-1961-7/art-23.md` |
| Quali atti hanno modificato la Legge, secondo le sue note? | `grep lavoro/legge-1961-7/ data/amendments.csv` |
| Ogni edizione della raccolta in materia di lavoro, con il giorno a cui è aggiornata | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- lavoro` |
| L'articolo 23 nell'edizione vigente al 1° gennaio 2026 | `python tools/in_force_on.py 2026-01-01 lavoro/legge-1961-7 art-23` |

**Fuori da git** pubblichiamo questo archivio anche online, gratuitamente:

- **[Chiedi a Claude del diritto sammarinese](https://global-law.lexifina.com/v1/try_claude?country=san-marino)**: apre Claude con una prima domanda già pronta.
- **[Chiedi a ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=san-marino)**: la stessa domanda in ChatGPT.
- **[Chiama l'API dal browser](https://global-law.lexifina.com/v1/search_law?query=ferie&jurisdictions=san-marino)**: una ricerca di "ferie" nel diritto sammarinese, con risposta in JSON. La documentazione è [qui](https://lexifina.com/api/global-law).

Entrambi gli assistenti leggono l'archivio tramite il connettore gratuito Global law (MCP, `https://global-law.lexifina.com/mcp`); la prima volta la chat ti dà il link per aggiungerlo. Puoi chiedere in italiano o in inglese.

**Ospitalo tu stesso, facilmente.** Bastano git e Python, e gli strumenti girano sul tuo computer:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add san-marino/national/acts
python3 tools/law.py show 2026-01-01 san-marino/national/acts/lavoro/legge-1961-7/art-23.md
```

Aperto in Claude Code, Cursor, VS Code o Codex, il clone avvia anche un server MCP locale con gli stessi strumenti ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Date

Ogni commit è datato a mezzogiorno, ora di San Marino (Europe/San_Marino), al giorno a cui il testo dichiara di essere aggiornato ("aggiornato al 22 dicembre 2025"), e lo riporta nei trailer `In-force:` e `Consolidated:`:

- 63 testi indicano una data completa; 1 indica solo un mese ("vigente a maggio 2026") ed è datato al primo giorno di quel mese; 1 non ne indica alcuna ed è datato al giorno in cui è stato scaricato, il 28 ottobre 2026. Il trailer `Date-source:` dice quale caso ricorre.
- La data è quella del coordinamento, non quella in cui una modifica ha avuto effetto: quelle date sono negli atti modificativi indicati nelle note.
- `tools/in_force_on.py` risponde per qualsiasi data uguale o successiva all'edizione di un testo; per una data anteriore dice che non esiste alcuna versione, perché la fonte non ne ha.

Ogni commit di testo normativo è attribuito a `Segreteria Istituzionale (Consiglio Grande e Generale)`, l'ufficio che predispone il coordinamento, con `Kind: consolidated`. Nessuna riga è attribuita a un atto modificativo, perché senza un'edizione precedente nessuno può mostrare quali parole abbia scritto una modifica; le modifiche di un'edizione successiva saranno attribuite a un atto dove le sue note ne indicano uno.

## Come viene verificato

- Le lettere e le cifre di ogni testo, in ordine, sono confrontate con la copia senza note del Consiglio stesso ("SENZA NOTE", 33 testi), letta da un diverso lettore PDF: differisce lo 0,17% di 925.721 parole, per lo più dove i due PDF stessi differiscono.
- Le parole di ogni testo sono confrontate con il suo PDF con le note: il 99,98% delle parole del PDF è nel repository (il testo più basso il 99,35%).
- I trailer di ogni commit sono analizzabili; non ci sono merge, né date che tornano indietro né date successive a quella della costruzione.
- La costruzione è deterministica: dagli stessi file, il cui sha256 è in [`data/source-sha256.tsv`](data/source-sha256.tsv), produce gli stessi hash dei commit. I risultati sono in [`data/verification.json`](data/verification.json) e [`REPRODUCE.md`](REPRODUCE.md).

## Che cosa non mostra

- **Qualsiasi edizione anteriore a quella vigente.** Il Consiglio non ne conserva; la formulazione precedente è solo nelle note.
- **Le leggi che non sono in un testo coordinato.** L'archivio del Consiglio contiene ogni legge e decreto come approvati; qui non ci sono, e nemmeno la giurisprudenza, i trattati o i progetti di legge.
- **Immagini, tabelle riprodotte come grafica, numeri di pagina e l'impaginazione del PDF.**
- **Il testo che il PDF stesso altera**: alcuni PDF hanno lettere prive di corrispondenza Unicode, mostrate come `�`; le note senza richiamo e i richiami senza nota sono elencati in [`data/issues.csv`](data/issues.csv).

## Fonti

| Fonte | Tipo | Versioni precedenti | Note |
| --- | --- | --- | --- |
| [Consiglio Grande e Generale, Testi coordinati](https://www.consigliograndeegenerale.sm/on-line/home/testi-coordinati.html) (Segreteria Istituzionale) | Testi coordinati ufficiali, per materia | no, solo l'edizione vigente | PDF con note (formulazione precedente, atti modificativi); fa fede solo il Bollettino Ufficiale |

## Licenza

Vedi [`LICENSE`](LICENSE) e [`SOURCES.md`](SOURCES.md). I testi sono atti dello Stato, che la Legge 25 gennaio 1991 n.8, articolo 98, lettera f), consente a chiunque di riprodurre integralmente; la formulazione non è stata modificata, solo suddivisa in file e righe. I contributi propri di Lexifina sono CC0 1.0.

Nessun modello di IA ha scritto o modificato testo normativo, e nessuno interviene quando il repository viene costruito o verificato; gli script sono stati scritti da un modello di IA (vedi [`REPRODUCE.md`](REPRODUCE.md)).

Questa è una traduzione della versione inglese ([README.en.md](README.en.md)); in caso di differenze, prevale la versione inglese.

## Per saperne di più

Dal repository [lexifina/global-law](https://github.com/lexifina/global-law) (pagine in inglese):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): tutte le funzionalità e ciò che ogni corpus deve supportare (`git blame`, `law.py`, strumenti MCP)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): domande e risposte · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proporre una modifica · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): server MCP · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): come è stato realizzato · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): quanto è aggiornato ogni corpus · [Monitoraggio](https://github.com/lexifina/global-law/tree/main/monitoring): se gli aggiornamenti funzionano · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): come ogni fonte ufficiale viene controllata per individuare le modifiche
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): quanto sono veloci gli strumenti, misurato
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): grafici e collegamenti attraverso il diritto di tutto il mondo
- [Vulnerabilità](https://github.com/lexifina/global-law/tree/main/vulnerabilities): errori nei testi così come sono stati pubblicati
