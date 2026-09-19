#!/usr/bin/env python3
"""Mechanical gate check for a bioinformatics analysis deliverable.

Part of the `bioinfo-trust-framework` skill. Checks only what can be checked
mechanically; judgement items stay with a human.

    python verify_deliverable.py <analysis_dir> [--expect-tier 0|1|2] [--json]
    python verify_deliverable.py --gate-map-check
    python verify_deliverable.py --write-gate-map

Exit codes:
    0  no FAIL findings (WARN and SKIP are allowed)
    1  at least one FAIL finding
    2  the checker itself is misconfigured: its check registry and the shipped
       assets/gate-map.tsv disagree, or a finding was emitted under an
       unregistered check id. Its output cannot be trusted in that state, so it
       refuses to pretend otherwise.

Files expected in <analysis_dir>:
    analysis-contract.txt    the Gate 1 contract
    run-context.txt          who/what ran it (Gate 1, closed at Gate 3)
    provenance-ledger.tsv    per-step provenance (Gate 2)
    claim-ledger.tsv         per-claim evidence (Gate 3)
    error-ledger.tsv         the error account -- required when a step is `deviated`
    review-record.tsv        what each human review actually did -- required at tier 2
                             whenever a claim carries `verified_by: human`

run-context.txt is required for tier >= 1; tier 0 (exploratory) skips it.
Steps need timestamps and an author for tier >= 1; tier 0 skips those too.

New in framework 1.1.0: the error ledger, the review record, the provenance
`deviation` column, and the gate classification below. A contract that does not
declare `framework_version` >= 1.1.0 keeps the pre-1.1.0 bar -- those requirements
report as WARN with an explicit marker rather than FAILing, so a deliverable
produced under an older framework is not retroactively judged non-compliant.

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
RUN_CONTEXT_NAME = "run-context.txt"
PROVENANCE_NAME = "provenance-ledger.tsv"
CLAIMS_NAME = "claim-ledger.tsv"
ERROR_LEDGER_NAME = "error-ledger.tsv"
REVIEW_NAME = "review-record.tsv"
IGNORE_NAME = ".trust-ignore"
GATE_MAP_NAME = "gate-map.tsv"

FRAMEWORK_VERSION_KEY = "framework_version"
CURRENT_FRAMEWORK_VERSION = (1, 1, 0)
LEGACY_MARK = "  [advisory: contract declares no framework_version >= 1.1.0]"

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
# Which gate a missing contract field belongs to. A missing `reference_genome` is an
# external-alignment gap, a missing `n_per_group` is a design gap, and a missing
# `random_seed` is a reproducibility gap -- they are not one finding with one cause.
CONTRACT_KEY_GATE = {
    "analysis_id": "design",
    "question": "design",
    "analysis_type": "design",
    "unit_of_analysis": "design",
    "tier": "design",
    "success_criteria": "design",
    "n_per_group": "design",
    "comparison": "design",
    "batch_confound": "design",
    "domain_skills_loaded": "design",
    "reference_genome": "external",
    "reference_annotation": "external",
    "reference_database": "external",
    "random_seed": "execution",
}
REFERENCE_KEYS = ["reference_genome", "reference_annotation", "reference_database"]
NA_SENTINELS = {"not_applicable", "n/a", "na"}
UNKNOWN_SENTINELS = {"unknown", "todo", "tbd", "not_recorded", "not recorded", "?", ""}
# A reviewer field whose value echoes the verified_by value itself ("human") identifies
# nobody -- the same reasoning that makes "none" a placeholder there. Found by the
# v1.1.0 regression suite, not by a hypothetical.
REVIEWER_PLACEHOLDERS = NA_SENTINELS | UNKNOWN_SENTINELS | {"none", "human"}
PLACEHOLDER = re.compile(r"^(a1b2c3.*|x{3,}|<[^>]*>|\.{3,}|example.*|placeholder.*)$", re.I)
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)

PROVENANCE_COLUMNS = [
    "step_id", "step", "tool", "tool_version", "script_or_command", "parameters",
    "input", "input_sha256", "output", "reference_build", "source_of_default",
    "rerun_match", "started_at", "ended_at", "authored_by", "notes",
]
# Added in 1.1.0. Absent in a pre-1.1.0 ledger -> advisory, not a defect.
PROVENANCE_NEW_COLUMNS = ("deviation",)
DEVIATION_STATES = {"met", "deviated", "unknown"}

CLAIM_COLUMNS = [
    "claim_id", "claim", "level", "evidence_artifact", "method",
    "literature", "confidence", "verified_by", "reviewer", "reviewed_at",
]
CLAIM_LEVELS = {"descriptive", "comparative", "hypothesis_generating", "causal", "clinical"}
CONFIDENCE_LEVELS = {"high", "moderate", "low"}
VERIFIED_BY = {"automated", "human", "none"}
RERUN_VALUES = {"yes", "no", "not_attempted"}

ERROR_COLUMNS = [
    "error_id", "stage", "class", "emergent_kind", "description", "detected_by",
    "detected_at", "containment", "propagated_to", "resolution",
]
ERROR_CLASSES = {"inherited", "amplified", "emergent"}
EMERGENT_KINDS = {
    "goal_drift",            # iterative planning quietly swaps the question for an easier one
    "context_loss",          # pairing, exclusion criteria or a control drop out of working context
    "stale_memory",          # a remembered fact is used past its expiry
    "retrieval_poisoning",   # instructions found in a repo or metadata are obeyed as instructions
    "incomplete_tool_description",
}
DETECTED_BY = {"auto", "human", "not_detected"}
UNCONTAINED = {"uncontained", "not_contained", "none"}

REVIEW_COLUMNS = [
    "review_id", "scope", "reviewer", "reviewed_at", "duration_min",
    "disagreements", "disagreements_detail", "overrides", "errors_found",
    "error_classes_found", "verdicts_changed", "calibration_note",
]
REVIEW_COUNT_FIELDS = ("disagreements", "overrides", "errors_found", "verdicts_changed")

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
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?")

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
SCAN_SKIP_NAMES = {PROVENANCE_NAME, CLAIMS_NAME, ERROR_LEDGER_NAME, REVIEW_NAME,
                   CONTRACT_NAME, RUN_CONTEXT_NAME}

# --------------------------------------------------------------------------- registry
#
# Every finding carries a check id, and every check id belongs to exactly one gate.
# `add()` refuses an unregistered id, so a finding cannot be emitted without a gate
# label -- the classification is enforced, not decorative. `assets/gate-map.tsv` is
# the human-readable mirror of this table and is checked against it at startup.

CHECKS = {
    # -- the contract (Gate 1) -------------------------------------------------
    "C01": ("design", "contract",
            "a required design field is absent from the contract"),
    "C02": ("external", "contract",
            "a required reference field (genome / annotation / database) is absent"),
    "C03": ("execution", "contract",
            "random_seed is absent from the contract"),
    "C04": ("design", "contract",
            "a field that conceptually always exists is marked not_applicable"),
    "C05": ("design", "contract",
            "a contract field is unresolved (UNKNOWN / blank / placeholder)"),
    "C06": ("design", "contract",
            "fields marked not_applicable carry no justification"),
    "C07": ("design", "contract",
            "not_applicable accepted with a justification"),
    "C08": ("design", "contract",
            "tier is not 0/1/2, or disagrees with --expect-tier"),
    "C09": ("external", "contract",
            "all three reference_* fields are not_applicable"),
    "C10": ("execution", "contract",
            "random_seed is unset, or justified as not_applicable"),
    "C11": ("design", "contract",
            "the contract declares no framework_version, so 1.1.0 requirements are advisory"),
    # -- the actor layer (run-context.txt) ------------------------------------
    "C12": ("execution", "run-context",
            "a required actor-layer key is absent"),
    "C13": ("execution", "run-context",
            "an actor-layer field is unresolved"),
    "C14": ("execution", "run-context",
            "model identity recorded as unavailable without a model_identity_note"),
    "C15": ("execution", "run-context",
            "not_applicable on an actor field that is always knowable"),
    "C16": ("execution", "run-context",
            "an actor field is not_applicable without justification"),
    "C17": ("execution", "run-context",
            "a run-window bound is not ISO-8601"),
    "C18": ("execution", "run-context",
            "run_started_at is after run_ended_at"),
    "C19": ("execution", "run-context",
            "an actor field accepted as unavailable / not_applicable"),
    # -- provenance (Gate 2) --------------------------------------------------
    "C20": ("execution", "provenance",
            "the provenance ledger is absent or has no data rows"),
    "C21": ("execution", "provenance",
            "the provenance ledger is missing a required column"),
    "C22": ("execution", "provenance",
            "an empty provenance cell (tool / version / parameters / input / output / default source)"),
    "C23": ("external", "provenance",
            "an empty reference_build on a step"),
    "C24": ("execution", "provenance",
            "an empty input_sha256"),
    "C25": ("execution", "provenance",
            "input_sha256 is not a 64-character hex digest"),
    "C26": ("execution", "provenance",
            "rerun_match is not in the enum"),
    "C27": ("execution", "provenance",
            "a declared output file is not on disk"),
    "C28": ("execution", "provenance",
            "a step timestamp is unresolved (blank / placeholder / unknown-family)"),
    "C29": ("execution", "provenance",
            "authored_by is unresolved or not in the enum"),
    "C30": ("execution", "provenance",
            "a step timestamp is not ISO-8601"),
    "C31": ("execution", "provenance",
            "a step window falls outside the declared run window"),
    "C32": ("execution", "provenance",
            "tier 2 requires a re-run (at least one rerun_match=yes)"),
    "C33": ("execution", "provenance",
            "the step deviation state is absent, unresolved, or `unknown`"),
    # -- claims (Gate 3) ------------------------------------------------------
    "C34": ("execution", "claims",
            "the claim ledger is absent or has no data rows"),
    "C35": ("execution", "claims",
            "the claim ledger is missing a required column"),
    "C36": ("inference", "claims",
            "an empty claim cell (claim / level / confidence / verified_by)"),
    "C37": ("execution", "claims",
            "an empty `method` on a claim"),
    "C38": ("execution", "claims",
            "evidence_artifact is empty or not on disk"),
    "C39": ("inference", "claims",
            "the claim level is not in the enum"),
    "C40": ("inference", "claims",
            "confidence is not in the enum"),
    "C41": ("inference", "claims",
            "verified_by is not in the enum"),
    "C42": ("inference", "claims",
            "a causal or clinical claim has neither literature nor human verification"),
    "C43": ("inference", "claims",
            "verified_by=none -- the claim is not yet verified"),
    "C44": ("inference", "claims",
            "tier 2 requires human verification for causal and clinical claims"),
    "C45": ("inference", "claims",
            "verified_by=human without an identified reviewer"),
    "C46": ("inference", "claims",
            "a reviewer is recorded but reviewed_at is empty"),
    "C47": ("inference", "claims",
            "reviewed_at is not ISO-8601"),
    # -- result tables --------------------------------------------------------
    "C48": ("inference", "tables",
            "a table has a p-value column but no multiple-testing-corrected column"),
    "C49": ("inference", "tables",
            "no uncorrected p-value column found in the scanned tables"),
    # -- reproducibility ------------------------------------------------------
    "C50": ("execution", "reproducibility",
            "an environment lock is present"),
    "C51": ("execution", "reproducibility",
            "tier 2 requires a pinned environment"),
    "C52": ("execution", "reproducibility",
            "no environment lock found (tier 1, advisory)"),
    "C53": ("execution", "reproducibility",
            "no environment lock recorded (tier 0)"),
    # -- the error account (1.1.0) -------------------------------------------
    "C54": ("inference", "errors",
            "the error class is not in {inherited, amplified, emergent}"),
    "C55": ("inference", "errors",
            "class=emergent without a valid emergent_kind"),
    "C56": ("execution", "errors",
            "the stage names a step_id absent from the provenance ledger"),
    "C57": ("inference", "errors",
            "detected_by=not_detected is inconsistent with containment / detected_at"),
    "C58": ("inference", "errors",
            "propagated_to names a claim_id absent from the claim ledger"),
    "C59": ("inference", "errors",
            "a step is recorded as deviated but the error ledger has no rows"),
    "C60": ("inference", "errors",
            "the error ledger records no errors and carries no `none-detected-by:` declaration"),
    "C61": ("execution", "errors",
            "an error-ledger required cell is empty"),
    "C62": ("execution", "errors",
            "the error ledger is absent although a deviated step requires it"),
    # -- the review record (1.1.0) -------------------------------------------
    "C63": ("inference", "review",
            "a human-verified claim at tier 2 is not covered by any review record"),
    "C64": ("inference", "review",
            "duration_min is not a positive number"),
    "C65": ("inference", "review",
            "errors_found is blank or not a non-negative integer"),
    "C66": ("inference", "review",
            "the reviewer is empty or a placeholder"),
    "C67": ("inference", "review",
            "reviewed_at is missing or not ISO-8601"),
    "C68": ("inference", "review",
            "a review count field is not a non-negative integer"),
    "C69": ("inference", "review",
            "a required review cell (review_id / scope / calibration_note) is empty"),
    "C70": ("execution", "review",
            "the review-record file is absent or has no rows"),
    "C71": ("inference", "review",
            "review summary statistics (informational -- the checker reports, it does not judge)"),
    # -- the classifier's own registry ---------------------------------------
    "M01": ("execution", "framework",
            "the gate map registers every check id under exactly one gate"),
}

GATE_ORDER = ["execution", "design", "inference", "biological", "external"]
GATE_MEANING = {
    "execution": "did it run, and is the record of the run complete (reproducibility layer)",
    "design": "does the design support the question (n, pairing, controls, sampling unit)",
    "inference": "do the statistics and the evidence license the conclusion",
    "biological": "does it hold up biologically (mechanism, pathway, known biology)",
    "external": "does it line up with the outside world (literature, databases, builds)",
}

findings: list[tuple[str, str, str]] = []   # (level, check_id, message)
ABSENT_COLUMNS: set[str] = set()            # columns read_tsv reported as missing
LEVEL_ORDER = {"FAIL": 0, "WARN": 1, "SKIP": 2, "OK": 3}


class FrameworkError(RuntimeError):
    """The checker cannot classify its own output. Not a finding about the deliverable."""


def add(level: str, message: str, check: str) -> None:
    """Record a finding. `check` is mandatory and must be registered.

    There is no default: a finding with no gate label is the failure mode this
    signature exists to make impossible.
    """
    if check not in CHECKS:
        raise FrameworkError(f"check {check!r} is not registered in CHECKS")
    findings.append((level, check, message))


def gate_of(check: str) -> str:
    return CHECKS[check][0]


def advisory(level: str, current: bool) -> str:
    """A 1.1.0 requirement does not FAIL a deliverable that predates 1.1.0."""
    return level if current else ("WARN" if level == "FAIL" else level)


def mark(message: str, current: bool) -> str:
    return message if current else message + LEGACY_MARK


def registered_gate_map() -> dict:
    return {cid: meta[0] for cid, meta in CHECKS.items()}


def render_gate_map() -> str:
    lines = [
        "check_id\tgate\tsection\twhat_it_checks",
        "# The gate map of scripts/verify_deliverable.py. Generated from the checker's",
        "# CHECKS registry (`--write-gate-map`), verified against it on every run",
        "# (`--gate-map-check`). A check id that is not here, or that carries a different",
        "# gate here than in the registry, makes the checker exit 2 rather than print a",
        "# classification it cannot justify.",
        "#",
        "# The four gates in SKILL.md are a TIME axis (when to check). These five are the",
        "# SUBSTANCE axis (what kind of judgement is being checked). Both are kept; neither",
        "# replaces the other.",
        "#",
        "#   execution   -- did it run, and is the record complete",
        "#   design      -- does the design support the question",
        "#   inference   -- do statistics and evidence license the conclusion",
        "#   biological  -- does it hold up biologically",
        "#   external    -- does it line up with the outside world",
        "#",
        "# NOTE on the empty column: no mechanical check carries the `biological` gate, and",
        "# that is a finding from doing the mapping, not an oversight. Deciding whether a",
        "# result is biologically coherent needs a model of the system under study; a",
        "# generic checker that claimed to do it would be guessing. Biological soundness",
        "# stays with the (human) checklist items.",
    ]
    for cid in sorted(CHECKS):
        gate, section, what = CHECKS[cid]
        lines.append(f"{cid}\t{gate}\t{section}\t{what}")
    return "\n".join(lines) + "\n"


def gate_map_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / GATE_MAP_NAME


def load_gate_map() -> dict:
    path = gate_map_path()
    if not path.is_file():
        raise FrameworkError(f"{GATE_MAP_NAME} not found at {path}")
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        data = [ln for ln in handle if ln.strip() and not ln.lstrip().startswith("#")]
    if not data:
        raise FrameworkError(f"{GATE_MAP_NAME} has no rows")
    out = {}
    for row in csv.DictReader(data, delimiter="\t"):
        cid = (row.get("check_id") or "").strip()
        if not cid:
            continue
        out[cid] = (row.get("gate") or "").strip().lower()
    return out


def gate_map_problems() -> list:
    """Differences between the shipped gate map and the registry."""
    shipped = load_gate_map()
    registry = registered_gate_map()
    problems = []
    for cid in sorted(set(registry) - set(shipped)):
        problems.append(f"check {cid} is emitted by the checker but absent from {GATE_MAP_NAME}")
    for cid in sorted(set(shipped) - set(registry)):
        problems.append(f"{GATE_MAP_NAME} lists check {cid}, which the checker never emits")
    for cid in sorted(set(shipped) & set(registry)):
        if shipped[cid] != registry[cid]:
            problems.append(
                f"check {cid}: {GATE_MAP_NAME} says {shipped[cid]!r}, "
                f"the registry says {registry[cid]!r}")
        elif shipped[cid] not in GATE_ORDER:
            problems.append(
                f"check {cid}: gate {shipped[cid]!r} is not one of {GATE_ORDER}")
    return problems


# --------------------------------------------------------------------------- readers

def is_unset(value: str) -> bool:
    """True when a field carries no actual record: blank, a placeholder, or an
    'unknown'-family sentinel. `not_recorded` counts -- it is an admission that the
    fact was not captured, which is what the field exists to prevent."""
    text = (value or "").strip()
    return (not text) or text.lower() in UNKNOWN_SENTINELS or bool(PLACEHOLDER.match(text))


def read_kv(path: Path, check_missing: str) -> dict:
    """Parse `key: value` files (the contract, the run context).

    Decoded as utf-8-sig: a UTF-8 BOM is stripped rather than becoming part of the
    first key. Excel on Windows writes a BOM by default, so this is the common
    real-world path, not a corner case.
    """
    if not path.is_file():
        add("FAIL", f"{path.name} not found in {path.parent}", check_missing)
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        values[key.strip().lower()] = value.strip()
    return values


def parse_tsv(path: Path):
    """Return (rows, header) with comment lines stripped. Emits nothing.

    `rows is None` means the file is not there; `rows == []` means it is there but
    carries no data row. The two are different conditions and the callers treat them
    differently, so this function refuses to collapse them.
    """
    if not path.is_file():
        return None, None
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        data = [ln for ln in handle if ln.strip() and not ln.lstrip().startswith("#")]
    if not data:
        return [], []
    reader = csv.DictReader(data, delimiter="\t")
    header = [(c or "").strip() for c in (reader.fieldnames or [])]
    rows = []
    for i, row in enumerate(reader, start=1):
        clean = {(k or "").strip(): (v or "").strip() for k, v in row.items() if k}
        clean["_line"] = str(i + 1)
        rows.append(clean)
    return rows, header


def read_directives(path: Path) -> dict:
    """`# key: value` comment directives -- machine-readable declarations that
    legitimately have no data row, such as 'no errors were detected'.

    Without this, the only way to say "we looked and found nothing" would be to leave
    the ledger empty, which is indistinguishable from "nobody looked".
    """
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = re.match(r"^#\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", raw.strip())
        if match:
            out[match.group(1).lower()] = match.group(2).strip()
    return out


def read_tsv(path: Path, columns, check_absent: str, check_columns: str, *,
             new_columns=(), check_new_column: str | None = None,
             current: bool = True, new_requirement: bool = False) -> list:
    """Read a ledger and report structural problems.

    `new_requirement` marks a ledger or column introduced in 1.1.0: when the contract
    does not opt in, its absence is advisory.
    """
    enforced = current or not new_requirement
    rows, header = parse_tsv(path)
    if rows is None:
        add(advisory("FAIL", enforced),
            mark(f"{path.name} not found in {path.parent}", enforced), check_absent)
        return []
    if not rows:
        add(advisory("FAIL", enforced),
            mark(f"{path.name} has no data rows (example lines only?)", enforced),
            check_absent)
        return []
    missing = [c for c in columns if c not in header]
    if missing:
        add("FAIL", f"{path.name} is missing columns: {', '.join(missing)}", check_columns)
    for column in new_columns:
        if column not in header:
            ABSENT_COLUMNS.add(column)
            if check_new_column:
                add(advisory("FAIL", enforced),
                    mark(f"{path.name} has no `{column}` column (added in framework 1.1.0)",
                         enforced), check_new_column)
    return rows


# --------------------------------------------------------------------------- checks

def parse_framework_version(values: dict):
    match = VERSION_RE.match((values.get(FRAMEWORK_VERSION_KEY) or "").strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))


def check_contract(values: dict, expect_tier):
    """Returns (tier, current) where `current` is True when the contract declares
    framework_version >= 1.1.0."""
    if not values:
        return None, False

    version = parse_framework_version(values)
    current = version is not None and version >= CURRENT_FRAMEWORK_VERSION

    for key in CONTRACT_REQUIRED:
        if key not in values:
            gate = CONTRACT_KEY_GATE.get(key, "design")
            check = {"design": "C01", "external": "C02", "execution": "C03"}[gate]
            add("FAIL", f"missing required key: {key}", check)

    not_applicable: list[str] = []
    unknown: list[str] = []
    for key in CONTRACT_REQUIRED:
        value = values.get(key, "")
        low = value.lower()
        if low in NA_SENTINELS:
            if key in NEVER_NA:
                add("FAIL", f"{key} is 'not_applicable' but conceptually always exists", "C04")
            else:
                not_applicable.append(key)
        elif low in UNKNOWN_SENTINELS or PLACEHOLDER.match(value):
            unknown.append(key)
    if unknown:
        add("FAIL",
            f"unresolved (UNKNOWN/blank): {', '.join(unknown)} -- UNKNOWN blocks execution",
            "C05")

    if not_applicable:
        justification = values.get("not_applicable_justification", "").strip()
        # `none` means "no field is not_applicable" -- it is NOT a justification.
        if justification.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none"}:
            add("FAIL",
                f"fields marked not_applicable ({', '.join(not_applicable)}) but no "
                "justification given -- `not_applicable_justification: none` does not "
                "justify anything", "C06")
        else:
            add("SKIP",
                f"not_applicable accepted for {', '.join(not_applicable)} "
                f"(justification: {justification})", "C07")

    tier_raw = values.get("tier", "")
    tier = None
    match = re.search(r"([012])", tier_raw)
    if not match:
        add("FAIL", f"tier must be 0, 1 or 2 -- got {tier_raw!r}", "C08")
    else:
        tier = int(match.group(1))
        if expect_tier is not None and tier != expect_tier:
            add("WARN", f"tier is {tier} but {expect_tier} was expected on the command line",
                "C08")
    if tier == 0:
        add("SKIP", "tier 0 (exploratory): full audit not required, "
                    "label the deliverable as exploratory", "C08")

    if tier in (1, 2) and all(
        values.get(k, "").lower() in NA_SENTINELS for k in REFERENCE_KEYS
    ):
        add("WARN",
            "all three reference_* fields are not_applicable -- confirm this analysis truly "
            "has no genome/annotation/database reference", "C09")

    seed = values.get("random_seed", "").lower()
    if not seed or seed in UNKNOWN_SENTINELS:
        add("WARN", "random_seed unset -- stochastic steps are not reproducible", "C10")
    elif seed in NA_SENTINELS and values.get("not_applicable_justification", "none").lower() != "none":
        add("SKIP", "random_seed not_applicable (justified)", "C10")

    if version is None:
        add("SKIP",
            "no framework_version declared -- the framework 1.1.0 requirements (error ledger, "
            "review record, deviation column) are reported as advisory for this deliverable",
            "C11")
    elif not current:
        add("SKIP",
            f"framework_version {values.get(FRAMEWORK_VERSION_KEY).strip()} predates 1.1.0 -- "
            "the 1.1.0 requirements are reported as advisory for this deliverable", "C11")

    return tier, current


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
        add("SKIP", "tier 0 (exploratory): execution context not required", "C19")
        return None

    for key in RUN_CONTEXT_REQUIRED:
        if key not in values:
            add("FAIL", f"missing required key: {key}", "C12")

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
                add("FAIL",
                    f"{key} is 'not_applicable' but is always knowable "
                    "(write `manual` when no agent was involved)", "C15")
            else:
                not_applicable.append(key)
            continue
        if low in UNKNOWN_SENTINELS or PLACEHOLDER.match(raw):
            unresolved.append(key)

    if unresolved:
        add("FAIL",
            f"unresolved (UNKNOWN/blank): {', '.join(unresolved)} -- the execution "
            "context blocks execution, exactly like the contract", "C13")

    if unavailable:
        note = values.get("model_identity_note", "").strip()
        if note.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none"}:
            add("FAIL",
                f"{', '.join(unavailable)} recorded as unavailable but model_identity_note "
                "is empty -- annotate why it cannot be obtained", "C14")
        else:
            add("SKIP", f"{', '.join(unavailable)} accepted as unavailable (note: {note})",
                "C19")

    if not_applicable:
        justification = values.get("not_applicable_justification", "").strip()
        if justification.lower() in NA_SENTINELS | UNKNOWN_SENTINELS | {"none", ""}:
            add("FAIL",
                f"{', '.join(not_applicable)} marked not_applicable but no "
                "not_applicable_justification is given", "C16")
        else:
            add("SKIP",
                f"not_applicable accepted for {', '.join(not_applicable)} "
                f"(justification: {justification})", "C19")

    raw_start = values.get("run_started_at", "").strip()
    raw_end = values.get("run_ended_at", "").strip()
    start, end = parse_ts(raw_start), parse_ts(raw_end)
    for name, raw, parsed in (("run_started_at", raw_start, start),
                              ("run_ended_at", raw_end, end)):
        if raw and raw.lower() not in UNKNOWN_SENTINELS and parsed is None:
            add("WARN", f"{name}={raw!r} is not ISO-8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM)",
                "C17")
    if start and end:
        if start > end:
            add("FAIL", "run_started_at is after run_ended_at", "C18")
        else:
            # `run_started_at: 2026-09-19` resolves to midnight. A window whose bounds
            # are date-only must be compared as a day, or every real step would fall
            # outside a zero-length window -- a gate that always cries wolf gets turned off.
            coarse = is_date_only(raw_start) or is_date_only(raw_end)
            return (start, end, coarse)
    return None


def find_lock_files(root: Path) -> list:
    found = []
    for pattern in LOCK_PATTERNS:
        for hit in root.glob(pattern):
            if hit.is_file():
                found.append(hit.name)
    for hit in root.glob("*/" + "environment.y*ml"):
        found.append(str(hit.relative_to(root)))
    return sorted(set(found))


def check_provenance(rows: list, root: Path, tier, current: bool, window=None) -> None:
    if not rows:
        return
    deviation_enforced = current
    for row in rows:
        line = row.get("_line", "?")
        for column in ("tool", "tool_version", "parameters", "input", "output",
                       "source_of_default"):
            if not row.get(column, "").strip():
                add("FAIL", f"row {line}: empty `{column}`", "C22")
        if not row.get("reference_build", "").strip():
            add("FAIL", f"row {line}: empty `reference_build`", "C23")
        digest = row.get("input_sha256", "")
        if not digest:
            add("FAIL", f"row {line}: empty `input_sha256`", "C24")
        elif not SHA256.match(digest) and digest.lower() not in NA_SENTINELS:
            add("WARN", f"row {line}: input_sha256 is not a 64-char hex digest ({digest[:20]!r})",
                "C25")
        rerun = row.get("rerun_match", "").strip().lower()
        if rerun and rerun not in RERUN_VALUES:
            add("WARN", f"row {line}: rerun_match={rerun!r} not in {sorted(RERUN_VALUES)}",
                "C26")
        output = row.get("output", "").strip()
        if output and output.lower() not in NA_SENTINELS and not SHA256.match(output):
            if not (root / output).exists():
                add("WARN", f"row {line}: declared output not on disk: {output}", "C27")

        # --- the deviation state, added in 1.1.0 ---
        if "deviation" not in ABSENT_COLUMNS:
            state = row.get("deviation", "").strip().lower()
            if state not in DEVIATION_STATES:
                add(advisory("FAIL", deviation_enforced),
                    mark(f"row {line}: `deviation` is "
                         f"{'empty' if not state else repr(state)} -- expected one of "
                         f"{sorted(DEVIATION_STATES)}", deviation_enforced), "C33")
            elif state == "unknown":
                # `unknown` is IN the enum but still blocks delivery: the template
                # documents it that way and the v1.1.0 regression suite held the
                # checker to its own documentation.
                add(advisory("FAIL", deviation_enforced),
                    mark(f"row {line}: `deviation` is `unknown` -- this blocks delivery "
                         "until it is resolved, because a deviation nobody recorded is "
                         "a defect, not a decision", deviation_enforced), "C33")

        # --- the actor layer, per step: when, and who/what produced it ---
        if tier in (1, 2):
            for column in ("started_at", "ended_at"):
                if is_unset(row.get(column, "")):
                    add("FAIL",
                        f"row {line}: `{column}` is unresolved "
                        "(blank, placeholder, or an unknown-family sentinel)", "C28")
            authored = row.get("authored_by", "").strip().lower()
            if is_unset(authored):
                add("FAIL",
                    f"row {line}: `authored_by` is unresolved -- expected one of "
                    f"{sorted(AUTHORED_BY)}", "C29")
            elif authored not in AUTHORED_BY:
                add("FAIL", f"row {line}: authored_by={authored!r} not in {sorted(AUTHORED_BY)}",
                    "C29")

            raw_start = row.get("started_at", "")
            raw_end = row.get("ended_at", "")
            step_start, step_end = parse_ts(raw_start), parse_ts(raw_end)
            for name, raw, parsed in (("started_at", raw_start, step_start),
                                      ("ended_at", raw_end, step_end)):
                if raw.strip() and parsed is None:
                    add("WARN", f"row {line}: {name}={raw!r} is not ISO-8601", "C30")
            if step_start and step_end and step_start > step_end:
                add("FAIL", f"row {line}: started_at is after ended_at", "C30")
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
                    add("FAIL",
                        f"row {line}: step window {raw_start.strip()}..{raw_end.strip()} "
                        f"falls outside the run window {shown} -- the step record was "
                        "not written when it claims to have been", "C31")

    if tier == 2 and not any(
        r.get("rerun_match", "").strip().lower() == "yes" for r in rows
    ):
        add("FAIL", "tier 2 requires at least one step with rerun_match=yes (the re-run test)",
            "C32")
    elif tier == 1 and not any(
        r.get("rerun_match", "").strip().lower() == "yes" for r in rows
    ):
        add("WARN", "no rerun_match=yes recorded -- reproducibility unverified", "C32")


def check_claims(rows: list, root: Path, tier) -> None:
    if not rows:
        return
    for row in rows:
        line = row.get("_line", "?")
        claim_id = row.get("claim_id", "") or f"row {line}"
        for column in ("claim", "level", "confidence", "verified_by"):
            if not row.get(column, "").strip():
                add("FAIL", f"{claim_id}: empty `{column}`", "C36")
        if not row.get("method", "").strip():
            add("FAIL", f"{claim_id}: empty `method`", "C37")
        level = row.get("level", "").strip().lower()
        confidence = row.get("confidence", "").strip().lower()
        verified = row.get("verified_by", "").strip().lower()
        if level and level not in CLAIM_LEVELS:
            add("FAIL", f"{claim_id}: level={level!r} not in {sorted(CLAIM_LEVELS)}", "C39")
        if confidence and confidence not in CONFIDENCE_LEVELS:
            add("WARN", f"{claim_id}: confidence={confidence!r} not in "
                        f"{sorted(CONFIDENCE_LEVELS)}", "C40")
        if verified and verified not in VERIFIED_BY:
            add("FAIL", f"{claim_id}: verified_by={verified!r} not in {sorted(VERIFIED_BY)}",
                "C41")

        artifact = row.get("evidence_artifact", "").strip()
        if artifact and artifact.lower() not in NA_SENTINELS and not (root / artifact).exists():
            add("FAIL", f"{claim_id}: evidence artifact not on disk: {artifact}", "C38")

        literature = row.get("literature", "").strip()
        has_literature = bool(literature) and literature.lower() not in NA_SENTINELS | {"none"}
        if level in {"causal", "clinical"} and not has_literature and verified != "human":
            add("FAIL",
                f"{claim_id}: level={level} needs literature support or human verification "
                "(association alone does not establish causation)", "C42")
        if verified == "none":
            add("WARN", f"{claim_id}: verified_by=none -- not yet verified", "C43")
        if tier == 2 and level in {"causal", "clinical"} and verified != "human":
            add("FAIL", f"{claim_id}: tier 2 requires human verification for {level} claims",
                "C44")

        # An identified human is what tier 2 asks for; an anonymous "human" is an assertion.
        # A personal name is not required -- a handle or a role id is an identity too.
        if verified == "human":
            reviewer = row.get("reviewer", "").strip()
            reviewed_at = row.get("reviewed_at", "").strip()
            identified = bool(reviewer) and reviewer.lower() not in REVIEWER_PLACEHOLDERS
            if not identified:
                add("FAIL" if tier == 2 else "WARN",
                    f"{claim_id}: verified_by=human without an identified `reviewer`"
                    + (" -- tier 2 requires an identity, not an assertion" if tier == 2 else ""),
                    "C45")
            elif not reviewed_at or reviewed_at.lower() in UNKNOWN_SENTINELS:
                add("FAIL", f"{claim_id}: reviewer {reviewer!r} recorded but `reviewed_at` "
                            "is empty", "C46")
            elif parse_ts(reviewed_at) is None:
                add("WARN", f"{claim_id}: reviewed_at={reviewed_at!r} is not ISO-8601", "C47")


def check_error_ledger(root: Path, provenance: list, claims: list, tier, current: bool) -> None:
    """The error account: what went wrong, and whether it was contained.

    Blank and 'we looked and found nothing' are different statements, and only one of
    them is checkable. The ledger exists so that the second one has to be made
    explicitly, with the detection method named.
    """
    if tier == 0:
        add("SKIP", "tier 0 (exploratory): the error account is not required", "C60")
        return
    path = root / ERROR_LEDGER_NAME
    rows, _ = parse_tsv(path)
    directives = read_directives(path)
    enforced = current

    deviated = sorted({
        (r.get("step_id") or f"row {r.get('_line', '?')}").strip()
        for r in provenance
        if r.get("deviation", "").strip().lower() == "deviated"
    })

    if not rows:
        present = rows is not None
        if deviated:
            add(advisory("FAIL", enforced),
                mark(f"{ERROR_LEDGER_NAME} is "
                     f"{'empty' if present else 'absent'} but "
                     f"{', '.join(deviated)} {'is' if len(deviated) == 1 else 'are'} recorded "
                     "as `deviated` in the provenance ledger -- a deviation without an error "
                     "entry is a decision nobody wrote down", enforced), "C62")
        else:
            declared = directives.get("none-detected-by", "")
            if is_unset(declared):
                add(advisory("FAIL", enforced),
                    mark(f"{ERROR_LEDGER_NAME} records no errors and carries no "
                         "`# none-detected-by: <method>` declaration "
                         f"({'file present but empty' if present else 'file absent'}) -- an "
                         "empty ledger is indistinguishable from nobody having looked",
                         enforced), "C60")
            else:
                add("OK", f"no errors recorded; detection method declared: {declared}", "C60")
        return

    claim_ids = {r.get("claim_id", "").strip() for r in claims if r.get("claim_id")}
    step_ids = {r.get("step_id", "").strip() for r in provenance if r.get("step_id")}

    for row in rows:
        line = row.get("_line", "?")
        error_id = row.get("error_id", "") or f"row {line}"
        for column in ("error_id", "description", "containment", "resolution"):
            if not row.get(column, "").strip():
                add(advisory("FAIL", enforced),
                    mark(f"{error_id}: empty `{column}`", enforced), "C61")

        klass = row.get("class", "").strip().lower()
        if klass not in ERROR_CLASSES:
            add(advisory("FAIL", enforced),
                mark(f"{error_id}: class={klass!r} not in {sorted(ERROR_CLASSES)}", enforced),
                "C54")

        kind = row.get("emergent_kind", "").strip().lower()
        if klass == "emergent":
            if kind not in EMERGENT_KINDS:
                add(advisory("FAIL", enforced),
                    mark(f"{error_id}: class=emergent needs an `emergent_kind` from "
                         f"{sorted(EMERGENT_KINDS)} -- it is the only part of the taxonomy "
                         "that says something the class alone does not", enforced), "C55")
        elif kind and kind not in {"-", "none"}:
            add(advisory("WARN", enforced),
                mark(f"{error_id}: class={klass!r} but emergent_kind={kind!r} is set -- "
                     "write `-`", enforced), "C55")

        stage = row.get("stage", "").strip()
        if stage and stage not in {"-", "none"} and stage not in step_ids:
            add(advisory("FAIL", enforced),
                mark(f"{error_id}: stage={stage!r} is not a step_id in "
                     f"{PROVENANCE_NAME}", enforced), "C56")

        detected = row.get("detected_by", "").strip().lower()
        detected_at = row.get("detected_at", "").strip()
        containment = row.get("containment", "").strip().lower()
        if detected and detected not in DETECTED_BY:
            add(advisory("FAIL", enforced),
                mark(f"{error_id}: detected_by={detected!r} not in {sorted(DETECTED_BY)}",
                     enforced), "C57")
        elif detected == "not_detected":
            if containment not in UNCONTAINED:
                add(advisory("FAIL", enforced),
                    mark(f"{error_id}: detected_by=not_detected requires "
                         "containment=uncontained -- an undetected error that is also "
                         "described as contained is a claim nobody can hold", enforced), "C57")
            if detected_at and detected_at not in {"-", "none"}:
                add(advisory("FAIL", enforced),
                    mark(f"{error_id}: detected_by=not_detected but `detected_at` is filled "
                         "-- nothing detected it", enforced), "C57")
        elif detected in {"auto", "human"} and is_unset(detected_at):
            add(advisory("FAIL", enforced),
                mark(f"{error_id}: detected_by={detected} but `detected_at` is empty",
                     enforced), "C57")

        propagated = [c.strip() for c in re.split(r"[,;]", row.get("propagated_to", ""))
                      if c.strip() and c.strip() not in {"-", "none"}]
        for target in propagated:
            if target not in claim_ids:
                add(advisory("FAIL", enforced),
                    mark(f"{error_id}: propagated_to names {target!r}, which is not a "
                         f"claim_id in {CLAIMS_NAME}", enforced), "C58")


def to_int(value: str):
    text = (value or "").strip()
    if not re.fullmatch(r"[+-]?\d+", text):
        return None
    return int(text)


def check_review_record(root: Path, claims: list, tier, current: bool) -> None:
    """The review record: what a human review actually did.

    A review is a component, not a ceremony. Recording its duration, the disagreements
    it surfaced and the errors it caught is what makes 'a human checked it' auditable
    as work rather than as a signature. The checker reports the totals; it does not set
    a threshold on them -- a numeric quota would turn the gate into paperwork.
    """
    path = root / REVIEW_NAME
    rows, _ = parse_tsv(path)
    enforced = current

    human_claims = [r.get("claim_id", "").strip() for r in claims
                    if r.get("verified_by", "").strip().lower() == "human"
                    and r.get("claim_id", "").strip()]
    required = tier == 2 and bool(human_claims)

    if not rows:
        if required:
            add(advisory("FAIL", enforced),
                mark(f"{REVIEW_NAME} is "
                     f"{'present but has no rows' if rows is not None else 'absent'} -- "
                     f"tier 2 has human-verified claims ({', '.join(human_claims)}) and no "
                     "record of what the review did", enforced), "C70")
        else:
            add("SKIP",
                "no human-verified claim at tier 2 -- no review record required", "C70")
        return

    durations: list[float] = []
    total_overrides = 0
    total_errors = 0
    scopes: dict[str, set] = {}

    for row in rows:
        line = row.get("_line", "?")
        review_id = row.get("review_id", "") or f"row {line}"
        for column in ("review_id", "scope", "calibration_note"):
            if not row.get(column, "").strip():
                add(advisory("FAIL", enforced),
                    mark(f"{review_id}: empty `{column}`", enforced), "C69")

        reviewer = row.get("reviewer", "").strip()
        if not reviewer or reviewer.lower() in REVIEWER_PLACEHOLDERS:
            add(advisory("FAIL", enforced),
                mark(f"{review_id}: `reviewer` is empty or a placeholder -- the same "
                     "identity rule as the claim ledger applies here", enforced), "C66")
        else:
            covered = {c.strip() for c in re.split(r"[,;]", row.get("scope", ""))
                       if c.strip() and c.strip() not in {"-", "none"}}
            scopes.setdefault(reviewer, set()).update(covered)

        reviewed_at = row.get("reviewed_at", "").strip()
        if is_unset(reviewed_at):
            add(advisory("FAIL", enforced),
                mark(f"{review_id}: `reviewed_at` is missing", enforced), "C67")
        elif parse_ts(reviewed_at) is None:
            add(advisory("WARN", enforced),
                mark(f"{review_id}: reviewed_at={reviewed_at!r} is not ISO-8601", enforced),
                "C67")

        duration = row.get("duration_min", "").strip()
        parsed_duration = None
        try:
            parsed_duration = float(duration) if duration else None
        except ValueError:
            parsed_duration = None
        if parsed_duration is None or parsed_duration <= 0:
            add(advisory("FAIL", enforced),
                mark(f"{review_id}: duration_min={duration!r} is not a positive number -- a "
                     "review with no time attached cannot be distinguished from a glance",
                     enforced), "C64")
        else:
            durations.append(parsed_duration)

        for field in REVIEW_COUNT_FIELDS:
            value = row.get(field, "")
            number = to_int(value)
            if number is None or number < 0:
                add(advisory("FAIL", enforced),
                    mark(f"{review_id}: `{field}` is "
                         f"{'blank' if not value.strip() else repr(value)} -- expected an "
                         "integer >= 0 (0 is a legal and informative value; blank is not, "
                         "because it cannot be told from 'not recorded')", enforced),
                    "C65" if field == "errors_found" else "C68")
            elif field == "overrides":
                total_overrides += number
            elif field == "errors_found":
                total_errors += number

        disagreements = to_int(row.get("disagreements", ""))
        # A detail of "-" is not a detail: when there is something to describe,
        # the dash is as uninformative as a blank.
        detail = row.get("disagreements_detail", "").strip().lower()
        if disagreements and detail in {"", "-", "none"}:
            add(advisory("FAIL", enforced),
                mark(f"{review_id}: disagreements={disagreements} but "
                     "`disagreements_detail` is empty", enforced), "C68")

    if required:
        for claim_id in human_claims:
            if not any(claim_id in covered for covered in scopes.values()):
                add(advisory("FAIL", enforced),
                    mark(f"claim {claim_id}: verified_by=human at tier 2 but no review "
                         f"record lists it in `scope` -- a review that does not say what it "
                         "covered cannot cover it", enforced), "C63")

    if durations:
        mean_duration = sum(durations) / len(durations)
        add("OK",
            f"review summary: {len(rows)} record(s), mean duration "
            f"{mean_duration:.1f} min, {total_overrides} conclusion(s) overridden, "
            f"{total_errors} error(s) found -- reported, not judged", "C71")


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
        if path.name in SCAN_SKIP_NAMES:
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
            add("FAIL",
                f"{rel}: has a p-value column but no multiple-testing-corrected column "
                f"(padj/q/FDR). Add the correction, or list this file in {IGNORE_NAME} "
                "if the column is not a hypothesis test", "C48")
    if scanned == 0:
        add("OK", "no uncorrected p-value columns found in scanned tables", "C49")


# --------------------------------------------------------------------------- main

def report(args, root: Path) -> int:
    contract = read_kv(root / CONTRACT_NAME, "C05")
    tier, current = check_contract(contract, args.expect_tier)

    context_path = root / RUN_CONTEXT_NAME
    if tier == 0:
        window = None
    elif context_path.is_file():
        window = check_run_context(read_kv(context_path, "C12"), tier)
    else:
        add("FAIL",
            f"{RUN_CONTEXT_NAME} not found -- required for tier {tier}: which agent, "
            "which model, which session, over what window ran this analysis", "C12")
        window = None

    provenance = read_tsv(root / PROVENANCE_NAME, PROVENANCE_COLUMNS, "C20", "C21",
                          new_columns=PROVENANCE_NEW_COLUMNS, check_new_column="C33",
                          current=current, new_requirement=True)
    claims = read_tsv(root / CLAIMS_NAME, CLAIM_COLUMNS, "C34", "C35")
    check_provenance(provenance, root, tier, current, window)
    check_claims(claims, root, tier)
    check_error_ledger(root, provenance, claims, tier, current)
    check_review_record(root, claims, tier, current)
    check_p_padj(root)

    locks = find_lock_files(root)
    if locks:
        add("OK", f"environment lock present: {', '.join(locks[:4])}", "C50")
    elif tier == 2:
        add("FAIL", "tier 2 requires a pinned environment (lock file / container / "
                    "conda env export)", "C51")
    elif tier == 1:
        add("WARN", "no environment lock file found", "C52")
    else:
        add("SKIP", "no environment lock found (tier 0)", "C53")

    if args.json:
        print(json.dumps(
            {"analysis_dir": str(root), "tier": tier,
             "framework_version_current": current,
             "findings": [{"level": l, "gate": gate_of(c), "section": CHECKS[c][1],
                           "check": c, "message": m} for l, c, m in findings],
             "failures": sum(1 for l, _, _ in findings if l == "FAIL")},
            indent=2))
    else:
        for level, check, message in sorted(
                findings, key=lambda f: (LEVEL_ORDER[f[0]],
                                         GATE_ORDER.index(gate_of(f[1])), f[1])):
            print(f"{level:<5} [{gate_of(check)}] {check}: {message}")
        fails = sum(1 for l, _, _ in findings if l == "FAIL")
        warns = sum(1 for l, _, _ in findings if l == "WARN")
        print("-" * 60)
        print("by gate (which kind of judgement is failing):")
        for gate in GATE_ORDER:
            g_fail = sum(1 for l, c, _ in findings if gate_of(c) == gate and l == "FAIL")
            g_warn = sum(1 for l, c, _ in findings if gate_of(c) == gate and l == "WARN")
            n_checks = sum(1 for c in CHECKS if gate_of(c) == gate)
            extra = ""
            if not n_checks:
                extra = "  (no mechanical check -- human checklist items only)"
            print(f"  {gate:<11} FAIL {g_fail}  WARN {g_warn}{extra}")
        print("-" * 60)
        print(f"RESULT: {fails} FAIL, {warns} WARN"
              f"{'  ->  gate NOT passed' if fails else '  ->  gate passed'}")
        if fails:
            print("Nothing ships with an unresolved FAIL. Fix, or declare the gap "
                  "explicitly in the deliverable.")
    return 1 if any(l == "FAIL" for l, _, _ in findings) else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical gate check for a bioinformatics analysis deliverable.")
    parser.add_argument("analysis_dir", nargs="?",
                        help="directory holding the contract and ledgers")
    parser.add_argument("--expect-tier", type=int, choices=[0, 1, 2], default=None,
                        help="fail the run if the contract declares a different tier")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--gate-map-check", action="store_true",
                        help="verify assets/gate-map.tsv against the checker's registry and exit")
    parser.add_argument("--write-gate-map", action="store_true",
                        help="regenerate assets/gate-map.tsv from the checker's registry")
    args = parser.parse_args()

    if args.write_gate_map:
        target = gate_map_path()
        target.write_text(render_gate_map(), encoding="utf-8", newline="\n")
        print(f"wrote {target} ({len(CHECKS)} checks)")
        return 0

    if args.gate_map_check:
        try:
            problems = gate_map_problems()
        except FrameworkError as exc:
            print(f"FRAMEWORK ERROR: {exc}")
            return 2
        for problem in problems:
            print(f"MISMATCH  {problem}")
        if problems:
            print(f"gate map OUT OF SYNC ({len(problems)} problem(s)); "
                  f"{len(CHECKS)} checks in the registry")
            return 2
        in_use = sorted({meta[0] for meta in CHECKS.values()})
        print(f"gate map OK: {len(CHECKS)} checks across {len(in_use)} gates "
              f"({', '.join(in_use)})")
        return 0

    if not args.analysis_dir:
        parser.error("analysis_dir is required unless --gate-map-check/--write-gate-map is used")

    try:
        problems = gate_map_problems()
    except FrameworkError as exc:
        print(f"FAIL  [framework] M01: {exc}")
        print("The checker classifies every finding by gate; without an intact gate map its "
              "output cannot be interpreted. Exit 2.")
        return 2
    if problems:
        print("FRAMEWORK ERROR  [framework] M01: the shipped gate map and the checker's "
              "registry disagree:")
        for problem in problems:
            print(f"  - {problem}")
        print("Run --gate-map-check, or --write-gate-map to regenerate. Exit 2.")
        return 2

    root = Path(args.analysis_dir).expanduser()
    if not root.is_dir():
        print(f"FAIL  [execution] M01: {root} is not a directory")
        return 1

    try:
        return report(args, root)
    except FrameworkError as exc:
        print(f"FRAMEWORK ERROR  [framework] M01: {exc}")
        return 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    sys.exit(main())
