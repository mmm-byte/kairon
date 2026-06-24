"""
kairon/intelligence/explainability.py
Five-layer explainability chain (Document 15) and full connection graph (Document 14).
Converts raw prediction data into human-readable causal chains.
"""
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("kairon.explain")


# ── Layer 1: Raw signals ──────────────────────────────────────────────────────
def build_layer1_raw_signals(indicators: dict, macro: dict, news: dict) -> dict:
    """What is the data saying right now?"""
    rsi     = indicators.get("rsi")
    macd    = indicators.get("macd")
    mh      = indicators.get("macd_hist")
    close   = indicators.get("close")
    ret_1d  = indicators.get("return_1d")
    vr      = indicators.get("vol_ratio")
    vix     = macro.get("vix")
    dxy     = macro.get("dxy")
    ry      = macro.get("real_yield_10y")
    fed     = macro.get("fed_rate")
    y10     = macro.get("yield_10y")
    gtone   = news.get("gdelt_tone_72h")
    gment   = news.get("gdelt_mentions")
    nlabel  = news.get("sentiment_label", "neutral")

    signals = []

    if close:
        chg_str = f"{'+' if (ret_1d or 0) >= 0 else ''}{(ret_1d or 0)*100:.2f}% today" if ret_1d else ""
        signals.append({"label": "Price", "value": f"${close:,.2f} {chg_str}",
                         "source": "Yahoo Finance", "type": "price"})
    if rsi:
        interp = ("overbought" if rsi > 70 else ("oversold" if rsi < 30 else "neutral"))
        signals.append({"label": "RSI (14)", "value": f"{rsi:.1f} — {interp}",
                         "source": "Computed", "type": "technical"})
    if macd is not None and mh is not None:
        macd_dir = "expanding" if mh > 0 else "contracting"
        signals.append({"label": "MACD", "value": f"{macd:+.3f} (histogram {macd_dir})",
                         "source": "Computed", "type": "technical"})
    if vr:
        signals.append({"label": "Volume ratio", "value": f"{vr:.2f}× average",
                         "source": "Computed", "type": "technical"})
    if vix:
        vix_label = "fear elevated" if vix > 25 else ("calm" if vix < 18 else "moderate")
        signals.append({"label": "VIX", "value": f"{vix:.1f} ({vix_label})",
                         "source": "FRED / Yahoo", "type": "macro"})
    if dxy:
        signals.append({"label": "DXY (dollar)", "value": f"{dxy:.1f}",
                         "source": "FRED / Yahoo", "type": "macro"})
    if ry is not None:
        signals.append({"label": "10Y real yield", "value": f"{ry:.2f}%",
                         "source": "FRED", "type": "macro"})
    if fed:
        signals.append({"label": "Fed funds rate", "value": f"{fed:.2f}%",
                         "source": "FRED", "type": "macro"})
    if gtone is not None:
        tone_label = "positive" if gtone > 1 else ("negative" if gtone < -1 else "neutral")
        signals.append({
            "label":  "GDELT 72h tone",
            "value":  f"{gtone:+.1f} ({tone_label})" + (f", {gment:,} mentions" if gment else ""),
            "source": "GDELT Project",
            "type":   "news",
        })

    return {"signals": signals, "summary": f"{len(signals)} raw data points collected"}


