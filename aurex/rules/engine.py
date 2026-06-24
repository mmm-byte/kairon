"""Standalone rule-engine: evaluates a list of rules against a context."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from aurex.core.primitives import Rule, RuleCheck
from aurex.rules.dsl import DSLError, evaluate


@dataclass
class RuleEvaluation:
    rule_id: str
    complies: bool
    reason: str
    expression: dict


def evaluate_rules(rules: Iterable[Rule], context: dict) -> list[RuleEvaluation]:
    out: list[RuleEvaluation] = []
    for r in rules:
        try:
            complies = bool(evaluate(r.expression, context))
        except DSLError as exc:
            out.append(RuleEvaluation(r.id, False, f"DSL error: {exc}", r.expression))
            continue
        reason = "ok" if complies else f"violated: {r.human_text}"
        out.append(RuleEvaluation(r.id, complies, reason, r.expression))
    return out


def to_checks(evals: list[RuleEvaluation]) -> list[RuleCheck]:
    return [RuleCheck(rule_id=e.rule_id, complies=e.complies, reason=e.reason) for e in evals]