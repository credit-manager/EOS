# EOS Architecture

## Canonical runtime
EOS has one browser runtime: `frontend/src/main.tsx` → `frontend/src/App.tsx` → `frontend/src/components/App.tsx` (`PlatformApp`).

## Platform spine
Metadata → records → relations → graph → workflow/rules/events → audit/reporting → governed AI tools.

The canonical backend is `backend/app/main.py`; PostgreSQL is the production source of truth and SQLite is for local/CI validation.

The current `SystemEvent` implementation is a persisted log with synchronous in-process dispatch, not yet a distributed event bus. AI workforce, integrations, document intelligence, SDKs, and marketplace execution remain future layers.