# ── Layer 2: Pattern recognition ──────────────────────────────────────────────
def build_layer2_patterns(indicators: dict, macro: dict, news: dict, market: str) -> dict:
    """What do these signals mean when seen together?"""
    patterns = []

    rsi  = indicators.get("rsi") or 50
    macd = indicators.get("macd") or 0
    mh   = indicators.get("macd_hist") or 0
    vr   = indicators.get("vol_ratio") or 1
    tr   = indicators.get("trend", "neutral")
    vix  = macro.get("vix") or 14
    dxy  = macro.get("dxy") or 104
    ry   = macro.get("real_yield_10y") or 2
    tone = news.get("gdelt_tone_72h") or 0

    # Technical patterns
    if tr in ("bullish", "mixed_bullish") and rsi > 50 and mh > 0:
        patterns.append({
            "name":     "Technical Breakout Pattern",
            "signals":  f"RSI {rsi:.0f} + MACD expanding + {tr} trend",
            "meaning":  "Momentum building with volume confirmation",
            "direction":"bullish",
            "strength": "strong" if rsi > 60 and mh > 0.5 else "moderate",
        })
    elif tr in ("bearish", "mixed_bearish") and rsi < 50:
        patterns.append({
            "name":     "Technical Breakdown Pattern",
            "signals":  f"RSI {rsi:.0f} + MACD contracting + {tr} trend",
            "meaning":  "Downtrend with weakening momentum",
            "direction":"bearish",
            "strength": "strong" if rsi < 40 else "moderate",
        })

    # Macro patterns
    if ry < 1.0 and market == "commodities":
        patterns.append({
            "name":     "Dollar Weakness / Low Real Yield Pattern",
            "signals":  f"Real yield {ry:.2f}% + DXY {dxy:.1f}",
            "meaning":  "Low real yields reduce opportunity cost of holding gold/commodities",
            "direction":"bullish" if ry < 1.5 else "neutral",
            "strength": "strong" if ry < 0.5 else "moderate",
        })
    if dxy > 105:
        patterns.append({
            "name":     "Strong Dollar Pattern",
            "signals":  f"DXY {dxy:.1f} (above 105)",
            "meaning":  "Strong USD headwind for dollar-denominated commodities",
            "direction":"bearish",
            "strength": "moderate",
        })

    # Fear / risk-off patterns
    if vix > 22:
        patterns.append({
            "name":     "Early Risk-Off Signal",
            "signals":  f"VIX {vix:.1f} (above 22 threshold)",
            "meaning":  "Rising fear — capital flows to safe havens",
            "direction":"bullish" if market in ("commodities","bonds") else "bearish",
            "strength": "strong" if vix > 30 else "moderate",
        })
    elif vix < 16:
        patterns.append({
            "name":     "Risk-On Complacency",
            "signals":  f"VIX {vix:.1f} (low fear)",
            "meaning":  "Low fear supports risk assets",
            "direction":"bullish" if market in ("stocks","crypto","real_estate") else "neutral",
            "strength": "moderate",
        })

    # News sentiment patterns
    if abs(tone) > 2:
        patterns.append({
            "name":     "Significant News Sentiment Pattern",
            "signals":  f"GDELT 72h tone: {tone:+.1f}",
            "meaning":  f"{'Positive' if tone > 0 else 'Negative'} global media sentiment",
            "direction":"bullish" if tone > 0 else "bearish",
            "strength": "strong" if abs(tone) > 4 else "moderate",
        })

    return {"patterns": patterns, "n_patterns": len(patterns)}


# ── Layer 3: Cross-signal correlation ─────────────────────────────────────────
def build_layer3_cross_signal(patterns: list, agent_signals: dict) -> dict:
    """How do these patterns reinforce or contradict each other?"""
    bull_count = sum(1 for p in patterns if p.get("direction") == "bullish")
    bear_count = sum(1 for p in patterns if p.get("direction") == "bearish")
    n          = len(patterns)

    agent_directions = {
        a: ("bullish" if s.get("signal", 0) > 0.1 else
            ("bearish" if s.get("signal", 0) < -0.1 else "neutral"))
        for a, s in agent_signals.items()
    }
    all_directions = list(agent_directions.values())
    agent_agreement = (
        all_directions.count("bullish") > len(all_directions) * 0.6 or
        all_directions.count("bearish") > len(all_directions) * 0.6
    )

    if bull_count >= n * 0.75:
        conviction = "HIGH CONVICTION" if agent_agreement else "MODERATE CONVICTION"
        direction  = "bullish"
        summary    = f"All {n} patterns consistent in bullish direction"
    elif bear_count >= n * 0.75:
        conviction = "HIGH CONVICTION" if agent_agreement else "MODERATE CONVICTION"
        direction  = "bearish"
        summary    = f"All {n} patterns consistent in bearish direction"
    elif bull_count > bear_count:
        conviction = "MODERATE"
        direction  = "mixed_bullish"
        summary    = f"{bull_count}/{n} patterns bullish, {bear_count}/{n} bearish — mixed but bullish lean"
    elif bear_count > bull_count:
        conviction = "MODERATE"
        direction  = "mixed_bearish"
        summary    = f"{bear_count}/{n} patterns bearish — mixed but bearish lean"
    else:
        conviction = "LOW — MIXED SIGNALS"
        direction  = "neutral"
        summary    = f"Signals split equally — no clear conviction"

    agreements     = []
    contradictions = []
    for i, p1 in enumerate(patterns):
        for p2 in patterns[i+1:]:
            if p1.get("direction") == p2.get("direction"):
                agreements.append(f"{p1['name']} + {p2['name']} AGREE → both {p1['direction']}")
            elif (p1.get("direction") in ("bullish","bearish") and
                  p2.get("direction") in ("bullish","bearish") and
                  p1.get("direction") != p2.get("direction")):
                contradictions.append(f"{p1['name']} CONTRADICTS {p2['name']}")

    return {
        "conviction":      conviction,
        "direction":       direction,
        "summary":         summary,
        "agreements":      agreements[:3],
        "contradictions":  contradictions[:2],
        "agent_agreement": agent_agreement,
    }


