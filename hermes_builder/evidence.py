# CONFIGURATION
# Evidence is append-only JSONL plus immutable JSON artifacts.
# Secret-like values are redacted before persistence.

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


SECRET_PATTERN = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+\-/=]{16,}|(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+)"
)


@dataclass(frozen=True)
class CommandEvidence:
    command: str
    cwd: str
    started_utc: str
    finished_utc: str
    exit_code: int
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact(text: str) -> str:
    return SECRET_PATTERN.sub("<redacted>", text)


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def command_evidence_to_dict(record: CommandEvidence) -> dict[str, object]:
    return asdict(record)


def tree_manifest(root: Path, excluded_names: set[str] | None = None) -> dict[str, dict[str, int | str]]:
    excluded = excluded_names or {".git", ".builder-runtime", "__pycache__"}
    manifest: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts) or not path.is_file():
            continue
        manifest[relative.as_posix()] = {"sha256": sha256_file(path), "size": path.stat().st_size}
    return manifest


def manifest_delta(
    before: dict[str, dict[str, int | str]],
    after: dict[str, dict[str, int | str]],
) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    return {
        "added": sorted(after_keys - before_keys),
        "deleted": sorted(before_keys - after_keys),
        "modified": sorted(key for key in before_keys & after_keys if before[key] != after[key]),
    }
