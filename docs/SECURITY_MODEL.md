# Security Model

## Assets

The private deployment can hold provider credentials, Telegram configuration, authenticated browser profiles, job-search history, application ledgers, project source code, and model-routing keys. None of these assets belongs in the public repository.

## Trust boundaries

1. **Public repository:** source, examples, sanitized audit evidence.
2. **VPS operating system:** services, private configuration, browser profiles, ledgers.
3. **Hermes:** scheduler and messaging control plane.
4. **OmniRoute:** local model-routing boundary.
5. **External platforms:** untrusted pages and APIs that can change behavior.
6. **Model output:** untrusted proposal data until deterministic validation passes.

## Controls

- credentials come from ignored environment/configuration files;
- all private HTTP/CDP endpoints bind to loopback;
- operator access uses SSH tunnels;
- systemd user units provide explicit ownership and lifecycle;
- browser profiles and debugging ports are isolated per workload;
- externally visible actions require dedicated confirmation flags;
- daily limits and target bounds are enforced by the workload, not by a prompt;
- the builder accepts source only from allowlisted roots;
- production roots are protected from builder access;
- Docker limits CPU, memory, disk, timeout, mount, and user identity;
- reviewer output must reference the exact implementation evidence hash;
- tests must exit with the configured expected result;
- watchdogs hash alert state to avoid notification storms.

## Explicitly excluded from publication

- `.env`, `auth.json`, real `config.toml`;
- API keys, bearer tokens, cookies, and OAuth artifacts;
- Telegram bot token or chat ID;
- SSH private keys, host addresses, and usernames;
- raw SQLite databases and JSON reports containing private records;
- browser user-data directories;
- candidate names, messages, resumes, or application content.

## Deployment checklist

- [ ] Run a secret scan before every push.
- [ ] Bind private services to `127.0.0.1`.
- [ ] Disable SSH password authentication.
- [ ] Keep host and cloud firewalls aligned with the loopback-first design.
- [ ] Confirm environment files are mode `0600`.
- [ ] Use a non-root service account.
- [ ] Review provider and target-platform terms before automation.
- [ ] Revalidate selectors in diagnostic mode after external UI changes.
- [ ] Back up ledgers before schema migrations.
- [ ] Rotate a credential immediately if it is ever printed or committed.

## Reporting a vulnerability

Follow [SECURITY.md](../SECURITY.md). Do not include real credentials or personal records in an issue.
