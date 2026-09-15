# EOS Security Baseline

- Authentication and authorization are enforced server-side and tenant-scoped.
- Refresh tokens are rotated by the backend; the canonical frontend calls refresh and logout endpoints.
- New commands, queries, events, reports, graph traversal and AI tools must be tenant-scoped and deny-by-default.
- Financial posting requires domain validation and audit; automation cannot self-approve.
- External side effects require transactional outbox, idempotency, retry and dead-letter handling.
- Never execute tenant-supplied code or use `eval`.

Browser token storage is an interim boundary; a future HttpOnly/Secure cookie design must include explicit CSRF controls.
