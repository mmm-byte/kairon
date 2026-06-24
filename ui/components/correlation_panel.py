"""
kairon/ui/components/correlation_panel.py
Reusable correlation heatmap and contagion alert component.
Imported by the Mission Control and Connection Map screens.
"""
import streamlit as st
import pandas as pd


def render_correlation_heatmap(regime: str = "Risk-On"):
    """Render the cross-market correlation heatmap."""
    try:
        from kairon.intelligence.correlation_tracker import get_correlation_heatmap_data
        data = get_correlation_heatmap_data(regime)
    except Exception as e:
        st.markdown(f'<div style="color:#3d4558;font-size:0.8rem">Correlation data unavailable: {e}</div>',
                    unsafe_allow_html=True)
        return

    heatmap = data.get("heatmap", [])
    if not heatmap:
        return

    st.markdown("#### Cross-Market Correlations")

    # Grid of correlation cells
    cols_per_row = 3
    rows = [heatmap[i:i + cols_per_row] for i in range(0, len(heatmap), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for i, item in enumerate(row):
            with cols[i]:
                a1  = item["asset1"]
                a2  = item["asset2"]
                c   = item["corr"]
                col = item["color"]
                strength_pct = int(abs(c) * 100)
                direction = "↑ positive" if c > 0.05 else ("↓ inverse" if c < -0.05 else "→ neutral")

                st.markdown(f"""<div style="background:#111820;border:1px solid #1e2a38;
                    border-top:3px solid {col};border-radius:6px;padding:10px;margin-bottom:8px">
                    <div style="font-size:0.72rem;color:#7a8496;text-transform:uppercase;
                         letter-spacing:.5px;margin-bottom:4px">{a1} / {a2}</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{col};
                         font-family:'JetBrains Mono',monospace">{c:+.2f}</div>
                    <div style="font-size:0.72rem;color:#3d4558">{direction}</div>
                    <div style="background:#1e2a38;border-radius:2px;height:4px;margin-top:6px;overflow:hidden">
                        <div style="width:{strength_pct}%;height:100%;background:{col};border-radius:2px"></div>
                    </div>
                </div>""", unsafe_allow_html=True)


def render_contagion_alert(regime: str = "Risk-On"):
    """Render a contagion detection alert if correlations are anomalous."""
    try:
        from kairon.intelligence.correlation_tracker import compute_correlation_matrix, detect_contagion
        corrs   = compute_correlation_matrix(regime)
        result  = detect_contagion(corrs, regime)
    except Exception:
        return

    if result["severity"] == "low":
        return

    sev_color = "#ff3d57" if result["contagion"] else "#ffb300"
    icon      = "🔴" if result["contagion"] else "⚠"

    st.markdown(f"""<div style="background:{sev_color}15;border:1px solid {sev_color};
        border-radius:6px;padding:12px 16px;margin-bottom:16px">
        <div style="display:flex;align-items:center;gap:8px">
            <span>{icon}</span>
            <span style="color:{sev_color};font-weight:600">
                {'CONTAGION ALERT' if result['contagion'] else 'Correlation Anomaly'}
            </span>
            <span style="color:#7a8496;font-size:0.78rem;margin-left:4px">
                avg abs corr: {result['avg_abs_corr']:.2f}
            </span>
        </div>
        {''.join(f'<div style="color:#e8edf5;font-size:0.82rem;margin-top:6px">→ {a["message"]}</div>'
                  for a in result["alerts"][:3])}
    </div>""", unsafe_allow_html=True)
