# Non-numeric cached values, and where recompute goes dark

This is the spreadsheet analog of the E3 email case (divergent free-text terms),
and it pins down exactly when the recompute defense stops working. Reproduce with
[`../poc/lying_xlsx_text.py`](../poc/lying_xlsx_text.py).

## Setup

A two-sheet workbook. The extracted **DealSummary** sheet shows text fields that
are *formulas* pulling from a separate **Refs** inputs sheet:

| DealSummary | formula | true (Refs) | tampered cache |
|-------------|---------|-------------|----------------|
| Governing Law | `=Refs!B1` | New York | **Delaware** |
| Counterparty Rating | `=Refs!B2` | BBB- | **AAA** |
| Maturity | `=Refs!B3` | 2030-12-31 | **2035-12-31** |

There is no arithmetic to cross-check. An LLM asked to extract these fields reports
the fabricated text and has nothing to question — the same outcome as E3, where
divergent contract terms were recorded as fact 10/10 on both models.

```
pipeline (pandas) reads: Governing Law=Delaware, Rating=AAA, Maturity=2035-12-31
human (Excel recalc)   : Governing Law=New York, Rating=BBB-, Maturity=2030-12-31
```

## The defense result (the point of this variant)

Recompute is *not* limited to numbers — it catches the text tamper too, **as long
as the precedents are present**:

```
detect_xlsx (full file)    -> DealSummary!B1 cached 'Delaware'    recomputed 'New York'
                              DealSummary!B2 cached 'AAA'         recomputed 'BBB-'
                              DealSummary!B3 cached '2035-12-31'  recomputed '2030-12-31'
detect_xlsx (summary-only) -> []   # Refs sheet dropped -> precedent gone -> cannot verify
```

So the real boundary is not numeric-vs-text. It is **whether the precedents the
formula depends on are in the extracted data M.** Drop them — as a single-named-sheet
extraction does, or as an external-workbook reference always does — and recompute has
nothing to reconstruct the truth from. It goes dark, returning no findings, which a
caller must read as *"unverified,"* not *"clean."*

## Unified takeaway

Across the whole repo, recompute-from-precedents is a complete numeric **and** text
defense only when the precedents survive into M. The cases where it cannot help —
summary-only extraction, external references, and genuinely typed free-text (E3, and
the email/doc variants) — are exactly the cases that have no internal redundancy at
all. There, the only remaining signal is the divergence between the two readers, so
the general defense is unchanged: **compare rendered H against extracted M; never
trust reasoning over M alone.**
