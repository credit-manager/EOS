"""Safe AST-based formula evaluator for computed metadata fields.

Supports: arithmetic (+, -, *, /, %, **), numeric literals, field references,
parentheses.  No function calls, no imports, no side-effects.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

_SAFE_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_SAFE_UNARY_OPS: dict[type, Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def evaluate_formula(formula: str, context: dict[str, Any]) -> float | None:
    """Evaluate *formula* against *context* of field values.

    Returns the numeric result or ``None`` when evaluation is impossible
    (missing field, division-by-zero, syntax error, or unsupported node).
    """
    try:
        tree = ast.parse(formula, mode="eval")
    except (SyntaxError, ValueError):
        return None
    return _eval(tree.body, context)  # type: ignore[return-value]


def _eval(node: ast.AST, ctx: dict[str, Any]) -> float | int | None:
    if isinstance(node, ast.Expression):
        return _eval(node.body, ctx)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.Name):
        value = ctx.get(node.id)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BIN_OPS:
        left = _eval(node.left, ctx)
        right = _eval(node.right, ctx)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Div) and right == 0:
            return None
        return _SAFE_BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_UNARY_OPS:
        operand = _eval(node.operand, ctx)
        if operand is None:
            return None
        return _SAFE_UNARY_OPS[type(node.op)](operand)

    return None