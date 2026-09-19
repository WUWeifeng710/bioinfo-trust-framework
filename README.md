# Trustworthy Bioinformatics Analysis

**A portable, agent-agnostic skill for the question that matters more than any tool choice:
*can this result be trusted?***

The failure mode this exists to prevent is not a crash. It is a **plausible wrong answer** — a clean
pipeline, a confident summary, a polished figure, and a number that is wrong. Nothing errors out, so
nothing stops you from acting on it.

| | |
|---|---|
| Skill name | `bioinfo-trust-framework` |
| Version | 1.0.0 |
| Description | 生信分析可信度总闸。任何生信分析开工前必须加载。Trustworthy bioinformatics. |
| Author | WU-WEIFENG |
| License | MIT |
| Platforms | linux / macos / windows |
| Category | research |
| Runtime needed | Python 3.8+ (verifier only; the skill itself is plain markdown) |
| Files | 1 `SKILL.md`, 3 references, 4 assets, 2 scripts, `README.md`, `CHANGELOG.md`, `LICENSE` |

It governs **whether a result can be trusted**, across bioinformatics analysis as a whole —
sequencing and omics work, sequence and gene-family analysis, phylogenetics, structural and docking
work, and anything else whose output a researcher will act on. It is deliberately not tied to one
data type, and it does not govern **how to produce** a result: no pipelines, no thresholds, no tool
choices, no technique-specific methods. Those belong to project-level skills.

It loads in any agent that reads markdown skills. The only fields any loader requires are `name` and
`description`; everything else is optional metadata. There are no tool names to translate, no runtime
to install, and no network calls.

---

## Install

### Option A — let your AI agent install it (recommended)

Paste this prompt into any agent that supports skills (WorkBuddy, Claude Code, Codex, Gemini CLI):

```
Install the "bioinfo-trust-framework" skill for me.

1. Clone https://github.com/WUWeifeng710/bioinfo-trust-framework.git into my skills directory
   as `bioinfo-trust-framework` (e.g. ~/.workbuddy/skills/bioinfo-trust-framework on WorkBuddy,
   ~/.claude/skills/bioinfo-trust-framework on Claude Code).
2. Confirm that SKILL.md is at the repo root, with assets/, references/ and scripts/ present.
3. Run `python scripts/test_verify_deliverable.py` and confirm every case passes.
4. Do not modify any other installed skills.
5. Report the installed path and a one-paragraph summary of when the skill applies.
```

### Option B — manual

```bash
# WorkBuddy
git clone https://github.com/WUWeifeng710/bioinfo-trust-framework.git \
  ~/.workbuddy/skills/bioinfo-trust-framework

# Claude Code
git clone https://github.com/WUWeifeng710/bioinfo-trust-framework.git \
  ~/.claude/skills/bioinfo-trust-framework
```

The repository root **is** the skill. Every skill root follows the same flat convention —
`<skill-root>/<skill-name>/SKILL.md` — so copying the folder is the whole installation.

