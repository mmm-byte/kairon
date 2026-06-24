"""
kairon/intelligence/llm_explainer.py
LLM-agnostic explanation generator. Tries Ollama first (free, local),
then OpenAI/Anthropic if configured. Falls back to a deterministic
template when no LLM is available. All explanations are hedged per Document 18.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from kairon.config import cfg
from kairon.data.source_status import source_status

logger = logging.getLogger("kairon.llm")

# System prompt enforcing Document 18 prohibited claims
SYSTEM_PROMPT = """You are a financial education assistant for Kairon, a simulation platform.
RULES:
- Always express uncertainty. Use "historically", "tends to", "the data suggests".
- Never say "will" or "guaranteed". Say "may", "could", "analysis indicates".
- Never say "you should buy/sell". Say "the signal suggests" or "the setup indicates".
- Note that past patterns may not repeat.
- Keep explanation under 120 words. Be specific about the key drivers.
- End with one key risk to watch.
- This is for educational simulation only — not financial advice."""


def _build_user_prompt(asset: str, market: str, decision: str, composite: float,
                       agent_signals: dict, regime: str, costs: dict,
                       key_risks: list) -> str:
    tech  = agent_signals.get("technical",    {}).get("signal", 0)
    fund  = agent_signals.get("fundamental",  {}).get("signal", 0)
    news  = agent_signals.get("news",         {}).get("signal", 0)
    mac   = agent_signals.get("macro",        {}).get("signal", 0)
    cross = agent_signals.get("cross_market", {}).get("signal", 0)
    net   = costs.get("total_cost_pct", 0)

    risk_str = "; ".join(key_risks[:2]) if key_risks else "none identified"
    return (
        f"Generate a brief explanation for this {asset} ({market}) analysis:\n"
        f"Decision: {decision} | Composite score: {composite:+.2f}\n"
        f"Agents: Technical={tech:+.2f}, Fundamental={fund:+.2f}, "
        f"News={news:+.2f}, Macro={mac:+.2f}, Cross-market={cross:+.2f}\n"
        f"Macro regime: {regime}\n"
        f"Transaction costs: {net:.2f}%\n"
        f"Key risks: {risk_str}"
    )


def _call_ollama(prompt: str) -> Optional[str]:
    """Call local Ollama instance."""
    try:
        payload = json.dumps({
            "model": cfg.llm_model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 200},
        }).encode()
        req = urllib.request.Request(
            f"{cfg.ollama_base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = data.get("response", "").strip()
        if text:
            source_status.mark_healthy("ollama")
            return text
    except urllib.error.URLError:
        source_status.mark_unavailable("ollama", "Not running — install Ollama for AI explanations")
    except Exception as e:
        source_status.mark_degraded("ollama", str(e)[:80])
    return None


def _call_openai(prompt: str) -> Optional[str]:
    if not cfg.openai_api_key:
        return None
    try:
        payload = json.dumps({
            "model": cfg.llm_model if cfg.llm_model != "llama3.2" else "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": 200,
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.openai_api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"].strip()
        if text:
            source_status.mark_healthy("openai")
            return text
    except Exception as e:
        source_status.mark_degraded("openai", str(e)[:80])
    return None


def _template_explanation(asset: str, market: str, decision: str,
                           composite: float, agent_signals: dict,
                           regime: str, key_risks: list) -> str:
    """
    Deterministic template explanation — always available, no LLM required.
    Follows Document 18 hedged language rules.
    """
    direction = "bullish" if composite > 0 else "bearish"
    strength  = "strong" if abs(composite) > 0.6 else ("moderate" if abs(composite) > 0.3 else "weak")

    tech  = agent_signals.get("technical",   {}).get("signal", 0)
    mac   = agent_signals.get("macro",       {}).get("signal", 0)
    news  = agent_signals.get("news",        {}).get("signal", 0)

    drivers = []
    if abs(tech) > 0.2:
        drivers.append(f"technical momentum is {'positive' if tech > 0 else 'negative'}")
    if abs(mac) > 0.2:
        drivers.append(f"the {regime} macro regime {'favours' if mac > 0 else 'challenges'} {market}")
    if abs(news) > 0.2:
        drivers.append(f"news sentiment is {'constructive' if news > 0 else 'cautious'}")

    driver_str = ", ".join(drivers) if drivers else "mixed signals across agents"
    risk_str   = key_risks[0] if key_risks else "data may not reflect real-time market conditions"

    return (
        f"{asset} analysis indicates a {strength} {direction} setup (score {composite:+.2f}). "
        f"The data suggests {driver_str}. "
        f"Decision: {decision}. "
        f"Key risk to watch: {risk_str}. "
        f"[AI explanation unavailable — template used · Not financial advice]"
    )


def generate_explanation(asset: str, market: str, decision: str,
                          composite: float, agent_signals: dict,
                          regime: str, costs: dict, key_risks: list) -> str:
    """
    Try LLM providers in order: Ollama → OpenAI → template fallback.
    Always returns a string. Never raises.
    """
    prompt = _build_user_prompt(asset, market, decision, composite,
                                 agent_signals, regime, costs, key_risks)

    # 1. Ollama (local, free)
    if cfg.llm_provider in ("ollama", "auto"):
        text = _call_ollama(prompt)
        if text:
            return text

    # 2. OpenAI
    if cfg.llm_provider in ("openai", "auto") and cfg.openai_api_key:
        text = _call_openai(prompt)
        if text:
            return text

    # 3. Template fallback
    logger.info("Using template explanation (no LLM available)")
    return _template_explanation(asset, market, decision, composite,
                                  agent_signals, regime, key_risks)
