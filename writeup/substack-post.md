# Lying Spreadsheets II: The Workbook That Tells Your AI a Different Story

*A document can show a human one thing and hand a machine another. When the machine is an LLM in your contract-review or covenant-monitoring pipeline, the model believes the version you never see — and no amount of "AI safety" helps, because nothing is being said to the model at all.*

---

Open a loan-covenant workbook in Excel. Debt is \$380M, EBITDA is \$100M, the covenant caps leverage at 3.0×. Excel does the arithmetic in front of you: **3.8× — breach.** You'd pick up the phone.

Now feed the *same file* to an AI pipeline that reads it with `pandas` — the default in roughly every "upload your spreadsheet" feature shipping today. The model reads **2.5× — compliant**, writes a tidy summary, and routes the deal onward. Same bytes. Two different truths. The human and the machine were handed different numbers, and only one of them was real.

This is not prompt injection. There is no hidden instruction, no jailbreak, nothing for the model to refuse. It is **data falsification at the extraction boundary** — and it is the natural sequel to [lying-spreadsheets](https://github.com/legalrealist/lying-spreadsheets), which showed the same trick using a cell's *display format*, and a cousin of [Noroboto](https://github.com/LegalQuants/noroboto), which does it with fonts. The full code, experiments, and detectors for everything below are at **[github.com/legalrealist/lying-spreadsheets-ii](https://github.com/legalrealist/lying-spreadsheets-ii)**.

## The shape of the attack

Every version of this is the same move:

> A file carries two representations of the same field. A human reads representation **H** — what the app renders. An LLM pipeline reads representation **M** — what a library extracts. The attacker controls both and makes **H ≠ M**.

Why it's nasty for LLM pipelines in particular:

- **It's safety-proof.** The payload is data, not an instruction. RLHF has nothing to grab.
- **It rides the defaults.** `pandas.read_excel`, plain-text email extraction, the popular document loaders — they all do the wrong thing out of the box.
- **It severs provenance.** The model's output — a risk score, a covenant verdict, a summary — gets trusted by a person who never re-derives it from the rendered source.

### Two new doors

**Spreadsheets.** An `.xlsx` formula cell stores both the formula *and* a cached result. Excel recomputes on open; headless readers return the cache verbatim. So you edit one number in the file's XML — leave the formula untouched — and the human (who recalculates) and the pipeline (which trusts the cache) part ways. No fonts, no invisible characters, byte-for-byte clean.

**Email.** A `multipart/alternative` message has a plain-text part and an HTML part. The attacker writes both. Most LLM email loaders take plain text (or strip the HTML to text, which *keeps* `display:none` content); the human reads rendered HTML. One message, three possible readings, none of which the human can audit by glancing at their inbox.

## The interesting part: does the model notice?

The pipeline never compares H and M, so the only thing standing between a forged document and a bad decision is the model's own reasoning. I tested it — blind analyst agents, given only the extracted view, asked to do a realistic job — across **GPT-5.5 and Claude Sonnet, ten runs per condition, labeled by an independent judge.**

When the fabrication is *sloppy* — say the ratio says 2.5× but debt ÷ EBITDA visibly works out to 3.8× — the model catches it every time (10/10, both models). But that's not news. That's exactly what lying-spreadsheets I taught us: **numbers must be cross-checked.** It's the baseline.

The new result is what happens when the attacker is *tidy*. Fake the components too, so every figure reconciles — 142 + 10 = 152, and 380 ÷ 152 = 2.5×. Now there's nothing to catch. Both models certified **COMPLIANT, 10 out of 10.** They cross-footed the table, found it internally consistent, and signed off. The true precedent — the real \$90M operating income — was never in the data they were handed.

Then the part I didn't expect.

### Telling the model to verify made it worse

I added one instruction: *"Before answering, independently recompute each figure and flag anything that doesn't reconcile."* Surely a model told to be suspicious does better?

It did worse. Detection stayed at zero. And Claude — which, left to its own devices, spontaneously warned "this data is only internally consistent, it could be falsified, require supporting schedules" in 6 of 10 runs — **stopped warning entirely (0 of 10) once told to verify.** The consistent table sailed through the recompute it was asked to perform, which *manufactured confidence* and suppressed the instinct that was actually protecting it. Asking for verification was worse than not asking.

### And most data has no math at all

A covenant ratio at least has arithmetic to check. A governing-law clause doesn't. A delivery date doesn't. A counterparty rating doesn't. When I diverged *contract terms* between the two readings — the email says six weeks at \$50 with no termination right; the rendered version the human reads says four weeks at \$40 with one — both models recorded the false terms verbatim, 10 out of 10, into the record the human would later trust. There is no cross-check for "is this the term we agreed to." The only signal that anything is wrong is the divergence itself, and the pipeline threw it away.

## These aren't strawman parsers

It would be easy to wave this off as "well, don't use a naive reader." So: Microsoft's **MarkItDown** — a tool whose entire purpose is converting documents *for LLM consumption* — reads the tampered workbook as `2.5× / COMPLIANT`. **BeautifulSoup's `.get_text()`**, the canonical HTML-to-text step in countless RAG pipelines, swallows the `display:none` instruction the human never sees. These are the defaults teams reach for.

## The fix, and its limit

The defense is not "make the model smarter." We just watched the smartest available models, *and* an explicit instruction to verify, all fail. The defense is structural: **reconstruct H and compare it to M before the model sees anything.**

For spreadsheets that means recomputing every formula from its raw inputs and flagging any cell whose cache disagrees — which catches numbers *and* text. The repo ships a detector that does exactly this, and it flags every tamper above. But it taught me its own limit: recompute only works while the precedents are present. Extract a single summary sheet and drop the inputs it references, and the detector goes dark — it returns nothing, because it has nothing to recompute against. That's not a clean bill of health; it's "unverifiable," and a pipeline must treat the two differently.

Which lands on the one defense that always applies: **compare the two readers.** Recompute numbers from inputs; diff the rendered document against the extracted text for everything else. Never let the model reason over the extracted view alone, because the extracted view is precisely what the attacker controls.

## Honest about the limits

These are constructed proofs-of-concept against generic pipelines, not a named-vendor disclosure. The model results are ten runs per condition across two model families — enough to show a clear boundary (tidy fabrications certified ~100%, sloppy ones caught ~100%), not a calibrated real-world rate. The class itself is known to the eDiscovery and security communities; what's new here is the cached-value and multipart instances and, more usefully, the map of *when the model's own reasoning saves you and when it can't* — including the counterintuitive finding that prompting it to verify can backfire.

If you're building document or email ingestion for anything that matters — legal review, underwriting, compliance — assume the file your model reads is not the file your client sees, and add the comparison. The code, the experiments, and the detectors are all here: **[github.com/legalrealist/lying-spreadsheets-ii](https://github.com/legalrealist/lying-spreadsheets-ii).**
