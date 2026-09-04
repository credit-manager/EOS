"""Fail CI when explicit frontend API paths disappear from the FastAPI contract.

The checker is intentionally static: it does not import the application or require
production secrets, database drivers, or startup side effects just to validate routes.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_backend_paths() -> set[str]:
    paths: set[str] = set()
    for file in [Path("main.py"), *sorted(Path("routers").glob("*.py"))]:
        if not file.exists():
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        router_prefixes: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            if not (isinstance(func, ast.Name) and func.id == "APIRouter"):
                continue
            prefix = ""
            for keyword in node.value.keywords:
                if keyword.arg == "prefix":
                    prefix = _literal_string(keyword.value) or ""
            for target in node.targets:
                if isinstance(target, ast.Name):
                    router_prefixes[target.id] = prefix.rstrip("/")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                if not isinstance(decorator.func.value, ast.Name):
                    continue
                if decorator.func.attr.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                    continue
                if not decorator.args:
                    continue
                route = _literal_string(decorator.args[0])
                if route is None:
                    continue
                prefix = router_prefixes.get(decorator.func.value.id, "")
                combined = f"{prefix}/{route.lstrip('/')}" if prefix else route
                paths.add(re.sub(r"//+", "/", combined))

    # main.py may define application-level routes directly.
    return paths


def _route_matches(client_path: str, route_path: str) -> bool:
    client_parts = client_path.rstrip("/").split("/")
    route_parts = route_path.rstrip("/").split("/")
    if len(client_parts) != len(route_parts):
        return False
    return all(a == b or b.startswith("{") for a, b in zip(client_parts, route_parts))


frontend_api = Path("frontend/src/services/api.js")
if not frontend_api.exists():
    raise SystemExit("Canonical frontend API service is missing: frontend/src/services/api.js")

text = frontend_api.read_text(encoding="utf-8")
raw_paths = set(
    re.findall(r"['\"](/(?:api/v1|auth|users|dashboard|entities|reports|industries|builder)[^'\"]*)['\"]", text)
)
paths = {p for p in raw_paths if p != "/api/v1"}
backend_paths = _collect_backend_paths()

missing = []
for path in sorted(paths):
    normalized = re.sub(r"\$\{[^}]+\}", "{id}", path)
    if not normalized.startswith("/api/v1/"):
        normalized = "/api/v1" + normalized
    if not any(_route_matches(normalized, route_path) for route_path in backend_paths):
        missing.append(path)

if missing:
    raise SystemExit("Frontend/backend API contract mismatch:\n" + "\n".join(missing))
print(f"API contract OK: checked {len(paths)} explicit frontend paths against {len(backend_paths)} backend routes")
