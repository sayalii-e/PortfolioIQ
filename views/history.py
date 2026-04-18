"""
pages/history.py
================
Tab 3 – Historical DQ scores, failed fetches, applied changes,
         full audit log, and all download/export options.

All data is read directly from SQLite via utils/database.py helpers,
so this tab works even after a page refresh (no session state dependency).
"""

import os

import pandas as pd
import streamlit as st

from utils.database import (
    DB_PATH,
    load_history,
    load_applied_changes,
    load_fetch_errors,
    load_audit_log,
)
from components.ui import section_header, log_entry_html


# ── Page render ────────────────────────────────────────────────────────────────

def render_history():
    _render_score_history()
    _render_failed_fetches()
    _render_applied_changes()
    _render_audit_log()
    _render_exports()


# ── Sub-sections ───────────────────────────────────────────────────────────────

def _render_score_history():
    section_header("Quality Score History")

    hist = load_history()

    if hist.empty:
        st.info("No history yet — go to **⬡ Ingestion** and fetch some sources first.")
        return

    # ── Trend chart ────────────────────────────────────────────────────────────
    chart_df = hist[["Assessed At", "Total Score", "Source"]].copy()
    chart_df["Assessed At"] = pd.to_datetime(chart_df["Assessed At"])

    if chart_df["Source"].nunique() > 1:
        # Multiple sources → pivot so each becomes its own line
        pivot = chart_df.pivot_table(
            index="Assessed At", columns="Source", values="Total Score", aggfunc="mean"
        )
        st.line_chart(pivot, height=280)
    else:
        # Single source → simple line
        chart_df = chart_df.set_index("Assessed At")[["Total Score"]]
        st.line_chart(chart_df, height=280)

    # ── Full table ─────────────────────────────────────────────────────────────
    section_header("Full Report Table")
    st.dataframe(hist, use_container_width=True, hide_index=True)

    csv = hist.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Quality History (CSV)",
        data=csv,
        file_name="dq_history.csv",
        mime="text/csv",
        key="dl_history",
    )


def _render_failed_fetches():
    errors = load_fetch_errors()
    if errors.empty:
        return

    section_header("Fetch Error Log")
    st.dataframe(errors, use_container_width=True, hide_index=True)

    csv = errors.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Error Log (CSV)",
        data=csv,
        file_name="fetch_errors.csv",
        mime="text/csv",
        key="dl_errors",
    )


def _render_applied_changes():
    changes = load_applied_changes()
    if changes.empty:
        return

    section_header("Applied Changes Log")
    st.dataframe(changes, use_container_width=True, hide_index=True)

    csv = changes.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Changes Log (CSV)",
        data=csv,
        file_name="dq_changes.csv",
        mime="text/csv",
        key="dl_changes",
    )


def _render_audit_log():
    audit = load_audit_log()
    if audit.empty:
        return

    section_header("Audit Log")
    with st.expander(f"Show full audit log ({len(audit)} entries)", expanded=False):
        for _, row in audit.iterrows():
            log_entry_html(str(row["Time"]), str(row["Event"]), str(row["Detail"]))


def _render_exports():
    section_header("Export")

    col1, col2 = st.columns(2)

    # ── SQLite database ────────────────────────────────────────────────────────
    with col1:
        st.markdown("**Full Database**")
        st.caption("Download the raw SQLite file containing all tables.")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button(
                label="⬇ Download findqe.db",
                data=db_bytes,
                file_name="findqe.db",
                mime="application/octet-stream",
                key="dl_db",
            )
        else:
            st.caption("Database not found. Run a fetch first.")

    # ── Modified DataFrames ────────────────────────────────────────────────────
    with col2:
        st.markdown("**Modified Source Data**")
        st.caption("Download the cleaned / fixed DataFrame for any source.")

        if not st.session_state.get("modified_dfs"):
            st.caption("No modified data in this session. Run a fetch first.")
        else:
            src_labels = {
                url: next(
                    (s["alias"] for s in st.session_state.sources if s["url"] == url),
                    url[:40],
                )
                for url in st.session_state.modified_dfs
            }
            chosen = st.selectbox(
                "Select source",
                list(src_labels.keys()),
                format_func=lambda u: src_labels[u],
                key="export_src_select",
            )
            if chosen:
                df_dl = st.session_state.modified_dfs[chosen]
                csv = df_dl.to_csv(index=False).encode("utf-8")
                safe_name = src_labels[chosen].replace(" ", "_").lower()
                st.download_button(
                    label=f"⬇ Download {src_labels[chosen]} (CSV)",
                    data=csv,
                    file_name=f"{safe_name}_modified.csv",
                    mime="text/csv",
                    key="dl_modified",
                )