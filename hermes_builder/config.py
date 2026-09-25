# CONFIGURATION
# Reads a TOML file; secrets remain in the Hermes profile environment.
# Required sections: runtime, routes, limits, gates, security.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class RuntimeConfig:
    hermes_bin: Path
    profile: str
    state_root: Path
    workspace_root: Path
    timeout_seconds: int
    specify_bin: Path


@dataclass(frozen=True)
class RoutesConfig:
    architect: str
    implementer: str
    reviewer: str


@dataclass(frozen=True)
class LimitsConfig:
    max_iterations: int
    max_changed_files: int
    max_changed_bytes: int
    reviewer_retries: int


@dataclass(frozen=True)
class GatesConfig:
    test_commands: tuple[str, ...]
    require_clean_test_exit: bool
    require_reviewer_approval: bool


@dataclass(frozen=True)
class SecurityConfig:
    allowed_source_roots: tuple[Path, ...]
    protected_roots: tuple[Path, ...]


@dataclass(frozen=True)
class BuilderConfig:
    runtime: RuntimeConfig
    routes: RoutesConfig
    limits: LimitsConfig
    gates: GatesConfig
    security: SecurityConfig


def load_config(path: Path) -> BuilderConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    runtime = data["runtime"]
    routes = data["routes"]
    limits = data["limits"]
    gates = data["gates"]
    security = data["security"]
    result = BuilderConfig(
        runtime=RuntimeConfig(
            hermes_bin=Path(runtime["hermes_bin"]),
            profile=str(runtime["profile"]),
            state_root=Path(runtime["state_root"]),
            workspace_root=Path(runtime["workspace_root"]),
            timeout_seconds=int(runtime["timeout_seconds"]),
            specify_bin=Path(runtime["specify_bin"]),
        ),
        routes=RoutesConfig(**routes),
        limits=LimitsConfig(**limits),
        gates=GatesConfig(
            test_commands=tuple(gates["test_commands"]),
            require_clean_test_exit=bool(gates["require_clean_test_exit"]),
            require_reviewer_approval=bool(gates["require_reviewer_approval"]),
        ),
        security=SecurityConfig(
            allowed_source_roots=tuple(Path(p) for p in security["allowed_source_roots"]),
            protected_roots=tuple(Path(p) for p in security["protected_roots"]),
        ),
    )
    _validate(result)
    return result


def _validate(config: BuilderConfig) -> None:
    if config.limits.max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if config.limits.reviewer_retries < 1:
        raise ValueError("reviewer_retries must be positive")
    if config.runtime.timeout_seconds < 30:
        raise ValueError("timeout_seconds must be at least 30")
    if len({config.routes.architect, config.routes.implementer, config.routes.reviewer}) != 3:
        raise ValueError("the three role routes must be distinct")
    if not config.security.allowed_source_roots:
        raise ValueError("at least one allowed source root is required")
