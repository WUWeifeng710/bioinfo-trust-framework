# Changelog

Versions are **skill versions** and move independently of any agent runtime. A rule change, a defect
fix or a new check is a minor or patch bump. **1.0.0 is the first public release** — published at the
point where the structure, the check enums and the authority relationship were frozen, and a
regression suite existed to keep them frozen.

The versions below 1.0.0 were private development iterations. They are kept because most of the
skill's design decisions are only explicable as a response to a defect, and deleting the record
would make them look arbitrary.

---

## 1.1.0 — 2026-09-19

**Three new mechanical layers, adopted from THREAD-Bio's failure taxonomy, and the reviewer
becomes a measurable component.** All three are *opt-in per deliverable* via
`framework_version: 1.1.0` in the contract: an older contract keeps the pre-1.1.0 bar with the
new checks downgraded to advisory — otherwise 1.1.0 would retroactively fail every honest
deliverable that predates it.

- **The error account (`assets/error-ledger.tsv`).** Every error carries a class:
  `inherited` (would have happened anyway), `amplified` (the agent accelerates, scales, or
  quietly propagates an inherited error), or `emergent` (agent-specific, with a `kind`:
  goal drift, context loss, stale memory, retrieval poisoning, incomplete tool description).
  "We looked and found nothing" must be declared explicitly via `# none-detected-by: <method>`
  — a blank ledger is indistinguishable from nobody having looked, and only one of the two is
  a checkable statement. A provenance row marked `deviated` without an error entry fails:
  a deviation is a decision, and a decision nobody wrote down is a defect. Every error
  cross-references its detection method, containment, and the claims it reached.
- **The review record (`assets/review-record.tsv`).** Tier 2 always spent human time; nothing
  recorded what it bought. One row per review: scope, identified reviewer, duration,
  disagreements (+detail when nonzero), overrides, errors found, verdicts changed, and a
  calibration note. The checker **reports the totals and judges nothing** — a numeric quota
  would turn measurement into paperwork, and a tier-2 review that never catches anything is a
  signal about the review process, not the analysis. Multiple agents or models agreeing are
  **not votes**: shared training distributions make agreement cheap, so the standard says so
  explicitly instead of leaving it to be discovered.
- **Substantive gate labels.** The four timeline gates answer *when* a check happens; the
  five labels — `execution`, `design`, `inference`, `biological`, `external` — answer *what
  kind of judgement failed*. The two axes are orthogonal and replacing one with the other is
  a category error. Every checker finding now reads `FAIL [inference] C42: …`, the run ends
  with a per-gate summary, and `assets/gate-map.tsv` is verified against the checker's
  registry at startup — a desynchronised map stops the checker (exit 2), because an
  unlabelled finding cannot be interpreted. The `biological` gate has no mechanical check by
  design; that judgement is what the review record is for.
- **Two defects the regression suite caught in the checker itself** (a rule tested against its
  own documentation is the only way to find these):
  `deviation: unknown` was documented to block delivery but the checker let it pass;
  and `reviewer: human` — the verified_by value echoed into the identity field — was not
  treated as the placeholder it is.
- **Regression suite: 19 cases / 24 → 54 assertions**, each new rule tested against both a
  legal and an illegal fixture.

---

## 1.0.1 — 2026-09-19

**"Named" was the wrong word for what tier 2 actually needs.** The requirement had read *named human
review* since 0.3.0, while the WorkBuddy implementation (`bio-analysis-guard`) never asked for a name
— which, under the authority rules, made the implementation the defect to be fixed. The owner decided
the *requirement* was the problem: a personal name is not what makes a review auditable, and demanding
one buys friction without buying evidence.

- **Tier 2 now requires an *identified* reviewer, not a named one.** `reviewer` may hold a personal
  name, initials, or a stable handle / role id (`@wuwei`, `lab-lead`, `pi`). The wording moves from
  "named" to "identity" throughout `SKILL.md`, `README.md` and the ledger template.
- **The field is still required, and that is the point.** An empty or placeholder value (`human`,
  `unknown`, `n/a`) remains indistinguishable from nobody having looked, so it still FAILs at tier 2
  and WARNs at tier 1. Loosening *who* counts is not the same as allowing an anonymous assertion —
  that was the defect 0.3.0 existed to close.
- **The regression suite gains the positive fixture the rule was missing:** a claim reviewed by a
  handle must **pass** at tier 2. 13 cases / 23 → **24** assertions. A rule tested only against its
  negative fixture is how a gate ends up rejecting its own legal input.
- **Figure standards are now explicitly out of scope here** (`references/visualization.md`). This
  reference answers exactly one question — does the figure support the claim made from it. How a
  figure is *rendered* (backend, plotting code, palette, export, journal templates) belongs to the
  figure toolchain. The two do not arbitrate each other; the reciprocal note lives in
  `sci-figure-toolkit/references/routing.md`.

---

## 1.0.0 — 2026-09-19

