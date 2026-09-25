# CONFIGURATION
# Invokes Hermes one-shot with an explicit OmniRoute combo per role.
# The Hermes profile holds its API key; this module never reads or logs it.

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from .config import BuilderConfig
from .evidence import CommandEvidence
from .process import run_command


LOGGER = logging.getLogger(__name__)

_HERMES_FAILURE_MARKERS = (
    "API call failed after",
    "all upstream accounts are inactive",
)


@dataclass(frozen=True)
class RoleResult:
    role: str
    route: str
    evidence: CommandEvidence
    usage_path: Path


def _container_is_owned_by_builder(info: dict, config: BuilderConfig) -> bool:
    labels = ((info.get("Config") or {}).get("Labels") or {})
    if labels.get("hermes-agent") != "1" or labels.get("hermes-profile") != config.runtime.profile:
        return False
    workspace_root = config.runtime.workspace_root.resolve()
    for mount in info.get("Mounts") or []:
        if mount.get("Type") != "bind" or not mount.get("Source"):
            continue
        source = Path(mount["Source"]).resolve()
        if source == workspace_root or workspace_root in source.parents:
            return True
    return False


def _cleanup_owned_builder_containers(config: BuilderConfig) -> tuple[str, ...]:
    docker = shutil.which("docker")
    if os.name != "posix" or docker is None:
        return ()
    listed = subprocess.run(
        [
            docker,
            "ps",
            "-aq",
            "--filter",
            "label=hermes-agent=1",
            "--filter",
            f"label=hermes-profile={config.runtime.profile}",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=30,
    )
    removed: list[str] = []
    for container_id in listed.stdout.split():
        inspected = subprocess.run(
            [docker, "inspect", container_id],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=30,
        )
        if inspected.returncode != 0:
            continue
        try:
            payload = json.loads(inspected.stdout)[0]
        except (json.JSONDecodeError, IndexError, TypeError):
            continue
        if not _container_is_owned_by_builder(payload, config):
            continue
        deleted = subprocess.run(
            [docker, "rm", "-f", container_id],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=30,
        )
        if deleted.returncode == 0:
            removed.append(container_id)
    if removed:
        LOGGER.info("builder_sandboxes_removed", extra={"container_ids": removed})
    return tuple(removed)


def _normalize_hermes_result(record: CommandEvidence) -> CommandEvidence:
    """Turn Hermes/OmniRoute soft failures into a real non-zero controller result."""
    if record.exit_code != 0:
        return record
    output = ""
    for path_value in (record.stdout_path, record.stderr_path):
        path = Path(path_value)
        if path.exists():
            output += path.read_text(encoding="utf-8", errors="replace")
    if any(marker in output for marker in _HERMES_FAILURE_MARKERS):
        LOGGER.error("hermes_soft_failure_detected")
        return replace(record, exit_code=75)
    return record


def run_role(
    config: BuilderConfig,
    role: str,
    route: str,
    prompt: str,
    workspace: Path,
    evidence_dir: Path,
    iteration: int,
) -> RoleResult:
    invocation_id = f"{role}-{iteration}-{uuid.uuid4().hex}"
    workspace_root = workspace.resolve()
    runtime_contract = f"""RUNTIME ISOLATION CONTRACT
Invocation ID: {invocation_id}
Controller host workspace: {workspace_root}
Agent-visible workspace: /workspace

This is a fresh invocation. Ignore every remembered, cached, or previously mentioned
workspace path. The host path is intentionally hidden inside the Docker sandbox. Before
any other action, run pwd and verify it is exactly /workspace. All reads and writes MUST
stay below /workspace and use absolute /workspace paths. If pwd differs, stop and report
the mismatch. Never look for the controller host path from inside Docker.

"""
    usage_path = evidence_dir / f"{role}-{iteration}.usage.json"
    argv = [
        str(config.runtime.hermes_bin),
        "-p",
        config.runtime.profile,
        "-m",
        route,
        "--provider",
        "custom",
        "--skills",
        "hermes-autonomous-builder",
        "--toolsets",
        "terminal,file,code_execution",
        "--usage-file",
        str(usage_path),
        "-z",
        runtime_contract + prompt,
    ]
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("HERMES_SESSION_") or key == "HERMES_UI_SESSION_ID":
            environment.pop(key, None)
    environment["HERMES_BUILDER_ROLE"] = role
    environment["TERMINAL_ENV"] = "docker"
    environment["TERMINAL_CWD"] = str(workspace_root)
    environment["TERMINAL_DOCKER_IMAGE"] = "hermes-builder-runtime:0.1.0"
    environment["TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE"] = "true"
    environment["TERMINAL_DOCKER_RUN_AS_HOST_USER"] = "true"
    environment["TERMINAL_CONTAINER_PERSISTENT"] = "false"
    environment["TERMINAL_DOCKER_PERSIST_ACROSS_PROCESSES"] = "false"
    _cleanup_owned_builder_containers(config)
    try:
        record = run_command(
            argv,
            cwd=workspace,
            evidence_dir=evidence_dir,
            label=f"{role}-{iteration}",
            timeout=config.runtime.timeout_seconds,
            env=environment,
        )
        record = _normalize_hermes_result(record)
    finally:
        _cleanup_owned_builder_containers(config)
    if usage_path.exists():
        try:
            json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid Hermes usage report: {exc}") from exc
    return RoleResult(role=role, route=route, evidence=record, usage_path=usage_path)
