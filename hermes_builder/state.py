# CONFIGURATION
# Append-only state lives below runtime.state_root/runs/<run_id>.
# State transitions are validated locally and never delegated to an LLM.

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path


class Phase(StrEnum):
    CREATED = "CREATED"
    ARCHITECTING = "ARCHITECTING"
    PLAN_READY = "PLAN_READY"
    IMPLEMENTING = "IMPLEMENTING"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFYING = "VERIFYING"
    REVIEWING = "REVIEWING"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[Phase, set[Phase]] = {
    Phase.CREATED: {Phase.ARCHITECTING, Phase.FAILED},
    Phase.ARCHITECTING: {Phase.PLAN_READY, Phase.FAILED},
    Phase.PLAN_READY: {Phase.IMPLEMENTING, Phase.FAILED},
    Phase.IMPLEMENTING: {Phase.IMPLEMENTED, Phase.FAILED},
    Phase.IMPLEMENTED: {Phase.VERIFYING, Phase.FAILED},
    Phase.VERIFYING: {Phase.REVIEWING, Phase.CHANGES_REQUESTED, Phase.FAILED},
    Phase.REVIEWING: {Phase.APPROVED, Phase.CHANGES_REQUESTED, Phase.FAILED},
    Phase.CHANGES_REQUESTED: {Phase.IMPLEMENTING, Phase.BLOCKED, Phase.FAILED},
    Phase.APPROVED: set(),
    Phase.BLOCKED: set(),
    Phase.FAILED: set(),
}


@dataclass
class RunState:
    run_id: str
    project_id: str
    source_path: str
    workspace_path: str
    goal_sha256: str
    phase: Phase
    iteration: int = 0
    current_git_sha: str = ""
    reason: str = ""


class StateStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "state.json"
        self.events_path = run_dir / "events.jsonl"
        run_dir.mkdir(parents=True, exist_ok=False)

    @classmethod
    def open(cls, run_dir: Path) -> "StateStore":
        instance = cls.__new__(cls)
        instance.run_dir = run_dir
        instance.state_path = run_dir / "state.json"
        instance.events_path = run_dir / "events.jsonl"
        return instance

    def save_initial(self, state: RunState) -> None:
        if self.state_path.exists():
            raise FileExistsError(self.state_path)
        self._write_state(state)
        self._append_event("RUN_CREATED", state)

    def load(self) -> RunState:
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        raw["phase"] = Phase(raw["phase"])
        return RunState(**raw)

    def transition(self, target: Phase, reason: str = "") -> RunState:
        state = self.load()
        if target not in ALLOWED_TRANSITIONS[state.phase]:
            raise ValueError(f"invalid transition: {state.phase} -> {target}")
        previous = state.phase
        state.phase = target
        state.reason = reason
        self._write_state(state)
        self._append_event("STATE_TRANSITION", state, {"from": previous, "to": target})
        return state

    def update(self, **changes: object) -> RunState:
        state = self.load()
        for key, value in changes.items():
            if not hasattr(state, key):
                raise AttributeError(key)
            setattr(state, key, value)
        self._write_state(state)
        self._append_event("STATE_UPDATED", state, {"fields": sorted(changes)})
        return state

    def _write_state(self, state: RunState) -> None:
        payload = asdict(state)
        payload["phase"] = state.phase.value
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)

    def _append_event(self, event: str, state: RunState, extra: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "run_id": state.run_id,
            "phase": state.phase.value,
        }
        if extra:
            payload.update(extra)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
