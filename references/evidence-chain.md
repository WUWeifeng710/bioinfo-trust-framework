# The evidence chain

Read this when a claim needs to be defended, or when an audit turned up something you cannot trace.

## The idea in one paragraph

A result is not a number. It is a **path**: data came in, code transformed it, a file came out, a
figure was drawn from that file, and a sentence was written about the figure. Every link in that
path is a place where something can be wrong without anything erroring out. The chain below makes
each link explicit, so that a reviewer can walk it and you can find the break yourself before
someone else does.

## The eight links

| # | Link | The reviewer's question | Recorded in |
|---|---|---|---|
| 1 | Claim | What exactly are you asserting, and at what level? | claim-ledger: `claim`, `level` |
| 2 | Figure / table | Which artifact carries it? | claim-ledger: `evidence_artifact` |
| 3 | Result file | Which on-disk output was it drawn from? | provenance-ledger: `output` |
| 4 | Script + command | What was actually executed? | provenance-ledger: `script_or_command` |
| 5 | Parameters | Which settings, and why those? | provenance-ledger: `parameters`, `source_of_default` |
| 6 | Tool + version | Which implementation, which release? | provenance-ledger: `tool`, `tool_version` |
| 7 | Input data | Which bytes went in? | provenance-ledger: `input`, `input_sha256` |
| 8 | Reference build | Which genome / annotation / database? | provenance-ledger: `reference_build` |

Plus one link that only matters for interpretation:

| 9 | Literature / database support | What external knowledge does this rest on? | claim-ledger: `literature` |

A chain is only as strong as its weakest link — which is why the rule is blunt: **one missing link
means the claim is not deliverable.** Downgrade it to `NOT VERIFIED`, or drop it.

## The layer the chain does not contain

The eight links describe the **work**: data in, code, files out. They say nothing about the
**worker**. Keep the two apart, because they fail differently — a broken chain makes a result
irreproducible, an unrecorded actor makes it unattributable, and only the first kind announces
itself when someone tries to reproduce it.

| Fact | Where it lives | Why it is not decoration |
|---|---|---|
| `agent` | run-context | Different agents fail in different ways; "which one produced this" is the first question in any dispute |
| `model` / `model_version` | run-context | A model update silently changes the code and the parameter choices an agent writes. Same command, different reasoning — the ledger alone cannot tell them apart |
| `session_id` | run-context | Lets a reviewer reach the transcript the numbers came from |
| run window | run-context | The boundary that makes the step timestamps checkable at all |
| `started_at` / `ended_at` | provenance-ledger, per step | Ordering, plus the anti-fabrication check below |
| `authored_by` | provenance-ledger, per step | Which steps a human actually touched, and which the agent produced unsupervised |
| `reviewer` / `reviewed_at` | claim-ledger, per claim | Turns "a human checked it" from an assertion into evidence |

The window is the point. A ledger written in one sitting at the end of the week, from memory, looks
exactly like an honest one — unless the steps carry timestamps that must fall inside the run window.
That is the entire mechanism: **it does not make retrospective ledger-writing impossible, it makes
it detectable.** A ledger claiming `reference_database: GO 2026-08` in a run that ended in June is
the same failure, caught the same way.

If the harness does not surface a model identity, that is not a reason to leave the field blank.
`not_exposed` plus a reason records what you know. Blank records nothing, and looks identical to an
oversight.

## Why "not deliverable" and not "flag it"

Because a flagged claim and a confident claim look identical three months later, when nobody
remembers which was which. The only durable protection is that the claim is not in the deliverable
until the chain is closed. If it must stay, its label must travel with it — `NOT VERIFIED` in the
sentence itself, not in a footnote the reader will skip.

## The 10-minute audit

Run this before delivering, on a sample rather than everything.

1. **Pick three claims** — the headline claim, the one you trust least, and one at random.
2. **Walk backwards.** From the sentence: to the figure → to the data file → to the script → to the
   command → to the parameters → to the tool version → to the input checksum → to the reference
   build. Write down the first link you cannot name from memory.
3. **Open the file at the break.** Verify the value in the figure actually appears in the result
   file. Not "looks similar" — the same number.
4. **Cross-check the reference build** across all steps of the chain. A build that changes halfway
   through is the classic silent failure.
5. **Re-run the head of the chain** if it is cheap (a QC step, a filter step). Match the output.
6. **Write the result down**: `verified` / `broken at link N` / `not checkable`.

Three claims is not a proof, but it is a detector. Chains break in clusters — if one is broken,
look at its neighbours.

## Worked broken chains

Drawn from sequencing, omics, structural and sequence-analysis work — the shapes repeat across
subfields. Each of these produces no error message. That is the point.

### 1. The silent reference-build swap

**Symptom.** Variant coordinates are nonsense relative to a known landmark; the pipeline is green.

**Broken link.** 8 — one step used GRCh38, another GRCh37, nothing in the record says which.

**Detection.** Grep every step's `reference_build`. If it is blank or differs between steps, stop.

**Repair.** Re-run everything against one declared build. Re-derive coordinates. You cannot patch
this by converting some downstream file and hoping.

### 2. The orphaned aggregate

**Symptom.** A "mean expression" column in a table. Nobody can say what was averaged, over what, or
with which filter.

**Broken link.** 3–5 — the aggregation step was done interactively and never recorded as a step.

**Detection.** Ask for the row count and the denominator. If the answer needs a new script to
produce, the link is broken.

**Repair.** Write the aggregation as a named step with declared input and output, re-run it, and
replace the column. Then it is reproducible.

### 3. The overwritten intermediate

**Symptom.** A figure cannot be regenerated because the file it read no longer exists — someone
tidied `interim/` after the analysis.

