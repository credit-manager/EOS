"""Production ASGI wrapper for the canonical EOS frontend.

The API application is intentionally kept in ``main.py``. This wrapper adds a
safe SPA/static fallback for Docker's canonical
``erp-system/frontend/dist`` artifact.

The middleware for ``/`` is intentional: ``main.py`` already registers a root
API route, so adding another ``@app.get('/')`` route does not replace it in
FastAPI's route order. Intercepting the production root here guarantees the
commercial frontend is the actual application entry point while leaving API,
health, metrics, and documentation routes untouched.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from main import app

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = (ROOT / "erp-system" / "frontend" / "dist").resolve()
INDEX_FILE = FRONTEND_DIST / "index.html"
_RESERVED_PREFIXES = frozenset({"api", "health", "metrics", "docs", "redoc", "openapi.json"})


def _safe_asset(path: str) -> Path | None:
    """Resolve a frontend asset without permitting path traversal."""
    if not path or not FRONTEND_DIST.is_dir():
        return None
    candidate = (FRONTEND_DIST / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


@app.middleware("http")
async def serve_canonical_frontend(request: Request, call_next):
    """Make the canonical React build the production web entry point."""
    if request.url.path == "/" and INDEX_FILE.is_file():
        return FileResponse(INDEX_FILE, media_type="text/html")
    return await call_next(request)


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_spa(full_path: str):
    """Serve real static assets or fall back to the React SPA for client routes."""
    first = full_path.split("/", 1)[0].lower()
    if first in _RESERVED_PREFIXES:
        raise HTTPException(status_code=404, detail="Not found")

    asset = _safe_asset(full_path)
    if asset is not None:
        return FileResponse(asset)
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=503, detail="Frontend build artifact is unavailable")
    return FileResponse(INDEX_FILE, media_type="text/html")
