#!/usr/bin/env python3
"""Regression tests for verify_deliverable.py.

Run:  python scripts/test_verify_deliverable.py

Each case builds a throwaway analysis directory in the system temp dir and asserts
the verifier's verdict. Cases marked (regression) encode a defect that was observed
in the field, not a hypothetical one -- a check that has never failed a known-bad
input has not been validated.

Standard library only, like the verifier itself.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "verify_deliverable.py"
ASSETS = HERE.parent / "assets"

CONTRACT = """\
analysis_id: TEST
question: does the gate hold?
analysis_type: test
unit_of_analysis: replicate
tier: {tier}
success_criteria: exit code as asserted
n_per_group: 3
comparison: a vs b
batch_confound: none
reference_genome: SL4.0
reference_annotation: ITAG4.1
reference_database: GO 2026-08
random_seed: 1
domain_skills_loaded: test
deviations: none
not_applicable_justification: none
notes: none
"""

RUN_CONTEXT = """\
agent: test-agent
model: test-model
model_version: 1.0
model_identity_note: none
session_id: test-session-1
not_applicable_justification: none
run_started_at: 2026-09-19T09:00
run_ended_at: 2026-09-19T10:00
notes: none
"""

CLAIM_HEADER = (
    "claim_id\tclaim\tlevel\tevidence_artifact\tmethod\tliterature\tconfidence\t"
    "verified_by\treviewer\treviewed_at\n"
)
CLAIM_ROW_HUMAN = (
    "C1\tGene X is up-regulated\tcomparative\tresults/deg.tsv\tdeseq2\tnone\tmoderate\t"
    "human\tW.W.\t2026-09-19\n"
)
CLAIM_ROW_ANON = (
    "C1\tGene X is up-regulated\tcomparative\tresults/deg.tsv\tdeseq2\tnone\tmoderate\t"
    "human\tnone\tnone\n"
)
# v1.0.1: tier 2 asks for an *identified* reviewer, not a personal name. A stable handle
# or role id is an identity, so this row is legal and must pass -- the positive fixture
# for the rule whose negative fixture is CLAIM_ROW_ANON.
CLAIM_ROW_HANDLE = (
    "C1\tGene X is up-regulated\tcomparative\tresults/deg.tsv\tdeseq2\tnone\tmoderate\t"
    "human\t@wuwei\t2026-09-19\n"
)
# Enrichment output: nominates a hypothesis, supports nothing stronger. The level did
# not exist in this standard until v0.3.2, while the WorkBuddy implementation required it.
CLAIM_ROW_HYP = (
    "C1\tEnrichment nominates a defence response\thypothesis_generating\tresults/deg.tsv\t"
    "clusterProfiler\tnone\tlow\tautomated\tnone\tnone\n"
)
CLAIM_ROW_CAUSAL = (
    "C1\tEnrichment proves the pathway is active\tcausal\tresults/deg.tsv\t"
    "clusterProfiler\tnone\tlow\tautomated\tnone\tnone\n"
)

STEPS = [
    ["S01", "read QC", "fastp", "0.23.4", "fastp -i raw/a.fq.gz -o qc/a.fq.gz",
     "-q 20 -l 50", "raw/a.fq.gz", "a" * 64, "results/deg.tsv", "SL4.0",
     "man page defaults", "yes", "2026-09-19T09:10", "2026-09-19T09:20", "agent", "-"],
]


def make_fixture(root: Path, *, tier: int = 2, steps=None, run_context=RUN_CONTEXT,
                 claims=CLAIM_HEADER + CLAIM_ROW_HUMAN, skip_run_context: bool = False,
                 ledger_text: str | None = None) -> Path:
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "results").mkdir(parents=True, exist_ok=True)
    (root / "raw" / "a.fq.gz").write_text("reads", encoding="utf-8")
    (root / "results" / "deg.tsv").write_text(
        "gene\tlog2FC\tp\tpadj\nSolyc01g\t2.1\t0.001\t0.01\n", encoding="utf-8")
    (root / "analysis-contract.txt").write_text(
        CONTRACT.format(tier=tier), encoding="utf-8")
    (root / "environment.yml").write_text("name: test\n", encoding="utf-8")
    if not skip_run_context:
        (root / "run-context.txt").write_text(run_context, encoding="utf-8")
    (root / "claim-ledger.tsv").write_text(claims, encoding="utf-8")
    if ledger_text is not None:
        (root / "provenance-ledger.tsv").write_text(ledger_text, encoding="utf-8")
    else:
        header = ("step_id\tstep\ttool\ttool_version\tscript_or_command\tparameters\t"
                  "input\tinput_sha256\toutput\treference_build\tsource_of_default\t"
                  "rerun_match\tstarted_at\tended_at\tauthored_by\tnotes\n")
        rows = "\n".join("\t".join(r) for r in (steps or STEPS))
        (root / "provenance-ledger.tsv").write_text(header + rows + "\n", encoding="utf-8")
    return root


def verify(root: Path, tier: int) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(root), "--expect-tier", str(tier)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout


FAILED = 0


def expect(name: str, root: Path, tier: int, want_exit: int, want_substring: str) -> None:
    global FAILED
    code, out = verify(root, tier)
    ok = code == want_exit and (want_substring in out if want_substring else True)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        FAILED += 1
        print(f"        exit={code} (wanted {want_exit}); "
              f"looking for {want_substring!r}")
        for line in out.splitlines():
            if "FAIL" in line or "RESULT" in line:
                print(f"        | {line}")


# --------------------------------------------------------------------------- cases

def case_valid_tier2(tmp: Path) -> None:
    """A complete tier-2 deliverable with the actor layer closed must pass."""
    root = tmp / "valid"
    make_fixture(root)
    expect("valid tier-2 deliverable passes", root, 2, 0, "gate passed")


def case_shipped_template(tmp: Path) -> None:
    """(regression) The shipped ledger template, copied verbatim and filled in,
    must pass. It shipped with a UTF-8 BOM, so its first column arrived as
    '\\ufeffstep_id' and the gate reported a phantom missing column."""
    root = tmp / "template"
    make_fixture(root)
    (root / "provenance-ledger.tsv").write_bytes(
        (ASSETS / "provenance-ledger.tsv").read_bytes()
        + ("\t".join(STEPS[0]) + "\n").encode("utf-8"))
    expect("shipped ledger template passes as-is", root, 2, 0, "gate passed")


def case_bom_ledger(tmp: Path) -> None:
    """(regression) Excel on Windows writes a BOM. The gate must not invent a
    missing column because of it."""
    root = tmp / "bom"
    make_fixture(root)
    path = root / "provenance-ledger.tsv"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    expect("BOM in the ledger header is tolerated", root, 2, 0, "gate passed")


def case_no_actor_layer(tmp: Path) -> None:
    """(regression) Before v0.3.0 a tier-2 deliverable with NO record of agent,
    model, session or time passed the gate. That was the gap; this asserts it closed."""
    root = tmp / "no-actor"
    make_fixture(root, skip_run_context=True)
    expect("missing run-context.txt fails tier 2", root, 2, 1, "run-context.txt not found")


def case_model_not_exposed(tmp: Path) -> None:
    """A harness that hides its model is annotated, not failed -- but the annotation
    itself is mandatory."""
    hidden = RUN_CONTEXT.replace("model: test-model", "model: not_exposed") \
                        .replace("model_version: 1.0", "model_version: not_exposed")
    root = tmp / "hidden-ok"
    make_fixture(root, run_context=hidden.replace(
        "model_identity_note: none", "model_identity_note: harness exposes no model id"))
    expect("model=not_exposed with a note passes", root, 2, 0, "gate passed")

    bare = tmp / "hidden-bare"
    make_fixture(bare, run_context=hidden)
    expect("model=not_exposed without a note fails", bare, 2, 1, "model_identity_note")


def case_window_break(tmp: Path) -> None:
    """(regression) A step timestamp outside the declared run window means the row
    was not written when it claims to have been. This is the cheapest available
    anti-fabrication check."""
    late = [list(STEPS[0])]
    late[0][12], late[0][13] = "2026-09-21T09:10", "2026-09-21T09:20"
    root = tmp / "late"
    make_fixture(root, steps=late)
    expect("step outside the run window fails", root, 2, 1, "outside the run window")

    backwards = [list(STEPS[0])]
    backwards[0][12], backwards[0][13] = "2026-09-19T09:40", "2026-09-19T09:10"
    root2 = tmp / "backwards"
    make_fixture(root2, steps=backwards)
    expect("ended_at before started_at fails", root2, 2, 1, "started_at is after ended_at")


def case_missing_step_time(tmp: Path) -> None:
    no_time = [list(STEPS[0])]
    no_time[0][12], no_time[0][13] = "not_recorded", "not_recorded"
    root = tmp / "no-time"
    make_fixture(root, steps=no_time)
    expect("empty step timestamps fail at tier 1", root, 1, 1, "unresolved")

    blank = [list(STEPS[0])]
    blank[0][12], blank[0][13] = "", ""
    root2 = tmp / "blank-time"
    make_fixture(root2, steps=blank)
    expect("blank step timestamps fail at tier 2", root2, 2, 1, "unresolved")

    no_author = [list(STEPS[0])]
    no_author[0][14] = "robot"
    root3 = tmp / "bad-author"
    make_fixture(root3, steps=no_author)
    expect("invalid authored_by fails", root3, 2, 1, "authored_by")


def case_anonymous_reviewer(tmp: Path) -> None:
    """(regression) Tier 2 asks for an IDENTIFIED human review; the ledger used to offer
    no place to put the identity, so 'human' was an unauditable assertion. Since v1.0.1 a
    personal name is not required -- a handle or a role id is an identity too."""
    root = tmp / "anon"
    make_fixture(root, claims=CLAIM_HEADER + CLAIM_ROW_ANON)
    expect("anonymous human review fails at tier 2", root, 2, 1,
           "without an identified `reviewer`")

    root2 = tmp / "anon-t1"
    make_fixture(root2, tier=1, claims=CLAIM_HEADER + CLAIM_ROW_ANON)
    expect("anonymous human review warns at tier 1", root2, 1, 0,
           "without an identified `reviewer`")

    # The positive half of the pair: a handle is not a personal name, and tier 2 must
    # accept it. Dropping the legal fixture is how a gate ends up rejecting its own
    # valid input -- which is what makes people switch the gate off.
    root3 = tmp / "handle"
    make_fixture(root3, claims=CLAIM_HEADER + CLAIM_ROW_HANDLE)
    expect("a handle instead of a personal name passes at tier 2", root3, 2, 0, "gate passed")


def case_tier0_skips(tmp: Path) -> None:
    """Exploratory work keeps the fast path: no actor layer required."""
    root = tmp / "t0"
    make_fixture(root, tier=0, skip_run_context=True,
                 steps=[["S01", "sketch", "python", "3.12", "python sketch.py", "-",
                         "raw/a.fq.gz", "a" * 64, "results/deg.tsv", "n/a", "none",
                         "not_attempted", "", "", "", "-"]])
    expect("tier 0 skips the actor layer", root, 0, 0, "gate passed")


def case_other_gates_still_work(tmp: Path) -> None:
    """The actor layer must not have softened the checks that were already there."""
    root = tmp / "no-padj"
    make_fixture(root)
    (root / "results" / "bad.tsv").write_text(
        "gene\tlog2FC\tp\nSolyc01g\t2.1\t0.001\n", encoding="utf-8")
    expect("uncorrected p-value is still caught", root, 2, 1, "no multiple-testing-corrected")

    root2 = tmp / "no-lock"
    make_fixture(root2)
    (root2 / "environment.yml").unlink()
    expect("tier 2 without a lock file is still caught", root2, 2, 1, "pinned environment")


def case_date_only_window(tmp: Path) -> None:
    """(regression) Declaring a run by date alone is legitimate. The window must then be
    compared as a day -- resolving it to midnight failed every real step."""
    by_date = (RUN_CONTEXT.replace("2026-09-19T09:00", "2026-09-19")
                          .replace("2026-09-19T10:00", "2026-09-19"))
    root = tmp / "date-window"
    make_fixture(root, run_context=by_date)
    expect("date-only run window accepts same-day steps", root, 2, 0, "gate passed")

    far = [list(STEPS[0])]
    far[0][12], far[0][13] = "2026-09-22T09:10", "2026-09-22T09:20"
    root2 = tmp / "date-window-far"
    make_fixture(root2, steps=far, run_context=by_date)
    expect("date-only run window still catches a later day",
           root2, 2, 1, "outside the run window")


def case_agent_values(tmp: Path) -> None:
    """UNKNOWN blocks, exactly as it does in the contract. `manual` is a value."""
    root = tmp / "unknown-agent"
    make_fixture(root, run_context=RUN_CONTEXT.replace("agent: test-agent", "agent: UNKNOWN"))
    expect("agent: UNKNOWN fails", root, 2, 1, "unresolved")

    root2 = tmp / "manual-agent"
    make_fixture(root2, run_context=RUN_CONTEXT.replace("agent: test-agent", "agent: manual"))
    expect("agent: manual is a value, not an absence", root2, 2, 0, "gate passed")

    root3 = tmp / "na-agent"
    make_fixture(root3, run_context=RUN_CONTEXT.replace("agent: test-agent", "agent: not_applicable"))
    expect("agent: not_applicable is rejected", root3, 2, 1, "always knowable")


def case_claim_levels(tmp: Path) -> None:
    """(regression) The level enum had no value for hypothesis-generating results, which
    is what enrichment output actually is: the WorkBuddy implementation *required* such a
    value while this standard *rejected* it, so one correctly-filled deliverable was valid
    on one stack and invalid on the other. Adding the level must not soften `causal`."""
    root = tmp / "hypothesis"
    make_fixture(root, claims=CLAIM_HEADER + CLAIM_ROW_HYP)
    expect("hypothesis_generating is a legal claim level", root, 2, 0, "gate passed")

    root2 = tmp / "causal-overreach"
    make_fixture(root2, claims=CLAIM_HEADER + CLAIM_ROW_CAUSAL)
    expect("a causal claim with no support still fails",
           root2, 2, 1, "needs literature support")


CASES = [
    case_valid_tier2,
    case_shipped_template,
    case_bom_ledger,
    case_no_actor_layer,
    case_model_not_exposed,
    case_window_break,
    case_date_only_window,
    case_agent_values,
    case_missing_step_time,
    case_anonymous_reviewer,
    case_tier0_skips,
    case_other_gates_still_work,
    case_claim_levels,
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    print(f"verify_deliverable regression tests ({len(CASES)} cases)\n")
    with tempfile.TemporaryDirectory(prefix="trust-fw-tests-") as tmpdir:
        tmp = Path(tmpdir)
        for case in CASES:
            case(tmp)
    print("\nAll cases behaved as asserted." if not FAILED else f"\n{FAILED} case(s) FAILED.")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
