"""
FinDQE – Financial Data Quality Engine

"""

import streamlit as st
from utils.database import init_db
from utils.styles import inject_css
from utils.session import init_session_state
from views.ingestion import render_ingestion
from views.quality_report import render_quality_report
from views.history import render_history
import numpy as np

# ── Page config (must be the very first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="FinDQE · Financial Data Quality Engine",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Bootstrap ──────────────────────────────────────────────────────────────────
init_db()             # create SQLite tables if they don't exist
inject_css()          # inject global light-theme stylesheet
init_session_state()  # set default session_state keys

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="logo" style="padding:0.5rem 0 0.25rem">⬡ FinDQE <span>· engine</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Navigation</div>', unsafe_allow_html=True)

    tab = st.radio(
        "Navigate to",
        ["⬡ Ingestion", "◈ Quality Report", "◇ History & Export"],
        label_visibility="hidden",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Connected Sources</div>', unsafe_allow_html=True)

    if st.session_state.sources:
        for s in st.session_state.sources:
            display = s["alias"] or s["url"][:32]
            res = st.session_state.fetch_results.get(s["url"], {})
            dot = "🔴" if res.get("error") else ("🟢" if res.get("df") is not None else "⚪")
            st.markdown(
                f'<div class="log-entry">{dot} {display}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No sources yet.")

    # Average score badge
    if st.session_state.reports:
        scores = [r["total"] for r in st.session_state.reports.values()]
        avg = float(np.mean(scores))
        color = "#059669" if avg >= 80 else ("#d97706" if avg >= 60 else "#dc2626")
        st.markdown(
            f'<div style="margin-top:1.2rem;">'
            f'<div class="metric-label">Avg DQ Score</div>'
            f'<div class="metric-value" style="color:{color}">{avg:.0f}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Top bar ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="topbar">
      <div class="logo">⬡ FinDQE <span>· Financial Data Quality Engine</span></div>
      <div class="badge">v1.1 · production</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Route ──────────────────────────────────────────────────────────────────────
if "Ingestion" in tab:
    render_ingestion()
elif "Quality" in tab:
    render_quality_report()
else:
    render_history()