# Security Policy

## Supported versions

Security fixes target the latest release on the `main` branch.

## Reporting

Do not open a public issue for a vulnerability that includes credentials,
personal records, host coordinates, authenticated URLs, or browser-session
material. Contact the repository owner privately through the security contact
available on the GitHub profile and provide:

- affected component and version;
- reproducible steps using synthetic data;
- expected impact;
- a proposed mitigation, if available.

## Deployment responsibility

This repository is a sanitized reference implementation. Operators are
responsible for secret management, host firewall rules, SSH hardening,
platform terms, account permissions, data protection, and the consequences of
automating external services.

## Out of scope

- credential leaks caused by committing ignored production files;
- bypassing CAPTCHA or anti-abuse controls;
- attacks against third-party providers or websites;
- social engineering and account-recovery requests.
