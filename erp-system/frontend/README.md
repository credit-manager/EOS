# Deprecated frontend

This frontend has been retired as a source tree.

## Canonical frontend

Use the repository-root `frontend/` directory for all EOS DBP frontend development.

Do not add new routes, components, API clients, dependencies, or build configuration here.

The root production Dockerfile builds `frontend/` and produces the UI artifact served by the main FastAPI application.

Any functionality discovered here that is still required must be migrated to the canonical frontend before this directory is removed completely.