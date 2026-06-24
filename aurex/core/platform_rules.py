"""Platform-level immutable rules. Users and agents cannot modify these."""
from aurex.core.primitives import Rule, Severity


PLATFORM_IMMUTABLE_RULES: list[Rule] = [
    Rule(
        id="PLAT_NO_REAL_MONEY_IN_SANDBOX",
        name="No Real Money MCP Calls In Sandbox",
        severity=Severity.HARD,
        scope="gateway.mode",
        expression_type="DSL",
        expression={
            "OR": [
                {"EQ": [{"FIELD": "mode"}, "LIVE"]},
                {"EQ": [{"FIELD": "real_money"}, False]},
            ]
        },
        human_text="Real-money MCP endpoints are unreachable while the IPT is in SANDBOX mode.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_AGENTS_CANT_MODIFY_RULES",
        name="Agents Cannot Modify Rules",
        severity=Severity.HARD,
        scope="agent.action",
        expression_type="DSL",
        expression={
            "NOT_IN": [
                {"FIELD": "action.tool"},
                ["modify_rule", "modify_guideline", "modify_prompt", "modify_memory"],
            ]
        },
        human_text="Self-modification of rules, guidelines, prompts, or memory is forbidden.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_ALL_MCP_CALLS_RULE_CHECKED",
        name="All MCP Calls Must Pass Rule Checks",
        severity=Severity.HARD,
        scope="gateway.call",
        expression_type="DSL",
        expression={
            "EQ": [{"FIELD": "rule_check.completed"}, True]
        },
        human_text="Every MCP call must clear rule evaluation before routing.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_ALL_ACTIONS_LOGGED",
        name="All Actions Must Be Logged",
        severity=Severity.HARD,
        scope="audit",
        expression_type="DSL",
        expression={
            "EQ": [{"FIELD": "logged"}, True]
        },
        human_text="Every action, rule check, and violation attempt must be recorded.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_DENY_BY_DEFAULT",
        name="Deny By Default",
        severity=Severity.HARD,
        scope="gateway.call",
        expression_type="DSL",
        expression={
            "EQ": [{"FIELD": "explicitly_allowed"}, True]
        },
        human_text="If the action is not explicitly allowed by the active rule set, it is blocked.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_NO_CROSS_IPT_CONTAMINATION",
        name="No Cross-IPT State Leakage",
        severity=Severity.HARD,
        scope="ipt.isolation",
        expression_type="DSL",
        expression={
            "EQ": [{"FIELD": "context.ipt_id"}, {"FIELD": "ipt_id"}]
        },
        human_text="An agent may only read or write state that belongs to its own IPT.",
        immutable=True,
        version=1,
    ),
    Rule(
        id="PLAT_NO_IRREVERSIBLE_WITHOUT_APPROVAL",
        name="No Irreversible Action Without Explicit User Approval",
        severity=Severity.HARD,
        scope="agent.action",
        expression_type="DSL",
        expression={
            "OR": [
                {"EQ": [{"FIELD": "action.irreversible"}, False]},
                {"EQ": [{"FIELD": "user_approved"}, True]},
            ]
        },
        human_text="Irreversible actions require explicit user approval at runtime.",
        immutable=True,
        version=1,
    ),
    # NOTE: PLAT_RULES_MACHINE_READABLE is an *authoring-time* invariant.
    # It is enforced by the RuleStore (only Rule/objects with
    # expression_type="DSL" can be constructed), not at runtime per-call.
]