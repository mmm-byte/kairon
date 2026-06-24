"""Core primitives: Rule, Guideline, IPT, Mode, Severity enums."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"


class Severity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class DecisionType(str, Enum):
    ACT = "ACT"
    ABSTAIN = "ABSTAIN"


class GatewayStatus(str, Enum):
    EXECUTED = "EXECUTED"
    SIMULATED = "SIMULATED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


@dataclass
class Rule:
    """A hard, machine-checked constraint."""
    id: str
    name: str
    severity: Severity
    scope: str
    expression_type: str
    expression: dict
    human_text: str
    immutable: bool = False
    version: int = 1


@dataclass
class Guideline:
    """A soft, tunable preference."""
    id: str
    name: str
    priority: int
    dimension: str
    expression_type: str
    expression: dict
    human_text: str
    user_editable: bool = True
    version: int = 1


@dataclass
class RuleCheck:
    rule_id: str
    complies: bool
    reason: str = ""


@dataclass
class GuidelineAlignment:
    guideline_id: str
    score: float
    notes: str = ""


@dataclass
class AgentOutput:
    agent_name: str
    ipt_id: str
    allowed_action_space_reasoning: str
    candidate_action: dict
    rule_check_self_assessment: dict
    guideline_alignment: dict
    final_decision: dict
    raw: dict = field(default_factory=dict)


@dataclass
class GatewayRequest:
    ipt_id: str
    agent_name: str
    mode: Mode
    action: dict
    context: dict = field(default_factory=dict)


@dataclass
class GatewayResponse:
    status: GatewayStatus
    reason: str
    rule_violations: list[RuleCheck]
    result: dict
    logs: dict