# Contributing

Contributions that improve portability, evidence quality, failure semantics,
tests, or security boundaries are welcome.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Pull request requirements

1. Keep production credentials and personal data out of commits and fixtures.
2. Preserve the deterministic controller: models may propose work but may not
   self-approve or bypass gates.
3. Add or update tests for behavioral changes.
4. Keep operational actions bounded, idempotent where possible, and explicit
   about external writes.
5. Update documentation and `CHANGELOG.md` when behavior changes.
6. Run the test suite and the GitHub Publisher checks before opening a PR.

## Commit style

Use concise imperative messages, for example:

```text
fix: distinguish candidate exhaustion from execution failure
docs: document loopback tunnel boundary
test: cover stale scheduler evidence
```

## Safe fixtures

Use synthetic names, URLs, identifiers, and outputs. Never submit real browser
profiles, application records, Telegram payloads, database copies, or model
provider tokens—even in a private issue.
