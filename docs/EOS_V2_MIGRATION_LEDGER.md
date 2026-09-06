# EOS DBP v2 — Migration Ledger

| Legacy capability | v2 destination | Strategy |
|---|---|---|
| `main.py` startup/router composition | `eos_v2/app` | Recompose, do not copy imports |
| `core/metadata_engine.py` | `eos_v2/domain/metadata` | Extract contracts first |
| `core/industry_engine/*` | `eos_v2/modules/industry` + domain services | Split bounded responsibilities |
| `core/security.py`, `core/auth.py` | `eos_v2/domain/identity` + `tenancy` | Centralize authorization and tenant context |
| `models.py` + Alembic baseline | `eos_v2/infrastructure/db` | Preserve schema semantics; remove ORM coupling from domain |
| `routers/*` | `eos_v2/interfaces/api` | Thin HTTP adapters only |
| `erp-system/frontend` | `eos_v2` frontend contract | Rebuild against versioned metadata API |
| AI composer | `eos_v2/application/services` | AI proposes metadata; policy validates before publish |

## Legacy safety
- Do not modify or delete legacy modules merely to make v2 compile.
- Do not run destructive database migrations against the existing development/production database during the rebuild.
- Any data migration must have backup, rehearsal, rollback and row-count/integrity verification.
- `test_eos.db` is test artifact only and is not a production source of truth.

## Promotion sequence
`v2 alpha` → `v2 integration` → `v2 staging` → `v2 production canary` → `v2 production`.

Each promotion requires green CI and an explicit comparison against the legacy contract where compatibility is required.
