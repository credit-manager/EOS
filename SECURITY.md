# EOS Security Baseline

## Current controls

* Backend access tokens are signed and checked against persisted sessions, active users, and tenant memberships.
* Refresh tokens are stored as hashes server-side and rotated by the backend.
* Tenant-scoped backend queries, request IDs, rate limits, body limits, CORS allowlist, and security headers are implemented.
* Production Compose requires secrets and the frontend proxies `/api/` to the backend.

## Frontend session behavior

The canonical frontend uses `frontend/src/api.ts` for login, refresh, and server logout. It schedules access-token refresh and clears local session state after server logout. Browser storage remains an interim risk boundary: any future move to HttpOnly cookies must add a CSRF strategy, and no UI-only permission check is a security control.

## Non-negotiable rules for new platform work

1. Scope every command, query, event, report, graph traversal, and future AI tool by tenant and server-side policy.
2. Use deny-by-default authorization; do not trust hidden UI controls.
3. Do not expose SQL, filesystem access, arbitrary HTTP, or unrestricted internal services to AI models or extensions.
4. Use declarative, bounded expressions—never `eval` or tenant-supplied code.
5. Financial posting requires financial-domain validation and audit; agents and rules cannot self-approve.
6. Before external side effects, introduce transactional outbox delivery, idempotency, retry, and dead-letter handling.

## Reporting issues

Report a suspected vulnerability privately to the repository maintainers. Do not include secrets, access tokens, customer data, or exploit payloads in issues, logs, test fixtures, or documentation.
