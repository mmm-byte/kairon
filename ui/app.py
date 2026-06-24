"""
kairon/ui/app.py
Complete Streamlit UI — all 6 screens from Document 09 + Screen 6 (Document 21).
Dark terminal / mission control aesthetic.
Run with: streamlit run kairon/ui/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import json
import time
import math
from datetime import datetime, timezone


import streamlit as st
import pandas as pd

# Fix for broker formats NameError
from kairon.engine.portfolio import BROKER_CSV_FORMATS

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Kairon — Financial Intelligence",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — dark terminal aesthetic ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #080b0f !important;
    color: #e8edf5;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
}
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #1e2a38;
}
.main .block-container { padding: 1.2rem 1.5rem; max-width: 1400px; }
h1,h2,h3,h4 { color: #e8edf5 !important; font-family: 'Syne','Segoe UI',sans-serif !important; }

/* ── KPI Cards ── */
.kpi-card {
    background: #111820;
    border: 1px solid #1e2a38;
    border-top: 3px solid;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 8px;
}
.kpi-value { font-size: 1.6rem; font-weight: 700; font-family: 'JetBrains Mono',monospace; }
.kpi-label { font-size: 0.72rem; color: #7a8496; text-transform: uppercase; letter-spacing: 1px; }
.kpi-sub   { font-size: 0.8rem; color: #7a8496; margin-top: 2px; }

/* ── Badges ── */
.badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.72rem; font-weight:600; }
.badge-green  { background:#003320; color:#00e676; border:1px solid #00e676; }
.badge-red    { background:#3a0010; color:#ff3d57; border:1px solid #ff3d57; }
.badge-amber  { background:#2a1800; color:#ffb300; border:1px solid #ffb300; }
.badge-blue   { background:#001a3a; color:#2979ff; border:1px solid #2979ff; }
.badge-purple { background:#1a0030; color:#aa00ff; border:1px solid #aa00ff; }
.badge-gray   { background:#1a1a1a; color:#7a8496; border:1px solid #3d4558; }
.sim-badge    { background:#2a1800; color:#ffb300; border:1px solid #ffb300;
                padding:3px 10px; border-radius:4px; font-size:0.72rem; font-weight:700; }

/* ── Move cards ── */
.move-card {
    background: #0d1117;
    border: 1px solid #1e2a38;
    border-radius: 8px;
    padding: 18px;
    margin-bottom: 16px;
}
.move-card-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 14px; padding-bottom: 10px;
    border-bottom: 1px solid #1e2a38;
}
.move-title { font-size:1.05rem; font-weight:700; color:#e8edf5; }

/* ── Agent cards ── */
.agent-card {
    background: #111820;
    border: 1px solid #1e2a38;
    border-radius: 6px;
    padding: 14px;
    height: 100%;
}
.agent-score { font-size:1.8rem; font-weight:700; font-family:'JetBrains Mono',monospace; }

/* ── Progress bars ── */
.bar-track { background:#1e2a38; border-radius:3px; height:6px; overflow:hidden; margin: 4px 0; }
.bar-fill  { height:100%; border-radius:3px; }

/* ── Disclaimer ── */
.disclaimer-strip {
    background:#111820; border-left:3px solid #ffb300;
    padding:8px 14px; border-radius:0 4px 4px 0;
    color:#7a8496; font-size:0.75rem; margin-bottom:16px;
}
.ai-attr { font-size:0.68rem; color:#3d4558; font-style:italic; margin-top:4px; }

/* ── Tables ── */
.market-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; }
.market-table th { color:#7a8496; font-size:0.72rem; text-transform:uppercase;
                   letter-spacing:1px; border-bottom:1px solid #1e2a38; padding:6px 8px; }
.market-table td { padding:8px; border-bottom:1px solid #111820; font-size:0.88rem; }
.market-table tr:hover td { background:#0d1117; }

/* ── Sidebar nav ── */
[data-testid="stSidebarNav"] { display: none; }
.nav-item { padding:8px 14px; border-radius:5px; cursor:pointer;
            color:#7a8496; font-size:0.88rem; margin-bottom:2px; }
.nav-item:hover { background:#161e28; color:#e8edf5; }
.nav-item-active { background:#161e28; color:#00e676; border-left:3px solid #00e676; }

/* ── Live dot ── */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.live-dot { width:8px; height:8px; background:#00e676; border-radius:50%;
            animation:pulse 2s infinite; display:inline-block; margin-right:6px; }

/* ── Cost waterfall ── */
.cost-row { display:flex; align-items:center; justify-content:space-between;
            padding:4px 0; font-size:0.82rem; }
.cost-label { color:#7a8496; }
.cost-value { font-family:'JetBrains Mono',monospace; }
.cost-positive { color:#00e676; }
.cost-negative { color:#ff3d57; }
.cost-zero     { color:#3d4558; }
.cost-divider  { border-top:1px solid #1e2a38; margin:6px 0; }
.cost-total    { font-weight:700; }

/* ── Regime chip ── */
.regime-chip { padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; display:inline-block; }
.regime-calm    { background:#003320; color:#00e676; }
.regime-risk-off{ background:#3a0010; color:#ff3d57; }
.regime-inflation{ background:#2a1800; color:#ffb300; }
.regime-crisis  { background:#1a0030; color:#aa00ff; }
.regime-stagflation{ background:#1a1a1a; color:#7a8496; }
.regime-deflation  { background:#001a3a; color:#2979ff; }

/* ── Scrollable container ── */
div[data-testid="stVerticalBlock"] > div > div > div[data-testid="element-container"] > div.stMarkdown { 
    margin-bottom: 4px !important; 
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def badge(text: str, color: str = "gray") -> str:
    return f'<span class="badge badge-{color}">{text}</span>'


def signal_badge(sig: str) -> str:
    colors = {"UP": "green", "DOWN": "red", "HOLD": "amber", "BUY": "green",
               "AVOID": "red", "SELL": "red"}
    return badge(sig, colors.get(sig, "gray"))


def kpi_card(label: str, value: str, sub: str = "", color: str = "#00e676") -> str:
    return f"""<div class="kpi-card" style="border-top-color:{color}">
    <div class="kpi-label">{label}</div>
    <div class="kpi-value" style="color:{color}">{value}</div>
    <div class="kpi-sub">{sub}</div>
</div>"""


def score_bar(score: float, label: str) -> str:
    pct    = min(100, abs(score) * 100)
    color  = "#00e676" if score > 0 else "#ff3d57" if score < 0 else "#7a8496"
    sign   = "+" if score > 0 else ""
    return f"""<div style="margin-bottom:8px">
    <div style="display:flex;justify-content:space-between;margin-bottom:3px">
      <span style="color:#7a8496;font-size:0.8rem">{label}</span>
      <span style="color:{color};font-family:'JetBrains Mono',monospace;font-size:0.82rem">{sign}{score:.2f}</span>
    </div>
    <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
</div>"""


def regime_chip(regime: str) -> str:
    cls_map = {
        "Risk-On": "calm", "Risk-Off": "risk-off",
        "Inflationary": "inflation", "Deflationary": "deflation",
        "Stagflationary": "stagflation", "Crisis": "crisis",
    }
    cls = cls_map.get(regime, "calm")
    return f'<span class="regime-chip regime-{cls}">{regime}</span>'


def _fmt_usd(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v:,.0f}"
    return f"${v:.2f}"


def _fmt_pct(v: float, digits: int = 1) -> str:
    s = "+" if v >= 0 else ""
    return f"{s}{v:.{digits}f}%"


# ── State ─────────────────────────────────────────────────────────────────────
if "regime_override" not in st.session_state:
    st.session_state.regime_override = None
if "screen" not in st.session_state:
    st.session_state.screen = "Mission Control"
if "executed_predictions" not in st.session_state:
    st.session_state.executed_predictions = set()
if "moves_cache" not in st.session_state:
    st.session_state.moves_cache = None
if "moves_cached_at" not in st.session_state:
    st.session_state.moves_cached_at = 0
if "portfolio_capital" not in st.session_state:
    from kairon.config import cfg
    st.session_state.portfolio_capital = cfg.portfolio_capital


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""<div style="padding:16px 8px 8px">
            <span style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:#e8edf5">
            Kai<span style="color:#00e676">ron</span></span>
            <span class="live-dot" style="margin-left:10px"></span>
        </div>""", unsafe_allow_html=True)

        # SIM badge (always visible — Document 18)
        st.markdown('<div style="padding:0 8px 12px"><span class="sim-badge">SIM MODE — Not financial advice</span></div>',
                    unsafe_allow_html=True)

        st.divider()

        # Navigation
        screens = [
            ("🌐", "Mission Control"),
            ("⚡", "Move Recommendations"),
            ("🧠", "Agent Intelligence"),
            ("📚", "Knowledge Base"),
            ("🧮", "Cost Calculator"),
            ("🕸️", "Connection Map"),
            ("📁", "Portfolio Loader"),
            ("🔬", "Backtesting"),
        ]
        for icon, name in screens:
            is_active = st.session_state.screen == name
            style = "nav-item nav-item-active" if is_active else "nav-item"
            if st.button(f"{icon}  {name}", key=f"nav_{name}",
                         width='stretch',
                         type="primary" if is_active else "secondary"):
                st.session_state.screen = name
                st.rerun()

        st.divider()

        # Portfolio value
        capital = st.session_state.portfolio_capital
        st.markdown(f"""<div style="padding:12px;background:#111820;border-radius:6px;border:1px solid #1e2a38;margin-bottom:10px">
            <div style="color:#7a8496;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px">SIMULATED PORTFOLIO</div>
            <div style="color:#00e676;font-size:1.4rem;font-weight:700;font-family:'JetBrains Mono',monospace">{_fmt_usd(capital)}</div>
            <div style="color:#3d4558;font-size:0.75rem">Simulation only</div>
        </div>""", unsafe_allow_html=True)

        # Regime switcher
        st.markdown('<div style="color:#7a8496;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">REGIME OVERRIDE</div>',
                unsafe_allow_html=True)
        regimes = ["Auto-detect", "Risk-On", "Risk-Off", "Inflationary", "Crisis"]
        chosen = st.selectbox("Regime Override", regimes, label_visibility="collapsed", key="regime_sel")
        st.session_state.regime_override = None if chosen == "Auto-detect" else chosen

        # Data source status
        st.divider()
        st.markdown('<div style="color:#7a8496;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">DATA SOURCES</div>',
                    unsafe_allow_html=True)
        try:
            from kairon.data.source_status import source_status
            statuses = source_status.all_statuses()
            for s in statuses[:6]:
                dot_color = {"healthy": "#00e676", "degraded": "#ffb300",
                             "unavailable": "#ff3d57"}.get(s["state"], "#3d4558")
                st.markdown(
                    f'<div style="font-size:0.72rem;padding:2px 0">'
                    f'<span style="color:{dot_color}">●</span> '
                    f'<span style="color:#7a8496">{s["display_name"][:22]}</span></div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            st.markdown('<span style="color:#7a8496;font-size:0.75rem">Status unavailable</span>',
                        unsafe_allow_html=True)


