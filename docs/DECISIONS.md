# Architecture Decisions

## ADR-001 — systemd owns persistent processes

**Decision:** browsers, gateways, and dashboards run as systemd user services.

**Why:** predictable lifecycle, restart policy, logs, ownership, and timer integration are more reliable than detached shells.

## ADR-002 — Hermes schedules wrappers, not business logic

**Decision:** Hermes cron jobs invoke small versioned shell wrappers.

**Why:** schedules remain readable while business logic stays testable in its own project. Wrappers also create an explicit authorization boundary for each action.

## ADR-003 — loopback first

**Decision:** dashboards, OmniRoute, CDP, and noVNC bind to loopback.

**Why:** the operator already has SSH access; a tunnel provides private access without maintaining another public authentication surface.

## ADR-004 — separate browser identities

**Decision:** each target platform owns its browser profile and CDP port.

**Why:** prevents session collision, accidental cross-target automation, and ambiguous browser ownership.

## ADR-005 — evidence beats chat memory

**Decision:** JSON and SQLite are the operational source of truth; Telegram is transport and notification.

**Why:** chat messages are convenient but not durable, queryable, or sufficient for idempotency.

## ADR-006 — deterministic controller over autonomous claims

**Decision:** models perform architect, implementer, and reviewer roles, but only the controller can transition state.

**Why:** model confidence is not proof. Completion requires bounded changes, test evidence, matching hashes, and independent review.

## ADR-007 — publish a sanitized platform repository

**Decision:** publish reusable code, templates, architecture, and verified aggregate evidence; keep production state private.

**Why:** the project should demonstrate engineering quality without exposing credentials, personal data, infrastructure coordinates, or authenticated sessions.