| Agent | Skill root | Notes |
|---|---|---|
| Claude Code | `~/.claude/skills/` | flat layout |
| OpenAI Codex | `~/.codex/skills/` | flat layout |
| Gemini CLI | `~/.gemini/skills/` | flat layout |
| WorkBuddy | `~/.workbuddy/skills/` | flat layout |
| Hermes Agent | `%LOCALAPPDATA%\hermes\skills\<category>\` | the only one that nests by category — use `research\` |

```bash
# copy to every agent that shares the machine
SRC="<path-to>/bioinfo-trust-framework"
cp -r "$SRC" ~/.claude/skills/ ~/.codex/skills/ ~/.gemini/skills/ ~/.workbuddy/skills/
```

Two portability notes worth knowing:

- **Hermes profiles do not share local skills.** A skill placed in the default profile's tree is
  invisible under another profile. Verify with
  `hermes skills list --profile <name> --enabled-only` rather than assuming that the file being on
  disk means it will load.
- Only `name` and `description` are required by any loader. The extra keys (`version`, `author`,
  `license`, `platforms`, `tags`, `category`, `metadata`) are ignored by agents that don't use them
  and honoured by those that do — the package is a superset, not a lowest common denominator.

---

## Why the description is not (only) in English

The listing an agent chooses from prints the skill name plus only the **first 28 characters** of the
description. Text past that is never displayed, and the cut lands mid-word. This skill was once
described as `Reliability, provenance, reproducibility in bioinformatics.` and listed as
`Reliability, provenance, rep` — the domain word `bioinformatics` sat at character 30, so the
listing carried **no domain signal at all**, and the skill was selected in **0 of 33** trials where a
bioinformatics task was described without naming it.

The current description leads with an unconditional load directive inside the window. That was not a
style choice. Measured on the same probes:

| Description inside the 28-char window | Selected |
|---|---|
| `Reliability, provenance, rep…` | 0 / 3 |
| `Bioinformatics trust gate: l…`, `Bioinformatics gate: load before any…`, `Bioinformatics mandatory bef…`, `生信分析可信度总闸 / mandatory…` | 0 / 18 |
| **`生信分析可信度总闸。任何生信分析开工前必须加载。`** | **9 / 9** (three independent repeats) |

A domain word alone is not enough, and `mandatory` in English is not enough. What reproduces is an
**unconditional load directive**. The Chinese clause carries it; the English tail
(`Trustworthy bioinformatics.`) rides along for human readers and terminates on an ASCII period.
If your environment prefers a pure-English listing, the rule to preserve is the directive, not the
language — but expect to re-measure, because that exact string has not been reproduced in English.

The `≤ 60` description budget that once pushed this description into a bare noun phrase comes from
Hermes' *repo* CI (`test_authoring_standards.py`), whose `_skill_paths()` globs only `skills/**` and
`optional-skills/**`. An **installed** skill is not covered by it. Across 645 installed skills the
median description length is 273 characters in the WorkBuddy root (88% exceed 60), 214 in Codex, 188
in Claude, and 57 in Hermes. The noun-phrase description this skill once carried was a response to a
rule that did not apply to it.

---

## The four problems it answers

| The problem | The mechanism | Where |
|---|---|---|
| **1. Is the result reliable?** A wrong answer costs wet-lab time, reagents, samples — irreversibly | Never hand-roll the compute core; state QC ranges *before* running; **plant a known answer** and confirm the pipeline recovers it; state the null expectation; independent re-derivation with *different assumptions*; no result without a run record | Pillar 1, `references/verification-gates.md` |
| **2. Where did it come from, and is the interpretation defensible?** | The **evidence chain** — every claim traces back through figure → result file → script → command → parameters → tool version → input checksum → reference build; parameter defaults need a cited source; method choices must match the community mainstream; claims labelled `descriptive` / `comparative` / `hypothesis_generating` / `causal` / `clinical`. Plus the **actor layer** — which agent, which model, which session, over what window, and who authored or reviewed each step | Pillar 2, `references/evidence-chain.md` |
| **3. Will it reproduce?** | Locked environment; orchestration over scattered scripts; checksummed inputs; fixed seeds; and the **re-run test** — re-execute from the locked environment and compare outputs | Pillar 3 |
| **4. Is the figure accurate, and does it read?** | Accuracy pass before aesthetics pass; every figure states its *n*, error definition, and test; axis-honesty rules; perceptually uniform and colour-blind-safe encoding; one figure language per deliverable; the **three-second test** | Pillar 4, `references/visualization.md` |

The unifying claim: **trust the evidence chain, not the agent's conclusion.**

---

## The evidence chain

```
CLAIM
  └─ figure / table            the artifact a reader sees
       └─ result file          the on-disk output it was drawn from
            └─ script + command what was actually executed
                 └─ parameters + why they were chosen
                      └─ tool + exact version
                           └─ input data + checksum
                                └─ reference build (genome / annotation / database)
  └─ literature or database support      needed for interpretation, not for description
```

One missing link means the claim is **not deliverable** — downgrade it to `NOT VERIFIED`, or drop it.
Softening a broken chain into confident prose is the single most damaging thing an analysis agent
can do, because the output looks identical either way.

### The layer the chain does not contain

The chain documents the **work** — data in, code, files out. It cannot document the **worker**.
`run-context.txt` carries that: `agent`, `model` and `model_version`, `session_id`, and the run
window. Per step the ledger adds `started_at` / `ended_at` / `authored_by`; per claim, `reviewer` /
`reviewed_at`.

This is what separates two runs that share every command but not their reasoning — a model update
changes the code and the parameter choices an agent writes, and the ledger alone cannot see the
difference. It is also where the cheapest integrity check in the whole framework lives: **every step
timestamp must fall inside the run window.** That does not make a ledger written on Friday from
memory impossible; it makes it detectable. A ledger claiming `reference_database: GO 2026-08` in a
run that ended in June is caught the same way.

A harness that does not surface a model identity is a real condition, not an excuse: write
`not_exposed` and say why in `model_identity_note`. **Blank is not an option** — it is
indistinguishable from an oversight.

---

## Risk tiers decide how much verification is owed

The tier comes from **what the result triggers**, not from how complex the analysis is.

| Tier | Decision rule | Owed |
|---|---|---|
| **0 — exploratory** | Wrong → costs a rerun, nothing else | Move fast, spot-check, label it exploratory |
| **1 — internal** | Wrong → rework inside the project | Contract, provenance rows, numeric cross-check, figure audit |
| **2 — decisive** | Wrong → spends wet-lab time, reagents, samples, animals or plants; supports a publication claim; informs a clinical or regulatory decision | Everything above, plus pinned environment, planted known answer, independent re-derivation, re-run test, and **named human review** |

**Rule of thumb: if the next step in the project spends money or irreversibly consumes a resource,
it is Tier 2.**

The tiering exists to keep the framework proportionate — running a Tier 2 process over Tier 0 work is
how a discipline gets abandoned as bureaucracy. But the tier only ever sets *how much* verification
is owed. It never relaxes honesty about what was and wasn't verified.

---

## The four gates

| Gate | When | What happens |
|---|---|---|
| **0 — Frame** | Before touching data | Question in one sentence, unit of analysis, comparison, success criterion, tier |
| **1 — Contract** | Before running | Fill `analysis-contract.txt` **and** `run-context.txt` (agent, model, session, `run_started_at`). **`UNKNOWN` blocks execution** — deliberate friction; `not_applicable` is allowed but must be justified, and a model identity may be `not_exposed` **with a reason** |
| **2 — In-run** | After every step | Append the provenance row *as you go*, including `started_at` / `ended_at` / `authored_by`; check the QC metric against its pre-stated range; resolve failures or record a deviation |
| **3 — Delivery audit** | Before the artifact leaves | Close `run_ended_at`; walk the checklist; add claim-ledger rows with the reviewer's name and date; run the verifier; **declare what was not verified** |

A deviation is allowed and expected. Silently complying is not. Every rule resolves to `met`,
`deviated` (with reason, scope, impact — stated in the deliverable), or `unknown` (**blocks
delivery**). A recorded deviation is a decision; an unrecorded one is a defect.

---

## The verifier

```bash
python scripts/verify_deliverable.py <analysis_dir> [--expect-tier 0|1|2] [--json]
```

Stdlib only, Python 3.8+, no network. Exit code `0` = no mechanical failures; `1` = at least one
FAIL.

**Checks structure**, grouped by section:

| Section | Representative checks |
|---|---|
| `contract` | required keys present; no `UNKNOWN`; tier ∈ {0,1,2}; every `not_applicable` actually justified; `not_applicable` rejected on fields that always exist |
| `run-context` | file present (tier ≥ 1); `agent` / `session_id` / run window resolved, no `UNKNOWN`; `agent: not_applicable` rejected (write `manual` instead — there is no gap to declare); `model` = `not_exposed` accepted **only with a `model_identity_note`**; window must be internally ordered |
| `provenance` | a row per step; required columns non-empty; `input_sha256` is a real digest; declared outputs exist on disk; tier 2 has a `rerun_match=yes`; per step `started_at` / `ended_at` are ISO-8601 and **fall inside the run window**; `authored_by` ∈ {`agent`, `human`, `agent+human`} |
| `claims` | evidence artifact exists on disk; `level` / `confidence` / `verified_by` in enum — `level` carries five values (`descriptive` / `comparative` / `hypothesis_generating` / `causal` / `clinical`); `causal` and `clinical` need literature or human verification; tier 2 requires human verification on those; `verified_by: human` at tier 2 needs a **named `reviewer` and a `reviewed_at`** — an anonymous "human" FAILs |
| `reproducibility` | environment lock present (FAIL at tier 2, WARN at tier 1) |
| `tables` | a `p` column without `padj`/`q`/`FDR` in any scanned `.tsv`/`.csv` |

Everything in `run-context`, plus step timestamps and `authored_by`, is skipped at **tier 0** — the
exploratory path stays fast on purpose.

Timestamps are compared at the coarsest granularity present: a window declared as `2026-09-19` is
compared by date, so writing the run window by date alone does not fail same-day steps.

If a scanned table has a column literally named `p` that is not a hypothesis test, list it in
`.trust-ignore` (one glob per line) with a comment explaining why.

**What it cannot check** — and this matters more than what it can:

- whether a number is *true*;
- whether the QC range was appropriate;
- whether an interpretation overreaches its evidence;
- whether a figure misleads;
- whether a cited paper says what the claim says.

Passing the verifier means the paper trail is complete. It is not a statement about the science.
The `(human)` items on the deliverable checklist are where the science gets checked, and no script
substitutes for them.

---

## Validation status

The verifier ships with a regression suite — `scripts/test_verify_deliverable.py`, 13 cases and 23
assertions, stdlib only. Run it after any edit to the checker:

```bash
python scripts/test_verify_deliverable.py
```

Cases marked *(regression)* encode a defect that was actually observed in the field or in the
artifact, rather than a hypothetical one:

| Fixture | Expected |
|---|---|
| Tier 2, complete contract, actor layer closed, `rerun_match=yes`, lock, `padj` | PASS |
| The shipped ledger template, copied verbatim and filled in *(regression)* | PASS |
| A BOM in the ledger header, as Excel on Windows writes *(regression)* | PASS |
| Tier 2 with no `run-context.txt` *(regression)* | FAIL — this passed before v0.3.0. That was the gap |
| `model: not_exposed`, with and without `model_identity_note` | PASS / FAIL |
| A step timestamp outside the run window; `ended_at` before `started_at` | FAIL |
| Run window written by date alone, same-day steps *(regression)* | PASS |
| Run window by date alone, a step on a later day | FAIL |
| `agent: UNKNOWN` / `agent: manual` / `agent: not_applicable` | FAIL / PASS / FAIL |
| Blank or placeholder step timestamps; invalid `authored_by` | FAIL |
| Anonymous `verified_by: human` at tier 2 / at tier 1 | FAIL / WARN |
| Tier 0 with an entirely empty actor layer | PASS — the fast path stays fast |
| An enrichment result labelled `hypothesis_generating` *(regression)* | PASS — the level was absent from the standard until v0.3.2 while the implementation required it |
| Uncorrected `p` column; tier 2 without a lock file | FAIL — earlier checks were not softened |

Five defects have been found and fixed by exercising the checker, none of which a read-through caught:

1. `not_applicable_justification: none` was accepted as a justification, so three reference fields
   could be waved through with no reason given. Now treated as empty.
2. Output used non-ASCII punctuation, which garbles under a non-UTF-8 console. Now pure ASCII.
3. **The shipped ledger template carried a UTF-8 BOM** *(v0.3.0 — half fixed; completed in v0.3.2)*.
   A user copying it as instructed got `FAIL provenance: missing columns: step_id` — the gate
   reporting a phantom missing column in the framework's own artifact. v0.3.0 fixed the *readers*
   (`utf-8-sig`), and this section then recorded that the templates ship without a BOM. They did not:
   both still began `ef bb bf`, and `claim-ledger.tsv` carried a comment asserting the opposite. **A
   comment that contradicts the bytes is worse than the bytes** — it is precisely what stops the next
   reader from checking. v0.3.2 strips both; the comment is now true.
4. **A run window written by date alone failed every step** *(v0.3.0)*. `run_started_at: 2026-09-19`
   resolves to midnight, so a window bounded only by dates had zero length and every real step fell
   outside it. Timestamps are now compared at the coarsest granularity present.
5. **The claim-level enum had no value for hypothesis-generating results** *(v0.3.2)*. Not found by
   feeding the checker a bad input but by diffing the standard against its implementation, which
   carried a level this file lacked. Enrichment output is not `comparative`, and marking it `causal`
   is the classic overreach; it nominates a hypothesis and nothing more. The level was added here, by
   the rule in *Authority*, instead of staying a local extension of one implementation.

Defect 4 is worth dwelling on. `references/verification-gates.md` already warns that a gate which is
uniformly painful is how a project concludes the discipline is bureaucracy and stops using it — and
the actor layer, added to catch silent gaps, would itself have been switched off. **A check that
fires on a legitimate input is worse than no check.**

That is the framework applied to itself: a check that has never failed a known-bad input has not
been validated.

---

## Package layout

```
bioinfo-trust-framework/
├── SKILL.md                          the framework (agent reads this)
├── README.md                         this file (agent does not read it)
├── CHANGELOG.md                      version history — why each rule exists
├── LICENSE                           MIT
├── .gitignore                        repo-only
├── .gitattributes                    repo-only — pins LF line endings
├── assets/
│   ├── analysis-contract.template    Gate 1 contract, key: value, `UNKNOWN` sentinel
│   ├── run-context.template          Gate 1 actor layer — agent, model, session, window
│   ├── provenance-ledger.tsv         Gate 2 — one row per executed step, with time + author
│   └── claim-ledger.tsv              Gate 3 — one row per claim, with its reviewer
├── references/
│   ├── evidence-chain.md             broken-chain examples + the 10-minute audit
│   ├── verification-gates.md         gate detail + what each tier owes
│   └── visualization.md              figure accuracy and layout standards
└── scripts/
    ├── verify_deliverable.py         mechanical gate checker (stdlib only)
    └── test_verify_deliverable.py    regression suite for the checker
```

The repository root **is** the skill folder: everything except the two repo-only dotfiles is what
gets installed into a skill root. Template rows are prefixed with `#` so they can never be mistaken
for data.

---

## Design boundaries

Written to be stable across projects rather than tuned to one. Anything project-specific is
deliberately absent, and that absence is the feature.

| In scope | Out of scope (project-level) |
|---|---|
| Trust principles, evidence requirements, risk tiers | STAR vs bowtie2, DESeq2 vs edgeR |
| The decision framework for *how to choose* | Concrete thresholds (padj, mapping rate, resolution, seed values) |
| Gate procedure, checklists, deviation handling | Pipeline steps and commands |
| Figure accuracy and readability standards | Venue templates, palettes, house styles |

**Guardrails, not shackles.** A rule that keeps being deviated from for the same reason across
projects is a wrong rule — move it to a project-level skill instead of leaving it to be ignored.

Deliberate deviations from the Hermes skill-authoring convention, recorded rather than left implicit:

| Convention | This skill | Why |
|---|---|---|
| ~200 lines for a complex skill | ~470 lines | Dense by design; every section is load-bearing and there is no filler to cut without losing a rule |
| Fixed section order (`## Prerequisites`, `## How to Run`, `## Quick Reference`, `## Procedure`) | Present: `Prerequisites`, `How to Run`, `Verification`, `Pitfalls`. Named `Operating procedure` and `Pitfalls`; no `Quick Reference` | There is nothing to quick-reference — the skill exposes exactly one command. A `Quick Reference` section is declared not applicable in `## How to Run`, so the deviation is visible to the reader rather than silent |

---

## Authority — the standard, not an implementation

This repository is the **authoritative source** for the standard it states. A machine may also carry
a project-local skill that *enforces* the same ideas with scripts and hooks — a contract template, a
checker, a tool whitelist, a post-write hook that can block a step. Two implementations of one idea
means **double-stack drift**: change one rule and the other keeps answering with the old verdict.

Three rules make the authority enforceable rather than decorative, and they are stated in `SKILL.md`
as well:

1. **An implementation may only strengthen the standard, never weaken it.** Where the standard
   returns FAIL and an implementation lets the input through, that is a **defect in the
   implementation**.
2. **A gap at the standard level is closed here, not worked around locally.** An implementation that
   quietly handles a case the standard has no vocabulary for creates a silent fork: neither side can
   explain the other's verdict. The fix belongs in this repository, so every implementation inherits
   it.
3. **Shared vocabularies must be the same table, verbatim** — claim levels, `UNKNOWN` vs
   `not_applicable`, the three deviation states. An implementation may add checks, thresholds and
   mechanisms. It may not re-spell these values.

The first diff run under those rules found a hard conflict: the implementation required the claim
level `hypothesis_generating` (its own rule forbids labelling enrichment output `causal`) and this
file had no such level — so a deliverable filled in correctly on one side was invalid on the other,
and *mandatory* on the first. The level was added here rather than left as a local extension. That is
the point of naming an authority: **its value is not that it can overrule downstream, but that a
downstream discovery can flow back and become a capability of the whole stack.**

---

## Companion skills

This skill sets the standard; other skills carry the methods. If an environment has no skill for a
subfield, record the gap in `domain_skills_loaded` and lower the confidence of the conclusions
accordingly.

- Sequence-level curation and accession handling → a sequence-curation skill
- Literature-level grounding and citation evidence → a citation/grounding skill
- Figure production for a target venue → a scientific-figure skill

Declared in frontmatter as `related_skills`: `bio-sequence-curation`, `grounded-citations`.

---

## Distribution

Installation is a folder copy (see [Install](#install)). When several skill roots share a machine,
keep them identical by syncing from one copy rather than editing in place — drift between roots is
silent, and a gate that answers differently depending on which agent loaded it is worse than one
installed once.

The repository is the source of truth; a local root is a deployment of it.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md). The short version: the evidence chain, four gates and three tiers
came first; the **actor layer** (who ran it, on what model, over what window) was added once a probe
showed a fully compliant Tier 2 deliverable could pass with no record of its worker at all; and the
**activation surface** was fixed once probes showed the skill was never selected from its own
listing.

---

## Author and license

- **Author**: WU-WEIFENG
- **License**: MIT — see [LICENSE](LICENSE).
