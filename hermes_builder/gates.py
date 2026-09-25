# CONFIGURATION
# Deterministic gates validate scope, test exit codes and reviewer JSON.
# No natural-language assertion can bypass a failed gate.

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .evidence import CommandEvidence


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: tuple[str, ...]


def validate_architect_delta(delta: dict[str, list[str]]) -> GateResult:
    changed = set(delta["added"] + delta["modified"] + delta["deleted"])
    allowed = {"specs/FEATURE_SPEC.md", "specs/IMPLEMENTATION_PLAN.md", "specs/TASKS.md"}
    reasons = []
    unexpected = sorted(changed - allowed)
    if unexpected:
        reasons.append(f"architect changed forbidden files: {unexpected}")
    missing = sorted(allowed - changed)
    if missing:
        reasons.append(f"architect did not produce required files: {missing}")
    return GateResult(not reasons, tuple(reasons))


def validate_change_limits(delta: dict[str, list[str]], root: Path, max_files: int, max_bytes: int) -> GateResult:
    changed = set(delta["added"] + delta["modified"] + delta["deleted"])
    reasons = []
    if len(changed) > max_files:
        reasons.append(f"changed file count {len(changed)} exceeds {max_files}")
    byte_total = sum((root / name).stat().st_size for name in changed if (root / name).is_file())
    if byte_total > max_bytes:
        reasons.append(f"changed bytes {byte_total} exceeds {max_bytes}")
    forbidden = sorted(name for name in changed if name == ".env" or name.endswith((".key", ".pem")))
    if forbidden:
        reasons.append(f"secret-like files changed: {forbidden}")
    return GateResult(not reasons, tuple(reasons))


def validate_implementer_delta(delta: dict[str, list[str]]) -> GateResult:
    changed = set(delta["added"] + delta["modified"] + delta["deleted"])
    protected_prefixes = ("specs/", ".specify/", ".agents/")
    forbidden = sorted(
        name
        for name in changed
        if name in {"GOAL.md", "AGENTS.md", "AGENTS.project.md"} or name.startswith(protected_prefixes)
    )
    reasons = (f"implementer changed protected planning/policy files: {forbidden}",) if forbidden else ()
    return GateResult(not reasons, reasons)


def validate_reviewer_delta(delta: dict[str, list[str]]) -> GateResult:
    changed = set(delta["added"] + delta["modified"] + delta["deleted"])
    unexpected = sorted(changed - {"REVIEW.json"})
    reasons = (f"reviewer changed files other than REVIEW.json: {unexpected}",) if unexpected else ()
    if "REVIEW.json" not in changed:
        reasons += ("reviewer did not write REVIEW.json",)
    return GateResult(not reasons, reasons)


def validate_tests(records: Iterable[CommandEvidence]) -> GateResult:
    records = tuple(records)
    reasons = []
    if not records:
        reasons.append("no test commands executed")
    failed = [record.command for record in records if record.exit_code != 0]
    if failed:
        reasons.append(f"tests failed: {failed}")
    return GateResult(not reasons, tuple(reasons))


def validate_review(path: Path, expected_git_sha: str) -> GateResult:
    reasons = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return GateResult(False, (f"invalid REVIEW.json: {exc}",))
    if payload.get("verdict") != "APPROVED":
        reasons.append("reviewer verdict is not APPROVED")
    if payload.get("reviewed_git_sha") != expected_git_sha:
        reasons.append("reviewed SHA does not match tested SHA")
    if payload.get("critical_findings"):
        reasons.append("critical findings remain")
    if payload.get("high_findings"):
        reasons.append("high findings remain")
    criteria = payload.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        reasons.append("acceptance criteria evidence is missing")
    elif any(item.get("status") != "PASS" for item in criteria if isinstance(item, dict)):
        reasons.append("not every acceptance criterion passed")
    tests = payload.get("test_commands")
    if not isinstance(tests, list) or not tests:
        reasons.append("reviewer did not execute tests")
    elif any(
        item.get("exit_code") != item.get("expected_exit_code", 0)
        for item in tests
        if isinstance(item, dict)
    ):
        reasons.append("reviewer reported a test with an unexpected exit code")
    return GateResult(not reasons, tuple(reasons))
