# EOS Dead-Code Cleanup — 2026-09-15

## Baseline

Branch: `cleanup/remove-dead-code-2026-09`
Base: `b34c07d` (`fix(security): refresh-token flow, CI gates, prod defaults — release blocker audit pass`)

## Removed

The following repository artifacts were removed after checking that they were not part of the current runtime registration path and were not found as active internal references.

### Pass 1

- `backend/app/api_docs.py` — unused response-schema/documentation helper.
- `backend/app/db_errors.py` — unused alternative database error/session wrapper; current application uses `db.py` and centralized error handlers.
- `backend/app/streaming.py` — unused streaming-response helper; no active route uses it.
- `backend/app/response_validation.py` — unused decorator/validator framework; FastAPI/Pydantic response validation is used directly.
- `backend/app/models.py` — unused aggregate model re-export module; application imports domain models from their owning packages.
- `Dockerfile.test` — unused test image definition; CI builds/tests the canonical Dockerfile and Python environment directly.
- `frontend/src/components/App.tsx` — unreachable duplicate frontend application entry; `frontend/src/main.tsx` renders `frontend/src/App.tsx`.

### Pass 2

- `backend/app/migration_utils.py` — unused Alembic helper wrapper; CI invokes Alembic directly and no runtime entrypoint imports this module.
- `backend/app/performance.py` — unused in-process performance monitor; runtime metrics are implemented through `backend/app/metrics.py` and the main app does not register/import this monitor.
- `frontend/src/api.ts` — obsolete API/session client belonging to the unreachable metadata-oriented frontend path.
- `frontend/src/types.ts` — obsolete shared types used by that unreachable metadata-oriented frontend path.
- `frontend/src/components/AuthScreen.tsx` — unreachable duplicate authentication screen.
- `frontend/src/components/CatalogPage.tsx` — unreachable metadata catalog page.
- `frontend/src/components/EntityPage.tsx` — unreachable metadata entity page.
- `frontend/src/components/MetadataStudio.tsx` — unreachable metadata editor.
- `frontend/src/components/RelationField.tsx` — dependency of the unreachable metadata entity page.

Total removed artifacts: **16** (7 in pass 1, 9 in pass 2).

## Intentionally retained

The following were reviewed but retained because they are active runtime infrastructure or legitimate platform foundations:

- `backend/app/cache.py`
- `backend/app/compression.py`
- `backend/app/query_logger.py`
- `backend/app/query_optimizer.py`
- `backend/app/request_logger.py`
- `backend/app/request_validator.py`
- `backend/app/rate_limiter.py`
- `backend/app/security_headers.py`
- `backend/app/retry.py`
- `backend/app/circuit_breaker.py`
- `backend/app/external_services.py`
- all registered routers and domain modules
- existing backend regression/security tests
- Alembic migration history

`retry.py`, `circuit_breaker.py`, and `external_services.py` are not part of the current primary request path, but they are retained as the bounded integration resilience foundation until the Integration Hub is implemented. They must not be described as currently active external integrations.

## Tests reviewed

No backend test file was identified as provably dead in this pass. The apparent `v2` and integration variants cover distinct behavior rather than duplicating the same assertions:

- metadata core vs computed-field/validation coverage
- workflow lifecycle vs condition/event/rule coverage
- workflow-to-record binding integration coverage
- dedicated security, financial, construction, graph, reporting, lookup, audit, and demo scenario coverage

The test suite remains configured through `backend/tests` in `pyproject.toml` and is exercised by CI.

## Validation required

The pull request must verify:

- Python lint
- SQLite migrations
- SQLite tests
- PostgreSQL migrations
- PostgreSQL tests
- frontend install/lint/format/build
- dependency audits
- Docker build/smoke test where the workflow permits

## Cleanup policy

Do not delete remaining code solely because it is large, old-looking, or not exposed in the current UI. Remove it only after proving it is dead, duplicated, or obsolete and checking runtime, CI, Docker, migrations, tests, and documentation references.

## Verification note

This cleanup deliberately preserves active runtime infrastructure, platform foundations, migration history, and meaningful regression/security tests. Acceptance depends on pull-request CI remaining green after the deletions.
