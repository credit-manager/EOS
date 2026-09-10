# EOS / 2TO — Canonical Single-Project Architecture

## Decision

EOS / 2TO is one deployable project and one production runtime. The repository root `main.py` is the sole application entrypoint.

`eos_v2/` is an internal architecture/package inside this same project. It is not a second application, product, deployment, or executable entrypoint.

## Runtime

- Production server: `main:app`
- Frontend source: `frontend/`
- Frontend artifact: `frontend/dist/`
- Backend: root application plus internal packages
- Database/migrations: repository-wide canonical database
- CI/CD: repository-wide workflows

The former `eos_v2/main.py` executable entrypoint has been removed so the repository no longer advertises a second runnable application.

## Integration rule

Legacy capability is migrated into the canonical root runtime before deletion. A capability is considered migrated only when its implementation, API contract, persistence, security/tenant behavior, tests, frontend usage where applicable, and CI coverage all work through the canonical runtime.

The `core/`, `routers/`, and `eos_v2/` directories may coexist temporarily as internal packages during convergence, but they do not represent separate projects.

## Deletion gate

A legacy package/file may be deleted only after:

1. Its production capability has a canonical replacement.
2. API consumers have been migrated.
3. Database behavior and migrations remain compatible.
4. Tenant isolation/authentication is covered by integration tests.
5. Frontend behavior is covered by the canonical frontend build/tests.
6. CI passes using only the canonical runtime.
7. No remaining import/reference points to the deleted capability.

Deletion is the final cleanup phase of the merge, not the merge itself.
