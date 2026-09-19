---
name: bioinfo-trust-framework
description: 生信分析可信度总闸。任何生信分析开工前必须加载。Trustworthy bioinformatics.
version: 1.0.1
author: WU-WEIFENG
license: MIT
platforms: [linux, macos, windows]
tags: [bioinformatics, research, reproducibility, provenance, verification, figures]
category: research
metadata:
  hermes:
    tags: [bioinformatics, research, reproducibility, provenance, verification, figures]
    category: research
    related_skills: [bio-sequence-curation, grounded-citations]
---

# Trustworthy Bioinformatics Analysis

This skill governs **whether a result can be trusted** — reliability, provenance, reproducibility,
and figures — across **bioinformatics analysis as a whole**: sequencing and omics work, sequence and
gene-family analysis, phylogenetics, structural and docking work, and anything else whose output a
researcher will act on. It is not tied to one data type, and it does not govern **how to produce** a
result: no pipelines, no thresholds, no tool choices, no technique-specific methods. Those belong to
project-level skills.

It is written to work in any agent that can load a markdown skill: the only fields any loader needs
are `name` and `description`. Everything else here is agent-neutral — no tool names to translate, no
runtime to install.

## Authority — this file is the standard, not an implementation

This skill is the **standard**, published at
[WUWeifeng710/bioinfo-trust-framework](https://github.com/WUWeifeng710/bioinfo-trust-framework).
Runtime-specific skills — WorkBuddy's `bio-analysis-guard`, and any
future equivalent — are **implementations**: they add enforcement machinery for one platform and may
restate these rules in another language. Both can be loaded at once; they are not rivals.

When the two disagree, **this file wins.** Two rules keep that from being a matter of taste:

- **Implementations may strengthen, never weaken.** Adding a check, narrowing a tolerance, or
  promoting an advisory item to mandatory is fine. Dropping a requirement, widening a threshold, or
  downgrading a FAIL to a WARN is not. *A local check that passes where the standard would fail is a
  defect in the implementation, not a legitimate local variation.*
- **Close a gap by amending the standard, not by routing around it.** When an implementation finds
  something this file does not cover, the fix belongs **here**, so every implementation inherits it.
  Patching it locally creates silent divergence: two stacks that agree today and return opposite
  verdicts two quarters later, with nothing in either file to say why. Behaviour that is genuinely
  local stays registered in the implementation's own deviation table — recorded, not implied.

`hypothesis_generating` entered the claim levels by exactly this route; see *Pillar 2*. The
implementation needed to forbid enrichment results from being labelled `causal`, and had no level
saying what they actually are. The level was added here rather than to the implementation.

**Shared vocabulary.** Some of these quantities are word lists, not thresholds. Two stacks that
spell them differently are not disagreeing about safety — they simply cannot communicate, and one of
them will reject a deliverable the other requires. These must read identically here and in every
implementation; changing one is a change to *this file*:

| Quantity | Defined in |
|---|---|
| Claim / evidence level enum | *Pillar 2* |
| `UNKNOWN` vs `not_applicable` semantics | *Gate 1 — Contract* |
| Deviation states (`met` / `deviated` / `unknown`) | *Gate 1 — Contract* |

An implementation may add checks, thresholds and mechanisms. It may not re-spell these.

## Core principle

**Trust the evidence chain, not the agent's conclusion.**

An analysis agent is good at calling mature tools, writing glue code, and running pipelines. Its
*conclusions* carry no authority of their own. Every conclusion must be traceable to executed code,
versioned data, and parameters with a stated basis.

The failure mode this skill exists to prevent is not a crash. It is a **plausible wrong answer**:
a clean pipeline, a confident summary, a polished figure, and a number that is wrong. Nothing errors
out, so nothing stops you from acting on it.

## Why this matters (and what it costs when it fails)

In research, a wrong result is not a failed run — it is a **downstream commitment**. Someone cultures
the plants, orders the reagents, runs the cohort, spends months at the bench, and then the effect
is not there. The cost lands on wet-lab time, materials, and sometimes a publication. It is
irreversible.

This single fact sets the whole posture of this skill:

- A result that might be wrong is not a result. It is a hypothesis, and it must be labelled as one.
- Verification effort should be proportional to **what the result triggers**, not to how tidy it looks.
- The agent's job is to make its own work checkable by someone else — not to sound confident.

## The evidence chain

Every claim in a deliverable must sit at the end of an unbroken chain:

```
CLAIM
  └─ figure / table            (the artifact a reader sees)
       └─ result file          (the on-disk output it was drawn from)
            └─ script + command (what was actually executed)
                 └─ parameters + why they were chosen
                      └─ tool + exact version
                           └─ input data + checksum
                                └─ reference build (genome / annotation / database version)
  └─ literature or database support   (required for interpretation, not for description)
```

Alongside the chain — not as a substitute for it — sits the layer that says **who or what
executed it**: the agent, the model, the session, the window, and the author of each step. A chain
proves the computation is reproducible; the actor layer is what tells a later reader whether two
results came from the same reasoning or only from the same commands. See *Gate 1 — Contract* for
`run-context.txt`, and the two ledger columns `started_at` / `authored_by`.

One missing link means the claim is **not deliverable**. Downgrade it to `NOT VERIFIED`, or drop it.
Never soften a broken chain into confident prose — that is the single most damaging thing an
analysis agent can do.

`references/evidence-chain.md` has worked examples of broken chains and a 10-minute audit procedure.

## When to Use

Load this skill at the start of any task whose output a human will treat as a scientific result, and
again before delivering it. Signals:

- Analysis types: differential expression, enrichment, variant calling, GWAS, metagenomics /
  abundance profiling, single-cell, gene-family identification (BLAST/HMMER), ChIP-seq / ATAC-seq,
  phylogenetics, molecular docking, molecular dynamics, structural geometry.
- Deliverables: a report, a result table, a figure for a paper, a dataset, a conclusion.
- Any time a result will be **used to decide the next experiment**.
- Any time the agent is about to summarize, interpret, or extrapolate.

## When Not to Use

- Choosing a tool, a threshold, or a pipeline step. That is project-level work.
- Throwaway exploration with no deliverable, where the human explicitly wants a fast sketch.
- Pure format conversion, file plumbing, or environment setup.

If a deliberate deviation is warranted, take it and **record it** — see *Deviation protocol*. The
point is never to force compliance; it is to make deviation an explicit decision instead of a
silent default.

## Prerequisites

- No runtime, no network, no API keys, no external dependencies. The framework itself is
  instruction-only.
- The gate checker needs Python 3.8+ and nothing else — standard library only.
- Knowledge of the analysis domain is assumed; this skill supplies the trust discipline, not the
  methods.

## How to Run

The framework has no commands of its own — it is followed, not executed. Its single executable is
the delivery gate:

```bash
python scripts/verify_deliverable.py <analysis_dir> [--expect-tier 0|1|2] [--json]
```

Exit code 0 means no mechanical failures. `references/verification-gates.md` explains each gate and
what every risk tier owes; `references/evidence-chain.md` covers broken chains.

If you change the checker, run `python scripts/test_verify_deliverable.py` before trusting it. A
gate that has never failed a known-bad input has not been validated — and, as its own regression
suite records, this one has twice been wrong in both directions.

There is no Quick Reference table, because the workflow *is* the reference: four gates in
`## Operating procedure`, one checklist, one deviation rule.

## Pillar 1 — Reliability: the result must not be wrong

- **Never hand-roll the compute core.** Statistical tests, aligners, quantifiers, and solvers come
  from validated, widely-used implementations. An agent-authored implementation of a standard
  method is an unvalidated method.
- **Know the expected range before you run it.** For each step, state the QC metric and the range you
  expect. Out of range means stop and resolve — not proceed and mention it later.
- **Plant a known answer (positive and negative controls).** Run the pipeline on a case whose outcome
  is already known — a validated gene set, a spike-in, a housekeeping control, a deliberately
  shuffled sample — and confirm it recovers that answer. A pipeline that has never recovered a known
  truth has not been validated, however reasonable it looks.
- **State the null expectation.** Write down what you should observe if the effect is absent, and
  check it. "Nothing surprising" is not a null check.
- **Independent re-derivation for high-impact results.** A second method with *different
  assumptions*. The same tool with a different parameter is not independent verification.
- **No result without a run record.** Anything not executed is labelled `NOT RUN`. "I estimate",
  "this should be", "typically around" — these are not results and must not appear in a results
  section.

## Pillar 2 — Provenance: every step and every claim has a stated basis

**Per step, persist five facts:** tool, exact version, parameters, input data version, and the
**reference build** — genome, annotation, and database version.

**Per run, persist the actor layer.** `run-context.txt` records which agent, which model and
version, which session, and the window the run occupied. **Per step, record when and who**:
`started_at`, `ended_at`, `authored_by`. This is not decoration. Without it two runs are
indistinguishable even when one was produced by an older model, a different agent, or a different
person — and an analysis's failure profile depends on its author, not only on its commands. If the
harness genuinely does not expose a model identity, that is a real condition: write `not_exposed`
**and explain it**. What is not acceptable is silence.

**The timestamp is the cheapest integrity check available.** A ledger claiming
`reference_database: GO 2026-08` in a run that ended in June is provably false. That check only
exists once steps carry dates — which is why every step timestamp must fall inside the declared run
window.

Reference-build omission is the most common provenance hole in the whole field, and it fails
silently: coordinates from GRCh37 and GRCh38 mix without a single error message. State the build
explicitly, every time, even when it feels obvious.

- **Defaults need a source.** If a parameter was not changed, say where the default comes from —
  official documentation or a paper. Choosing "by feel" is not a decision.
- **Stay aligned with the mainstream.** Method and parameter choices should match what the field
  currently does. A deviation from the community default is a *deliberate* deviation: justify it in
  writing, and say what it could change.
- **Write the decision log.** One line of "why" for every threshold, filter, and tool choice.
- **Quantify uncertainty properly.** Test type, multiple-testing correction, effect size with an
  interval, and the real *n*. A p-value by itself is not an interpretation, and an uncorrected
  p-value in a genome-wide scan is a defect, not a stylistic choice.
- **Label every claim by level** — `descriptive` (what the data shows) / `comparative` (A vs B) /
  `hypothesis_generating` (the result can only nominate a hypothesis — enrichment, pathway,
  co-expression, correlation screens) / `causal` (X drives Y) / `clinical` (decision-grade). A
  descriptive result written up as causal is the most common overreach in agent-assisted analysis.
  Causal and clinical claims need an experiment, a mechanism, or literature support — they never
  follow from the association alone. `hypothesis_generating` is not a softer word for `causal`: it
  records that the analysis **cannot** support more, and a downstream step that treats it as
  established is a defect. An enrichment or pathway result labelled `causal` is the canonical case.
- **External claims carry their evidence.** For literature-level assertions, use a citation/grounding
  discipline if one is available; otherwise attach the source and the exact supporting sentence, or
  mark the claim `[unverified]`. Never cite a source you did not open.
- **Record who reviewed it.** `verified_by: human` on its own is an assertion, not evidence — an
  identity and a date make it auditable. Tier 2 requires `reviewer`; there is no such thing as an
  anonymous "a human checked this". A personal name is **not** required: a stable handle, initials
  or role id (`@wuwei`, `lab-lead`, `pi`) satisfies it. What is rejected is an empty or placeholder
  value, because that is indistinguishable from nobody having looked.
- **The decision log records who, not only why.** "The threshold is 0.05" and "the agent proposed
  0.05 and the human approved it" are different records, and only the second tells a reviewer whose
  judgement to interrogate.
- **Keep the interpretation separable from the result.** A reader must be able to tell what was
  measured from what you concluded about it.

## Pillar 3 — Reproducibility: someone else gets the same numbers

- **Lock the environment.** Version-pinned environment file or container image, recorded alongside
  the result. "It worked on my setup" is not reproducibility.
- **Orchestrate rather than accumulate scripts.** A declared workflow (Snakemake, Nextflow, a
  Makefile, a single driver script with declared inputs/outputs) beats a pile of numbered scripts.
- **Version the data.** Checksum raw inputs and store the checksums. Never overwrite upstream files;
  derive new names. Intermediate files are part of the chain — don't "tidy them up" away.
- **Fix every random seed** — clustering, dimensionality reduction, subsampling, bootstrapping,
  model training — and record it with the result.
- **Run the re-run test.** Re-execute from the locked environment on the recorded inputs and confirm
  the outputs match (bit-identical, or within a stated numerical tolerance). If it was never re-run,
  reproducibility is unverified, and should be reported as such.
- **Scale the effort to the risk.** Lockfile ≤ container ≤ full orchestration. Do not containerize a
  one-off exploration; do not ship a publishable pipeline with unpinned versions.

## Pillar 4 — Visualization: accurate first, good-looking second

Aesthetics never buy back inaccuracy. But accuracy alone is not enough either — a figure a reader
cannot parse has failed just as surely as a wrong one.

**Every figure states:** what it shows in one sentence, the *n*, what the error bars represent
(SD / SEM / CI / range / nothing), and the test used.

- **Axis honesty.** No truncated quantitative axes without an explicit break marker. No dual axes for
  unrelated quantities. No area or 3D encoding for a magnitude. No rainbow colormap for continuous
  data — use a perceptually uniform one. Bar charts of means hide distributions: show the data,
  especially at small *n*.
- **Uncertainty must be visible.** A point estimate drawn without its interval is a claim of
  precision you have not earned.
- **Accessibility.** Colour-blind-safe palettes; never colour as the *only* channel; legible at final
  print size.
- **One figure language.** Consistent fonts, sizes, palette, and legend style across the whole
  deliverable. Per-figure free-styling reads as noise, and noise reads as carelessness.
- **Label language.** Pick one — normally the target venue's — and apply it consistently. Don't mix
  languages within a figure set.
- **The three-second test.** A reader who did not do the analysis should be able to state the
  takeaway in three seconds. If they can't, the figure is carrying too much: split it.
- **Fewer and denser beats a wall of panels.** If a panel doesn't change the conclusion, cut it.

`references/visualization.md` has the full accuracy and layout checklist.

## Risk tiers: let impact set the verification strength

The tier is decided by **what the result triggers**, not by how much you like the analysis.

| Tier | Decision rule | Required verification |
|---|---|---|
| **0 — exploratory** | Wrong → costs a rerun and nothing else | Move fast. Spot-check. Label as exploratory. |
| **1 — internal** | Wrong → rework inside the project (redo an analysis, rewrite a section) | Self-check + numeric cross-check + figure audit. Contract + provenance rows. |
| **2 — decisive** | Wrong → spends wet-lab time, reagents, samples, or animals/plants; supports a publication claim; informs a clinical or regulatory decision | Contract + full evidence chain + planted known answer + independent re-derivation + **attributed human review of the load-bearing steps**. |

**Rule of thumb: if the next step in the project spends money or irreversibly consumes a resource,
it is Tier 2.** Ask it explicitly, out loud, before deciding to skip verification.

Tiering sets *how much* verification. It never sets *whether* to be honest about what was and wasn't
verified.

## Operating procedure: four gates

### Gate 0 — Frame (before touching data)

Write down: the question, the unit of analysis (what one *n* is), the comparison, the success
criterion, and the tier. If the question cannot be stated in one sentence, the analysis is not ready
to run.

### Gate 1 — Contract (before running)

Fill in `assets/analysis-contract.template` and copy it into the analysis directory. Also copy
`assets/run-context.template` in as `run-context.txt` and fill in the actor layer: `agent`,
`model`, `model_version`, `session_id`, and `run_started_at`. Required for tier ≥ 1; tier 0 skips it.

- Unresolved fields are written `UNKNOWN`. **`UNKNOWN` blocks execution.** This friction is
  deliberate: better to admit you don't know than to let a blank pass unnoticed.
- Genuinely non-existent quantities are written `not_applicable`, with a justification recorded in
  `not_applicable_justification`. `UNKNOWN` and `not_applicable` mean different things — one is "not
  thought through yet", the other is "does not exist in this analysis". Don't use the second to
  dodge the first.
- **Fields that may never be `not_applicable`:** `analysis_id`, `question`, `analysis_type`,
  `unit_of_analysis`, `tier`, `success_criteria`. These conceptually always exist. In
  `run-context.txt` the same applies to `agent`, `run_started_at` and `run_ended_at` — and
  `agent: manual` is a legitimate value when no agent was involved, so there is no gap to declare.
- The one thing you may legitimately be unable to supply is a model identity, when the harness does
  not surface one. Write `not_exposed` and say why in `model_identity_note`.

### Gate 2 — In-run checks (while executing)

After every step:

1. Append a row to the provenance ledger (`assets/provenance-ledger.tsv`) — five facts, plus the
   command, the source of any default you relied on, and **when the step ran and who or what ran
   it** (`started_at`, `ended_at`, `authored_by`). Write it **as you go**, never reconstructed
   afterwards from memory.
2. Check the step's QC metric against the expected range.
3. If a check fails, resolve it or record a deviation. Don't carry it forward silently.

### Gate 3 — Delivery audit (before the artifact leaves your hands)

1. Close `run_ended_at` in `run-context.txt`. Every step timestamp must fall inside that window.
2. Walk the deliverable checklist below.
3. Add one claim-ledger row per claim (`assets/claim-ledger.tsv`), with its level, evidence
   artifact, and — where a human reviewed it — the reviewer's identity and the date.
4. Run the verifier if the project carries one:
   `python scripts/verify_deliverable.py <analysis_dir>`
5. Anything still unverified is **declared in the deliverable**, in plain language: what was not
   verified, and why. An honest gap is a result; a hidden gap is misconduct.

## Deliverable checklist

Items marked *(auto)* can be checked mechanically — by `scripts/verify_deliverable.py` or an
equivalent. Items marked *(human)* require judgment and must be reviewed by a person.

- *(auto)* Contract complete: no `UNKNOWN`, every `not_applicable` justified.
- *(auto)* A provenance row exists for every executed step.
- *(auto)* Five facts present per step: tool, version, parameters, data version, reference build.
- *(auto)* `run-context.txt` present (tier ≥ 1) with `agent`, `session_id` and the run window
  resolved, and a model identity either given or annotated `not_exposed`.
- *(auto)* Every step carries ISO-8601 `started_at` / `ended_at` that fall inside the run window,
  plus an `authored_by` of `agent` / `human` / `agent+human`.
- *(auto)* Every claim has a claim-ledger row whose evidence artifact exists on disk.
- *(auto)* Every `verified_by: human` claim at tier 2 fills `reviewer` — any non-placeholder
  identity; a personal name is not required — and dates it.
- *(auto)* Every result table containing a `p` column also contains a multiple-testing-corrected
  column (e.g. `padj`, `q`, `FDR`).
- *(auto)* Random seed recorded; environment lock file present.
- *(auto)* No claim at level `causal` or `clinical` without literature or human verification.
- *(human)* QC metrics in range; every exception explained or excluded.
- *(human)* High-impact results independently re-derived; a known answer was recovered.
- *(human)* Interpretation level matches evidence level — description not sold as causation.
- *(human)* Uncertainty reported with the correct test, correction, effect size, and *n*.
- *(human)* Figures pass the accuracy and layout checklist for the target venue.
- *(human)* Decision log complete: every threshold and tool choice has a stated "why" — **and who
  made it**.
- *(human)* The run record describes the run that actually happened: the model in
  `run-context.txt` is the one that produced the steps, not the one most flattering to cite.

## Deviation protocol

Standards are guardrails, not shackles. Deviations are expected — but they must be visible.

Every rule in this skill resolves to one of three states, recorded in the decision log:

| State | Meaning | Effect |
|---|---|---|
| `met` | Followed | — |
| `deviated` | Deliberately not followed, with reason, scope, and expected impact recorded | Allowed. State it in the deliverable. |
| `unknown` | Not established | **Blocks delivery** until resolved or explicitly declared. |

A recorded deviation is a decision. An unrecorded one is a defect. If a rule keeps getting deviated
from for the same reason across projects, that rule is wrong and belongs in a project-level skill —
move it there instead of leaving it to be ignored.

The same mechanism covers the "a check failed" case: a QC value outside its expected range does not
have to deadlock a legitimate analysis. Record the deviation, the reason, and the impact on
conclusions — that is categorically different from proceeding quietly.

## Pitfalls

- **Polished output is not verified output.** A clean notebook and a beautiful figure say nothing
  about correctness.
- **Plausible is not correct.** A wrong answer that agrees with prior expectation passes every review
  that only reads the summary.
- **Counting is not cross-checking.** Two datasets that both "have 80 genes" can still disagree.
  Cross-validate by matching keys or sequences, not by comparing totals.
- **Same tool, new parameter, is not independent verification.** Independence means different
  assumptions, ideally different data or a different algorithm class.
- **A missing reference build fails silently.** Nothing errors out; the coordinates are just wrong.
- **Provenance written after the fact is provenance reconstructed from memory** — the same failure
  mode as fabricated citations, and just as serious.
- **The chain proves the computation, not the author.** The same commands produced by a different
  model, a different agent, or a different person are a different run — and the difference is
  invisible in the ledger unless the actor layer is filled in.
- **When a gate is uniformly painful, it gets switched off.** A check that fires on a legitimate
  input is worse than no check: it teaches the project to ignore the output. Fix the check, or
  narrow it — never leave it crying wolf.
- **A model identity you cannot obtain is not a model identity you may omit.** `not_exposed` plus a
  reason is a record; silence is a gap.
- **Deleting intermediate files breaks the chain.** Someone will need the read counts later.
- **"Handled it internally" without evidence.** QC exceptions that get a one-line mention and no
  record are indistinguishable from QC exceptions that were never noticed.
- **Reflexive over-verification.** Tier 0 work run through a Tier 2 process wastes the project's time
  for no gain. Proportion is the point.
- **Tiering used as an excuse.** "It's only Tier 0" justifies less verification, never less honesty
  about what was verified.
- **A figure that hides uncertainty is a wrong figure**, even when every pixel is accurate.
- **Quietly downgrading when the human asks for speed.** Say what is being skipped and what it costs.
  Let them make that call — it's their research.

## Verification (self-test)

Before delivering, answer these about your own output. Any "no" is an unfinished gate, not a
detail to mention in passing.

1. For each claim, can I name the script, the command, and the tool version that produced it?
2. Does every step record its reference build?
3. Can a reviewer tell which agent and model produced these steps, and over what window? If the
   model is unrecorded, is it annotated as `not_exposed` rather than simply absent?
4. Has this pipeline ever recovered a known answer, and can I show where?
5. Have I re-run it from the locked environment and compared the outputs?
6. Is every claim's level (`descriptive` → `clinical`) supported by its evidence?
7. For every `verified_by: human`, is there a name and a date?
8. Does every figure state its *n*, error definition, and test?
9. What did I **not** verify? (If the answer is "nothing", look harder.)

## Files

| Path | Purpose |
|---|---|
| `assets/analysis-contract.template` | Fill-in contract for Gate 1 |
| `assets/run-context.template` | Fill-in actor layer for Gate 1 — agent, model, session, window |
| `assets/provenance-ledger.tsv` | Per-step provenance ledger for Gate 2 |
| `assets/claim-ledger.tsv` | Per-claim evidence ledger for Gate 3 |
| `scripts/verify_deliverable.py` | Mechanical gate checker (stdlib only; exit 0 = pass) |
| `scripts/test_verify_deliverable.py` | Regression tests for the checker — run after any edit to it |
| `references/evidence-chain.md` | Broken-chain examples + the 10-minute audit |
| `references/verification-gates.md` | Per-tier gate checklists |
| `references/visualization.md` | Figure accuracy and layout checklist |
| `README.md` | Human-facing documentation (not read by the agent) |
| `CHANGELOG.md` | Version history — why each rule exists |
| `LICENSE` | MIT |

## Companion skills

This skill sets the standard; domain skills carry the methods. When a task needs one, load it —
if this environment has none, record the gap in `domain_skills_loaded` and lower the confidence
of the conclusions accordingly.

- Sequence-level curation and accession handling → a sequence-curation skill if available.
- Literature-level grounding and citations → a citation/grounding skill if available.
- Figure production for a specific venue → a scientific-figure skill if available.
