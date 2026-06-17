# Lying Spreadsheets II

**Extraction-time data falsification, and the limits of model-side defense.**

[![CI](https://github.com/legalrealist/lying-spreadsheets-ii/actions/workflows/ci.yml/badge.svg)](https://github.com/legalrealist/lying-spreadsheets-ii/actions/workflows/ci.yml)

![A loan-covenant spreadsheet that reads 2.5x COMPLIANT to a pandas pipeline but recalculates to 3.8x BREACH in Excel; the bundled detector flags every cell where the cached value diverges from recomputation](assets/demo.gif)

*Real output from `poc/lying_xlsx.py` and `defense/detect_xlsx.py` on the C3 (fully-consistent) tamper.*

A document can render one thing to a human and hand a parser something else. When that parser feeds an LLM pipeline, the model faithfully reasons over the **attacker's** version while the human approves the **rendered** version. This is not prompt injection — there is no instruction to refuse, and safety alignment is irrelevant. It is **data falsification at the extraction boundary.**

This repo is a sequel to [`lying-spreadsheets`](https://github.com/legalrealist/lying-spreadsheets) (XLSX number-format display vs. raw value) and a companion to [Noroboto](https://github.com/LegalQuants/noroboto) (DOCX/PDF glyph remapping). It adds two more members of the class — a **cached-value** XLSX variant and a **MIME-multipart** email variant — and, more importantly, characterizes the **only defense that actually fires today: the model's own domain reasoning.** We show experimentally that this backstop is real but domain-specific and bypassable, and that the pipeline itself is undefended in every case.

> Everything here is a constructed PoC against *generic* pipelines, built to be net-defensive (the repo ships the detectors). If you build document/email ingestion for high-stakes decisions, assume exposure and add reader-comparison.

*Prefer prose? A narrative write-up of these findings is in [`writeup/substack-post.md`](writeup/substack-post.md).*

## The vulnerability class

Every member shares one shape:

> An untrusted file has two representations of the same field. A human consumes representation **H** (what the application renders). An automated LLM pipeline consumes representation **M** (what a library extracts). The attacker controls both and makes **H ≠ M**.

What makes it dangerous for LLM pipelines specifically:

- **Safety-hardening-proof.** The payload is *data*, not an instruction — nothing for RLHF to refuse.
- **It rides the dominant tooling.** `pandas.read_excel`, `python-docx`, `pdfplumber`, plain-text email extraction — the defaults do the wrong thing.
- **It severs provenance.** The model's output (a summary, a risk score, a covenant verdict) is trusted by a human who never re-derives it from the rendered source.

## Two instances in this repo

### R1 — Cached-value spoofing (`poc/lying_xlsx.py`)

XLSX stores each formula cell as both the formula and a cached result (`<v>`). Excel recalculates on open; headless readers return the cache verbatim. `openpyxl(data_only=True)` and **`pandas.read_excel` (default)** both surface the cached value. Tampering is a single XML edit per cell — replace `<v>` with a fabricated number, leave the formula intact.

- **H (human, Excel):** recalculates → true value.
- **M (pipeline, pandas):** reads the fabricated cache → attacker value.

No fonts, no Private-Use-Area characters, byte-clean (same part count as an untouched file). The only signal is *cache ≠ recomputation*.

### R4 — Email multipart divergence (`poc/lying_email.py`)

A `multipart/alternative` message carries `text/plain` and `text/html`. The attacker controls both. Most LLM email loaders take `text/plain` (or strip HTML to text, which *keeps* `display:none` content); humans read rendered HTML.

## The contribution: the model is the only guard, and it is domain-specific

The pipeline never compares H and M, so the only thing between a falsified document and a bad decision is the LLM's own reasoning over M. We tested whether it fires, using blind analyst agents (Claude Sonnet) given only the extracted representation M and a realistic task. Full logs: [`experiments/`](experiments/).

**R1 — loan covenant (Debt/EBITDA ≤ 3.0×; true state 3.8× = BREACH):**

| Condition | M (pandas) | H (recalc) | Analyst verdict | Caught? |
|-----------|-----------|------------|-----------------|---------|
| C0 control | 3.8× / BREACH | 3.8× / BREACH | BREACH | n/a |
| C1 ratio faked only | 2.5× / COMPLIANT | 3.8× / BREACH | COMPLIANT* | **yes** — 380/100 ≠ 2.5 |
| C2 EBITDA also faked | 2.375× / COMPLIANT | 3.8× / BREACH | COMPLIANT* | **yes** — 90+10 ≠ 160 |
| **C3 fully consistent** | 2.5× / COMPLIANT | 3.8× / BREACH | **COMPLIANT** | **no** |

<sub>* headline verdict COMPLIANT; the contradiction surfaced only in a separate free-text flag, so a verdict-only consumer is still fooled.</sub>

**R4 — email triage / contract summary:**

| Condition | M (pipeline) | H (human) | AI outcome | Exploit |
|-----------|-------------|-----------|------------|---------|
| E1 blatant wire | $48,500 + urgency | benign note | **BLOCK** (BEC reflex) | surfaced, blocked |
| E1′ plausible wire | $12,300 routine PO | benign note | **MEDIUM** + verify | partial |
| E2 `display:none` injection | hidden `[system]` override | benign note | **refused** | no |
| **E3 contract terms** | 6wk / $50 / no-term | 4wk / $40 / +term | **recorded verbatim** | **yes — clean** |

**What's new here vs. lying-spreadsheets I.** That the model cross-foots arithmetic and catches *inconsistent* numbers (C1/C2) is the LS-I result, not a new one — LS-I already established that numeric extraction must be recomputed. Those conditions are the **baseline**. Two things go beyond it:

1. **Cross-checking the visible extract is necessary but not sufficient.** A fully internally-consistent fabrication (C3 — components faked so 142+10=152 and 380/152=2.5) passes every cross-foot you can do on the *extracted table*. What catches it is recomputing from the **raw precedents** — the non-formula input cells — because divergence can only live in a formula's cached `<v>`; a raw input has no cache to tamper and so cannot diverge between the human and the pipeline. So recompute-from-inputs is actually a *complete* defense for this attack, and the bundled [`detect_xlsx.py`](defense/detect_xlsx.py) does exactly that (it flags C1, C2, **and** C3). The sharpened lesson: **recompute from inputs, not from the extract.** A validator that merely cross-foots the visible numbers — like the model does — is defeated by C3. Recompute works for *text* formulas too (governing law, rating, dates), not just numbers — but only while the precedents survive into the extracted data; a single-sheet extraction or an external reference drops them and recompute goes dark, the same blind spot free-text has. See [`experiments/nonnumeric.md`](experiments/nonnumeric.md).

2. **Most falsifiable data has no math to check.** Contract terms, dates, entities, obligations (E3) carry no arithmetic relationship, so cross-checking is *structurally inapplicable* — and both models recorded the divergent terms verbatim. Here the rendered-vs-extracted divergence is the **only** signal; nothing in M alone betrays it.

So the LS-I defense (recompute numbers) is both **incomplete** (it must reach raw inputs, not the extract) and **inapplicable** to the larger non-numeric surface. The one general defense is **comparing the two readers — rendered H vs extracted M** — never reasoning about M alone. lying-spreadsheets said *safety alignment doesn't help*; this adds *task competence helps only where there is redundancy to check, and the attacker simply removes it (consistency) or works where there is none (free-text terms).*

**Powered results (N = 10 per condition × 2 models, judge-labeled).** Re-running the boundary conditions across GPT-5.5 (Codex) and Claude Sonnet (`claude -p`), labeled by an independent judge ([full results](experiments/sweep-results.md), [raw outputs](experiments/sweep-raw/)):

| Condition | GPT-5.5 | Sonnet |
|-----------|---------|--------|
| C1 inconsistent | caught (BREACH) 10/10 | caught (BREACH) 10/10 |
| C3 fully consistent | certified COMPLIANT 10/10, 0 warned | certified COMPLIANT 10/10, 6/10 warned "unverified" |
| C3 + *"recompute & verify"* instruction | COMPLIANT 10/10, **0 warned** | COMPLIANT 10/10, **0 warned** |
| E3 non-numeric terms | recorded as fact 10/10 | recorded as fact 10/10 |

Two things worth flagging. (a) The boundary is identical across both model families. (b) **Telling the model to verify backfires:** adding an explicit "recompute and flag anything that doesn't reconcile" instruction did not raise detection (still 0/20) and *suppressed* Sonnet's spontaneous "this data is unverified / could be falsified" warning (6/10 → 0/10) — the consistent table passes the recompute and manufactures false confidence. Asking for verification was worse than not asking.

## The defense: compare the readers

The only robust defense is structural — reconstruct **H** and diff it against **M** before the LLM sees anything. This repo ships both:

- **`defense/detect_xlsx.py`** — recompute every formula from its raw precedents (bottom-up, so a tampered upstream cache can't poison the result) and flag any cell where recomputation ≠ cached `<v>`.
- **`defense/detect_email.py`** — extract both MIME parts, strip `display:none`, and flag divergence in money / account / duration / term signals.

Both are cheap and deterministic. Neither is deployed by default in the tooling people actually use — which is the whole problem.

## Quickstart

```bash
pip install -r requirements.txt

python poc/lying_xlsx.py      # show pandas reading fabricated caches vs. the true recalculation
python poc/lying_email.py     # show three readers, three different emails
python poc/lying_xlsx_text.py # non-numeric: tampered text fields (law/rating/date)

pip install -r requirements-demo.txt   # for the next line only (markitdown, bs4)
python poc/real_loaders.py    # named tools (MarkItDown, BeautifulSoup) ingest the falsified content
python defense/detect_xlsx.py <workbook.xlsx>   # recompute-vs-cache detector
python defense/detect_email.py <message.eml>    # plain-vs-html detector

python -m pytest -q           # deterministic proof: divergence is real, detectors catch it
```

## Not a strawman parser

The defaults of tools teams actually use surface the falsified content. Microsoft's **MarkItDown** (a document→Markdown loader built for LLM ingestion) reads the tampered workbook as `Debt/EBITDA 2.5 / COMPLIANT` while Excel shows `3.8 / BREACH`; **BeautifulSoup `.get_text()`** (the canonical HTML-to-text step in RAG/email pipelines) ingests `display:none` content the human never sees. See [`experiments/real-loaders.md`](experiments/real-loaders.md).

## Reproducing the LLM results

The divergence is deterministic and needs no model. For the "does the LLM catch it" results: single-run prompts/verdicts are in [`experiments/analyst-prompts.md`](experiments/analyst-prompts.md); the powered N=10 × 2-model sweep (raw outputs, judge labels, runner) is in [`experiments/sweep-results.md`](experiments/sweep-results.md) and [`scripts/`](scripts/).

## Limitations & honesty

- The "model catches it" results span two model families (Claude Sonnet and GPT-5.5) at N=10 per condition, judge-labeled (see [`experiments/sweep-results.md`](experiments/sweep-results.md)). N=10 gives rates over a small sample, not population estimates, and the conditions are constructed; the result is a clear boundary (consistent/non-numeric fabrications certified ~100%, inconsistent ones caught ~100%), not a calibrated real-world incidence.
- The bundled `detect_xlsx` recompute engine is intentionally small (common operators + `IF`/`SUM`/`MIN`/`MAX`/`ROUND`/`ABS`/`AVERAGE`). For arbitrary workbooks use LibreOffice headless recalc, [`formulas`](https://pypi.org/project/formulas/), or [`pycel`](https://pypi.org/project/pycel/).
- This is a known class in eDiscovery and security research. The new material is the two instances and the **defense characterization**, not the existence of parser-differentials.

## Prior art

[`lying-spreadsheets`](https://github.com/legalrealist/lying-spreadsheets) (number-format layer) · [Noroboto](https://github.com/LegalQuants/noroboto) (glyph/font layer) · Trojan Source / bidi (CVE-2021-42574) · invisible-text PDF (Snyk) · PoisonedRAG (USENIX 2025) · CSV formula injection.

## License

MIT — see [LICENSE](LICENSE).
