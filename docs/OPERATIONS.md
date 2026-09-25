# Operations

## Deployment assumptions

- Ubuntu or another systemd-based Linux distribution;
- Python 3.11 or newer;
- Docker for isolated builder commands and the OmniRoute container;
- Hermes Agent installed in its own virtual environment;
- private services bound to loopback;
- secrets injected from an ignored environment file or a secret manager.

## Suggested filesystem layout

```text
/opt/hermes/                         Hermes installation
/srv/hermes-builder/inputs/          Approved source inputs
/srv/hermes-builder/workspaces/      Ephemeral project workspaces
/srv/automation/<workload>/          Independent production workloads
/var/lib/hermes-builder/state/       Controller state and evidence
~/.config/systemd/user/              User service/timer definitions
```

Use a dedicated Linux account. Do not reuse a privileged root session for routine automation.

## Builder setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp config.example.toml config.toml
```

Edit the ignored `config.toml` with deployment paths. Export the OmniRoute credential through the service environment; never write it into either example configuration.

Build the optional command sandbox:

```bash
docker build -t hermes-builder-runtime:0.2.0 .
```

Validate before the first real project:

```bash
python -m unittest discover -s tests -v
hermes-builder --config config.toml run \
  --source /srv/hermes-builder/inputs/smoke-event-counter \
  --goal-file smoke_fixture/GOAL_INPUT.md \
  --project-name smoke-event-counter
```

## Scheduling pattern

Hermes cron entries should invoke a wrapper in `ops/scripts/`. The wrapper sets a strict shell mode, loads only required environment variables, changes to an explicit workload directory, and uses an action-specific confirmation flag.

The audited deployment used this sequence in its local timezone:

| Time | Job | Intent |
|---|---|---|
| 10:20 | VPS preflight | Quiet infrastructure check |
| 11:00 | Wellfound Saved | Bounded discovery/save run |
| 12:00 | External Saved Cleaner | Cleanup-only pass |
| 15:00 | Wellfound Apply | Bounded authorized application run |
| 18:30 | InfoJobs rotation | Present but intentionally paused |
| 21:00 Mon–Sat | LinkedIn watchdog | Validate timer/report/database health |
| 22:00 | Daily report | Summarize official evidence |

These are reference values, not a universal schedule. Stagger CPU- or browser-heavy workloads and keep browser profile ownership unambiguous.

## systemd pattern

Long-running browsers and panels belong to systemd, not to a detached interactive shell. Use restart policies for daemons, but use bounded retries for externally visible automation. An on-demand browser should start with its scheduler and stop when the run finishes.

Useful read-only checks:

```bash
systemctl --user --failed
systemctl --user status hermes-gateway.service
systemctl --user list-timers --all
docker ps --format '{{.Names}} {{.Status}}'
ss -ltn
```

## Evidence and reporting

Treat a workflow as complete only when its evidence file is present, parseable, current, and internally consistent. Exit code alone is not sufficient for browser automation: a workflow can perform useful actions and later terminate on an exhausted candidate set. The reverse is also possible—a process can exit cleanly without completing its business target.

The public `daily_automation_report.sh` reads JSON and SQLite in read-only mode and prints a sanitized summary. Configure its root paths through environment variables.

## Recovery order

1. Read the most recent evidence and systemd result.
2. Verify the browser service and CDP endpoint.
3. Verify SQLite with `PRAGMA quick_check` in read-only mode.
4. Confirm the failure is not an intentional pause, rest day, or exhausted candidate set.
5. Restart only the affected service.
6. Re-run in dry-run or diagnostic mode before allowing an external write.
7. Preserve the failed evidence; do not overwrite it during recovery.

## SSH tunnel pattern

Keep dashboards on loopback and forward only the required port:

```bash
ssh -N \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -L LOCAL_PORT:127.0.0.1:REMOTE_PORT \
  user@example-host
```

Use your SSH config or key agent rather than publishing key paths in scripts or documentation.
