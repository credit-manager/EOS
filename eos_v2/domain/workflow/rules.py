from __future__ import annotations

from enum import Enum
from typing import Any


class RuleOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EXISTS = "exists"


def evaluate_rule(data: dict[str, Any], field: str, operator: RuleOperator, expected: Any = None) -> bool:
    """Evaluate a small declarative rule language; never execute user code."""
    exists = field in data and data[field] is not None
    if operator is RuleOperator.EXISTS:
        return exists == bool(expected)
    if not exists:
        return False
    actual = data[field]
    if operator is RuleOperator.EQ:
        return actual == expected
    if operator is RuleOperator.NE:
        return actual != expected
    if operator is RuleOperator.IN:
        return actual in expected
    if operator is RuleOperator.GT:
        return actual > expected
    if operator is RuleOperator.GTE:
        return actual >= expected
    if operator is RuleOperator.LT:
        return actual < expected
    if operator is RuleOperator.LTE:
        return actual <= expected
    return False
