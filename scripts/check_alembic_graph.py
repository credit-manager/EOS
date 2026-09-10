"""Verify the Alembic revision graph before database-dependent CI stages."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"
EXPECTED_HEAD = "20260910_rate_limits"


def parse_parents(node: ast.AST | None) -> list[str]:
    if node is None or (isinstance(node, ast.Constant) and node.value is None):
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List)):
        values: list[str] = []
        for item in node.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                raise ValueError("down_revision must contain only string literals")
            values.append(item.value)
        return values
    raise ValueError("down_revision must be a string or tuple/list of strings")


def load_graph() -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        if path.name.startswith("__"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        revision = None
        parents = None
        for statement in tree.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id == "revision" and isinstance(statement.value, ast.Constant):
                revision = statement.value.value
            elif target.id == "down_revision":
                parents = parse_parents(statement.value)
        if not isinstance(revision, str) or not revision:
            raise ValueError(f"Missing revision in {path.name}")
        if revision in graph:
            raise ValueError(f"Duplicate revision: {revision}")
        graph[revision] = parents or []
    return graph


def verify() -> None:
    graph = load_graph()
    references = {parent for parents in graph.values() for parent in parents}
    missing = sorted(parent for parent in references if parent not in graph)
    if missing:
        raise ValueError(f"Missing Alembic parents: {missing}")

    heads = sorted(set(graph) - references)
    if heads != [EXPECTED_HEAD]:
        raise ValueError(f"Unexpected Alembic heads: {heads}; expected {EXPECTED_HEAD}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"Alembic cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    print(f"Alembic graph PASS: {len(graph)} revisions, head={EXPECTED_HEAD}")


if __name__ == "__main__":
    try:
        verify()
    except Exception as exc:
        print(f"Alembic graph FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
