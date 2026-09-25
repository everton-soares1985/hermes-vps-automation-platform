# CONFIGURATION
# Executes commands without a shell. Output is persisted and hashed.
# Timeouts terminate the process group on POSIX systems.

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import signal
import subprocess
from typing import Sequence

from .evidence import CommandEvidence, redact, sha256_file


LOGGER = logging.getLogger(__name__)


def run_command(
    argv: Sequence[str],
    cwd: Path,
    evidence_dir: Path,
    label: str,
    timeout: int,
    env: dict[str, str] | None = None,
) -> CommandEvidence:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = evidence_dir / f"{label}.stdout.log"
    stderr_path = evidence_dir / f"{label}.stderr.log"
    started = datetime.now(timezone.utc)
    LOGGER.info("command_started", extra={"label": label, "cwd": str(cwd), "argv": list(argv)})
    popen_kwargs: dict[str, object] = {
        "cwd": cwd,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "env": env,
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(list(argv), **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        stdout, stderr = process.communicate(timeout=30)
        exit_code = 124
        stderr = f"{stderr}\ncontroller_timeout={timeout}\n"
    stdout_path.write_text(redact(stdout), encoding="utf-8")
    stderr_path.write_text(redact(stderr), encoding="utf-8")
    finished = datetime.now(timezone.utc)
    LOGGER.info("command_finished", extra={"label": label, "exit_code": exit_code})
    return CommandEvidence(
        command=" ".join(argv),
        cwd=str(cwd),
        started_utc=started.isoformat(),
        finished_utc=finished.isoformat(),
        exit_code=exit_code,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        stdout_sha256=sha256_file(stdout_path),
        stderr_sha256=sha256_file(stderr_path),
    )
