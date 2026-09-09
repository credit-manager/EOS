# EOS Release Gate

EOS release validation is fail-closed at the workflow summary level.

## Required gates

1. Canonical React frontend install, lint, build, and artifact verification.
2. Python syntax/import smoke validation.
3. Critical Ruff and Flake8 checks.
4. Bandit high-confidence security checks.
5. Dependency audit with `pip-audit`.
6. PostgreSQL-backed automated test suite with coverage artifacts.
7. Tenant-isolation/security regression validation.

## Product readiness

- The canonical frontend source is `erp-system/frontend`.
- Production containers build the canonical frontend and publish it to the runtime UI directory.
- The Business Builder uses the backend onboarding state machine and persists each ordered step.
- Dynamic workspaces consume backend metadata rather than inventing a parallel data model.
- Reporting clients use the production `/reports/*` API surface.

A release is not considered green until the GitHub Actions gates complete successfully; a source review alone does not constitute a green build.