# ── Layer 4: Historical precedent ────────────────────────────────────────────
def build_layer4_precedent(kb_context: dict) -> dict:
    """When has this combination appeared before, and what happened?"""
    n       = kb_context.get("n_similar", 0)
    nc      = kb_context.get("n_correct", 0)
    acc     = kb_context.get("accuracy", 0.5)
    avg_ret = kb_context.get("avg_return", 0)
    matches = kb_context.get("top_matches", [])

    if n == 0:
        return {
            "has_history":  False,
            "summary":      "No similar situations found yet — KB is building",
            "matches":      [],
            "lesson":       "Insufficient history for pattern matching",
        }

    lesson = None
    if acc >= 0.80 and n >= 5:
        lesson = (f"Strong historical pattern: {nc}/{n} similar situations were correct "
                  f"(avg return {avg_ret*100:+.1f}%). High confidence from KB.")
    elif acc >= 0.65:
        lesson = (f"Moderate historical pattern: {nc}/{n} similar situations were correct.")
    elif acc < 0.45:
        lesson = (f"WARNING: In similar past situations, only {nc}/{n} ({acc:.0%}) were correct. "
                  f"KB reduces confidence on this signal.")
    else:
        lesson = f"Mixed historical pattern: {nc}/{n} similar situations ({acc:.0%}) correct."

    failure_cases = [m for m in matches if m.get("outcome") == "WRONG"]
    failure_note  = None
    if failure_cases:
        failure_note = (f"Last incorrect: {failure_cases[0].get('date','?')} "
                        f"— {failure_cases[0].get('notes','')[:80]}")

    return {
        "has_history":   True,
        "n_similar":     n,
        "n_correct":     nc,
        "accuracy":      acc,
        "avg_return":    avg_ret,
        "summary":       f"KB found {n} similar situations: {nc} correct ({acc:.0%})",
        "lesson":        lesson,
        "matches":       matches[:5],
        "failure_note":  failure_note,
    }


# ── Layer 5: Forward projection ───────────────────────────────────────────────
def build_layer5_projection(composite: float, confidence: float, kb: dict,
                              horizon_days: int, costs: dict, asset: str) -> dict:
    """Given all of the above, what is likely to happen next?"""
    direction = "UP" if composite > 0 else "DOWN"
    strength  = abs(composite)
    acc       = kb.get("accuracy", 0.5)
    avg_ret   = abs(kb.get("avg_return", 0)) if kb.get("has_history") else strength * 0.02

    # Base case
    base_ret_pct  = max(avg_ret, strength * 0.02) * 100
    base_conf     = min(95, int(confidence * 100))
    bear_conf     = 100 - base_conf

    base_driver   = []
    if composite > 0.3:
        base_driver.append("Momentum continues with volume confirmation")
    if kb.get("has_history") and acc > 0.65:
        nc = kb.get("n_correct", 0)
        ns = kb.get("n_similar", 0)
        base_driver.append(f"KB: {nc}/{ns} similar setups confirm")

    bear_triggers = []
    bear_triggers.append("Signal reverses below key technical support")
    bear_triggers.append("Unexpected macro shock (CPI, Fed surprise)")
    if horizon_days > 3:
        bear_triggers.append("Time decay — signal weakens if no follow-through")

    net_cost_pct = costs.get("total_cost_pct", 0.4)
    net_ret_pct  = base_ret_pct - net_cost_pct

    return {
        "direction":          direction,
        "base_case_return":   round(base_ret_pct, 2),
        "base_confidence":    base_conf,
        "net_return_after_costs": round(net_ret_pct, 2),
        "bear_confidence":    bear_conf,
        "horizon_days":       horizon_days,
        "base_drivers":       base_driver,
        "bear_triggers":      bear_triggers[:3],
        "summary":            (
            f"Base case ({base_conf}%): {asset} {'rises' if direction=='UP' else 'falls'} "
            f"~{base_ret_pct:.1f}% in {horizon_days} days. "
            f"Bear case ({bear_conf}%): flat or reversal."
        ),
    }


