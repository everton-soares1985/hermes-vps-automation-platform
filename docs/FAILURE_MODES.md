# Failure Modes and Recovery

| Failure | Detection | Safe response |
|---|---|---|
| Login/session expired | Missing expected page state or auth redirect | Stop writes, preserve evidence, request interactive renewal |
| CAPTCHA/checkpoint | Explicit detector or uncertain DOM state | Block run; never attempt automated bypass |
| Browser/CDP unavailable | systemd state and `/json/version` check | Restart only the affected browser service, then diagnose |
| Selector drift | No eligible elements plus changed page signature | Run diagnostic capture; update selector tests before writes |
| SQLite locked/corrupt | Read-only open or `PRAGMA quick_check` fails | Stop run, copy database, investigate writer ownership |
| Stale/missing report | Watchdog timestamp check | Alert once; inspect scheduler/service evidence |
| Resource pressure | Available-memory and disk thresholds | Skip heavy work, clean approved artifacts, scale if persistent |
| Model route unavailable | Non-zero role runner result or soft-failure marker | Use configured OmniRoute fallback or block with evidence |
| Model edits protected files | File-boundary gate | Reject iteration and preserve diff |
| Tests fail | Expected exit-code gate | Return bounded failure context to implementer |
| Reviewer evidence mismatch | SHA or schema gate | Reject review; never accept free-form approval |
| Duplicate alert storm | Failure-state hash | Suppress identical alert until state changes |
| Intentional pause | Disabled schedule or rest-day evidence | Treat as expected state, not outage |

## Known semantic failure

The audited Wellfound Saved runner can finish useful work and then return `1` when no additional candidate passes preflight. Recovery should not blindly retry, because that can duplicate work. Read the evidence counters first. A future contract should reserve separate exit codes for technical failure, candidate exhaustion, and partial success.
