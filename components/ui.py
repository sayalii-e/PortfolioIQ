"""
components/ui.py
================
Reusable HTML/CSS snippets rendered via st.markdown.
All functions are side-effect-free (no DB calls, no session state).
"""

import streamlit as st


def section_header(label: str):
    st.markdown(f'<div class="section-header">{label}</div>', unsafe_allow_html=True)


def score_ring(total: float, alias: str):
    """Circular conic-gradient ring showing the overall DQ score."""
    if total >= 80:
        color, pill = "#059669", '<span class="pill pill-ok">GOOD</span>'
    elif total >= 60:
        color, pill = "#d97706", '<span class="pill pill-warn">NEEDS WORK</span>'
    else:
        color, pill = "#dc2626", '<span class="pill pill-danger">POOR</span>'

    st.markdown(
        f"""
        <div class="score-wrap">
          <div class="score-ring" style="--pct:{total}%; --rc:{color};">
            <div class="score-num" style="color:{color}">{total}</div>
            <div class="score-sub">/100</div>
          </div>
          <div style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);
                      letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">
            {alias}
          </div>
          <div>{pill}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dimension_bar(name: str, score: float, weight: str):
    """Single horizontal progress bar for one DQ dimension."""
    color = "#059669" if score >= 80 else ("#d97706" if score >= 60 else "#dc2626")
    st.markdown(
        f"""
        <div class="dim-bar-wrap">
          <div class="dim-label">
            <span>{name} <span style="color:var(--muted)">({weight})</span></span>
            <span style="color:{color};font-weight:600">{score}</span>
          </div>
          <div class="dim-bar">
            <div class="dim-fill" style="width:{score}%; background:{color};"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def suggestion_card(sug: dict):
    """Coloured suggestion box. Caller renders the Apply/Skip buttons below it."""
    st.markdown(
        f"""
        <div class="suggestion-box" style="--sug-color:{sug['color']};">
          <div class="suggestion-title" style="color:{sug['color']}">
            ▲ +{sug['impact']} pts · {sug['dim'].upper()}
          </div>
          <div style="font-size:0.85rem;font-weight:600;margin-bottom:4px;color:var(--text)">
            {sug['title']}
          </div>
          <div style="font-size:0.8rem;color:var(--muted)">{sug['body']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def failed_fetch_card(alias: str, error: str, hint: str):
    """Red card shown when a fetch fails — includes a human-readable hint."""
    st.markdown(
        f"""
        <div class="failed-card">
          <div class="failed-title">✕ FETCH FAILED — {alias}</div>
          <div class="failed-detail">{error}</div>
          <div class="failed-hint">💡 {hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def log_entry_html(ts: str, event: str, detail: str):
    st.markdown(
        f'<div class="log-entry">'
        f'<span class="log-ts">{ts}</span> · {event} · {detail}'
        f"</div>",
        unsafe_allow_html=True,
    )