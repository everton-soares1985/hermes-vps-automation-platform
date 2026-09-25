# Sanitized Live Audit — 2026-09-25

## Scope and method

This audit was performed read-only against the operational VPS. It inspected operating-system capacity, systemd user services and timers, loopback listeners, Docker health, Hermes scheduler metadata, recent execution records, and the autonomous builder test suite. Secret files, message content, cookies, private datasets, account identifiers, and raw application records were not copied.

## Host baseline

| Item | Observation |
|---|---|
| Operating system | Ubuntu 24.04 |
| CPU | 2 virtual CPUs |
| Memory | 11 GiB total; 6.7 GiB available during audit |
| Root filesystem | 193 GiB total; 171 GiB free; 12% used |
| Uptime | 8 weeks, 2 days |
| Hermes Agent | v0.19.0, installed from Git |
| Python used by Hermes | 3.11.15 |

The real hostname and public address are intentionally omitted.

## Service health

| Component | Audit result |
|---|---|
| Hermes Gateway | Active/running; result `success`; zero restarts; active since 2026-08-03 |
| OmniRoute | Docker container healthy; six-week uptime; loopback binding |
| Global Builder Radar panel | Active/running; result `success`; zero restarts |
| Wellfound browser | Active |
| InfoJobs browser | Active |
| LinkedIn browser | Inactive as designed outside a scheduled run |
| LinkedIn scheduler | Last run completed with exit code 0 |

Private dashboard, model gateway, browser CDP, and noVNC listeners were all bound to `127.0.0.1`.

## Hermes scheduler — 30-day window

| Job | Completed | Failed | Interpretation |
|---|---:|---:|---|
| VPS daily preflight | 31 | 0 | Healthy and quiet |
| Daily automation report | 30 | 0 | Healthy |
| Wellfound Apply daily | 30 | 0 | Healthy |
| Wellfound External Saved Cleaner | 31 | 0 | Healthy |
| LinkedIn Warmup watchdog | 15 | 0 | Healthy for scheduled days |
| Wellfound Saved daily | 2 | 29 | Exit-status semantics issue; see below |

InfoJobs Apply was intentionally disabled and therefore had no runs in this window.

## Wellfound Saved finding

The latest audited run recorded:

- 46 candidate save actions considered;
- 16 saves attempted;
- 16 saves confirmed;
- 0 failed save clicks;
- 0 apply clicks;
- 0 submissions;
- verified, hashed JSON evidence.

After those successful saves, the script stopped because no additional candidate passed preflight and returned exit code `1`. Hermes therefore recorded the process as failed. This is a real observability defect: the scheduler status and the business outcome disagree. The workflow remains bounded and its evidence is trustworthy, but the wrapper should eventually distinguish `completed_with_exhausted_candidates` from a technical failure.

## LinkedIn warm-up evidence

After a selector/click correction in September, five audited runs completed 104 profile visits with no blockers or reported errors. Likes remained disabled. The browser starts only for the scheduled run, and a separate watchdog validates timer state, report freshness, scheduler result, and SQLite integrity.

## Autonomous builder evidence

The production-host source tree passed all 15 controller tests during this audit. Coverage includes:

- distinct route validation;
- architect write boundaries;
- immutable specification protection;
- reviewer evidence/hash requirements;
- bounded feedback;
- runtime ignore rules;
- container ownership and workspace mount checks;
- soft OmniRoute failure conversion;
- source-root and workspace-root protections.

Two old smoke-test systemd units remain in a failed state. One stopped after reviewer rejection of a failing test; the other reached the maximum implementation iterations. Both are inactive historical test artifacts and do not affect production services. Their presence is useful evidence that gates stop invalid work rather than forcing success.

## Security observations

- SSH password authentication was disabled in the previous infrastructure audit.
- Private services were loopback-only.
- No unknown successful login was observed in the reviewed period.
- Internet background scans were rejected.
- Host firewall state and cloud-account billing/free-tier status were outside this repository audit and should be verified independently.

## Overall verdict

**Operational with documented exceptions.** The control plane, health reporting, apply/cleanup flows, private panel, and browser isolation were stable. The main corrective item is the Wellfound Saved exit-status mismatch. The autonomous builder is a validated prototype, not yet a production-default project generator.
