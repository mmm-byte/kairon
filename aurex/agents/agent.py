"""Agent cognition loop: rule-first thinking + standard output schema."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable

from aurex.core.primitives import AgentOutput, DecisionType
from aurex.rules.dsl import DSLError, evaluate


def render_system_prompt(
    *,
    agent_name: str,
    ipt_id: str,
    mode: str,
    rules_text: list[str],
    guidelines_text: list[str],
) -> str:
    rules_block = "\n".join(f"- {r}" for r in rules_text) or "- (none)"
    guidelines_block = "\n".join(f"- {g}" for g in guidelines_text) or "- (none)"
    return f"""You are {agent_name} running inside IPT '{ipt_id}' (mode: {mode}).

Hard rules (you may NEVER violate):
{rules_block}

Guidelines (preferences, tunable by user):
{guidelines_block}

For every decision you must:
1. Identify your allowed action space.
2. Generate a single candidate action.
3. Self-check the candidate against every hard rule.
4. Score alignment with each guideline.
5. Output the JSON below — and nothing else.

Required JSON schema:
{{
  "allowed_action_space_reasoning": "...",
  "candidate_action": {{ ... }},
  "rule_check_self_assessment": {{ "complies": true, "violated_rules": [] }},
  "guideline_alignment": {{ "<guideline_id>": {{ "score": 0.0, "notes": "..." }} }},
  "final_decision": {{ "type": "ACT|ABSTAIN", "reason": "..." }}
}}
"""


class LLMRunner:
    """Pluggable LLM backend. Default is a deterministic template-only stub."""

    def __init__(self, runner: Callable[[str, dict], str] | None = None) -> None:
        self.runner = runner or _default_template_runner

    def complete(self, system_prompt: str, user_payload: dict) -> str:
        return self.runner(system_prompt, user_payload)


def _default_template_runner(system_prompt: str, user_payload: dict) -> str:
    """Template-only fallback: produce a valid schema response."""
    return json.dumps(
        {
            "allowed_action_space_reasoning": "Template fallback: no LLM configured.",
            "candidate_action": user_payload.get("hint_action", {"tool": "noop"}),
            "rule_check_self_assessment": {"complies": True, "violated_rules": []},
            "guideline_alignment": {},
            "final_decision": {"type": "ABSTAIN", "reason": "no LLM attached"},
        }
    )


class RuleFirstAgent:
    """Wraps an LLM call with rule-first thinking and post-LLM rule re-check."""

    def __init__(
        self,
        *,
        name: str,
        llm: LLMRunner,
        rules_provider: Callable[[], list],
        guidelines_provider: Callable[[], list],
        action_factory: Callable[[dict], dict] | None = None,
    ) -> None:
        self.name = name
        self.llm = llm
        self.rules_provider = rules_provider
        self.guidelines_provider = guidelines_provider
        self.action_factory = action_factory or (lambda ctx: {"tool": "noop"})

    def _build_prompt(self, ipt_id: str, mode: str, context: dict) -> str:
        rules = self.rules_provider()
        guidelines = self.guidelines_provider()
        return render_system_prompt(
            agent_name=self.name,
            ipt_id=ipt_id,
            mode=mode,
            rules_text=[r.human_text for r in rules],
            guidelines_text=[g.human_text for g in guidelines],
        )

    def run(self, ipt_id: str, mode: str, context: dict) -> AgentOutput:
        system_prompt = self._build_prompt(ipt_id, mode, context)
        raw = self.llm.complete(system_prompt, {"hint_action": self.action_factory(context)})
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "allowed_action_space_reasoning": "Invalid LLM JSON — abstaining.",
                "candidate_action": {"tool": "noop"},
                "rule_check_self_assessment": {"complies": False, "violated_rules": ["LLM_PARSE"]},
                "guideline_alignment": {},
                "final_decision": {"type": "ABSTAIN", "reason": "LLM output unparseable"},
            }

        # ---- External rule re-check (the orchestrator does this too, defensively) ----
        rules = self.rules_provider()
        for r in rules:
            try:
                if not evaluate(r.expression, context):
                    parsed.setdefault("rule_check_self_assessment", {})
                    parsed["rule_check_self_assessment"]["complies"] = False
                    parsed["rule_check_self_assessment"].setdefault("violated_rules", []).append(r.id)
            except DSLError:
                continue

        return AgentOutput(
            agent_name=self.name,
            ipt_id=ipt_id,
            allowed_action_space_reasoning=parsed.get("allowed_action_space_reasoning", ""),
            candidate_action=parsed.get("candidate_action", {}),
            rule_check_self_assessment=parsed.get("rule_check_self_assessment", {}),
            guideline_alignment=parsed.get("guideline_alignment", {}),
            final_decision=parsed.get("final_decision", {"type": DecisionType.ABSTAIN.value, "reason": ""}),
            raw=parsed,
        )


def output_to_dict(out: AgentOutput) -> dict:
    return asdict(out)