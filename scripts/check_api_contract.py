"""Fail CI when explicit frontend API paths disappear from the FastAPI contract."""
from __future__ import annotations

import re
from pathlib import Path

from main import app


frontend_api = Path("frontend/src/services/api.js")
text = frontend_api.read_text(encoding="utf-8")
backend_paths = {getattr(route, "path", "") for route in app.routes}

# Only inspect explicit string paths; interpolated resource IDs are normalized.
paths = set(re.findall(r"['\"](/(?:api/v1|auth|users|dashboard|entities|reports|industries|builder)[^'\"]*)['\"]", text))
missing = []
for path in sorted(paths):
    normalized = re.sub(r"\$\{[^}]+\}", "{id}", path)
    if not any(_route_matches(normalized, route_path) for route_path in backend_paths):
        missing.append(path)


def _route_matches(client_path: str, route_path: str) -> bool:
    client_parts = client_path.rstrip("/").split("/")
    route_parts = route_path.rstrip("/").split("/")
    if len(client_parts) != len(route_parts):
        return False
    return all(a == b or b.startswith("{") for a, b in zip(client_parts, route_parts))


if missing:
    raise SystemExit("Frontend/backend API contract mismatch:\n" + "\n".join(missing))
print(f"API contract OK: checked {len(paths)} explicit frontend paths against {len(backend_paths)} backend routes")