# ── Connection graph builder ───────────────────────────────────────────────────
def build_connection_graph(
    asset:         str,
    indicators:    dict,
    macro:         dict,
    news:          dict,
    agent_signals: dict,
    kb_context:    dict,
    composite:     float,
    decision:      str,
) -> dict:
    """
    Build a full directed connection graph (Document 14).
    Nodes = data points, Edges = causal relationships.
    """
    nodes = []
    edges = []
    node_id = [0]

    def add_node(type_: str, label: str, value: float, source: str) -> str:
        nid = f"n{node_id[0]}"
        node_id[0] += 1
        nodes.append({"id": nid, "type": type_, "label": label,
                       "value": round(value, 3), "source": source})
        return nid

    def add_edge(src: str, tgt: str, weight: float, direction: str, label: str):
        if abs(weight) > 0.03:
            edges.append({
                "source":    src, "target": tgt,
                "weight":    round(abs(weight), 3),
                "direction": direction,
                "label":     label,
            })

    # World events
    gdelt_tone = news.get("gdelt_tone_72h") or 0
    gment      = news.get("gdelt_mentions") or 0
    n_gdelt    = add_node("world_event",
                           f"Global news: {gment:,} mentions, tone {gdelt_tone:+.1f}",
                           gdelt_tone / 10, "GDELT")

    # Macro indicators
    vix   = macro.get("vix") or 14
    dxy   = macro.get("dxy") or 104
    ry    = macro.get("real_yield_10y") or 2
    fed   = macro.get("fed_rate") or 4.33
    yc    = macro.get("yield_curve", "flat")
    n_vix = add_node("macro_indicator", f"VIX {vix:.1f}", -(vix - 15) / 30, "FRED/Yahoo")
    n_dxy = add_node("macro_indicator", f"DXY {dxy:.1f}", -(dxy - 103) / 5, "FRED/Yahoo")
    n_ry  = add_node("macro_indicator", f"Real yield {ry:.2f}%", -ry / 3, "FRED")
    n_fed = add_node("macro_indicator", f"Fed rate {fed:.2f}%", -fed / 8, "FRED")

    # Price signals
    rsi   = indicators.get("rsi") or 50
    macd  = indicators.get("macd") or 0
    trend = indicators.get("trend", "neutral")
    n_rsi  = add_node("price_signal", f"RSI {rsi:.0f}", (rsi - 50) / 50, "Yahoo Finance")
    n_macd = add_node("price_signal", f"MACD {macd:+.2f}", macd / 20, "Yahoo Finance")
    n_trnd = add_node("price_signal", f"Trend: {trend}", 0.7 if "bullish" in trend else -0.5, "Yahoo Finance")

    # Agent signals
    agent_nodes = {}
    for ag, info in agent_signals.items():
        s = info.get("signal", 0)
        n = add_node("agent_signal", f"{ag.replace('_',' ').title()}: {s:+.2f}", s, f"Agent/{ag}")
        agent_nodes[ag] = n

    # KB match
    n_kb = add_node("kb_match",
                     f"KB: {kb_context.get('n_correct',0)}/{kb_context.get('n_similar',0)} similar correct",
                     kb_context.get("accuracy", 0.5), "Knowledge Base")

    # Final signal
    n_fin = add_node("final_signal", f"{decision} {asset}", composite, "Signal Fusion")

    # ── Causal edges ──────────────────────────────────────────────────────────
    # GDELT → news agent
    if "news" in agent_nodes:
        add_edge(n_gdelt, agent_nodes["news"], abs(gdelt_tone) / 10,
                 "positive" if gdelt_tone > 0 else "negative",
                 "news sentiment feeds agent")

    # Real yield → DXY (rate drives dollar)
    add_edge(n_ry, n_dxy, 0.6, "positive" if ry > 2 else "negative",
             "real yields influence dollar strength")

    # DXY → technical (dollar affects commodity pricing)
    if "cross_market" in agent_nodes:
        dxy_impact = -0.68 if "commodit" in asset.lower() else -0.2
        add_edge(n_dxy, agent_nodes["cross_market"], abs(dxy_impact),
                 "positive" if dxy < 103 else "negative",
                 "dollar strength → asset headwind/tailwind")

    # VIX → macro agent
    if "macro" in agent_nodes:
        add_edge(n_vix, agent_nodes["macro"], 0.7,
                 "negative" if vix > 18 else "positive",
                 "fear index shapes macro regime")

    # RSI + MACD → technical agent
    if "technical" in agent_nodes:
        add_edge(n_rsi,  agent_nodes["technical"], 0.5,
                 "positive" if rsi > 50 else "negative", "RSI momentum")
        add_edge(n_macd, agent_nodes["technical"], 0.6,
                 "positive" if macd > 0 else "negative", "MACD direction")
        add_edge(n_trnd, agent_nodes["technical"], 0.7,
                 "positive" if "bullish" in trend else "negative", "trend alignment")

    # All agents → final signal
    for ag, nid in agent_nodes.items():
        s = agent_signals.get(ag, {}).get("signal", 0)
        add_edge(nid, n_fin, abs(s),
                 "positive" if s > 0 else "negative",
                 f"{ag.replace('_',' ')} contributes to composite")

    # KB → final signal (history adjustment)
    kb_acc = kb_context.get("accuracy", 0.5)
    kb_adj = (kb_acc - 0.5) * 0.3
    add_edge(n_kb, n_fin, abs(kb_adj),
             "positive" if kb_adj > 0 else "negative",
             "KB historical accuracy adjusts confidence")

    # Fed → macro agent
    if "macro" in agent_nodes:
        add_edge(n_fed, agent_nodes["macro"], 0.5,
                 "positive" if fed < 3 else "negative",
                 "policy rate shapes macro outlook")

    return {
        "nodes":           nodes,
        "edges":           edges,
        "n_nodes":         len(nodes),
        "n_edges":         len(edges),
        "decision":        decision,
        "asset":           asset,
        "composite_score": round(composite, 4),
    }


