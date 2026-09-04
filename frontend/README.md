# EOS DBP — Canonical Frontend

This directory is the **single canonical frontend source** for EOS DBP.

## Architecture decision

- `frontend/` is the authoritative React/Vite application source.
- `eos-system/frontend/dist/` is a generated production artifact and is rebuilt by the root production Dockerfile. It is not a source tree.
- `erp-system/frontend/` is deprecated legacy code and must not receive new features.

## Rules

1. New UI features are implemented only in `frontend/`.
2. API integration must target the root EOS DBP FastAPI backend (`/api/v1`).
3. Do not introduce a second router/application tree outside this directory.
4. Do not edit generated files under `eos-system/frontend/dist/` by hand.
5. Legacy functionality must be migrated into this application before the legacy frontend is removed.

## Build

```bash
npm install
npm run build
```

The production container builds this application from source and places the generated output at the path currently served by `main.py` (`/ui`).
