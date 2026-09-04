"""Validate the canonical frontend API service against FastAPI routes."""
from __future__ import annotations

import ast
import re
from pathlib import Path

METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def literal(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def backend_routes():
    routes = set()
    for file in [Path("main.py"), *sorted(Path("routers").glob("*.py"))]:
        if not file.exists():
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        prefixes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter":
                prefix = next((literal(k.value) for k in node.value.keywords if k.arg == "prefix"), "") or ""
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        prefixes[target.id] = prefix.rstrip("/")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or not isinstance(dec.func.value, ast.Name):
                    continue
                if dec.func.attr.lower() not in METHODS or not dec.args:
                    continue
                route = literal(dec.args[0])
                if route is None:
                    continue
                prefix = prefixes.get(dec.func.value.id, "")
                routes.add(re.sub(r"//+", "/", f"{prefix}/{route.lstrip('/')}" if prefix else route))
    return routes


def normalize(path):
    path = re.sub(r"\$\{[^}]+\}", "{id}", path)
    if not path.startswith("/api/v1"):
        path = "/api/v1" + ("" if path.startswith("/") else "/") + path
    return re.sub(r"//+", "/", path).rstrip("/") or "/"


def matches(client, route):
    a, b = client.split("/"), route.rstrip("/").split("/")
    return len(a) == len(b) and all(x == y or (y.startswith("{") and y.endswith("}")) for x, y in zip(a, b))

service = Path("frontend/src/services/api.js")
if not service.exists():
    raise SystemExit("Canonical frontend API service is missing: frontend/src/services/api.js")
text = service.read_text(encoding="utf-8")
# Catch api.method('...') and api.method(`...`) paths. Dynamic template segments are normalized above.
pattern = re.compile(r"\bapi\.(?:get|post|put|patch|delete|head|options)\s*\(\s*(['\"`])([^'\"`]*?)\1")
frontend = {m.group(2) for m in pattern.finditer(text) if m.group(2).startswith("/")}
routes = backend_routes()
missing = [p for p in sorted(frontend) if not any(matches(normalize(p), normalize(r)) for r in routes)]
if missing:
    raise SystemExit("Frontend/backend API contract mismatch:\n" + "\n".join(missing))
print(f"API contract OK: checked {len(frontend)} explicit frontend paths against {len(routes)} backend routes")
