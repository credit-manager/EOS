# 2TO EOS

2TO EOS is a clean-room rebuild of the EOS ERP Platform: an AI-native, metadata-driven ERP platform for emerging markets.

## Architecture

The rebuild follows one production runtime and explicit boundaries:

- `backend/app` — application and domain code.
- `backend/tests` — executable contract tests.
- `frontend` — the only web UI source.
- `infra` — local/production infrastructure definitions.
- PostgreSQL is the production database.

The platform is rebuilt in this order:

CI → Core Hardening → Metadata Platform → Security → Financial Core → Workflow → Industry Packs → AI → Integrations → Globalization → UX → Production Scale

No phase is considered complete from a green lint/test result alone; each phase requires executable behavior evidence.
