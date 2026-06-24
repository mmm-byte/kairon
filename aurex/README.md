# Aurex — Agent Governance Platform

A rule-governed, multi-agent execution platform with full IPT (Intelligent Process Thread) isolation, MCP routing, sandbox simulation, and an immutable audit trail.

## Quick start

```bash
# Run smoke tests
python -m aurex.cli test

# Load + validate an IPT
python -m aurex.cli load-ipt aurex/_ipt_data/IPT-01

# Run a sandbox replay
python -m aurex.cli sandbox aurex/_ipt_data/IPT-01 --days 10 --capital 100000

# View the audit log
python -m aurex.cli audit --format json
```

## Architecture

```
aurex/
├── core/          # Primitives + platform immutable rules
├── rules/         # DSL evaluator, store, hot-reload
├── ipt/           # IPT loader + registry
├── mcp/           # MCP adapters (simulated + plug-in real)
├── gateway/       # Single choke point — enforces rules before routing
├── agents/        # Rule-first agent cognition loop + built-ins
├── orchestrator/  # Pipeline runner + aggregation + gateway dispatch
├── sandbox/       # Replay engine + report
├── audit/         # Append-only JSON-line audit trail
├── registry/      # Plug-in registry for agents/MCP/IPT templates
├── tests/         # Smoke tests + IPT fixture
├── _ipt_data/     # On-disk IPT definitions (data folder, not a Python module)
└── cli.py         # `python -m aurex.cli`
```

## Layers

1. **DSL + Rule store** — JSON-Logic-compatible expression language; rules + guidelines hot-reload from disk.
2. **Agent cognition loop** — every agent receives hard rules + guidelines and must produce a standard JSON output; the orchestrator re-checks rules independently.
3. **MCP Gateway** — the only path to MCP endpoints; evaluates platform rules → IPT rules → endpoint allowlist → routes to sandbox or live.
4. **Sandbox** — replays historical periods, injects synthetic news, simulates MCP endpoints, produces a report.
5. **IPTs** — isolated universes with their own rules, guidelines, and endpoints. No cross-IPT contamination.
6. **Audit trail** — every agent decision, rule check, MCP call, and violation attempt is logged as JSON.

## Platform-level immutable rules

Cannot be modified by users or agents. Enforced at the gateway:

- No real-money MCP calls in SANDBOX mode
- Agents cannot modify rules, guidelines, prompts, or memory
- All MCP calls must pass rule checks
- All actions must be logged
- Deny by default
- No cross-IPT contamination
- No irreversible action without explicit user approval
- Rules must be machine-readable (enforced at authoring time)

## Adding a new IPT

```bash
mkdir aurex/_ipt_data/MyIPT/rules
mkdir aurex/_ipt_data/MyIPT/guidelines
# Write config.json, mcp_endpoints.json, and your rules
python -m aurex.cli load-ipt aurex/_ipt_data/MyIPT
```

## Adding a new agent

```python
from aurex.agents.agent import LLMRunner, RuleFirstAgent

def my_agent(ipt, llm):
    return RuleFirstAgent(
        name="MyAgent",
        llm=llm,
        rules_provider=lambda: ipt.rule_store.rules,
        guidelines_provider=lambda: ipt.rule_store.guidelines,
    )

from aurex.orchestrator.orchestrator import Orchestrator
orch = Orchestrator(audit=..., gateway=..., agent_pipeline=["MyAgent", ...])
```

## Adding a real MCP adapter

```python
from aurex.mcp.base import MCPAdapter, MCPRequest, MCPResponse

class MyBroker:
    name = "my_broker"
    endpoint_group = "BROKER"

    def handle(self, request: MCPRequest) -> MCPResponse:
        # call real broker SDK here
        return MCPResponse(request_id=request.request_id, ok=True, payload={...})

    def health(self) -> dict:
        return {"ok": True}

from aurex.registry.registry import GLOBAL_REGISTRY
GLOBAL_REGISTRY.register_mcp("my.broker.MyBroker", MyBroker())
```

Then point your IPT's `mcp_endpoints.json` `live` field at the registered key.

## Tests

```bash
python -m aurex.cli test
```

Exercises every layer: DSL evaluator, platform rules, IPT loading, rule engine, gateway sandbox safety, orchestrator pipeline, sandbox replay, and audit trail round-trip.

## License

Educational and prototyping use. No real-money execution is supported out of the box.