# ── Screen 1: Mission Control ─────────────────────────────────────────────────
def screen_mission_control():
    try:
        from kairon.db import database as db
        from kairon.data import macro_data as macro_mod
        from kairon.data.source_status import source_status

        macro  = macro_mod.get_macro_snapshot()
        regime = macro_mod.classify_regime(macro)
        regime_override = st.session_state.regime_override
        if regime_override:
            regime["regime"] = regime_override

        regime_name = regime["regime"]
        vix  = macro.get("vix") or 14.2
        dxy  = macro.get("dxy") or 103.9
        yc   = macro.get("yield_curve", "normal")

        # Header
        st.markdown(f"""<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
            <h1 style="margin:0;font-family:'Syne',sans-serif">Mission Control</h1>
            {regime_chip(regime_name)}
            <span style="color:#3d4558;font-size:0.8rem">{datetime.now(timezone.utc).strftime('%H:%M UTC')}</span>
        </div>""", unsafe_allow_html=True)

        # Disclaimer (Document 18)
        st.markdown('<div class="disclaimer-strip">Educational simulation only · All analysis is AI-generated · Not financial advice · Past patterns may not repeat</div>',
                    unsafe_allow_html=True)

        # KPI row
        kb_stats = {}
        try:
            from kairon.intelligence.knowledge_base import KnowledgeBase
            kb_stats = KnowledgeBase().get_stats()
        except Exception:
            pass

        c1, c2, c3, c4, c5 = st.columns(5)
        capital = st.session_state.portfolio_capital
        fear_greed = max(0, min(100, int(100 - (vix - 10) * 3)))
        fg_label = "Extreme Greed" if fear_greed > 75 else ("Greed" if fear_greed > 55 else
                   ("Neutral" if fear_greed > 45 else ("Fear" if fear_greed > 25 else "Extreme Fear")))
        colors = {"Risk-On": "#00e676", "Risk-Off": "#ff3d57",
                  "Inflationary": "#ffb300", "Crisis": "#aa00ff",
                  "Stagflationary": "#7a8496", "Deflationary": "#2979ff"}
        rc = colors.get(regime_name, "#00e676")

        c1.markdown(kpi_card("Portfolio (sim)", _fmt_usd(capital), "Simulation only", "#00e676"),
                    unsafe_allow_html=True)
        c2.markdown(kpi_card("VIX", f"{vix:.1f}", f"{'Low fear' if vix < 20 else 'Elevated fear'}", rc),
                    unsafe_allow_html=True)
        c3.markdown(kpi_card("DXY", f"{dxy:.1f}", f"Yield curve: {yc}",
                              "#ffb300" if dxy > 105 else "#00e676"), unsafe_allow_html=True)
        total_preds = kb_stats.get("total_predictions", 0)
        accuracy = kb_stats.get("overall_accuracy", 0)
        c4.markdown(kpi_card("KB Accuracy",
                              f"{accuracy*100:.0f}%" if total_preds > 5 else "Building...",
                              f"{total_preds} predictions tracked", "#2979ff"),
                    unsafe_allow_html=True)
        c5.markdown(kpi_card("Fear & Greed", f"{fear_greed}", fg_label,
                              "#00e676" if fear_greed > 50 else "#ff3d57"),
                    unsafe_allow_html=True)

        st.divider()

        # Market snapshot + Sentiment
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("#### Market Snapshot")
            from kairon.data import market_data as mkt
            rows_html = ""
            display_tickers = ["GC=F", "BTC-USD", "SPY", "EURUSD=X", "CL=F", "TLT", "^VIX", "DX-Y.NYB"]
            for ticker in display_tickers:
                info = mkt.ASSETS.get(ticker, {"name": ticker, "market": "unknown"})
                price_data = mkt.fetch_ohlcv(ticker, period="5d")
                df = price_data.get("df")
                if df is None or df.empty:
                    continue
                price  = df["close"].iloc[-1]
                chg_1d = df["close"].pct_change().iloc[-1]
                chg_col = "#00e676" if chg_1d >= 0 else "#ff3d57"
                chg_str = f"{'+' if chg_1d >= 0 else ''}{chg_1d*100:.2f}%"
                stale = "⚠" if price_data.get("stale") else ""
                rows_html += f"""<tr>
                    <td><span style="color:#e8edf5">{info['name']}</span>
                        <span style="color:#3d4558;font-size:0.75rem"> {ticker}</span>{stale}</td>
                    <td style="font-family:'JetBrains Mono',monospace">{price:,.4f}</td>
                    <td style="color:{chg_col};font-family:'JetBrains Mono',monospace">{chg_str}</td>
                    <td><span class="badge badge-{'green' if chg_1d >= 0 else 'red'}">
                        {'↑' if chg_1d >= 0 else '↓'}</span></td>
                </tr>"""

            st.markdown(f"""<table class="market-table">
                <thead><tr>
                    <th>Asset</th><th>Price</th><th>24h Change</th><th>Signal</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("#### Market Sentiment")
            market_sentiments = {
                "Stocks":      0.72 if regime_name == "Risk-On" else -0.38,
                "Crypto":      0.63 if regime_name == "Risk-On" else -0.55,
                "Forex":       -0.38 if regime_name == "Risk-Off" else 0.10,
                "Commodities": 0.81 if regime_name in ("Risk-Off","Inflationary") else 0.25,
                "Bonds":       0.55 if regime_name == "Risk-Off" else -0.20,
                "Real Estate": 0.44 if regime_name == "Risk-On" else -0.15,
            }
            for mkt_name, score in market_sentiments.items():
                color = "#00e676" if score > 0 else "#ff3d57"
                pct   = int(abs(score) * 100)
                st.markdown(f"""<div style="margin-bottom:10px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                        <span style="font-size:0.82rem">{mkt_name}</span>
                        <span style="color:{color};font-family:'JetBrains Mono',monospace;font-size:0.82rem">
                            {'+' if score >= 0 else ''}{score:.2f}</span>
                    </div>
                    <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""<div style="margin-top:14px;padding:10px;background:#111820;border-radius:6px;border:1px solid #1e2a38">
                <div style="color:#7a8496;font-size:0.72rem">FEAR & GREED INDEX</div>
                <div style="font-size:1.4rem;font-weight:700;color:{'#00e676' if fear_greed > 50 else '#ff3d57'};
                     font-family:'JetBrains Mono',monospace">{fear_greed} — {fg_label}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # Correlation heatmap + contagion
        corr_col, alert_col = st.columns([3, 2])
        with corr_col:
            try:
                from kairon.ui.components.correlation_panel import render_correlation_heatmap
                render_correlation_heatmap(regime_name)
            except Exception:
                pass
        with alert_col:
            st.markdown("#### Market Regime Detail")
            vix_trend  = "↑ rising" if vix > 18 else "↓ contained"
            y10        = macro.get("yield_10y") or 4.21
            y2         = macro.get("yield_2y")  or 4.68
            ry         = macro.get("real_yield_10y") or 1.87
            fed        = macro.get("fed_rate") or 4.33
            st.markdown(f"""<div style="background:#111820;border-radius:6px;
                padding:14px;border:1px solid #1e2a38">
                <div style="margin-bottom:10px;font-size:0.85rem">
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">Fed rate</span>
                        <span style="color:#e8edf5;font-family:'JetBrains Mono',monospace">{fed:.2f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">10Y yield</span>
                        <span style="color:#e8edf5;font-family:'JetBrains Mono',monospace">{y10:.2f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">2Y yield</span>
                        <span style="color:#e8edf5;font-family:'JetBrains Mono',monospace">{y2:.2f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">Real yield 10Y</span>
                        <span style="color:{'#ff3d57' if ry < 1 else '#e8edf5'};font-family:'JetBrains Mono',monospace">{ry:.2f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">VIX</span>
                        <span style="color:{'#ff3d57' if vix > 25 else '#ffb300' if vix > 18 else '#00e676'};
                             font-family:'JetBrains Mono',monospace">{vix:.1f} {vix_trend}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e2a38">
                        <span style="color:#7a8496">DXY</span>
                        <span style="color:{'#ffb300' if dxy > 105 else '#e8edf5'};font-family:'JetBrains Mono',monospace">{dxy:.1f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:4px 0">
                        <span style="color:#7a8496">Yield curve</span>
                        <span style="color:{'#ff3d57' if yc == 'inverted' else '#ffb300' if yc == 'flat' else '#00e676'};
                             font-family:'JetBrains Mono',monospace">{yc}</span>
                    </div>
                </div>
                <div style="margin-top:10px">
                    <div style="color:#7a8496;font-size:0.72rem;margin-bottom:4px">REGIME REASONING</div>
                    <div style="color:#7a8496;font-size:0.8rem;line-height:1.5">{regime.get('reasoning','')[:150]}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Mission Control error: {e}. Check data sources in sidebar.")


# ── Screen 2: Move Recommendations ───────────────────────────────────────────
def screen_moves():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif;margin-bottom:4px">Move Recommendations</h1>',
                unsafe_allow_html=True)
    st.markdown('<div class="disclaimer-strip">AI-generated signals for educational simulation. Not financial advice. Confidence scores reflect historical pattern matching, not profit probability.</div>',
                unsafe_allow_html=True)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        capital = st.number_input("Simulation capital ($)", min_value=10,
                                   max_value=10_000_000, value=int(st.session_state.portfolio_capital),
                                   step=5000, key="moves_capital")
    with col_b:
        run_btn = st.button("🔍 Run Analysis", type="primary", width='stretch')

    # Cache moves for 15 minutes
    cache_age = time.time() - st.session_state.moves_cached_at
    need_refresh = run_btn or st.session_state.moves_cache is None or cache_age > 900

    if need_refresh:
        with st.spinner("Running all 8 agents across watchlist…"):
            try:
                from kairon.engine.moves import get_move_recommendations
                result = get_move_recommendations(
                    capital_usd=capital,
                    regime_override=st.session_state.regime_override,
                )
                st.session_state.moves_cache     = result
                st.session_state.moves_cached_at = time.time()
                st.session_state.portfolio_capital = capital
            except Exception as e:
                st.error(f"Analysis error: {e}")
                return

    result = st.session_state.moves_cache
    if not result:
        return

    moves = result.get("moves", [])

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("Total Net Profit", _fmt_usd(result.get("total_net_profit", 0)),
                           "if all executed", "#00e676"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Capital Required", _fmt_usd(result.get("total_capital_required", 0)),
                           f"of {_fmt_usd(capital)} available", "#2979ff"), unsafe_allow_html=True)
    if moves:
        top = moves[0]
        c3.markdown(kpi_card("Best Confidence", f"{top['confidence']*100:.0f}%",
                               top["asset"], "#00e676"), unsafe_allow_html=True)
        avg_cost = sum(m["costs"]["total_cost_pct"] for m in moves) / len(moves)
        c4.markdown(kpi_card("Avg Cost Drag", f"{avg_cost:.2f}%",
                               "transaction costs", "#ffb300"), unsafe_allow_html=True)

    st.divider()

    if not moves:
        st.info("No profitable opportunities found with current signal strength. The system only recommends moves with positive net profit after all costs.")
        return

    for move in moves:
        _render_move_card(move)


def _render_move_card(move: dict):
    pid = move["prediction_id"]
    is_executed = pid in st.session_state.executed_predictions
    opacity = "0.45" if is_executed else "1.0"

    urgency_colors = {"IMMEDIATE": "red", "SHORT": "amber", "MEDIUM": "blue", "PATIENT": "gray"}
    urg_color = urgency_colors.get(move.get("urgency", "MEDIUM"), "gray")

    with st.container():
        st.markdown(f'<div class="move-card" style="opacity:{opacity}">', unsafe_allow_html=True)

        # Header
        rank_colors = {1: "#00e676", 2: "#aa00ff", 3: "#2979ff"}
        rc = rank_colors.get(move["rank"], "#7a8496")
        st.markdown(f"""<div class="move-card-header">
            <div>
                <span style="color:{rc};font-size:1.1rem;font-weight:700">#{move['rank']}</span>
                <span class="move-title" style="margin-left:10px">{move['asset']}</span>
                {badge(move['market'].upper(), 'blue')}
                {signal_badge(move['signal'])}
            </div>
            <div>
                {badge(move.get('urgency','MEDIUM'), urg_color)}
                <span style="color:#7a8496;font-size:0.78rem;margin-left:8px">
                    {move['horizon_days']}d horizon · {move['confidence']*100:.0f}% confidence
                </span>
            </div>
        </div>""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        # Column 1: Cost waterfall
        with col1:
            st.markdown("**Cost Waterfall**")
            costs = move["costs"]
            gross = move["position"].get("position_usd", 0) * 0.03
            items = [
                ("Gross profit (est.)",    gross,                          True),
                ("Broker fees (×2)",       -costs["broker_cost"],          costs["broker_cost"] > 0),
                ("Spread + slippage",      -(costs["spread_cost"]+costs["slippage_cost"]), True),
                ("FX conversion",          -costs["fx_conversion_cost"],   costs["fx_conversion_cost"] > 0),
                ("Crypto gas",             -costs["crypto_gas_cost"],      costs["crypto_gas_cost"] > 0),
                ("Wire fee",               -costs["wire_cost"],            costs["wire_cost"] > 0),
                ("Capital gains tax",      -costs["tax_cost"],             costs["tax_cost"] > 0),
            ]
            for label, amt, show in items:
                if not show:
                    continue
                color_cls = "cost-positive" if amt >= 0 else "cost-negative"
                st.markdown(f"""<div class="cost-row">
                    <span class="cost-label">{label}</span>
                    <span class="cost-value {color_cls}">{'+' if amt>=0 else ''}{_fmt_usd(abs(amt)) if abs(amt) >= 1 else '$0'}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('<div class="cost-divider"></div>', unsafe_allow_html=True)
            net = move["net_profit_usd"]
            net_color = "#00e676" if net > 0 else "#ff3d57"
            st.markdown(f"""<div class="cost-row cost-total">
                <span style="color:#e8edf5">NET PROFIT</span>
                <span style="color:{net_color};font-family:'JetBrains Mono',monospace;font-size:1.1rem">
                    {'+' if net>=0 else ''}{_fmt_usd(net)}</span>
            </div>
            <div style="color:#7a8496;font-size:0.75rem">{move['net_profit_pct']:.2f}% · 
                Break-even: {costs['break_even_return_pct']:.2f}%</div>""",
                         unsafe_allow_html=True)

            # Tax optimisation alert
            if costs.get("tax_optimization"):
                opt = costs["tax_optimization"]
                st.markdown(f"""<div style="background:#2a1800;border:1px solid #ffb300;border-radius:4px;
                    padding:8px;margin-top:8px;font-size:0.75rem;color:#ffb300">
                    ⚠ {opt['message']}</div>""", unsafe_allow_html=True)

        # Column 2: Agent signals
        with col2:
            st.markdown("**Agent Signals**")
            sigs = move["agent_signals"]
            agent_names = {
                "technical": "Technical", "fundamental": "Fundamental",
                "news": "News", "macro": "Macro", "cross_market": "Cross-Mkt",
            }
            for key, label in agent_names.items():
                s = sigs.get(key, {}).get("signal", 0.0)
                st.markdown(score_bar(s, label), unsafe_allow_html=True)

            kb = move["kb_context"]
            n  = kb.get("n_similar", 0)
            if n > 0:
                acc = kb.get("accuracy", 0)
                nc  = kb.get("n_correct", 0)
                st.markdown(f"""<div style="background:#111820;border-radius:4px;padding:8px;
                    border:1px solid #1e2a38;margin-top:4px">
                    <div style="color:#7a8496;font-size:0.72rem">KNOWLEDGE BASE</div>
                    <div style="color:#2979ff;font-size:0.82rem">{nc}/{n} similar → {acc*100:.0f}% accurate</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#3d4558;font-size:0.78rem;margin-top:8px">KB: building history...</div>',
                            unsafe_allow_html=True)

        # Column 3: Timing & risks
        with col3:
            st.markdown("**Timing & Risks**")
            st.markdown(f"""<div style="margin-bottom:10px">
                <span class="badge badge-{urg_color}">{move.get('urgency','MEDIUM')}</span>
                <span style="color:#7a8496;font-size:0.8rem;margin-left:6px">{move['force_type'].replace('_',' ').title()}</span>
            </div>""", unsafe_allow_html=True)

            pos = move["position"]
            if pos.get("viable"):
                st.markdown(f"""<div style="font-size:0.82rem;color:#7a8496">
                    Stop-loss: <span style="color:#ff3d57;font-family:'JetBrains Mono',monospace">
                    ${pos['stop_loss_price']:,.2f} (-{pos['stop_loss_pct']*100:.1f}%)</span><br>
                    Take-profit: <span style="color:#00e676;font-family:'JetBrains Mono',monospace">
                    ${pos['take_profit_price']:,.2f} (+{pos['take_profit_pct']*100:.1f}%)</span><br>
                    R/R ratio: <span style="color:#2979ff">{pos['risk_reward_ratio']:.1f}:1</span>
                </div>""", unsafe_allow_html=True)

            risks = move.get("key_risks", [])
            if risks:
                st.markdown('<div style="margin-top:8px;color:#7a8496;font-size:0.72rem">KEY RISKS</div>',
                            unsafe_allow_html=True)
                for r in risks[:3]:
                    st.markdown(f'<div style="color:#ff3d57;font-size:0.78rem">→ {r}</div>',
                                unsafe_allow_html=True)

        # AI Explanation strip
        explanation = move.get("llm_explanation", "")
        if explanation:
            st.markdown(f"""<div style="background:#080b0f;border-left:3px solid #2979ff;
                border-radius:0 4px 4px 0;padding:10px 14px;margin-top:8px">
                <span style="color:#2979ff;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px">AI Analysis</span>
                <div style="color:#e8edf5;font-size:0.85rem;margin-top:4px;line-height:1.5">{explanation}</div>
                <div class="ai-attr">AI-generated · Public data only · Not financial advice</div>
            </div>""", unsafe_allow_html=True)

        # Action row
        st.markdown('<div style="margin-top:12px">', unsafe_allow_html=True)
        act1, act2, act3 = st.columns([2, 2, 3])
        with act1:
            if not is_executed:
                if st.button(f"✓ Execute", key=f"exec_{pid}", type="primary",
                              use_container_width=True):
                    st.session_state.executed_predictions.add(pid)
                    from kairon.engine.analyzer import log_user_decision
                    log_user_decision(pid, "execute", capital_deployed=move["position"].get("position_usd", 0))
                    st.success("Decision logged to Knowledge Base")
                    st.rerun()
            else:
                st.markdown('<span class="badge badge-green">✓ Executed — logged to KB</span>',
                            unsafe_allow_html=True)
        with act2:
            if not is_executed:
                if st.button("Pass →", key=f"pass_{pid}", use_container_width=True):
                    st.session_state.executed_predictions.add(pid)
                    from kairon.engine.analyzer import log_user_decision
                    log_user_decision(pid, "pass")
                    st.rerun()
        with act3:
            if st.button("Agent Details →", key=f"detail_{pid}", use_container_width=True):
                st.session_state.screen = "Agent Intelligence"
                st.session_state.selected_prediction = move
                st.rerun()

        st.markdown('</div></div>', unsafe_allow_html=True)


# ── Screen 3: Agent Intelligence ─────────────────────────────────────────────
def screen_agents():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Agent Intelligence</h1>', unsafe_allow_html=True)

    pred = getattr(st.session_state, "selected_prediction", None)
    if not pred:
        st.info("Select a move from the Move Recommendations screen to see agent details. Or run a quick analysis below:")
        ticker = st.selectbox("Asset", ["GC=F","BTC-USD","SPY","EURUSD=X","CL=F"], key="agent_ticker")
        if st.button("Analyse →", type="primary"):
            with st.spinner("Running 8 agents..."):
                from kairon.engine.analyzer import analyze
                from kairon.data.market_data import ASSETS
                info = ASSETS.get(ticker, {"name": ticker, "market": "stocks"})
                pred = analyze(ticker=ticker, market=info["market"],
                               capital_usd=20000,
                               regime_override=st.session_state.regime_override)
                st.session_state.selected_prediction = pred
                st.rerun()
        return

    sigs   = pred.get("agent_signals", {})
    debate = pred.get("debate", {})

    # Agent cards — 2 per row
    agent_info = [
        ("technical",    "Technical Analyst",   "TA", "#00e676"),
        ("fundamental",  "Fundamental Analyst",  "FA", "#ffb300"),
        ("news",         "News Analyst",          "NA", "#2979ff"),
        ("macro",        "Macro Agent",           "MA", "#ff3d57"),
        ("cross_market", "Cross-Market Agent",   "CX", "#aa00ff"),
    ]

    for i in range(0, len(agent_info), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(agent_info):
                break
            key, label, initials, color = agent_info[i + j]
            sig = sigs.get(key, {})
            score = sig.get("signal", 0)
            conf  = sig.get("confidence", 0)
            sign  = "+" if score >= 0 else ""

            with col:
                st.markdown(f"""<div class="agent-card">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                        <div style="width:36px;height:36px;border-radius:50%;background:{color}22;
                             border:2px solid {color};display:flex;align-items:center;justify-content:center;
                             color:{color};font-weight:700;font-size:0.85rem">{initials}</div>
                        <div>
                            <div style="font-weight:600;color:#e8edf5">{label}</div>
                            <div style="color:#7a8496;font-size:0.75rem">{sig.get('direction','HOLD')} · {conf*100:.0f}% confidence</div>
                        </div>
                        <div style="margin-left:auto">
                            <span class="agent-score" style="color:{color}">{sign}{score:.2f}</span>
                        </div>
                    </div>
                    <div style="color:#7a8496;font-size:0.8rem;line-height:1.5">
                        {sig.get('reasoning','')[:200]}
                    </div>
                </div>""", unsafe_allow_html=True)
                st.markdown("")

    # Bull/Bear debate
    st.markdown("---")
    st.markdown("#### Bull vs Bear Debate")
    bc1, bc2 = st.columns(2)
    with bc1:
        bs = debate.get("bull_score", 0)
        st.markdown(f"""<div style="background:#003320;border:1px solid #00e676;border-radius:6px;padding:14px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <span style="color:#00e676;font-weight:700">BULL CASE</span>
                <span style="color:#00e676;font-size:1.2rem;font-family:'JetBrains Mono',monospace">+{bs:.2f}</span>
            </div>
            <div style="color:#a0f0c0;font-size:0.83rem;line-height:1.5">{debate.get('bull_argument','')[:300]}</div>
        </div>""", unsafe_allow_html=True)
    with bc2:
        bs2 = debate.get("bear_score", 0)
        st.markdown(f"""<div style="background:#3a0010;border:1px solid #ff3d57;border-radius:6px;padding:14px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <span style="color:#ff3d57;font-weight:700">BEAR CASE</span>
                <span style="color:#ff3d57;font-size:1.2rem;font-family:'JetBrains Mono',monospace">+{bs2:.2f}</span>
            </div>
            <div style="color:#ffaaaa;font-size:0.83rem;line-height:1.5">{debate.get('bear_argument','')[:300]}</div>
        </div>""", unsafe_allow_html=True)

    # Trader verdict
    cons = debate.get("consensus", "neutral")
    rec  = debate.get("recommendation", "hold")
    st.markdown(f"""<div style="background:#111820;border-left:3px solid #2979ff;padding:12px 16px;
        margin-top:14px;border-radius:0 6px 6px 0">
        <span style="color:#2979ff;font-size:0.72rem">TRADER VERDICT</span>
        <div style="color:#e8edf5;margin-top:4px;font-size:0.9rem">
            Consensus: <strong>{cons.replace('_',' ').title()}</strong> | 
            Recommendation: <strong>{rec.replace('_',' ').title()}</strong> |
            Debate quality: <strong>{debate.get('debate_quality','medium').title()}</strong>
        </div>
        <div style="color:#7a8496;font-size:0.78rem;margin-top:6px">
            {' · '.join(debate.get('key_disagreements', ['No major disagreements'])[:3])}
        </div>
    </div>""", unsafe_allow_html=True)


# ── Screen 4: Knowledge Base ──────────────────────────────────────────────────
def screen_kb():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Knowledge Base</h1>', unsafe_allow_html=True)
    try:
        from kairon.intelligence.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()
        stats = kb.get_stats()
        preds = kb.get_recent_predictions(limit=50)

        total = stats.get("total_predictions", 0)
        resolved = stats.get("with_outcomes", 0)
        acc = stats.get("overall_accuracy", 0)

        # KPI row
        c1, c2, c3 = st.columns(3)
        c1.markdown(kpi_card("Total Predictions", str(total), f"{resolved} with outcomes", "#2979ff"),
                    unsafe_allow_html=True)
        c2.markdown(kpi_card("Overall Accuracy",
                              f"{acc*100:.1f}%" if resolved > 5 else "Building...",
                              f"Min 5 outcomes needed" if resolved < 5 else f"{resolved} resolved", "#00e676"),
                    unsafe_allow_html=True)
        lessons = stats.get("total_lessons", 0)
        c3.markdown(kpi_card("Lessons Extracted", str(lessons),
                              "Patterns with >70% accuracy", "#aa00ff"),
                    unsafe_allow_html=True)

        # Cold-start states (Document 16)
        if total == 0:
            st.info("Your knowledge base is empty. Every prediction Kairon makes gets stored here. After ~20 predictions, accuracy patterns will emerge. Make your first prediction in Move Recommendations.")
            return
        if total < 20:
            progress = total / 20
            st.markdown(f"""<div style="background:#111820;border-radius:6px;padding:12px;border:1px solid #1e2a38;margin-bottom:16px">
                <div style="color:#7a8496;font-size:0.82rem">Building knowledge base — {total}/20 predictions before first insights</div>
                <div class="bar-track" style="margin-top:8px"><div class="bar-fill"
                    style="width:{progress*100:.0f}%;background:#2979ff"></div></div>
            </div>""", unsafe_allow_html=True)

        # Accuracy by asset
        st.markdown("#### Accuracy by Asset")
        by_asset = stats.get("by_asset", [])
        if by_asset:
            for row in by_asset:
                acc_v = row.get("accuracy_pct") or 0
                color = "#00e676" if acc_v >= 70 else ("#ffb300" if acc_v >= 55 else "#ff3d57")
                st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                    <span style="min-width:120px;font-size:0.85rem">{row['asset']}</span>
                    <div class="bar-track" style="flex:1"><div class="bar-fill"
                        style="width:{acc_v}%;background:{color}"></div></div>
                    <span style="color:{color};font-family:'JetBrains Mono',monospace;min-width:50px">{acc_v:.1f}%</span>
                    <span style="color:#3d4558;font-size:0.75rem">({row['n']} predictions)</span>
                </div>""", unsafe_allow_html=True)

        # Prediction log
        st.divider()
        st.markdown("#### Prediction Log")
        if preds:
            df_display = pd.DataFrame([{
                "Date":       p["created_at"][:10],
                "Asset":      p["asset"],
                "Signal":     p["signal"],
                "Confidence": f"{(p['confidence'] or 0)*100:.0f}%",
                "Outcome":    "✓ CORRECT" if p.get("prediction_correct") == 1 else
                              ("✗ WRONG" if p.get("prediction_correct") == 0 else "⏳ PENDING"),
                "Return":     f"{(p.get('actual_return') or 0)*100:.1f}%",
                "Decision":   p.get("user_decision") or "—",
            } for p in preds])
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No predictions recorded yet.")

    except Exception as e:
        st.error(f"Knowledge Base error: {e}")


# ── Screen 5: Cost Calculator ─────────────────────────────────────────────────
def screen_costs():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Cost Calculator</h1>', unsafe_allow_html=True)
    st.markdown("Calculate exact net profit for any move you're considering.")

    col_in, col_out = st.columns([1, 1])

    with col_in:
        amount    = st.number_input("Capital amount ($)", 1000, 5_000_000, 20000, step=1000)
        from_m    = st.selectbox("From market", ["stocks","crypto","forex","commodities","bonds","real_estate"])
        to_m      = st.selectbox("To market",   ["commodities","stocks","crypto","forex","bonds","real_estate"])
        to_asset  = st.text_input("Destination ticker (for gas fee)", "GC=F")
        exp_ret   = st.slider("Expected gross return (%)", 0.1, 20.0, 2.5, 0.1)
        days_held = st.number_input("Days held in current position", 0, 730, 0)
        unreal_g  = st.slider("Unrealized gain on position being sold (%)", 0.0, 100.0, 0.0, 0.5)
        vix_val   = st.slider("Current VIX", 8.0, 60.0, 14.2, 0.1)

        regions = ["US","UK","Germany","Australia","Canada","Singapore","UAE","Custom"]
        tax_r   = st.selectbox("Tax region", regions)

    with col_out:
        from kairon.engine.cost_engine import calculate_all_costs, passes_minimum_profit
        costs = calculate_all_costs(
            amount_usd=amount,
            from_market=from_m,
            to_market=to_m,
            to_asset=to_asset,
            holding_days=days_held,
            unrealized_gain_pct=unreal_g / 100,
            vix=vix_val,
            tax_region=tax_r,
        )
        gross_usd = amount * exp_ret / 100
        net_usd   = gross_usd - costs.total_cost_usd
        passes, msg = passes_minimum_profit(exp_ret / 100, costs)

        verdict_color = "#00e676" if passes else "#ff3d57"
        verdict_label = "✓ PROCEED" if passes else "✗ DO NOT PROCEED"

        st.markdown(f"""<div style="background:#111820;border:1px solid #1e2a38;border-radius:8px;padding:18px">
            <div style="font-size:0.75rem;color:#7a8496;margin-bottom:14px;text-transform:uppercase;letter-spacing:1px">Cost Breakdown</div>
        """, unsafe_allow_html=True)

        items = [
            ("Gross profit",        gross_usd,                 True),
            ("Broker fees (×2)",    -costs.broker_cost,        True),
            ("Spread + slippage",   -(costs.spread_cost + costs.slippage_cost), True),
            ("FX conversion",       -costs.fx_conversion_cost, costs.fx_conversion_cost > 0),
            ("Crypto gas",          -costs.crypto_gas_cost,    costs.crypto_gas_cost > 0),
            ("Wire / transfer",     -costs.wire_cost,          costs.wire_cost > 0),
            (f"Tax ({costs.tax_type})", -costs.tax_cost,       costs.tax_cost > 0),
        ]
        for label, amt, show in items:
            if not show:
                continue
            c = "#00e676" if amt >= 0 else "#ff3d57"
            st.markdown(f"""<div class="cost-row">
                <span class="cost-label">{label}</span>
                <span class="cost-value" style="color:{c};font-family:'JetBrains Mono',monospace">
                    {'+' if amt>=0 else ''}{_fmt_usd(abs(amt))}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="cost-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="cost-row cost-total">
            <span style="color:#e8edf5;font-weight:700">Total costs</span>
            <span style="color:#ff3d57;font-family:'JetBrains Mono',monospace">-{_fmt_usd(costs.total_cost_usd)}</span>
        </div>
        <div class="cost-row cost-total" style="margin-top:6px;padding-top:6px;border-top:1px solid #1e2a38">
            <span style="color:#e8edf5;font-weight:700;font-size:1.05rem">NET PROFIT</span>
            <span style="color:{verdict_color};font-family:'JetBrains Mono',monospace;font-size:1.2rem;font-weight:700">
                {'+' if net_usd>=0 else ''}{_fmt_usd(net_usd)}</span>
        </div>
        <div style="color:#7a8496;font-size:0.78rem;margin-top:4px">
            Net {net_usd/amount*100:.2f}% · Break-even: {costs.break_even_return_pct:.2f}%
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style="background:{verdict_color}22;border:1px solid {verdict_color};
            border-radius:6px;padding:12px;margin-top:14px;text-align:center">
            <div style="color:{verdict_color};font-size:1.1rem;font-weight:700">{verdict_label}</div>
            <div style="color:#7a8496;font-size:0.8rem;margin-top:4px">{msg}</div>
        </div>""", unsafe_allow_html=True)

        if costs.tax_optimization:
            opt = costs.tax_optimization
            st.warning(f"💡 Tax optimization: {opt['message']}")

        # Tax disclaimer (Document 18)
        st.markdown("""<div style="margin-top:10px;color:#3d4558;font-size:0.72rem">
            Tax estimates use simplified rates and may not reflect your jurisdiction.
            Consult a qualified tax professional. Not financial advice.
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── Screen 6: Connection Map ──────────────────────────────────────────────────
def screen_connection_map():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Connection Map</h1>', unsafe_allow_html=True)
    st.markdown("Visualise how the system connected signals to reach its recommendation.")

    pred = getattr(st.session_state, "selected_prediction", None)
    if not pred:
        st.info("Run an analysis on any asset to see its connection map. Go to Agent Intelligence and analyse an asset first.")
        return

    sigs   = pred.get("agent_signals", {})
    regime = pred.get("macro_regime", "Risk-On")
    asset  = pred.get("asset", "Unknown")
    comp   = pred.get("composite_score", 0)

    # Signal flow diagram
    st.markdown(f"#### Signal Flow — {asset}")

    forces_up   = []
    forces_down = []

    for agent, label in [("technical","Technical"), ("fundamental","Fundamental"),
                          ("news","News"), ("macro","Macro"), ("cross_market","Cross-Market")]:
        s = sigs.get(agent, {}).get("signal", 0)
        if s > 0.1:
            forces_up.append((label, s))
        elif s < -0.1:
            forces_down.append((label, s))

    cu, cd = st.columns(2)
    with cu:
        st.markdown("**↑ Increasing Forces**")
        for label, score in sorted(forces_up, key=lambda x: x[1], reverse=True):
            st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;
                padding:8px;background:#003320;border-radius:4px;margin-bottom:6px">
                <span style="color:#00e676;font-family:'JetBrains Mono';font-weight:700">↑</span>
                <span style="flex:1;color:#e8edf5;font-size:0.85rem">{label} signal</span>
                <span style="color:#00e676;font-family:'JetBrains Mono';font-size:0.9rem">+{score:.3f}</span>
            </div>""", unsafe_allow_html=True)
        if not forces_up:
            st.markdown('<div style="color:#3d4558;font-size:0.82rem">No significant upward forces</div>', unsafe_allow_html=True)

    with cd:
        st.markdown("**↓ Decreasing Forces**")
        for label, score in sorted(forces_down, key=lambda x: x[1]):
            st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;
                padding:8px;background:#3a0010;border-radius:4px;margin-bottom:6px">
                <span style="color:#ff3d57;font-family:'JetBrains Mono';font-weight:700">↓</span>
                <span style="flex:1;color:#e8edf5;font-size:0.85rem">{label} signal</span>
                <span style="color:#ff3d57;font-family:'JetBrains Mono';font-size:0.9rem">{score:.3f}</span>
            </div>""", unsafe_allow_html=True)
        if not forces_down:
            st.markdown('<div style="color:#3d4558;font-size:0.82rem">No significant downward forces</div>', unsafe_allow_html=True)

    # Net force
    st.divider()
    net_label = "STRONG BUY" if comp > 0.6 else ("BUY" if comp > 0.3 else ("HOLD" if comp > -0.3 else "AVOID"))
    net_color = "#00e676" if comp > 0.2 else ("#ff3d57" if comp < -0.2 else "#ffb300")
    st.markdown(f"""<div style="text-align:center;padding:20px;background:#111820;border-radius:8px;border:1px solid #1e2a38">
        <div style="color:#7a8496;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px">Net Signal Force</div>
        <div style="font-size:2.5rem;font-weight:700;color:{net_color};font-family:'JetBrains Mono',monospace">
            {'+' if comp >= 0 else ''}{comp:.3f}</div>
        <div style="color:{net_color};font-size:1.1rem;font-weight:600">{net_label}</div>
        <div style="color:#7a8496;font-size:0.8rem;margin-top:6px">Macro regime: {regime}</div>
    </div>""", unsafe_allow_html=True)

    # Causal chain
    st.divider()
    st.markdown("#### Causal Chain")
    explanation = pred.get("llm_explanation", "")
    if explanation:
        st.markdown(f"""<div style="background:#080b0f;border-left:3px solid #2979ff;
            padding:14px 18px;border-radius:0 6px 6px 0;line-height:1.7;color:#e8edf5">
            {explanation}
        </div>
        <div class="ai-attr" style="margin-top:6px">AI-generated · Not financial advice</div>
        """, unsafe_allow_html=True)

    # KB precedent
    kb = pred.get("kb_context", {})
    if kb.get("has_history"):
        st.divider()
        st.markdown("#### Historical Precedents")
        for m in kb.get("top_matches", [])[:5]:
            outcome_color = "#00e676" if m["outcome"] == "CORRECT" else "#ff3d57"
            st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;
                padding:8px;background:#111820;border-radius:4px;margin-bottom:4px;font-size:0.82rem">
                <span style="color:#3d4558">{m['date']}</span>
                {badge(m['signal'], 'green' if m['signal']=='UP' else 'red')}
                <span style="color:{outcome_color};font-weight:600">{m['outcome']}</span>
                <span style="color:#7a8496">Return: {'+' if m['return']>=0 else ''}{m['return']:.1f}%</span>
                <span style="color:#3d4558;margin-left:auto">Similarity: {m['similarity']:.0%}</span>
            </div>""", unsafe_allow_html=True)

    # 5-Layer explainability
    expl = pred.get("explainability")
    if expl:
        st.divider()
        st.markdown("#### 5-Layer Analysis Chain")

        layer_tab1, layer_tab2, layer_tab3, layer_tab4, layer_tab5 = st.tabs([
            "① Raw Signals", "② Patterns", "③ Cross-Signal",
            "④ KB Precedent", "⑤ Projection"
        ])

        with layer_tab1:
            st.markdown("**What the data says right now:**")
            for s in expl.get("layer1_raw_signals", {}).get("signals", []):
                type_colors = {"price": "#00e676", "technical": "#2979ff",
                               "macro": "#ffb300", "news": "#aa00ff"}
                tc = type_colors.get(s.get("type", ""), "#7a8496")
                st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;
                    padding:6px 0;border-bottom:1px solid #111820;font-size:0.83rem">
                    <span style="color:{tc};min-width:10px">●</span>
                    <span style="color:#e8edf5;min-width:160px;font-weight:500">{s['label']}</span>
                    <span style="color:#7a8496;font-family:'JetBrains Mono',monospace">{s['value']}</span>
                    <span style="color:#3d4558;font-size:0.72rem;margin-left:auto">{s['source']}</span>
                </div>""", unsafe_allow_html=True)

        with layer_tab2:
            st.markdown("**Patterns the system recognises:**")
            patterns = expl.get("layer2_patterns", {}).get("patterns", [])
            if patterns:
                for p in patterns:
                    dir_color = "#00e676" if p["direction"] == "bullish" else "#ff3d57"
                    st.markdown(f"""<div style="background:#111820;border-left:3px solid {dir_color};
                        padding:10px 14px;border-radius:0 4px 4px 0;margin-bottom:8px">
                        <div style="color:#e8edf5;font-weight:600">{p['name']}</div>
                        <div style="color:#7a8496;font-size:0.82rem;margin-top:3px">{p['signals']}</div>
                        <div style="color:{dir_color};font-size:0.8rem;margin-top:3px">
                            → {p['meaning']} ({p['direction']}, {p['strength']})</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#3d4558">No significant patterns detected in this setup.</div>',
                            unsafe_allow_html=True)

        with layer_tab3:
            cs = expl.get("layer3_cross_signal", {})
            conv = cs.get("conviction", "UNKNOWN")
            conv_color = "#00e676" if "HIGH" in conv else ("#ffb300" if "MODERATE" in conv else "#ff3d57")
            st.markdown(f"""<div style="text-align:center;padding:16px;background:#111820;border-radius:8px;margin-bottom:14px">
                <div style="color:#7a8496;font-size:0.72rem">CONVICTION LEVEL</div>
                <div style="color:{conv_color};font-size:1.3rem;font-weight:700">{conv}</div>
                <div style="color:#7a8496;font-size:0.82rem;margin-top:4px">{cs.get('summary','')}</div>
            </div>""", unsafe_allow_html=True)
            if cs.get("agreements"):
                st.markdown("**Agreements:**")
                for a in cs["agreements"]:
                    st.markdown(f'<div style="color:#00e676;font-size:0.82rem;padding:3px 0">✓ {a}</div>',
                                unsafe_allow_html=True)
            if cs.get("contradictions"):
                st.markdown("**Contradictions:**")
                for c in cs["contradictions"]:
                    st.markdown(f'<div style="color:#ff3d57;font-size:0.82rem;padding:3px 0">✗ {c}</div>',
                                unsafe_allow_html=True)

        with layer_tab4:
            l4 = expl.get("layer4_precedent", {})
            if l4.get("has_history"):
                acc = l4.get("accuracy", 0)
                acc_color = "#00e676" if acc >= 0.70 else ("#ffb300" if acc >= 0.55 else "#ff3d57")
                st.markdown(f"""<div style="background:#111820;padding:14px;border-radius:6px;margin-bottom:10px">
                    <div style="font-size:1.4rem;font-weight:700;color:{acc_color};font-family:'JetBrains Mono',monospace">
                        {l4['n_correct']}/{l4['n_similar']} correct ({acc*100:.0f}%)</div>
                    <div style="color:#7a8496;font-size:0.82rem;margin-top:4px">
                        Avg return: {l4['avg_return']*100:+.1f}%</div>
                </div>""", unsafe_allow_html=True)
                if l4.get("lesson"):
                    st.markdown(f'<div style="color:#e8edf5;font-size:0.85rem;line-height:1.5">{l4["lesson"]}</div>',
                                unsafe_allow_html=True)
                if l4.get("failure_note"):
                    st.markdown(f'<div style="color:#ff3d57;font-size:0.78rem;margin-top:8px">Last error: {l4["failure_note"]}</div>',
                                unsafe_allow_html=True)
            else:
                st.info("No historical matches found yet — KB is building. Make more predictions to see patterns.")

        with layer_tab5:
            l5 = expl.get("layer5_projection", {})
            direction = l5.get("direction", "UP")
            base_conf = l5.get("base_confidence", 50)
            base_ret  = l5.get("base_case_return", 0)
            net_ret   = l5.get("net_return_after_costs", 0)
            col_dir   = "#00e676" if direction == "UP" else "#ff3d57"

            st.markdown(f"""<div style="display:flex;gap:14px;margin-bottom:14px">
                <div style="flex:1;background:#111820;border-radius:6px;padding:12px;text-align:center;border:1px solid #1e2a38">
                    <div style="color:#7a8496;font-size:0.72rem">Base case</div>
                    <div style="color:{col_dir};font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono'">{base_conf}%</div>
                    <div style="color:#7a8496;font-size:0.75rem">confidence</div>
                </div>
                <div style="flex:1;background:#111820;border-radius:6px;padding:12px;text-align:center;border:1px solid #1e2a38">
                    <div style="color:#7a8496;font-size:0.72rem">Gross return est.</div>
                    <div style="color:{col_dir};font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono'">{base_ret:+.1f}%</div>
                    <div style="color:#7a8496;font-size:0.75rem">before costs</div>
                </div>
                <div style="flex:1;background:#111820;border-radius:6px;padding:12px;text-align:center;border:1px solid #1e2a38">
                    <div style="color:#7a8496;font-size:0.72rem">Net return est.</div>
                    <div style="color:{'#00e676' if net_ret > 0 else '#ff3d57'};font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono'">{net_ret:+.1f}%</div>
                    <div style="color:#7a8496;font-size:0.75rem">after costs</div>
                </div>
            </div>""", unsafe_allow_html=True)

            drivers = l5.get("base_drivers", [])
            if drivers:
                st.markdown("**Drivers:**")
                for d in drivers:
                    st.markdown(f'<div style="color:#00e676;font-size:0.82rem;padding:2px 0">→ {d}</div>',
                                unsafe_allow_html=True)
            bear_triggers = l5.get("bear_triggers", [])
            if bear_triggers:
                st.markdown("**What could make this wrong:**")
                for t in bear_triggers:
                    st.markdown(f'<div style="color:#ff3d57;font-size:0.82rem;padding:2px 0">→ {t}</div>',
                                unsafe_allow_html=True)


# ── Screen 7: Portfolio Loader ────────────────────────────────────────────────
def screen_portfolio():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Portfolio Loader</h1>', unsafe_allow_html=True)
    st.markdown("""<div class="disclaimer-strip">
        <strong>Privacy first:</strong> Your quantities, prices, and gains are processed entirely in your browser.
        Only ticker symbols are sent to our server to fetch live prices.
        When you close this tab, your portfolio data is gone from our systems (it was never there).
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Manual Entry", "📂 CSV Upload", "🎭 Demo Portfolio"])

    with tab1:
        st.markdown("#### Enter Your Holdings")
        if "manual_holdings" not in st.session_state:
            st.session_state.manual_holdings = [
                {"ticker": "", "quantity": 0.0, "avg_price": 0.0, "days_held": 0}
            ]

        updated_holdings = []
        for i, h in enumerate(st.session_state.manual_holdings):
            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1.5, 0.5])
            ticker    = c1.text_input("Ticker", value=h["ticker"], key=f"tk_{i}",
                                       placeholder="AAPL / BTC-USD / GC=F")
            qty       = c2.number_input("Quantity", value=float(h["quantity"]),
                                         min_value=0.0, key=f"qty_{i}", step=0.01)
            avg_price = c3.number_input("Avg Price ($)", value=float(h["avg_price"]),
                                         min_value=0.0, key=f"price_{i}", step=0.01)
            days      = c4.number_input("Days Held", value=int(h["days_held"]),
                                         min_value=0, key=f"days_{i}")
            if c5.button("✕", key=f"del_{i}") and len(st.session_state.manual_holdings) > 1:
                st.session_state.manual_holdings.pop(i)
                st.rerun()
            if ticker.strip():
                updated_holdings.append({"ticker": ticker.upper().strip(),
                                          "quantity": qty, "avg_price": avg_price,
                                          "days_held": days})

        col_add, col_cash = st.columns(2)
        if col_add.button("＋ Add holding", use_container_width=True):
            st.session_state.manual_holdings.append(
                {"ticker": "", "quantity": 0.0, "avg_price": 0.0, "days_held": 0})
            st.rerun()
        cash = col_cash.number_input("Cash position ($)", min_value=0.0,
                                       value=0.0, step=100.0, key="manual_cash")

        if st.button("📊 Run Analysis on My Portfolio", type="primary",
                      use_container_width=True):
            valid_h = [h for h in updated_holdings if h["ticker"] and h["quantity"] > 0 and h["avg_price"] > 0]
            if valid_h:
                with st.spinner("Loading portfolio..."):
                    _load_and_show_portfolio(valid_h, cash)
            else:
                st.warning("Enter at least one holding with ticker, quantity, and price.")

    with tab2:
        st.markdown("#### Upload Broker CSV")
        broker = st.selectbox("Broker format", list(["Auto-detect"] + [b.title() for b in BROKER_CSV_FORMATS if b != "generic"]))
        uploaded = st.file_uploader("Drop CSV here", type=["csv"], label_visibility="collapsed")
        if uploaded:
            content = uploaded.read().decode("utf-8", errors="ignore")
            broker_key = broker.lower() if broker != "Auto-detect" else "generic"
            try:
                from kairon.engine.portfolio import parse_csv
                raw = parse_csv(content, broker_key)
                st.success(f"Parsed {len(raw)} holdings from CSV")
                st.markdown(f'<div class="disclaimer-strip">Your file was processed in-browser. No financial data was sent to our servers.</div>',
                            unsafe_allow_html=True)
                cash_csv = st.number_input("Add cash position ($)", value=0.0, step=100.0, key="csv_cash")
                if st.button("📊 Run Portfolio Analysis", type="primary", use_container_width=True):
                    with st.spinner("Fetching current prices..."):
                        _load_and_show_portfolio(raw, cash_csv)
            except Exception as e:
                st.error(f"CSV parsing failed: {e}. Try 'Auto-detect' or a different broker format.")

    with tab3:
        st.markdown("#### Demo Portfolios")
        from kairon.engine.portfolio import DEMO_PORTFOLIOS
        demo_name = st.selectbox("Choose a demo portfolio", list(DEMO_PORTFOLIOS.keys()))
        st.markdown(f"*{len(DEMO_PORTFOLIOS[demo_name])} holdings · pre-configured for simulation*")
        if st.button("Load Demo Portfolio", type="primary", use_container_width=True):
            with st.spinner("Loading demo portfolio..."):
                _load_and_show_portfolio(DEMO_PORTFOLIOS[demo_name], 0.0)


