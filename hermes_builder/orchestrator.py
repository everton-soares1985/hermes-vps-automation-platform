# CONFIGURATION
# Sequential V0 orchestrator: architect -> implementer -> deterministic gates -> reviewer.
# Source projects are copied into an isolated run workspace; production projects are denied.

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil
import subprocess
import uuid

from .config import BuilderConfig
from .evidence import CommandEvidence, append_jsonl, command_evidence_to_dict, manifest_delta, tree_manifest, write_json_atomic
from .gates import (
    validate_architect_delta,
    validate_change_limits,
    validate_implementer_delta,
    validate_review,
    validate_reviewer_delta,
    validate_tests,
)
from .process import run_command
from .prompts import architect_prompt, implementer_prompt, reviewer_prompt
from .role_runner import run_role
from .security import validate_source_path, validate_workspace_path
from .state import ALLOWED_TRANSITIONS, Phase, RunState, StateStore


LOGGER = logging.getLogger(__name__)


class BuildBlocked(RuntimeError):
    pass


_RUNTIME_GITIGNORE_MARKER = "# Hermes Builder runtime hygiene"
_RUNTIME_GITIGNORE_PATTERNS = (
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".coverage",
    ".builder-runtime/",
)


def _slug(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return "-".join(part for part in cleaned.split("-") if part)[:48] or "project"


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, text=True, encoding="utf-8", errors="replace", capture_output=True, check=True
    )
    return completed.stdout.strip()


def _ensure_runtime_gitignore(workspace: Path) -> None:
    path = workspace / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _RUNTIME_GITIGNORE_MARKER in existing:
        return
    block = "\n".join((_RUNTIME_GITIGNORE_MARKER, *_RUNTIME_GITIGNORE_PATTERNS)) + "\n"
    separator = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + separator + block, encoding="utf-8")


def _initialize_workspace(source: Path, workspace: Path, specify_bin: Path) -> None:
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", ".builder-runtime", "__pycache__"))
    source_policy = workspace / "AGENTS.md"
    if source_policy.exists():
        source_policy.replace(workspace / "AGENTS.project.md")
    controller_policy = Path(__file__).resolve().parents[1] / "AGENTS.md"
    shutil.copy2(controller_policy, source_policy)
    _git(workspace, "init", "-b", "main")
    _git(workspace, "config", "user.name", "Hermes Builder")
    _git(workspace, "config", "user.email", "builder@localhost")
    completed = subprocess.run(
        [
            str(specify_bin),
            "init",
            "--here",
            "--force",
            "--integration",
            "codex",
            "--integration-options=--skills",
            "--script",
            "sh",
            "--ignore-agent-tools",
        ],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=180,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Spec Kit initialization failed: {completed.stderr[-1000:]}")
    _ensure_runtime_gitignore(workspace)
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "-m", "builder: isolated input snapshot")


def _commit(workspace: Path, message: str) -> str:
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "--allow-empty", "-m", message)
    return _git(workspace, "rev-parse", "HEAD")


def _block(store: StateStore, reasons: list[str]) -> None:
    reason = "; ".join(reasons)
    current = store.load().phase
    if Phase.BLOCKED in ALLOWED_TRANSITIONS[current]:
        store.transition(Phase.BLOCKED, reason)
    else:
        store.transition(Phase.FAILED, reason)
    raise BuildBlocked(reason)


def _controller_test_feedback(command_records: list[CommandEvidence]) -> dict[str, object]:
    """Build bounded, actionable feedback from deterministic controller tests."""
    failures: list[dict[str, object]] = []
    for record in command_records:
        if record.exit_code == 0:
            continue
        stderr = Path(record.stderr_path).read_text(encoding="utf-8", errors="replace")
        stdout = Path(record.stdout_path).read_text(encoding="utf-8", errors="replace")
        failures.append(
            {
                "command": record.command,
                "exit_code": record.exit_code,
                "stderr_tail": stderr[-6000:],
                "stdout_tail": stdout[-3000:],
            }
        )
    return {
        "source": "controller",
        "instruction": "Correct only the verified failures below, then rerun the project tests.",
        "failures": failures,
    }