**Broken link.** 3 — the result file is gone.

**Repair.** Restore from backup if possible; otherwise the claim is not reproducible and must be
labelled so. Prevention: never overwrite or delete upstream; derive new names.

### 4. The uncorrected scan

**Symptom.** 4,000 "significant" genes at p < 0.05 in a genome-wide test.

**Broken link.** 5 — the multiple-testing correction was not applied, and nothing recorded says
otherwise.

**Detection.** Header scan: a `p` column with no `padj`/`q`/`FDR` column.

**Repair.** Apply the correction, re-derive, report the corrected values. The uncorrected numbers can
stay as a supplementary column, never as the basis of a claim.

### 5. The cited-but-unread paper

**Symptom.** A sentence in the discussion says "as shown in [12]" and [12] does not support it.

**Broken link.** 9 — the citation was attached from memory or from a search snippet.

**Repair.** Open the source. If it supports the claim, quote the exact sentence. If it does not,
remove the citation or change the claim to `[unverified]`.

### 6. Two denominators, one comparison

**Symptom.** "Taxon A increased 3×" — but the two groups were normalized against different totals.

**Broken link.** 5 — normalization method unrecorded, so nobody notices the inconsistency.

**Detection.** Confirm that the comparison's numerator and denominator come from the same
normalization step. State the normalization explicitly, every time.

**Repair.** Re-normalize both groups under one declared method; re-derive the ratio.

### 7. The converged simulation that never equilibrated

**Symptom.** A simulation "finished" and produced trajectories that look plausible.

**Broken link.** 1/5 — a convergence check exists in the method but was never run as a recorded step,
so "it completed" was read as "it converged".

**Repair.** Run the equilibration/convergence diagnostics as a named step with a stated threshold,
record it, and only then interpret the production phase.

### 8. The gene family with an unrecorded threshold

**Symptom.** "This family has 47 members in tomato" — and nobody can reproduce the count.

**Broken link.** 5 — the BLAST/HMMER cutoffs (E-value, coverage, identity), the database version, and
any manual curation were applied but not recorded, so the boundary between member and non-member is
invisible to anyone else.

**Detection.** Ask for the single command that produced the final member list. If the last step
happened in a spreadsheet, that step is unrecorded by definition.

**Repair.** Re-derive with the thresholds stated in the deliverable, keep the raw hit table, and
record any curation as a named step with an explicit rule. The count is now defensible; without this,
it is an opinion.

### 9. The analysis with no author

**Symptom.** A deliverable whose chain is complete — every step has a tool, a version, a command, a
checksum, a reference build — and yet nobody can say which agent or model produced it, in which
session, or over what period. Nothing is wrong with any individual step.

**Broken layer.** The actor layer, entirely. The work is documented; the worker is not.

**Why it matters.** A model update changes the code and the parameters an agent writes, so two runs
can share every command and still rest on different reasoning. When a result is questioned months
later, "which model, and can we see the session" is the first question asked and the only one the
chain cannot answer. It also makes the record un-auditable in the direction that matters: you cannot
weigh an answer by its source if the source is anonymous.

**Detection.** Can you name the agent, the model, and the run window from the record alone? If any
answer is "we can probably infer it", the layer is missing.

**Repair.** Fill `run-context.txt`. It is a five-minute cost at Gate 1, and it cannot be
reconstructed later — which is the entire reason it belongs at Gate 1 and not at Gate 3.

### 10. The ledger written on Friday

**Symptom.** Three weeks of steps, all with correct-looking provenance, all appended in one session
at the end of the project. The numbers are right, because they were copied from the outputs.

**Broken layer.** The step timestamps, and with them the only check that distinguishes a live record
from a reconstructed one.

**Detection.** Do the step windows fall inside the declared run window, and do they spread across the
work, or do they all land within the same few minutes? A run window of a single day containing forty
steps that each "took four seconds" is a record written after the fact.

**Why this one is worth the friction.** It is cheap, mechanical, and it catches a class of defect
that is otherwise completely invisible: **a plausible record that was never true when it claims to
have been.** The same check catches a step dated before a reference database existed, which is how a
fabricated citation of a database version gets caught without reading a single paper.

**Repair.** There is no retrofit. Write the row after the step, which is what Gate 2 already asks
for — this example exists to explain why that instruction is not bureaucratic.

## Recording: how the chain gets built

Three files in the analysis directory, filled as you go:

- `run-context.txt` — the actor layer: agent, model, session, run window. Filled at Gate 1, closed at
  Gate 3. Template: `assets/run-context.template`.
- `provenance-ledger.tsv` — one row per executed step, including **when it ran and who or what ran
  it**. Columns are listed in `assets/provenance-ledger.tsv`. Append after each step, not at the end.
- `claim-ledger.tsv` — one row per claim in the deliverable, with its level, evidence artifact, and,
  where a person reviewed it, their name and the date.

Template rows are prefixed with `#` so they cannot be mistaken for data. Delete them when you start.

Writing any of these afterwards, from memory, is the same failure mode as fabricating a citation: the
numbers will be right, the details will be reconstructed, and you will not know which is which. The
run window exists so that this is at least detectable rather than merely discouraged.

## What to do when a chain is broken and cannot be fixed

Three honest options, in order of preference:

1. **Re-derive.** Cheapest when the break is at link 3–5 and the environment is intact.
2. **Downgrade the claim to a hypothesis.** Moves it out of the results and into "future work" or
   "suggested by these data", where it belongs.
3. **Declare the gap.** Keep the claim but label it explicitly with what is missing, in the sentence:
   "this was not reproducible because the aggregation step was not recorded".

What is not an option: leaving the reader to assume the chain holds because the figure looks good.
