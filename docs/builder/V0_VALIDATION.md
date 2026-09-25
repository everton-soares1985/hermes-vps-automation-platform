# Autonomous Builder V0 Validation

## Controller result

The V0 controller passed 15/15 deterministic tests on Windows and Linux on 2026-08-10. The same 15 tests passed again on the operational VPS during the 2026-09-25 audit.

## Historical implementation smoke run

An early smoke run produced a working implementation and 22/22 independent fixture tests. An isolated reviewer approved the exact tested Git SHA with no critical or high findings. The overall run still ended as failed because the original contract incorrectly treated an intentional negative test—whose expected exit code was `1`—as a failed test.

The current contract stores `exit_code` and `expected_exit_code` separately and includes a regression test for that behavior.

## Provider-unavailable smoke run

A later smoke run was blocked when OmniRoute reported that every upstream account for the implementer route was inactive. Hermes CLI returned process exit code `0` while its output described the failure. The controller now recognizes that soft-failure pattern, converts it into non-zero exit code `75`, and stops without consuming further implementation iterations.

## Current operational position

- no Builder process or container stays active between runs;
- OmniRoute and the production Hermes gateway remain independent;
- workspaces use local Git only and have no remote;
- production automation roots are protected;
- two historical failed smoke systemd units are inactive and do not affect the platform;
- a complete terminal `APPROVED` run with the final contract remains pending stable upstream route availability.

Raw run identifiers, host paths, hashes, and model-provider account details are intentionally omitted from the public portfolio edition.
