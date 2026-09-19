#!/usr/bin/env python3
"""Mechanical gate check for a bioinformatics analysis deliverable.

Part of the `bioinfo-trust-framework` skill. Checks only what can be checked
mechanically; judgement items stay with a human.

    python verify_deliverable.py <analysis_dir> [--expect-tier 0|1|2] [--json]

Exit code 0 = no FAIL findings (WARN is allowed). Exit code 1 = at least one FAIL.

Files expected in <analysis_dir>:
    analysis-contract.txt    the Gate 1 contract
    run-context.txt          who/what ran it -- agent, model, session, window (Gate 1)
    provenance-ledger.tsv    per-step provenance (Gate 2)
    claim-ledger.tsv         per-claim evidence (Gate 3)

run-context.txt is required for tier >= 1; tier 0 (exploratory) skips it.
Steps need timestamps and an author for tier >= 1; tier 0 skips those too.

Optional:
    .trust-ignore            newline-separated glob patterns to skip in the result-table scan

Standard library only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CONTRACT_NAME = "analysis-contract.txt"
PROVENANCE_NAME = "provenance-ledger.tsv"
CLAIMS_NAME = "claim-ledger.tsv"
RUN_CONTEXT_NAME = "run-context.txt"
IGNORE_NAME = ".trust-ignore"

CONTRACT_REQUIRED = [
    "analysis_id", "question", "analysis_type", "unit_of_analysis", "tier",
    "success_criteria", "n_per_group", "comparison", "batch_confound",
    "reference_genome", "reference_annotation", "reference_database",
    "random_seed", "domain_skills_loaded",
]
NEVER_NA = {
    "analysis_id", "question", "analysis_type", "unit_of_analysis", "tier",
    "success_criteria",
}
REFERENCE_KEYS = ["reference_genome", "reference_annotation", "reference_database"]
NA_SENTINELS = {"not_applicable", "n/a", "na"}
UNKNOWN_SENTINELS = {"unknown", "todo", "tbd", "not_recorded", "not recorded", "?", ""}
PLACEHOLDER = re.compile(r"^(a1b2c3.*|x{3,}|<[^>]*>|\.{3,}|example.*|placeholder.*)$", re.I)


def is_unset(value: str) -> bool:
    """True when a field carries no actual record: blank, a placeholder, or an
    'unknown'-family sentinel. `not_recorded` counts -- it is an admission that the
    fact was not captured, which is what the field exists to prevent."""
    text = (value or "").strip()
    return (not text) or text.lower() in UNKNOWN_SENTINELS or bool(PLACEHOLDER.match(text))
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)

PROVENANCE_COLUMNS = [
    "step_id", "step", "tool", "tool_version", "script_or_command", "parameters",
    "input", "input_sha256", "output", "reference_build", "source_of_default",
    "rerun_match", "started_at", "ended_at", "authored_by", "notes",
]
CLAIM_COLUMNS = [
    "claim_id", "claim", "level", "evidence_artifact", "method",
    "literature", "confidence", "verified_by", "reviewer", "reviewed_at",
]
CLAIM_LEVELS = {"descriptive", "comparative", "hypothesis_generating", "causal", "clinical"}
CONFIDENCE_LEVELS = {"high", "moderate", "low"}
VERIFIED_BY = {"automated", "human", "none"}
RERUN_VALUES = {"yes", "no", "not_attempted"}

# --- the actor layer: who/what executed the analysis (run-context.txt) ---
RUN_CONTEXT_REQUIRED = [
    "agent", "model", "model_version", "session_id", "run_started_at", "run_ended_at",
]
# Conceptually always knowable -> `not_applicable` is a FAIL, not a legal value.
# No agent involved is written `manual`, which is a value, not an absence.
RUN_CONTEXT_NEVER_NA = {"agent", "run_started_at", "run_ended_at"}
# A harness that does not surface its model is a real condition (the user's call:
# annotate rather than fail) -- but the annotation itself is mandatory.
NOT_EXPOSED = {"not_exposed", "not-exposed", "not exposed"}
AUTHORED_BY = {"agent", "human", "agent+human"}

ISO_TS = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?")

LOCK_PATTERNS = [
    "*.lock", "environment.y*ml", "requirements*.txt", "pyproject.toml", "Pipfile*",
    "conda*.y*ml", "renv.lock", "Dockerfile", "*.dockerfile", "*.def", "singularity*",
    "Snakefile", "*.smk", "*.nf", "nextflow.config", "Makefile", "makefile",
]
P_COLUMNS = re.compile(r"^(p|pval|p_val|p_value|pvalue)$", re.I)
PADJ_COLUMNS = re.compile(
    r"^(padj|p_adj|p\.adj|p_adjusted|adjusted_p|adj_p|q|qval|q_value|qvalue|fdr|fdr_p|bh)$",
    re.I,
)
TABLE_SUFFIXES = {".tsv", ".csv", ".txt"}

findings: list[tuple[str, str, str]] = []  # (level, section, message)


def add(level: str, section: str, message: str) -> None:
    findings.append((level, section, message))


def read_kv(path: Path, section: str) -> dict:
    """Parse `key: value` files (the contract, the run context).

    Decoded as utf-8-sig: a UTF-8 BOM is stripped rather than becoming part of the
    first key. Excel on Windows writes a BOM by default, so this is the common
    real-world path, not a corner case.
    """
    if not path.is_file():
        add("FAIL", section, f"{path.name} not found in {path.parent}")
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        values[key.strip().lower()] = value.strip()
    return values


def read_tsv(path: Path, columns: list[str], section: str) -> list[dict]:
    if not path.is_file():
        add("FAIL", section, f"{path.name} not found in {path.parent}")
        return []
    rows: list[dict] = []
    # utf-8-sig, not utf-8: a BOM in the header would rename the first column to
    # '<BOM>step_id' and every column check would report a phantom missing column.
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        data_lines = [ln for ln in handle if ln.strip() and not ln.lstrip().startswith("#")]
    if not data_lines:
        add("FAIL", section, f"{path.name} has no data rows (example lines only?)")
        return []
    reader = csv.DictReader(data_lines, delimiter="\t")
    header = [(c or "").strip() for c in (reader.fieldnames or [])]
    missing = [c for c in columns if c not in header]
    if missing:
        add("FAIL", section, f"{path.name} is missing columns: {', '.join(missing)}")
    for i, row in enumerate(reader, start=1):
        clean = {(k or "").strip(): (v or "").strip() for k, v in row.items() if k}
        clean["_line"] = str(i + 1)
        rows.append(clean)
    return rows


def check_contract(values: dict, expect_tier) -> int | None:
    if not values:
        return None
    for key in CONTRACT_REQUIRED:
        if key not in values:
            add("FAIL", "contract", f"missing required key: {key}")
    not_applicable: list[str] = []
    unknown: list[str] = []
    for key in CONTRACT_REQUIRED:
        value = values.get(key, "")
        low = value.lower()
        if low in NA_SENTINELS:
            if key in NEVER_NA:
                add("FAIL", "contract",
                    f"{key} is 'not_applicable' but conceptually always exists")
            else:
                not_applicable.append(key)
        elif low in UNKNOWN_SENTINELS or PLACEHOLDER.match(value):
            unknown.append(key)
    if unknown:
        add("FAIL", "contract",
            f"unresolved (UNKNOWN/blank): {', '.join(unknown)} -- UNKNOWN blocks execution")

    if not_applicable:
        justification = values.get("not_applicable_justification", "").strip()
        # `none` means "no field is not_applicable" -- it is NOT a justification.
        if justification.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none"}:
            add("FAIL", "contract",
                "fields marked not_applicable "
                f"({', '.join(not_applicable)}) but no justification given -- "
                "`not_applicable_justification: none` does not justify anything")
        else:
            add("SKIP", "contract",
                f"not_applicable accepted for {', '.join(not_applicable)} "
                f"(justification: {justification})")

    tier_raw = values.get("tier", "")
    tier = None
    match = re.search(r"([012])", tier_raw)
    if not match:
        add("FAIL", "contract", f"tier must be 0, 1 or 2 -- got {tier_raw!r}")
    else:
        tier = int(match.group(1))
        if expect_tier is not None and tier != expect_tier:
            add("WARN", "contract",
                f"tier is {tier} but {expect_tier} was expected on the command line")
    if tier == 0:
        add("SKIP", "contract", "tier 0 (exploratory): full audit not required, "
                                 "label the deliverable as exploratory")

    if tier in (1, 2) and all(
        values.get(k, "").lower() in NA_SENTINELS for k in REFERENCE_KEYS
    ):
        add("WARN", "contract",
            "all three reference_* fields are not_applicable -- confirm this analysis truly "
            "has no genome/annotation/database reference")

    seed = values.get("random_seed", "").lower()
    if not seed or seed in UNKNOWN_SENTINELS:
        add("WARN", "contract", "random_seed unset -- stochastic steps are not reproducible")
    elif seed in NA_SENTINELS and values.get("not_applicable_justification", "none").lower() != "none":
        add("SKIP", "contract", "random_seed not_applicable (justified)")

    return tier


def parse_ts(value: str):
    """Parse a leading ISO-8601 date/datetime. Returns None if unrecognised."""
    match = ISO_TS.match((value or "").strip())
    if not match:
        return None
    year, month, day = (int(match.group(i)) for i in (1, 2, 3))
    hour, minute, second = (int(match.group(i) or 0) for i in (4, 5, 6))
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None


def is_date_only(value: str) -> bool:
    """True for `YYYY-MM-DD` with no time part -- a coarser but legitimate record."""
    match = ISO_TS.match((value or "").strip())
    return bool(match) and match.group(4) is None


def check_run_context(values: dict, tier):
    """The actor layer: which agent, which model, in which session, over what window.

    Returns the run window as (start, end, day_granularity), or None, so that per-step
    timestamps can be checked against it.
    """
    if tier is None:
        return None
    if tier == 0:
        add("SKIP", "run-context",
            "tier 0 (exploratory): execution context not required")
        return None

    for key in RUN_CONTEXT_REQUIRED:
        if key not in values:
            add("FAIL", "run-context", f"missing required key: {key}")

    unavailable: list[str] = []       # model identity the harness does not surface
    not_applicable: list[str] = []    # fields that genuinely do not exist here
    unresolved: list[str] = []
    for key in RUN_CONTEXT_REQUIRED:
        raw = values.get(key, "")
        low = raw.lower()
        if key in {"model", "model_version"} and (low in NOT_EXPOSED or low in NA_SENTINELS):
            unavailable.append(key)
            continue
        if low in NA_SENTINELS:
            if key in RUN_CONTEXT_NEVER_NA:
                add("FAIL", "run-context",
                    f"{key} is 'not_applicable' but is always knowable "
                    "(write `manual` when no agent was involved)")
            else:
                not_applicable.append(key)
            continue
        if low in UNKNOWN_SENTINELS or PLACEHOLDER.match(raw):
            unresolved.append(key)

    if unresolved:
        add("FAIL", "run-context",
            f"unresolved (UNKNOWN/blank): {', '.join(unresolved)} -- the execution "
            "context blocks execution, exactly like the contract")

    if unavailable:
        note = values.get("model_identity_note", "").strip()
        if note.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none"}:
            add("FAIL", "run-context",
                f"{', '.join(unavailable)} recorded as unavailable but "
                "model_identity_note is empty -- annotate why it cannot be obtained")
        else:
            add("SKIP", "run-context",
                f"{', '.join(unavailable)} accepted as unavailable (note: {note})")

    if not_applicable:
        justification = values.get("not_applicable_justification", "").strip()
        if justification.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none", ""}:
            add("FAIL", "run-context",
                f"{', '.join(not_applicable)} marked not_applicable but no "
                "not_applicable_justification is given")
        else:
            add("SKIP", "run-context",
                f"not_applicable accepted for {', '.join(not_applicable)} "
                f"(justification: {justification})")

    raw_start = values.get("run_started_at", "").strip()
    raw_end = values.get("run_ended_at", "").strip()
    start, end = parse_ts(raw_start), parse_ts(raw_end)
    for name, raw, parsed in (("run_started_at", raw_start, start),
                              ("run_ended_at", raw_end, end)):
        if raw and raw.lower() not in UNKNOWN_SENTINELS and parsed is None:
            add("WARN", "run-context",
                f"{name}={raw!r} is not ISO-8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM)")
    if start and end:
        if start > end:
            add("FAIL", "run-context", "run_started_at is after run_ended_at")
        else:
            # `run_started_at: 2026-09-19` resolves to midnight. A window whose bounds
            # are date-only must be compared as a day, or every real step would fall
            # outside a zero-length window -- a gate that always cries wolf gets turned off.
            coarse = is_date_only(raw_start) or is_date_only(raw_end)
            return (start, end, coarse)
    return None


def find_lock_files(root: Path) -> list[str]:
    found = []
    for pattern in LOCK_PATTERNS:
        for hit in root.glob(pattern):
            if hit.is_file():
                found.append(hit.name)
    for hit in root.glob("*/" + "environment.y*ml"):
        found.append(str(hit.relative_to(root)))
    return sorted(set(found))


def check_provenance(rows: list[dict], root: Path, tier, window=None) -> None:
    if not rows:
        return
    for row in rows:
        line = row.get("_line", "?")
        for column in ("tool", "tool_version", "parameters", "input", "output",
                       "reference_build", "source_of_default"):
            if not row.get(column, "").strip():
                add("FAIL", "provenance", f"row {line}: empty `{column}`")
        digest = row.get("input_sha256", "")
        if not digest:
            add("FAIL", "provenance", f"row {line}: empty `input_sha256`")
        elif not SHA256.match(digest) and digest.lower() not in NA_SENTINELS:
            add("WARN", "provenance",
                f"row {line}: input_sha256 is not a 64-char hex digest ({digest[:20]!r})")
        rerun = row.get("rerun_match", "").strip().lower()
        if rerun and rerun not in RERUN_VALUES:
            add("WARN", "provenance",
                f"row {line}: rerun_match={rerun!r} not in {sorted(RERUN_VALUES)}")
        output = row.get("output", "").strip()
        if output and output.lower() not in NA_SENTINELS and not SHA256.match(output):
            if not (root / output).exists():
                add("WARN", "provenance",
                    f"row {line}: declared output not on disk: {output}")

        # --- the actor layer, per step: when, and who/what produced it ---
        if tier in (1, 2):
            for column in ("started_at", "ended_at"):
                if is_unset(row.get(column, "")):
                    add("FAIL", "provenance",
                        f"row {line}: `{column}` is unresolved "
                        "(blank, placeholder, or an unknown-family sentinel)")
            authored = row.get("authored_by", "").strip().lower()
            if is_unset(authored):
                add("FAIL", "provenance",
                    f"row {line}: `authored_by` is unresolved -- expected one of "
                    f"{sorted(AUTHORED_BY)}")
            elif authored not in AUTHORED_BY:
                add("FAIL", "provenance",
                    f"row {line}: authored_by={authored!r} not in {sorted(AUTHORED_BY)}")

            raw_start = row.get("started_at", "")
            raw_end = row.get("ended_at", "")
            step_start, step_end = parse_ts(raw_start), parse_ts(raw_end)
            for name, raw, parsed in (("started_at", raw_start, step_start),
                                      ("ended_at", raw_end, step_end)):
                if raw.strip() and parsed is None:
                    add("WARN", "provenance",
                        f"row {line}: {name}={raw!r} is not ISO-8601")
            if step_start and step_end and step_start > step_end:
                add("FAIL", "provenance", f"row {line}: started_at is after ended_at")
            if window and step_start and step_end:
                run_start, run_end, coarse = window
                # Compare at the coarsest granularity present on either side.
                if coarse or is_date_only(raw_start) or is_date_only(raw_end):
                    within = (step_start.date() >= run_start.date()
                              and step_end.date() <= run_end.date())
                    shown = f"{run_start.date()}..{run_end.date()} (by date)"
                else:
                    within = step_start >= run_start and step_end <= run_end
                    shown = f"{run_start.isoformat()}..{run_end.isoformat()}"
                if not within:
                    add("FAIL", "provenance",
                        f"row {line}: step window {raw_start.strip()}..{raw_end.strip()} "
                        f"falls outside the run window {shown} -- the step record was "
                        "not written when it claims to have been")

    if tier == 2 and not any(
        r.get("rerun_match", "").strip().lower() == "yes" for r in rows
    ):
        add("FAIL", "provenance",
            "tier 2 requires at least one step with rerun_match=yes (the re-run test)")
    elif tier == 1 and not any(
        r.get("rerun_match", "").strip().lower() == "yes" for r in rows
    ):
        add("WARN", "provenance", "no rerun_match=yes recorded -- reproducibility unverified")


def check_claims(rows: list[dict], root: Path, tier) -> None:
    if not rows:
        return
    for row in rows:
        line = row.get("_line", "?")
        claim_id = row.get("claim_id", "") or f"row {line}"
        for column in ("claim", "level", "evidence_artifact", "method", "confidence",
                       "verified_by"):
            if not row.get(column, "").strip():
                add("FAIL", "claims", f"{claim_id}: empty `{column}`")
        level = row.get("level", "").strip().lower()
        confidence = row.get("confidence", "").strip().lower()
        verified = row.get("verified_by", "").strip().lower()
        if level and level not in CLAIM_LEVELS:
            add("FAIL", "claims",
                f"{claim_id}: level={level!r} not in {sorted(CLAIM_LEVELS)}")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            add("WARN", "claims",
                f"{claim_id}: confidence={confidence!r} not in {sorted(CONFIDENCE_LEVELS)}")
        if verified and verified not in VERIFIED_BY:
            add("FAIL", "claims",
                f"{claim_id}: verified_by={verified!r} not in {sorted(VERIFIED_BY)}")

        artifact = row.get("evidence_artifact", "").strip()
        if artifact and artifact.lower() not in NA_SENTINELS and not (root / artifact).exists():
            add("FAIL", "claims", f"{claim_id}: evidence artifact not on disk: {artifact}")

        literature = row.get("literature", "").strip()
        has_literature = bool(literature) and literature.lower() not in NA_SENTINELS | {"none"}
        if level in {"causal", "clinical"} and not has_literature and verified != "human":
            add("FAIL", "claims",
                f"{claim_id}: level={level} needs literature support or human verification "
                "(association alone does not establish causation)")
        if verified == "none":
            add("WARN", "claims", f"{claim_id}: verified_by=none -- not yet verified")
        if tier == 2 and level in {"causal", "clinical"} and verified != "human":
            add("FAIL", "claims",
                f"{claim_id}: tier 2 requires human verification for {level} claims")

        # A named human is what tier 2 asks for; an anonymous "human" is an assertion.
        if verified == "human":
            reviewer = row.get("reviewer", "").strip()
            reviewed_at = row.get("reviewed_at", "").strip()
            named = bool(reviewer) and reviewer.lower() not in (
                NA_SENTINELS | UNKNOWN_SENTINELS | {"none"})
            if not named:
                add("FAIL" if tier == 2 else "WARN", "claims",
                    f"{claim_id}: verified_by=human without a named `reviewer`"
                    + (" -- tier 2 requires a name, not an assertion" if tier == 2 else ""))
            elif not reviewed_at or reviewed_at.lower() in UNKNOWN_SENTINELS:
                add("FAIL", "claims",
                    f"{claim_id}: reviewer {reviewer!r} named but `reviewed_at` is empty")
            elif parse_ts(reviewed_at) is None:
                add("WARN", "claims",
                    f"{claim_id}: reviewed_at={reviewed_at!r} is not ISO-8601")


def check_p_padj(root: Path) -> None:
    patterns = []
    ignore_file = root / IGNORE_NAME
    if ignore_file.is_file():
        patterns = [ln.strip() for ln in ignore_file.read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.startswith("#")]
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TABLE_SUFFIXES:
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if path.name in {PROVENANCE_NAME, CLAIMS_NAME, CONTRACT_NAME}:
            continue
        if any(fnmatch.fnmatch(rel, p) for p in patterns):
            continue
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                header = handle.readline().strip()
        except OSError:
            continue
        if not header or "\t" not in header and "," not in header:
            continue
        cells = [c.strip().strip('"') for c in re.split(r"[\t,]", header)]
        has_p = any(P_COLUMNS.match(c) for c in cells)
        has_padj = any(PADJ_COLUMNS.match(c) for c in cells)
        if has_p and not has_padj:
            scanned += 1
            add("FAIL", "tables",
                f"{rel}: has a p-value column but no multiple-testing-corrected column "
                f"(padj/q/FDR). Add the correction, or list this file in {IGNORE_NAME} "
                "if the column is not a hypothesis test.")
    if scanned == 0:
        add("OK", "tables", "no uncorrected p-value columns found in scanned tables")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical gate check for a bioinformatics analysis deliverable.")
    parser.add_argument("analysis_dir", help="directory holding the contract and ledgers")
    parser.add_argument("--expect-tier", type=int, choices=[0, 1, 2], default=None,
                        help="fail the run if the contract declares a different tier")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args()

    root = Path(args.analysis_dir).expanduser()
    if not root.is_dir():
        print(f"FAIL  {root} is not a directory")
        return 1

    contract = read_kv(root / CONTRACT_NAME, "contract")
    tier = check_contract(contract, args.expect_tier)

    context_path = root / RUN_CONTEXT_NAME
    if tier == 0:
        window = None
    elif context_path.is_file():
        window = check_run_context(read_kv(context_path, "run-context"), tier)
    else:
        add("FAIL", "run-context",
            f"{RUN_CONTEXT_NAME} not found -- required for tier {tier}: which agent, "
            "which model, which session, over what window ran this analysis")
        window = None

    provenance = read_tsv(root / PROVENANCE_NAME, PROVENANCE_COLUMNS, "provenance")
    claims = read_tsv(root / CLAIMS_NAME, CLAIM_COLUMNS, "claims")
    check_provenance(provenance, root, tier, window)
    check_claims(claims, root, tier)
    check_p_padj(root)

    locks = find_lock_files(root)
    if locks:
        add("OK", "reproducibility", f"environment lock present: {', '.join(locks[:4])}")
    elif tier == 2:
        add("FAIL", "reproducibility",
            "tier 2 requires a pinned environment (lock file / container / conda env export)")
    elif tier == 1:
        add("WARN", "reproducibility", "no environment lock file found")
    else:
        add("SKIP", "reproducibility", "no environment lock found (tier 0)")

    if args.json:
        print(json.dumps(
            {"analysis_dir": str(root), "tier": tier,
             "findings": [{"level": l, "section": s, "message": m} for l, s, m in findings],
             "failures": sum(1 for l, _, _ in findings if l == "FAIL")},
            indent=2))
    else:
        order = {"FAIL": 0, "WARN": 1, "SKIP": 2, "OK": 3}
        for level, sec, message in sorted(findings, key=lambda f: (order[f[0]], f[1])):
            print(f"{level:<4}  {sec:<15} {message}")
        fails = sum(1 for l, _, _ in findings if l == "FAIL")
        warns = sum(1 for l, _, _ in findings if l == "WARN")
        print("-" * 60)
        print(f"RESULT: {fails} FAIL, {warns} WARN"
              f"{'  ->  gate NOT passed' if fails else '  ->  gate passed'}")
        if fails:
            print("Nothing ships with an unresolved FAIL. Fix, or declare the gap "
                  "explicitly in the deliverable.")
    return 1 if any(l == "FAIL" for l, _, _ in findings) else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    sys.exit(main())