def run_build(config: BuilderConfig, source_path: Path, goal_text: str, project_name: str | None = None) -> RunState:
    source = validate_source_path(source_path, config.security)
    project_id = _slug(project_name or source.name)
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_dir = config.runtime.state_root / "runs" / run_id
    workspace = validate_workspace_path(config.runtime.workspace_root / project_id / run_id / "work", config.runtime.workspace_root)
    workspace.parent.mkdir(parents=True, exist_ok=False)
    _initialize_workspace(source, workspace, config.runtime.specify_bin)
    goal_path = workspace / "GOAL.md"
    goal_path.write_text(goal_text.rstrip() + "\n", encoding="utf-8")
    _commit(workspace, "builder: record immutable goal")
    goal_sha = hashlib.sha256(goal_path.read_bytes()).hexdigest()
    store = StateStore(run_dir)
    state = RunState(
        run_id=run_id,
        project_id=project_id,
        source_path=str(source),
        workspace_path=str(workspace),
        goal_sha256=goal_sha,
        phase=Phase.CREATED,
        current_git_sha=_git(workspace, "rev-parse", "HEAD"),
    )
    store.save_initial(state)
    evidence_dir = run_dir / "evidence"
    command_records = []

    try:
        store.transition(Phase.ARCHITECTING)
        before = tree_manifest(workspace)
        architect = run_role(
            config, "architect", config.routes.architect, architect_prompt(goal_path), workspace, evidence_dir, 0
        )
        append_jsonl(run_dir / "commands.jsonl", command_evidence_to_dict(architect.evidence))
        if architect.evidence.exit_code != 0:
            _block(store, ["architect invocation failed"])
        after = tree_manifest(workspace)
        architect_delta = manifest_delta(before, after)
        write_json_atomic(evidence_dir / "architect-delta.json", architect_delta)
        gate = validate_architect_delta(architect_delta)
        if not gate.passed:
            _block(store, list(gate.reasons))
        plan_sha = _commit(workspace, "builder: approve architecture artifacts")
        store.update(current_git_sha=plan_sha)
        store.transition(Phase.PLAN_READY)

        for iteration in range(1, config.limits.max_iterations + 1):
            store.update(iteration=iteration)
            store.transition(Phase.IMPLEMENTING)
            before = tree_manifest(workspace)
            feedback = workspace / "REVIEW_FEEDBACK.json"
            result = run_role(
                config,
                "implementer",
                config.routes.implementer,
                implementer_prompt(iteration, feedback if feedback.exists() else None),
                workspace,
                evidence_dir,
                iteration,
            )
            append_jsonl(run_dir / "commands.jsonl", command_evidence_to_dict(result.evidence))
            if result.evidence.exit_code != 0:
                _block(store, ["implementer invocation failed"])
            after = tree_manifest(workspace)
            delta = manifest_delta(before, after)
            write_json_atomic(evidence_dir / f"implementer-delta-{iteration}.json", delta)
            limits_gate = validate_change_limits(
                delta, workspace, config.limits.max_changed_files, config.limits.max_changed_bytes
            )
            implementer_gate = validate_implementer_delta(delta)
            if not limits_gate.passed or not implementer_gate.passed:
                _block(store, list(limits_gate.reasons + implementer_gate.reasons))
            implementation_sha = _commit(workspace, f"builder: implementation iteration {iteration}")
            store.update(current_git_sha=implementation_sha)
            store.transition(Phase.IMPLEMENTED)
            store.transition(Phase.VERIFYING)

            command_records = []
            for index, command in enumerate(config.gates.test_commands, start=1):
                record = run_command(
                    ["bash", "-lc", command],
                    workspace,
                    evidence_dir,
                    f"controller-test-{iteration}-{index}",
                    config.runtime.timeout_seconds,
                )
                command_records.append(record)
                append_jsonl(run_dir / "commands.jsonl", command_evidence_to_dict(record))
            tests_gate = validate_tests(command_records)
            if not tests_gate.passed:
                feedback.write_text(
                    json.dumps(_controller_test_feedback(command_records), indent=2) + "\n",
                    encoding="utf-8",
                )
                store.transition(Phase.CHANGES_REQUESTED, "; ".join(tests_gate.reasons))
                continue

            tested_sha = _git(workspace, "rev-parse", "HEAD")
            evidence_summary = {
                "run_id": run_id,
                "tested_git_sha": tested_sha,
                "goal_sha256": goal_sha,
                "commands": [command_evidence_to_dict(record) for record in command_records],
                "implementation_delta": delta,
            }
            write_json_atomic(workspace / "CONTROLLER_EVIDENCE.json", evidence_summary)
            store.transition(Phase.REVIEWING)
            valid_changes_requested = False
            review_failures: list[str] = []
            for review_attempt in range(1, config.limits.reviewer_retries + 1):
                reviewer_root = validate_workspace_path(
                    config.runtime.workspace_root
                    / project_id
                    / run_id
                    / f"review-{iteration}-{review_attempt}",
                    config.runtime.workspace_root,
                )
                shutil.copytree(
                    workspace,
                    reviewer_root,
                    ignore=shutil.ignore_patterns(".git", ".builder-runtime", "__pycache__"),
                )
                reviewer_before = tree_manifest(reviewer_root)
                review = run_role(
                    config,
                    "reviewer",
                    config.routes.reviewer,
                    reviewer_prompt(tested_sha, reviewer_root / "CONTROLLER_EVIDENCE.json"),
                    reviewer_root,
                    evidence_dir,
                    iteration * 10 + review_attempt,
                )
                append_jsonl(run_dir / "commands.jsonl", command_evidence_to_dict(review.evidence))
                reviewer_after = tree_manifest(reviewer_root)
                reviewer_delta = manifest_delta(reviewer_before, reviewer_after)
                write_json_atomic(
                    evidence_dir / f"reviewer-delta-{iteration}-{review_attempt}.json", reviewer_delta
                )
                reviewer_scope_gate = validate_reviewer_delta(reviewer_delta)
                review_path = reviewer_root / "REVIEW.json"
                review_gate = validate_review(review_path, tested_sha)
                if review.evidence.exit_code == 0 and reviewer_scope_gate.passed and review_gate.passed:
                    shutil.copy2(review_path, workspace / "REVIEW.json")
                    final_sha = _commit(workspace, "builder: attach independent approval")
                    store.update(current_git_sha=final_sha)
                    return store.transition(Phase.APPROVED, "all deterministic gates passed")

                reasons = list(review_gate.reasons + reviewer_scope_gate.reasons)
                if review.evidence.exit_code != 0:
                    reasons.append("reviewer invocation failed")
                review_failures.extend(f"attempt {review_attempt}: {reason}" for reason in reasons)
                if review.evidence.exit_code == 0 and reviewer_scope_gate.passed and review_path.exists():
                    try:
                        review_payload = json.loads(review_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        review_payload = {}
                    if review_payload.get("verdict") == "CHANGES_REQUESTED":
                        shutil.copy2(review_path, feedback)
                        valid_changes_requested = True
                        break

            if valid_changes_requested:
                store.transition(Phase.CHANGES_REQUESTED, "; ".join(review_failures))
                continue
            _block(store, ["reviewer failed to produce a valid review", *review_failures])

        store.transition(Phase.BLOCKED, "maximum implementation iterations exhausted")
        return store.load()
    except BuildBlocked:
        return store.load()
    except Exception as exc:
        LOGGER.exception("build_failed", extra={"run_id": run_id})
        current = store.load().phase
        if current not in {Phase.APPROVED, Phase.BLOCKED, Phase.FAILED}:
            store.transition(Phase.FAILED, f"{type(exc).__name__}: {exc}")
        return store.load()
