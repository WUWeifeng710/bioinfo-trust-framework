# Verification gates

The four gates in detail, plus what each risk tier owes. `SKILL.md` states the rules; this file is
the operational version — what to actually do, and what to write down.

## Setting the tier before anything else

Ask one question: **if this result is wrong, what does it cost?**

| Answer | Tier |
|---|---|
| Nothing beyond re-running it | 0 |
| Rework inside the project — redo the analysis, rewrite a section | 1 |
| Wet-lab time, reagents, samples, animals or plants; a publication claim; a clinical or regulatory decision | 2 |

The trigger is the **next action the project will take**, not the complexity of the analysis. A
simple t-test that decides which construct gets cloned is Tier 2. A 40-step assembly that only feeds
a figure caption nobody will cite can be Tier 1.

Say the tier out loud in the contract. When you cannot decide, take the higher tier — the cost of
one extra verification step is minutes; the cost of the wrong tier is measured in months.

## Gate 0 — Frame

Before touching data, write down five things:

1. **Question** — one sentence. If it takes two, the analysis is not ready.
2. **Unit of analysis** — what one *n* is. "Biological individual" is an answer; "cell" and "read"
   are not, unless the population genuinely is cells.
3. **Comparison** — against what.
4. **Success criterion** — what outcome would count as answering the question.
5. **Tier**.

Where this goes: the top of `analysis-contract.txt`.

A framed question prevents the most expensive failure mode in agent-assisted analysis: producing a
technically correct result to a question the project did not ask.

## Gate 1 — Contract

Copy `assets/analysis-contract.template` into the analysis directory as `analysis-contract.txt` and
fill it.

The three value states, and why they are different:

| Written | Meaning | Effect |
|---|---|---|
| `UNKNOWN` or blank | Not thought through yet | **Blocks execution.** Fix it first. |
| `not_applicable` | Does not exist in this analysis | Allowed, but every use must be justified in `not_applicable_justification` |
| A concrete value | Decided | Checked against the rules |

`not_applicable_justification: none` does not justify anything — if any field is `not_applicable`,
that line must carry the real reason.

Fields that may never be `not_applicable`: `analysis_id`, `question`, `analysis_type`,
`unit_of_analysis`, `tier`, `success_criteria`. These conceptually always exist; marking them
`not_applicable` is how a version record gets bypassed.

Worked example — a taxonomy-profiling run:

```
analysis_type: shotgun_metagenomics
unit_of_analysis: biological individual (soil core)
reference_genome: not_applicable
reference_annotation: not_applicable
reference_database: GTDB r220
not_applicable_justification: taxonomy profiling uses a marker database, not a genome build
```

That is a legitimate `not_applicable`: the quantity genuinely does not exist here, and the reason is
recorded. Compare with `reference_database: not_applicable` on the same analysis — that one would be
false, because kraken2 cannot classify against nothing.

## Gate 2 — In-run checks

Three actions after **every** step, in this order:

1. **Append the provenance row.** Five facts + the command + where any default came from. Do it now,
   not at the end.
2. **Check the step's QC metric** against the range you expected *before* running it.
3. **Handle a failure explicitly** — resolve it, or write a deviation record.

### Step-level QC expectations

State the metric and range before running. The point is that you cannot judge "normal" after the
fact, once you have already seen the result.

| Step class | Typical metric to state up front |
|---|---|
| Read QC / trimming | reads surviving, per-base quality, adapter content |
| Alignment | mapping rate, uniquely mapped fraction, duplication |
| Quantification | assignment rate, genes detected, library-size distribution |
| Variant calling | depth at called sites, Ti/Tv, het/hom ratio, call count vs expectation |
| Assembly | N50, contiguity, BUSCO completeness, contamination |
| Differential testing | dispersion fit, PCA outliers, sample clustering vs design |
| Clustering / embedding | cluster stability across seeds, silhouette, marker coherence |
| Metagenomics | classified fraction, host-read contamination, rarefaction saturation |
| Sequence search / family identification | hits above threshold, database version, coverage against a full-length reference |
| Phylogenetics | alignment length, gap fraction, model fit, support values, concordance with known clades |
| Structure prediction / simulation (MD, docking) | geometry sanity (no atom clashes), RMSD against a known structure, binding-site occupancy, equilibration, RMSD plateau, convergence of the measured quantity |

Ranges belong to the project, not to this skill. State them; don't inherit them silently.

### Stop conditions

Stop and resolve when:

