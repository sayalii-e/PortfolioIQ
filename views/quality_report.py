"""
pages/quality_report.py
=======================
Tab 2 – Per-source DQ report with interactive fix suggestions.

Responsibilities:
  • Source selector dropdown
  • Score ring + five dimension bars
  • Collapsible detailed issues per dimension
  • Scrollable data preview (up to 50 rows)
  • Ranked suggestion cards with Apply / Skip buttons
  • Live re-score after each applied fix
"""

import streamlit as st

from utils.database import log_event, save_applied_change
from utils.fixes import apply_fix
from utils.scoring import (
    score_completeness, score_accuracy, score_validity,
    score_consistency, score_timeliness,
    compute_total, build_suggestions,
)
from components.ui import section_header, score_ring, dimension_bar, suggestion_card


# ── Page render ────────────────────────────────────────────────────────────────

def render_quality_report():
    if not st.session_state.reports:
        st.info("No reports yet. Go to **⬡ Ingestion**, add sources, and click **Fetch & Analyse**.")
        return

    selected_url = _render_source_selector()
    if not selected_url:
        return

    report = st.session_state.reports[selected_url]
    df     = st.session_state.modified_dfs.get(selected_url)

    _render_score_overview(report)
    st.markdown("<hr>", unsafe_allow_html=True)
    _render_issues_detail(report)
    _render_data_preview(df)
    _render_suggestions(selected_url, report, df)


# ── Sub-sections ───────────────────────────────────────────────────────────────

def _render_source_selector() -> str | None:
    labels = {url: r["alias"] for url, r in st.session_state.reports.items()}
    if not labels:
        return None
    return st.selectbox(
        "Select source to inspect",
        list(labels.keys()),
        format_func=lambda u: labels[u],
    )


def _render_score_overview(report: dict):
    col_ring, col_bars = st.columns([1, 2])

    with col_ring:
        score_ring(report["total"], report["alias"])

    with col_bars:
        section_header("Dimension Breakdown")
        for name, key, weight in [
            ("Completeness", "completeness", "25%"),
            ("Accuracy",     "accuracy",     "25%"),
            ("Validity",     "validity",     "20%"),
            ("Consistency",  "consistency",  "15%"),
            ("Timeliness",   "timeliness",   "15%"),
        ]:
            dimension_bar(name, report[key], weight)


def _render_issues_detail(report: dict):
    with st.expander("🔍 Detailed Issues per Dimension", expanded=False):
        any_issues = False
        for label, key in [
            ("Completeness", "completeness_issues"),
            ("Accuracy",     "accuracy_issues"),
            ("Validity",     "validity_issues"),
            ("Consistency",  "consistency_issues"),
            ("Timeliness",   "timeliness_issues"),
        ]:
            issues = report.get(key, [])
            if issues:
                any_issues = True
                st.markdown(f"**{label}**")
                for iss in issues:
                    st.markdown(f"- {iss}")
        if not any_issues:
            st.success("No issues detected across all dimensions.")


def _render_data_preview(df):
    section_header("Data Preview")
    if df is not None and not df.empty:
        st.dataframe(df.head(50), use_container_width=True)
        st.caption(f"{len(df)} rows × {len(df.columns)} columns · Showing up to 50 rows")
    else:
        st.warning("No structured data available for this source.")


def _render_suggestions(url: str, report: dict, df):
    suggestions = report.get("suggestions", [])
    section_header("Improvement Suggestions")

    if not suggestions:
        st.success("✓ No suggestions — data quality looks strong!")
        return

    applied_keys = st.session_state.applied.get(url, [])

    for sug in suggestions:
        suggestion_card(sug)

        if sug["action"] in applied_keys:
            st.markdown('<span class="pill pill-ok">✓ Applied</span>', unsafe_allow_html=True)
        else:
            col_a, col_s, _ = st.columns([1, 1, 5])
            with col_a:
                if st.button("Apply Fix", key=f"apply_{url}_{sug['action']}"):
                    _apply_and_rescore(url, sug, df)
                    st.rerun()
            with col_s:
                if st.button("Skip", key=f"skip_{url}_{sug['action']}"):
                    st.session_state.applied[url].append(sug["action"])
                    log_event("suggestion_skipped", f"{url}: {sug['action']}")
                    st.rerun()

        st.markdown("<div style='margin-bottom:0.6rem'></div>", unsafe_allow_html=True)


# ── Fix + re-score ─────────────────────────────────────────────────────────────

def _apply_and_rescore(url: str, sug: dict, df):
    new_df, result_msg = apply_fix(df, sug["action"])

    save_applied_change(sug["action"], sug["body"], result_msg)
    log_event("change_applied", f"{url}: {sug['action']}")

    st.session_state.modified_dfs[url] = new_df
    st.session_state.applied[url].append(sug["action"])
    st.success(result_msg)

    other_dfs = [
        st.session_state.modified_dfs[u]
        for u in st.session_state.modified_dfs
        if u != url
    ]

    c_s, c_i   = score_completeness(new_df)
    a_s, a_i   = score_accuracy(new_df)
    v_s, v_i   = score_validity(new_df)
    co_s, co_i = score_consistency(new_df, other_dfs)
    t_s, t_i   = score_timeliness(None, new_df)

    scores = {
        "completeness": c_s, "accuracy": a_s, "validity": v_s,
        "consistency": co_s, "timeliness": t_s,
        "total": compute_total({
            "completeness": c_s, "accuracy": a_s, "validity": v_s,
            "consistency": co_s, "timeliness": t_s,
        }),
    }
    issues = {
        "completeness_issues": c_i, "accuracy_issues": a_i,
        "validity_issues": v_i, "consistency_issues": co_i, "timeliness_issues": t_i,
    }
    alias = st.session_state.reports[url]["alias"]
    st.session_state.reports[url] = {
        "alias": alias, **scores, **issues,
        "suggestions": build_suggestions(scores, issues),
    }
