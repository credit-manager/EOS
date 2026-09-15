# EOS Architecture

## Canonical runtime

EOS has one browser entrypoint: `frontend/src/main.tsx` → `frontend/src/App.tsx` → `frontend/src/components/App.tsx` (`PlatformApp`). The legacy dashboard shell is no longer rendered. The canonical frontend uses hash routes for `/workspace`, `/objects`, `/objects/:entity`, and `/builder`, the shared `frontend/src/api.ts` client, and one session lifecycle.

The canonical backend is the FastAPI application in `backend/app/main.py`. Its platform primitives are metadata, records, audit, events, rules, workflow, graph, reporting, notifications, financial, and construction modules. PostgreSQL is the production source of truth; SQLite remains a local/CI convenience only.

## Current request and session boundary

```text
Browser → Nginx /api proxy or VITE_API_URL → FastAPI → SQLAlchemy → PostgreSQL
```

The frontend persists the current session metadata so it can refresh access credentials before expiry. It invokes the backend refresh endpoint, stores the rotated session, and invokes server logout before clearing local state. This is an interim browser-token architecture; a future cookie/BFF decision must include CSRF controls and must not bypass the backend session and tenant checks.

## Product spine

```text
Metadata definition → dynamic record → relation → graph story
  → workflow/rules/events → audit/reporting → future governed AI tools
```

Financial posting remains a domain service: metadata and automation may create an approved financial intent, but must not bypass journal validation or posting invariants.

## Explicit non-goals of the current implementation

The current persisted `SystemEvent` log is not yet a distributed event bus; rule dispatch is still synchronous. AI, document intelligence, integration workers, SDKs, and marketplace packages are not implemented. See the dated engineering audit and `EOS_PRODUCT_VISION_V1_AR.md` for status and delivery order.
