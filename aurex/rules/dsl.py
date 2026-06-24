"""JSON-Logic-compatible DSL evaluator for Aurex rules & guidelines."""
from __future__ import annotations

from typing import Any


class DSLError(Exception):
    """Raised when a DSL expression is malformed or fails to evaluate."""


def _resolve(field: str, ctx: dict) -> Any:
    """Walk a dotted FIELD path against the context dict."""
    node: Any = ctx
    for part in field.split("."):
        if isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        elif isinstance(node, list):
            try:
                idx = int(part)
            except ValueError as exc:
                raise DSLError(f"Cannot index list with non-int key '{part}'") from exc
            if idx >= len(node):
                return None
            node = node[idx]
        else:
            return None
    return node


def evaluate(expression: dict, context: dict) -> Any:
    """Evaluate a DSL expression and return its result.

    Supported ops: AND, OR, NOT, LT, LTE, GT, GTE, EQ, NEQ, IN, NOT_IN, IMPLIES, FIELD.
    Raw Python literals (int, float, str, bool, list, None) are allowed wherever an
    operand is expected — they evaluate to themselves. This makes rules easier to write.
    """
    # Allow raw Python literals as operands.
    if not isinstance(expression, dict):
        return expression

    if len(expression) != 1:
        raise DSLError(f"Expression must be a single-key dict, got: {expression!r}")

    ((op, args),) = expression.items()

    if op == "FIELD":
        if not isinstance(args, str):
            raise DSLError("FIELD requires a string path")
        return _resolve(args, context)

    if op == "CONST":
        return args

    if op == "NOT":
        return not evaluate(args, context)

    if op == "AND":
        return all(evaluate(a, context) for a in args)

    if op == "OR":
        return any(evaluate(a, context) for a in args)

    if op == "IMPLIES":
        if not isinstance(args, list) or len(args) != 2:
            raise DSLError("IMPLIES requires [antecedent, consequent]")
        a, b = args
        return (not evaluate(a, context)) or bool(evaluate(b, context))

    if op in {"LT", "LTE", "GT", "GTE", "EQ", "NEQ"}:
        if not isinstance(args, list) or len(args) != 2:
            raise DSLError(f"{op} requires [left, right]")
        left = evaluate(args[0], context)
        right = evaluate(args[1], context)
        if left is None or right is None:
            return False
        if op == "LT":
            return left < right
        if op == "LTE":
            return left <= right
        if op == "GT":
            return left > right
        if op == "GTE":
            return left >= right
        if op == "EQ":
            return left == right
        return left != right

    if op == "IN":
        if not isinstance(args, list) or len(args) != 2:
            raise DSLError("IN requires [needle, haystack]")
        needle = evaluate(args[0], context)
        haystack = evaluate(args[1], context)
        if haystack is None:
            return False
        return needle in haystack

    if op == "NOT_IN":
        if not isinstance(args, list) or len(args) != 2:
            raise DSLError("NOT_IN requires [needle, haystack]")
        needle = evaluate(args[0], context)
        haystack = evaluate(args[1], context)
        if haystack is None:
            return False
        return needle not in haystack

    raise DSLError(f"Unknown DSL operator: {op}")