def _load_and_show_portfolio(raw_holdings: list, cash: float):
    """Load portfolio and render analysis."""
    try:
        from kairon.engine.portfolio import load_portfolio_from_holdings, detect_tax_optimisations
        from kairon.config import cfg

        portfolio = load_portfolio_from_holdings(raw_holdings, cash)
        portfolio.compute_totals()
        tax_alerts = detect_tax_optimisations(portfolio)

        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        total_g_color = "#00e676" if portfolio.total_gain >= 0 else "#ff3d57"
        c1.markdown(kpi_card("Total Value", _fmt_usd(portfolio.total_value), "Current market value", "#00e676"),
                    unsafe_allow_html=True)
        c2.markdown(kpi_card("Total Gain", _fmt_usd(portfolio.total_gain),
                              _fmt_pct(portfolio.total_gain_pct * 100, 2), total_g_color),
                    unsafe_allow_html=True)
        c3.markdown(kpi_card("Holdings", str(len(portfolio.holdings)),
                              f"+ ${portfolio.cash:,.0f} cash", "#2979ff"),
                    unsafe_allow_html=True)
        c4.markdown(kpi_card("Tax Alerts", str(len(tax_alerts)),
                              "Approaching long-term threshold" if tax_alerts else "No optimizations",
                              "#ffb300" if tax_alerts else "#7a8496"),
                    unsafe_allow_html=True)

        st.divider()

        # Holdings table
        st.markdown("#### Holdings Breakdown")
        for h in portfolio.holdings:
            gain_color = "#00e676" if h.unrealized_gain >= 0 else "#ff3d57"
            bar_w = max(4, min(100, int(h.pct_of_portfolio * 100)))
            st.markdown(f"""<div style="background:#111820;border:1px solid #1e2a38;
                border-radius:6px;padding:12px 16px;margin-bottom:8px">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <div>
                        <span style="color:#e8edf5;font-weight:600">{h.name}</span>
                        <span style="color:#3d4558;font-size:0.78rem;margin-left:8px">{h.ticker}</span>
                        {badge(h.market, 'blue')}
                        {badge(h.tax_label, 'green' if h.is_long_term else 'amber')}
                    </div>
                    <div style="text-align:right">
                        <span style="color:{gain_color};font-family:'JetBrains Mono',monospace;font-size:1.1rem">
                            {'+' if h.unrealized_gain >= 0 else ''}{_fmt_usd(h.unrealized_gain)}</span>
                        <span style="color:#7a8496;font-size:0.78rem;margin-left:6px">
                            ({'+' if h.unrealized_pct >= 0 else ''}{h.unrealized_pct*100:.1f}%)</span>
                    </div>
                </div>
                <div style="display:flex;gap:20px;font-size:0.8rem;color:#7a8496">
                    <span>Qty: <span style="color:#e8edf5">{h.quantity:,.4g}</span></span>
                    <span>Avg: <span style="color:#e8edf5">${h.avg_price:,.2f}</span></span>
                    <span>Now: <span style="color:#e8edf5">${h.current_price:,.2f}</span></span>
                    <span>Value: <span style="color:#e8edf5">{_fmt_usd(h.current_value)}</span></span>
                    <span>Held: <span style="color:#e8edf5">{h.days_held}d</span></span>
                </div>
                <div style="margin-top:8px">
                    <div class="bar-track"><div class="bar-fill"
                        style="width:{bar_w}%;background:#2979ff44"></div></div>
                    <span style="color:#3d4558;font-size:0.72rem">{h.pct_of_portfolio*100:.1f}% of portfolio</span>
                </div>
            </div>""", unsafe_allow_html=True)

        # Tax optimisation alerts
        if tax_alerts:
            st.divider()
            st.markdown("#### Tax Optimisation Alerts")
            for alert in tax_alerts:
                st.markdown(f"""<div style="background:#2a1800;border:1px solid #ffb300;
                    border-radius:6px;padding:12px;margin-bottom:8px">
                    <span style="color:#ffb300;font-weight:600">⚠ {alert['name']}</span>
                    <span style="color:#e8edf5;margin-left:8px;font-size:0.85rem">{alert['message']}</span>
                    <span style="color:#ffb300;font-family:'JetBrains Mono',monospace;margin-left:auto">
                        Save ${alert['tax_saving']:,.0f}</span>
                </div>""", unsafe_allow_html=True)

        # Run analysis button
        st.divider()
        if st.button("⚡ Run Move Recommendations for This Portfolio", type="primary",
                      use_container_width=True):
            from kairon.engine.moves import get_move_recommendations
            with st.spinner("Running 8 agents on your portfolio..."):
                result = get_move_recommendations(
                    capital_usd=portfolio.total_value,
                    regime_override=st.session_state.regime_override,
                )
                st.session_state.moves_cache     = result
                st.session_state.moves_cached_at = 0
                st.session_state.portfolio_capital = portfolio.total_value
                st.session_state.screen = "Move Recommendations"
                st.rerun()

    except Exception as e:
        st.error(f"Portfolio loading error: {e}")


