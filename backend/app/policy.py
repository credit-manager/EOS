from typing import Any


def resolve_path(ctx: dict[str, Any], path: str) -> tuple[bool, Any]:
    """Resolve a dotted path ('payload.amount') inside an evaluation context."""
    node: Any = ctx
    for segment in path.split("."):
        if isinstance(node, dict) and segment in node:
            node = node[segment]
        else:
            return False, None
    return True, node


def _coerce_num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num_or_none(a: Any, b: Any) -> tuple[float, float] | None:
    na, nb = _coerce_num(a), _coerce_num(b)
    if na is not None and nb is not None:
        return na, nb
    return None


def evaluate_conditions(ctx: dict[str, Any], conditions: list[dict]) -> bool:
    """Evaluate a list of conditions with AND semantics over a context dict.

    Supported operators: exists, eq, neq, gt, gte, lt, lte, contains,
    not_contains, in, starts_with. Numeric-aware when both sides are numeric.
    """
    if not conditions:
        return True
    return all(_evaluate_condition(ctx, cond) for cond in conditions)


def _evaluate_condition(ctx: dict[str, Any], cond: dict) -> bool:
    field = cond.get("field", "")
    op = cond.get("op", "eq")
    value = cond.get("value")
    found, actual = resolve_path(ctx, field)

    if op == "exists":
        return found is bool(value)

    if not found:
        return False

    pair = _num_or_none(actual, value)
    if pair is not None and op in ("eq", "neq", "gt", "gte", "lt", "lte"):
        a, b = pair
        if op == "eq":
            return a == b
        if op == "neq":
            return a != b
        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        return a <= b

    if op == "eq":
        return actual == value
    if op == "neq":
        return actual != value
    if op == "contains":
        return value in actual if isinstance(actual, (str, list, tuple)) else False
    if op == "not_contains":
        return value not in actual if isinstance(actual, (str, list, tuple)) else True
    if op == "in":
        return actual in value if isinstance(value, list) else False
    if op == "starts_with":
        return actual.startswith(value) if isinstance(actual, str) else False
    return False
