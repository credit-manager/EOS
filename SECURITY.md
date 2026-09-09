# EOS Security Policy

## Supported versions

Security fixes are applied to the default branch and the latest supported production release.
Older releases should be upgraded before reporting issues that are already fixed upstream.

## Reporting a vulnerability

Do not disclose suspected vulnerabilities in public GitHub issues.

Use a private GitHub Security Advisory for this repository when available. Include:

- affected component, endpoint, or workflow;
- reproducible steps or a minimal proof of concept;
- expected and observed behavior;
- impact assessment;
- affected EOS version/commit;
- any mitigation already applied.

Please avoid submitting customer data, credentials, access tokens, production secrets, or other sensitive information.

## Response expectations

Reports are triaged by severity and reproducibility. Critical tenant-isolation, authentication,
authorization, payment, or remote-code-execution issues receive highest priority.

A fix should include a regression test where practical, preserve tenant isolation, and pass the
commercial release gate before production deployment.

## Production security boundary

Production deployments must use:

- explicit production authentication mode;
- least-privilege runtime database roles;
- PostgreSQL Row-Level Security with FORCE RLS for tenant-scoped tables;
- TLS at the public edge;
- secrets supplied through the deployment secret manager rather than committed files;
- dependency and container vulnerability scanning;
- SBOM generation for production images.