# ── Screen 8: Backtesting ─────────────────────────────────────────────────────
def screen_backtest():
    st.markdown('<h1 style="font-family:\'Syne\',sans-serif">Backtesting</h1>', unsafe_allow_html=True)
    st.markdown("""<div class="disclaimer-strip">
        Walk-forward validation only — no look-ahead bias. Each test fold trains only on data
        available at that point in time. Past performance does not guarantee future results.
    </div>""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    ticker_bt  = col_a.selectbox("Asset to backtest",
                                   ["GC=F","BTC-USD","SPY","EURUSD=X","CL=F","TLT","VNQ"])
    horizon_bt = col_b.selectbox("Signal horizon", [2, 3, 5, 10, 20],
                                   index=2, format_func=lambda x: f"{x} days")
    n_folds_bt = col_c.slider("Number of folds", 2, 8, 5)

    if st.button("▶ Run Backtest", type="primary", use_container_width=True):
        from kairon.data.market_data import ASSETS
        info = ASSETS.get(ticker_bt, {"name": ticker_bt, "market": "stocks"})
        with st.spinner(f"Running {n_folds_bt}-fold walk-forward backtest on {info['name']}…"):
            try:
                from kairon.intelligence.backtester import walk_forward_backtest
                result = walk_forward_backtest(
                    ticker=ticker_bt, market=info["market"],
                    horizon_days=horizon_bt, n_folds=n_folds_bt,
                )
                st.session_state.backtest_result = result
            except Exception as e:
                st.error(f"Backtest error: {e}")
                return

    result = getattr(st.session_state, "backtest_result", None)
    if not result:
        st.info("Configure and run a backtest above. Results appear here. Walk-forward ensures no look-ahead bias.")
        return

    r = result.to_dict()
    grade_colors = {"A": "#00e676", "B": "#ffb300", "C": "#2979ff", "D": "#ff3d57"}
    grade = r.get("grade", "C")
    gc    = grade_colors.get(grade, "#7a8496")

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(kpi_card("Grade", grade, "Walk-forward result", gc), unsafe_allow_html=True)
    c2.markdown(kpi_card("Accuracy",
                           f"{r['accuracy']*100:.1f}%",
                           f"{r['n_correct']}/{r['n_predictions']} correct",
                           "#00e676" if r["accuracy"] >= 0.60 else "#ff3d57"),
                unsafe_allow_html=True)
    c3.markdown(kpi_card("Sharpe Ratio",
                           f"{r['sharpe_ratio']:.2f}",
                           "Risk-adjusted return",
                           "#00e676" if r["sharpe_ratio"] >= 0.5 else "#ff3d57"),
                unsafe_allow_html=True)
    c4.markdown(kpi_card("Max Drawdown",
                           f"{r['max_drawdown']*100:.1f}%",
                           "Worst peak-to-trough",
                           "#ffb300" if r["max_drawdown"] > 0.10 else "#00e676"),
                unsafe_allow_html=True)
    c5.markdown(kpi_card("Total Return",
                           _fmt_pct(r["total_return_pct"], 1),
                           f"Over {r['n_predictions']} trades",
                           "#00e676" if r["total_return_pct"] > 0 else "#ff3d57"),
                unsafe_allow_html=True)

    st.divider()

    # Fold results
    if r["folds"]:
        st.markdown("#### Fold-by-Fold Results")
        for f in r["folds"]:
            acc_v  = f.get("accuracy", 0) * 100
            color  = "#00e676" if acc_v >= 60 else ("#ffb300" if acc_v >= 50 else "#ff3d57")
            ret_v  = f.get("avg_return", 0) * 100
            rc     = "#00e676" if ret_v >= 0 else "#ff3d57"
            st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;
                padding:10px;background:#111820;border-radius:4px;margin-bottom:6px;font-size:0.85rem">
                <span style="color:#7a8496;min-width:50px">Fold {f['fold']}</span>
                <span style="color:#3d4558;min-width:140px">{f.get('date_start','?')} → {f.get('date_end','?')}</span>
                <span style="min-width:80px">n={f['n_predictions']}</span>
                <div class="bar-track" style="flex:1"><div class="bar-fill"
                    style="width:{acc_v:.0f}%;background:{color}"></div></div>
                <span style="color:{color};font-family:'JetBrains Mono',monospace;min-width:55px">{acc_v:.1f}%</span>
                <span style="color:{rc};font-family:'JetBrains Mono',monospace;min-width:70px">
                    {'+' if ret_v>=0 else ''}{ret_v:.2f}%</span>
            </div>""", unsafe_allow_html=True)

    # Warnings
    if r.get("warnings"):
        st.divider()
        st.markdown("#### Warnings")
        for w in r["warnings"]:
            st.markdown(f'<div style="color:#ffb300;font-size:0.82rem;padding:4px 0">⚠ {w}</div>',
                        unsafe_allow_html=True)

    # By signal
    if r.get("by_signal"):
        st.divider()
        st.markdown("#### Accuracy by Signal Direction")
        cs1, cs2 = st.columns(2)
        for col, (sig, data) in zip([cs1, cs2], r["by_signal"].items()):
            with col:
                acc_s = data["accuracy"] * 100
                sc    = "#00e676" if sig == "UP" else "#ff3d57"
                st.markdown(f"""<div style="background:#111820;border:1px solid #1e2a38;
                    border-radius:6px;padding:14px;text-align:center">
                    <div style="color:{sc};font-size:1.5rem;font-weight:700">{sig}</div>
                    <div style="font-size:1.2rem;font-weight:600;font-family:'JetBrains Mono',monospace">
                        {acc_s:.1f}%</div>
                    <div style="color:#7a8496;font-size:0.78rem">{data['n']} predictions</div>
                    <div style="color:{sc};font-size:0.8rem">
                        Avg return: {data['avg_ret']*100:+.2f}%</div>
                </div>""", unsafe_allow_html=True)



def main():
    # Init DB on first run
    try:
        from kairon.db.database import init_db
        init_db()
    except Exception as e:
        st.sidebar.warning(f"DB init: {e}")

    # First-run onboarding wizard (Document 16)
    try:
        from kairon.ui.onboarding import is_first_run, render_onboarding
        if is_first_run() and not st.session_state.get("onboarding_done"):
            if not render_onboarding():
                return  # Wizard not yet complete — don't render main app
    except Exception:
        pass  # If onboarding fails, continue to main app

    render_sidebar()

    screen = st.session_state.screen
    if screen == "Mission Control":
        screen_mission_control()
    elif screen == "Move Recommendations":
        screen_moves()
    elif screen == "Agent Intelligence":
        screen_agents()
    elif screen == "Knowledge Base":
        screen_kb()
    elif screen == "Cost Calculator":
        screen_costs()
    elif screen == "Connection Map":
        screen_connection_map()
    elif screen == "Portfolio Loader":
        screen_portfolio()
    elif screen == "Backtesting":
        screen_backtest()


if __name__ == "__main__":
    main()
