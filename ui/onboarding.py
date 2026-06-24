"""
kairon/ui/onboarding.py
First-run wizard (Document 16).
Rendered when FIRST_RUN=true in .env or when kairon.db doesn't exist yet.
Guides the user through: setup choice → portfolio → system check → launch.
Returns True when onboarding is complete.
"""
import os
import logging

logger = logging.getLogger("kairon.onboarding")


def is_first_run() -> bool:
    """Check whether this is the first time the user has opened Kairon."""
    # Completed flag stored in a local file so it persists across sessions
    return not os.path.exists(".kairon_configured")


def mark_configured():
    """Write the configured flag so wizard doesn't show again."""
    try:
        with open(".kairon_configured", "w") as f:
            f.write("1")
    except Exception:
        pass


def render_onboarding() -> bool:
    """
    Render the 4-step first-run wizard using Streamlit.
    Returns True when the user has completed or skipped the wizard.
    """
    import streamlit as st

    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1
    if "onboarding_done" not in st.session_state:
        st.session_state.onboarding_done = False

    if st.session_state.onboarding_done:
        return True

    step = st.session_state.onboarding_step

    # ── Wizard chrome ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="max-width:680px;margin:40px auto">
    """, unsafe_allow_html=True)

    # Progress dots
    dots = "".join(
        f'<span style="width:10px;height:10px;border-radius:50%;display:inline-block;margin:0 4px;'
        f'background:{"#00e676" if i <= step else "#1e2a38"}"></span>'
        for i in range(1, 5)
    )
    st.markdown(f'<div style="text-align:center;margin-bottom:24px">{dots}</div>',
                unsafe_allow_html=True)

    # Skip link
    c_title, c_skip = st.columns([4, 1])
    with c_skip:
        if st.button("Skip →", key="skip_wizard", help="Use all defaults and launch immediately"):
            _apply_defaults()
            mark_configured()
            st.session_state.onboarding_done = True
            st.rerun()

    # ── Step 1: Welcome ────────────────────────────────────────────────────────
    if step == 1:
        with c_title:
            st.markdown("### Welcome to Kairon")
        st.markdown("""
        <div style="background:#111820;border:1px solid #1e2a38;border-radius:8px;padding:24px;margin:16px 0">
            <div style="font-size:1.05rem;color:#e8edf5;margin-bottom:12px">
                Your financial intelligence system — powered by open data and AI.
            </div>
            <div style="color:#7a8496;font-size:0.88rem;line-height:1.7">
                Kairon watches 6 global markets simultaneously, uses a team of 8 AI agents to 
                identify opportunities, and calculates exact net profit after every cost.<br><br>
                <span style="color:#ffb300">SIM MODE:</span> Kairon operates in simulation. 
                No real trades are executed. All recommendations are educational only.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Get started →", type="primary", use_container_width=True,
                     key="step1_next"):
            st.session_state.onboarding_step = 2
            st.rerun()

    # ── Step 2: Setup choice ──────────────────────────────────────────────────
    elif step == 2:
        with c_title:
            st.markdown("### Choose your setup")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div style="background:#003320;border:2px solid #00e676;border-radius:8px;padding:16px;text-align:center">
                <div style="color:#00e676;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">RECOMMENDED</div>
                <div style="color:#e8edf5;font-weight:600;margin-bottom:8px">Zero Config</div>
                <div style="color:#7a8496;font-size:0.82rem">Open data + local AI. Works immediately. No keys needed.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Use Zero Config", key="setup_zero", type="primary",
                          use_container_width=True):
                _apply_defaults()
                st.session_state.onboarding_step = 3
                st.rerun()

        with col2:
            st.markdown("""
            <div style="background:#111820;border:1px solid #1e2a38;border-radius:8px;padding:16px;text-align:center">
                <div style="color:#2979ff;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">ENHANCED</div>
                <div style="color:#e8edf5;font-weight:600;margin-bottom:8px">Add API Keys</div>
                <div style="color:#7a8496;font-size:0.82rem">Add FRED + Brave Search for richer data quality.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Add keys", key="setup_keys", use_container_width=True):
                st.session_state.onboarding_setup = "keys"
                st.session_state.onboarding_step  = 3
                st.rerun()

        with col3:
            st.markdown("""
            <div style="background:#111820;border:1px solid #1e2a38;border-radius:8px;padding:16px;text-align:center">
                <div style="color:#aa00ff;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">POWER USER</div>
                <div style="color:#e8edf5;font-weight:600;margin-bottom:8px">Full Setup</div>
                <div style="color:#7a8496;font-size:0.82rem">Cloud LLM + all data sources configured.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Full setup", key="setup_full", use_container_width=True):
                st.session_state.onboarding_setup = "full"
                st.session_state.onboarding_step  = 3
                st.rerun()

        # Key entry if chosen
        if st.session_state.get("onboarding_setup") in ("keys", "full"):
            st.divider()
            st.markdown("**Optional API Keys** (leave blank to skip any)")
            fred  = st.text_input("FRED API Key",   type="password",
                                   help="Free at fred.stlouisfed.org — improves macro data")
            brave = st.text_input("Brave Search Key", type="password",
                                   help="Free 2000/mo at api.search.brave.com — multi-outlet news")
            llm_choice = st.selectbox("AI explanations", ["Local (Ollama)", "OpenAI", "None"])
            api_key = ""
            if llm_choice == "OpenAI":
                api_key = st.text_input("OpenAI API Key", type="password")

            if st.button("Save & continue →", key="save_keys", type="primary"):
                if fred:
                    os.environ["FRED_API_KEY"] = fred
                if brave:
                    os.environ["BRAVE_SEARCH_API_KEY"] = brave
                if api_key:
                    os.environ["OPENAI_API_KEY"]  = api_key
                    os.environ["LLM_PROVIDER"]    = "openai"
                elif llm_choice == "Local (Ollama)":
                    os.environ["LLM_PROVIDER"] = "ollama"
                st.session_state.onboarding_step = 3
                st.rerun()

    # ── Step 3: Portfolio choice ───────────────────────────────────────────────
    elif step == 3:
        with c_title:
            st.markdown("### Choose a starting portfolio")

        from kairon.engine.portfolio import DEMO_PORTFOLIOS
        portfolios = {
            "Conservative Investor": "60% bonds · 30% gold · 10% cash — defensive setup",
            "Balanced (Default)":    "40% stocks · 20% bonds · 20% gold · 20% cash — classic",
            "Aggressive Growth":     "60% NASDAQ · 30% crypto · 10% cash — high risk/reward",
            "Crypto Focus":          "50% BTC · 30% ETH · 20% stable — crypto portfolio",
            "All Equities":          "SPY + AAPL + NVDA + TSLA + AMZN — equity only",
        }
        choice = st.radio(
            "Select demo portfolio:",
            list(portfolios.keys()),
            index=1,
            label_visibility="collapsed",
        )
        st.markdown(f'<div style="color:#7a8496;font-size:0.85rem;margin:8px 0 16px">{portfolios[choice]}</div>',
                    unsafe_allow_html=True)

        capital = st.slider("Starting capital", 10_000, 500_000, 100_000, 5_000,
                             format="$%d")

        c_back, c_next = st.columns(2)
        with c_back:
            if st.button("← Back", key="step3_back"):
                st.session_state.onboarding_step = 2
                st.rerun()
        with c_next:
            if st.button("Continue →", type="primary", key="step3_next"):
                st.session_state.portfolio_capital = float(capital)
                st.session_state.selected_demo_portfolio = choice
                st.session_state.onboarding_step = 4
                st.rerun()

    # ── Step 4: System check ──────────────────────────────────────────────────
    elif step == 4:
        with c_title:
            st.markdown("### System ready")

        from kairon.data.source_status import source_status
        statuses = source_status.all_statuses()

        # Show source status
        sources_to_show = [
            ("yahoo_finance", "Yahoo Finance (prices)", True),
            ("gdelt",         "GDELT (global news)",    True),
            ("duckduckgo",    "DuckDuckGo (web news)",  True),
            ("fred",          "FRED macro data",         False),
            ("ollama",        "Ollama local AI",         False),
        ]
        st.markdown("**Data sources:**")
        for name, label, required in sources_to_show:
            info = next((s for s in statuses if s["name"] == name), None)
            state = info["state"] if info else "unknown"
            icon  = "✓" if state == "healthy" else ("!" if state == "degraded" else "○")
            color = "#00e676" if state == "healthy" else ("#ffb300" if state == "degraded" else "#3d4558")
            note  = "" if required else " (optional)"
            st.markdown(
                f'<div style="padding:4px 0;font-size:0.85rem">'
                f'<span style="color:{color}">{icon}</span> '
                f'<span style="color:#e8edf5">{label}</span>'
                f'<span style="color:#3d4558">{note}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("")
        st.markdown("""
        <div style="background:#111820;border-left:3px solid #00e676;padding:10px 14px;border-radius:0 6px 6px 0;font-size:0.85rem;color:#7a8496">
            Sources showing ○ (unknown) are optional and will connect when their API keys are added in Settings.
            Kairon works fully without them.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")
        if st.button("Launch Kairon →", type="primary", use_container_width=True,
                      key="launch_btn"):
            mark_configured()
            st.session_state.onboarding_done = True
            os.environ["FIRST_RUN"] = "false"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    return False


def _apply_defaults():
    """Apply zero-config defaults."""
    import streamlit as st
    if "portfolio_capital" not in st.session_state:
        st.session_state.portfolio_capital = 100_000.0
    if "selected_demo_portfolio" not in st.session_state:
        st.session_state.selected_demo_portfolio = "Balanced (Default)"
