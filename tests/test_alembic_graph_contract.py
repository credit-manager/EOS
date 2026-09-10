"""Static validation for the production Alembic revision graph."""
from __future__ import annotations

import ast
from pathlib import Path


VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"
EXPECTED_HEAD = "20260910_commercial_schema_merge"


def _literal_string_or_tuple(node: ast.AST | None) -> list[str]:
    if node is None or isinstance(node, ast.Constant) and node.value is None:
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List)):
        values: list[str] = []
        for item in node.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                raise AssertionError("Alembic down_revision must be a string or tuple/list of strings")
            values.append(item.value)
        return values
    raise AssertionError("Alembic down_revision must be statically representable")


def _load_graph() -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for path in sorted(VERSIONS.glob("*.py")):
        if path.name.startswith("__"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        revision = None
        down_revisions = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id == "revision" and isinstance(node.value, ast.Constant):
                    revision = node.value.value
                elif node.targets[0].id == "down_revision":
                    down_revisions = _literal_string_or_tuple(node.value)
        if not isinstance(revision, str) or not revision:
            raise AssertionError(f"Missing revision id in {path.name}")
        if revision in graph:
            raise AssertionError(f"Duplicate Alembic revision: {revision}")
        graph[revision] = down_revisions or []
    return graph


def test_alembic_graph_has_expected_single_head_and_no_cycles():
    graph = _load_graph()
    all_parents = {parent for parents in graph.values() for parent in parents}
    missing = sorted(parent for parent in all_parents if parent not in graph)
    assert not missing, f"Missing Alembic parents: {missing}"

    heads = sorted(set(graph) - all_parents)
    assert heads == [EXPECTED_HEAD], f"Unexpected Alembic heads: {heads}"

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise AssertionError(f"Alembic cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for revision in graph:
        visit(revision)
