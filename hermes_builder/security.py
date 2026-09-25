# CONFIGURATION
# Paths are resolved before any copy or subprocess execution.
# Protected roots always win over allowed roots.

from __future__ import annotations

from pathlib import Path

from .config import SecurityConfig


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_source_path(path: Path, config: SecurityConfig) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"source is not a directory: {resolved}")
    protected = [root.expanduser().resolve(strict=False) for root in config.protected_roots]
    if any(is_relative_to(resolved, root) or is_relative_to(root, resolved) for root in protected):
        raise PermissionError(f"source intersects a protected root: {resolved}")
    allowed = [root.expanduser().resolve(strict=False) for root in config.allowed_source_roots]
    if not any(is_relative_to(resolved, root) for root in allowed):
        raise PermissionError(f"source is outside allowed roots: {resolved}")
    validate_no_escaping_symlinks(resolved)
    return resolved


def validate_no_escaping_symlinks(root: Path) -> None:
    """Reject links whose resolved target escapes the source tree."""
    resolved_root = root.resolve(strict=True)
    for candidate in root.rglob("*"):
        if not candidate.is_symlink():
            continue
        try:
            target = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PermissionError(f"broken symlink in source: {candidate}") from exc
        if not is_relative_to(target, resolved_root):
            raise PermissionError(f"symlink escapes source root: {candidate} -> {target}")


def validate_workspace_path(path: Path, workspace_root: Path) -> Path:
    root = workspace_root.expanduser().resolve(strict=False)
    resolved = path.expanduser().resolve(strict=False)
    if resolved == root or not is_relative_to(resolved, root):
        raise PermissionError(f"unsafe workspace path: {resolved}")
    return resolved
