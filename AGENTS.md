# Agent Instructions

## Mission

Maintain an evidence-driven, least-privilege VPS automation platform. Prefer
deterministic validation over model confidence.

## Required checks

Before changing code:

1. Read `README.md`, `docs/ARCHITECTURE.md`, and `docs/SECURITY_MODEL.md`.
2. Inspect existing modules and scripts before adding a new abstraction.
3. Confirm the change does not expose production state or expand an external
   write permission.

After changing code:

```bash
python -m unittest discover -s tests -v
```

Run the GrowthTech GitHub Publisher audit/check before publication.

## Non-negotiable rules

- Never commit credentials, cookies, chat IDs, host addresses, browser
  profiles, real databases, or raw personal records.
- Never let a model advance builder state without deterministic gates.
- Never weaken tests, acceptance criteria, protected roots, or resource limits
  merely to make a run pass.
- Keep browser identities and CDP ports isolated by workload.
- Use structured evidence for background jobs; do not rely on chat history as
  operational memory.
- Preserve failed evidence during recovery.
- Keep external writes explicit, bounded, and independently pausable.