# ── Master explainability builder ─────────────────────────────────────────────
def build_full_explanation(
    asset:         str,
    market:        str,
    ticker:        str,
    decision:      str,
    composite:     float,
    confidence:    float,
    indicators:    dict,
    macro:         dict,
    news:          dict,
    agent_signals: dict,
    kb_context:    dict,
    costs:         dict,
    horizon_days:  int,
) -> dict:
    """
    Build all 5 layers + connection graph in one call.
    This is what the API serves for full prediction transparency.
    """
    layer1 = build_layer1_raw_signals(indicators, macro, news)
    layer2 = build_layer2_patterns(indicators, macro, news, market)
    layer3 = build_layer3_cross_signal(layer2["patterns"], agent_signals)
    layer4 = build_layer4_precedent(kb_context)
    layer5 = build_layer5_projection(composite, confidence, kb_context,
                                      horizon_days, costs, asset)
    graph  = build_connection_graph(asset, indicators, macro, news,
                                     agent_signals, kb_context, composite, decision)

    # Increasing / decreasing forces (for Connection Map screen)
    increasing = []
    decreasing = []
    for ag, info in agent_signals.items():
        s = info.get("signal", 0)
        label = ag.replace("_", " ").title()
        if s > 0.1:
            increasing.append({"factor": label, "contribution": round(s, 3),
                                "evidence": info.get("reasoning", "")[:80]})
        elif s < -0.1:
            decreasing.append({"factor": label, "contribution": round(s, 3),
                                "evidence": info.get("reasoning", "")[:80]})

    increasing.sort(key=lambda x: x["contribution"], reverse=True)
    decreasing.sort(key=lambda x: x["contribution"])

    return {
        "layer1_raw_signals":    layer1,
        "layer2_patterns":       layer2,
        "layer3_cross_signal":   layer3,
        "layer4_precedent":      layer4,
        "layer5_projection":     layer5,
        "connection_graph":      graph,
        "increasing_forces":     increasing[:5],
        "decreasing_forces":     decreasing[:5],
        "overall_conviction":    layer3["conviction"],
        "overall_direction":     layer3["direction"],
        "summary":               layer5["summary"],
    }