- a QC metric falls outside its stated range;
- a step produces zero (or an implausible) number of features;
- the sample structure in an embedding contradicts the design (a batch driving the split);
- a known answer fails to be recovered;
- a step's output changes when re-run without a change in inputs.

Stopping is not the same as deadlocking — see the deviation record below.

### Deviation record

One line per deviation, appended to the decision log:

```
rule:        <what the standard said>
did:         <what was done instead>
why:         <the reason>
impact:      <what this could change about the conclusions>
```

A recorded deviation is a decision. That is categorically different from proceeding quietly, and it
is the difference between "the QC threshold was inappropriate for this library type" and "nobody
looked".

Since framework 1.1.0 the deviation state also lives per step in the provenance ledger's
`deviation` column (`met` / `deviated` / `unknown`). `deviated` requires a matching entry in
`error-ledger.tsv`; `unknown` blocks delivery — the checker enforces both.

## Gate 3 — Delivery audit

Before the artifact leaves your hands:

1. Walk the deliverable checklist in `SKILL.md`.
2. Add one claim-ledger row per claim — including the ones you think are obvious.
3. Close the **error account**: fill `error-ledger.tsv` with one row per error that occurred
   (class `inherited` / `amplified` / `emergent`, plus `emergent_kind` for emergent ones), or
   declare `# none-detected-by: <method>` at the top. An empty ledger without the declaration
   fails the gate.
4. At tier 2 with human-verified claims: record what the review did in `review-record.tsv` —
   scope, identified reviewer, duration, disagreements, overrides, errors found. The checker
   reports the totals and judges nothing; the point is that "a human checked it" becomes a
   measurable component instead of a signature.
5. Run the mechanical check:

   ```
   python scripts/verify_deliverable.py <analysis_dir>
   ```

   Exit 0 = no mechanical failures. Fix what it reports, or list genuinely mis-flagged tables in
   `.trust-ignore` with a comment saying why. Findings are grouped by substantive gate
   (`execution` / `design` / `inference` / `biological` / `external`); the `biological` gate has
   no mechanical check — it is exactly what the review record exists to cover.
6. Write the **unverified declaration**: what was not verified, and why. Put it in the deliverable.

## What each tier owes

### Tier 0 — exploratory

| Do | Record |
|---|---|
| Run it, look at it | Nothing formal |
| Spot-check one number | A note that this is exploratory |
| Label every output as exploratory | — |

Do not build a contract for tier 0 work. The framework's value is proportionate; applying it
uniformly is how projects decide the whole thing is bureaucracy and stop using it.

### Tier 1 — internal

| Do | Record |
|---|---|
| Contract filled at Gate 1 | `analysis-contract.txt` |
| Provenance row per step | `provenance-ledger.tsv` |
| Numeric cross-check of the headline result by a second route | A line in the decision log |
| Figure audit | Checklist in `references/visualization.md` |
| Claim ledger for the deliverable's claims | `claim-ledger.tsv` |

Missing at tier 1: a pinned environment (a warning, not a failure), and the re-run test.

### Tier 2 — decisive

Everything in tier 1, plus:

| Do | Why |
|---|---|
| Pinned environment + lock file with the result | Someone else must get the same numbers |
| **Plant a known answer and recover it** | Proves the pipeline can detect the effect it claims to detect |
| **Independent re-derivation** — a second method with different assumptions | Catches method-specific artefacts |
| **Re-run test** — re-execute from the locked environment, compare outputs | Turns "should reproduce" into "does reproduce" |
| **Named human review** of the load-bearing steps | The only defence against a plausible wrong answer |
| Human verification recorded on every causal and clinical claim | Association is not causation, and the label must be earned |

The planted-known-answer step is the one most often skipped and the most valuable. Feed the pipeline
a case whose answer is already established — a validated gene set, a spike-in, a positive control
sample, a known-null comparison — and confirm it returns that answer. A pipeline that has never
recovered a known truth has not been validated, however clean its logs look.

## The verifier's limits

`scripts/verify_deliverable.py` checks structure: presence, formatting, enums, cross-references,
missing corrections. It cannot check whether a number is **true**.

- It cannot tell whether the QC range was appropriate.
- It cannot tell whether an interpretation overreaches.
- It cannot tell whether a figure is misleading.
- It cannot tell whether a cited paper says what the claim says.

Passing it means the paper trail is complete. It does not mean the science is right. The human items
on the checklist are where the science gets checked, and no script substitutes for them.