**First public release.** No behaviour change from 0.3.2; this is a packaging and provenance release.

- Published at `https://github.com/WUWeifeng710/bioinfo-trust-framework` (MIT), with the one-prompt
  install path, `LICENSE`, and this changelog.
- **Author identity unified** as `WU-WEIFENG` across `SKILL.md`, `README.md` and `LICENSE`.
- The **Authority** section now names the published repository, so a copy installed on any machine
  can be traced back to the upstream standard it claims to be.
- Ships the full state of 0.3.2: actor layer, five claim levels, `utf-8-sig` readers, BOM-free
  templates, date-granularity window comparison, and a 13-case / 23-assertion regression suite.

What 1.0.0 means here, precisely: the **rules** are considered stable enough to build on. It does not
mean the checker is complete — see `README.md` *Validation status* for the five defects found so far
by exercising it, and *The verifier* for the list of things it explicitly cannot check.

---

## 0.3.2 — 2026-09-19

**Authoritative source declared, and the drift that declaring it exposed.**

A machine can end up carrying both this skill and a project-local enforcer such as
`bio-analysis-guard`. The README had until now left the resolution open ("either name an
authoritative source or keep exactly one"). The authority is now named — **this skill** — and a new
`## Authority` section states what makes it enforceable rather than decorative: an implementation may
strengthen but never weaken, and a standard-level gap is closed *here* so every implementation
inherits the fix.

Diffing the two stacks under that rule immediately turned up a hard conflict. The implementation
required the claim level `hypothesis_generating` (its rule H10 forbids labelling enrichment output
`causal`) and this file had no such level — so a deliverable filled in correctly on one side was
invalid on the other, and *mandatory* on the first. `hypothesis_generating` is now a claim level
here, and the implementation's `associative` is aligned to `comparative`.

Separately: the BOM fix recorded in 0.3.0 reached only the *readers*. Both shipped TSV templates
still began `ef bb bf`, while `claim-ledger.tsv`'s own comment asserted the file had no BOM. Bytes
stripped, comment now true.

---

## 0.3.1 — 2026-09-19

**Activation surface fixed.**

The listing an agent chooses from shows only the first 28 characters of the description, and 0.3.0's
description put the domain word `bioinformatics` at character 30 — so the skill was listed as
`Reliability, provenance, rep`, with no domain signal at all, and was selected in **0 of 33**
unnamed-request trials.

The description now leads with an unconditional load directive inside the window:
`生信分析可信度总闸。任何生信分析开工前必须加载。Trustworthy bioinformatics.` Re-measured on the
same probes: **9/9 across three independent repeats** for the directive clause.

Measured context, recorded because it changes the design rule: the `≤ 60` description budget comes
from Hermes' *repo* CI (`test_authoring_standards.py`), whose `_skill_paths()` globs only `skills/**`
and `optional-skills/**` — an installed skill is not covered by it. Across 645 installed skills the
median description length is 273 in the WorkBuddy root (88% exceed 60), 214 in Codex, 188 in Claude,
and 57 in Hermes. The noun-phrase description 0.3.0 carried was a response to a rule that did not
apply.

---

## 0.3.0 — 2026-09-19

**Actor layer added.**

The evidence chain documented the *work*; nothing documented the *worker*. New
`assets/run-context.template` → `run-context.txt` (agent, model + version, session id, run window);
`provenance-ledger.tsv` gains `started_at` / `ended_at` / `authored_by`; `claim-ledger.tsv` gains
`reviewer` / `reviewed_at`, which finally gives the tier-2 "named human review" requirement somewhere
to land.

A model identity the harness does not surface is recorded as `not_exposed` **with a mandatory
reason**, not failed. Every step timestamp must fall inside the run window — the cheapest
anti-fabrication check available.

The verifier gains a `run-context` section, per-step time/author checks, window checks and reviewer
checks, plus a shipped regression suite (12 cases / 21 assertions) and tolerance for both a BOM and
date-only windows. Tier 0 skips the whole layer.

---

## 0.2.1 — 2026-09-19

**Scope corrected.**

0.2.0 had promoted "omics" — an *example* in 0.1.0's body text — into the title, description and
tags, silently narrowing the skill to omics work and contradicting its own `When to Use` list
(phylogenetics, docking, molecular dynamics are not omics). Restored to bioinformatics as a whole,
with the scope stated explicitly in the opening paragraph. Also replaced "modality" (an omics-typed
word) with "technique" / "domain".

---

## 0.2.0 — 2026-09-19

Rewritten as a portable, agent-agnostic English skill. Added the evidence-chain model, the four-gate
operating procedure, the three-tier risk model, the deviation protocol, three fillable assets, three
references, and a tested stdlib verifier. Added explicit human-vs-mechanical labelling of every
checklist item.

---

## 0.1.0 — 2026-09-19

Initial Chinese version: four pillars as principles plus a prose checklist. No executable artefacts,
no procedure, no tier criteria.
