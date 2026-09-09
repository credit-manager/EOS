"""Production ASGI wrapper for the canonical EOS frontend.

The API application is intentionally kept in ``main.py``. This wrapper imports
it after all API routers have been registered, then appends a safe SPA/static
fallback so Docker's canonical ``erp-system/frontend/dist`` artifact is
actually reachable in production.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from main import app

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = (ROOT / "erp-system" / "frontend" / "dist").resolve()
INDEX_FILE = FRONTEND_DIST / "index.html"
_RESERVED_PREFIXES = ("api", "health", "metrics", "docs", "redoc", "openapi.json")


def _safe_asset(path: str) -> Path | None:
    if not path or not FRONTEND_DIST.is_dir():
        return None
    candidate = (FRONTEND_DIST / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


@app.get("/", include_in_schema=False)
async def frontend_root():
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=503, detail="Frontend build artifact is unavailable")
    return FileResponse(INDEX_FILE)


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_spa(full_path: str):
    first = full_path.split("/", 1)[0].lower()
    if first in _RESERVED_PREFIXES:
        raise HTTPException(status_code=404, detail="Not found")

    asset = _safe_asset(full_path)
    if asset is not None:
        return FileResponse(asset)
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=503, detail="Frontend build artifact is unavailable")
    return FileResponse(INDEX_FILE)
