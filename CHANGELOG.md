# Changelog

Versions are **skill versions** and move independently of any agent runtime. A rule change, a defect
fix or a new check is a minor or patch bump. **1.0.0 is the first public release** — published at the
point where the structure, the check enums and the authority relationship were frozen, and a
regression suite existed to keep them frozen.

The versions below 1.0.0 were private development iterations. They are kept because most of the
skill's design decisions are only explicable as a response to a defect, and deleting the record
would make them look arbitrary.

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
