"""
pages/ingestion.py
==================
Tab 1 – API Source Configuration & Data Fetching.

Responsibilities:
  • Let the user add / remove API endpoints (with optional auth headers)
  • Provide one-click demo APIs for instant testing
  • Trigger fetch + score for all registered sources
  • Show a clear failure card when a source cannot be reached
  • Persist raw data, quality reports, and fetch errors to SQLite
"""

import json
import time

import streamlit as st
import pandas as pd

from utils.database import (
    log_event, save_source, save_fetch, save_report,
    save_fetch_error, load_source_id,
)
from utils.fetcher import fetch_api, to_dataframe
from utils.scoring import (
    score_completeness, score_accuracy, score_validity,
    score_consistency, score_timeliness,
    compute_total, build_suggestions,
)
from components.ui import section_header, failed_fetch_card

# ── Pre-loaded demo endpoints ──────────────────────────────────────────────────
DEMO_APIS: dict[str, str] = {
    "CoinGecko (Cryptos)": (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&ids=bitcoin,ethereum,solana,cardano"
        "&order=market_cap_desc&per_page=10&page=1"
    ),
    "ExchangeRate (USD)": "https://open.er-api.com/v6/latest/USD",
    "Alpha Vantage IBM": (
        "https://www.alphavantage.co/query"
        "?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo"
    ),
    "Open Meteo (NY)": (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=40.71&longitude=-74.01&current_weather=true"
    ),
}


# ── Page render ────────────────────────────────────────────────────────────────

def render_ingestion():
    _render_add_form()
    _render_demo_buttons()
    _render_source_table()
    _render_failed_sources()
    _render_fetch_button()


# ── Sub-sections ───────────────────────────────────────────────────────────────

def _render_add_form():
    section_header("Add API Source")

    col_url, col_alias = st.columns([3, 1])
    with col_url:
        new_url = st.text_input(
            "API Endpoint URL",
            placeholder="https://api.example.com/v1/market/quotes?symbol=AAPL",
            key="new_url_input",
        )
    with col_alias:
        new_alias = st.text_input("Alias (optional)", placeholder="My API")

    auth_raw = st.text_input(
        "Auth Header – JSON object (optional)",
        placeholder='{"Authorization": "Bearer YOUR_TOKEN"}',
        help='e.g. {"X-Api-Key": "abc123"}',
    )

    if st.button("＋ Add Source"):
        if not new_url:
            st.warning("Please enter a URL.")
            return
        auth: dict = {}
        if auth_raw:
            try:
                auth = json.loads(auth_raw)
            except json.JSONDecodeError:
                st.warning("Auth header is not valid JSON – ignored.")
        if any(s["url"] == new_url for s in st.session_state.sources):
            st.info("This URL is already in the list.")
            return
        alias = new_alias or new_url[:40]
        save_source(new_url, alias, auth)
        st.session_state.sources.append({"url": new_url, "alias": alias, "auth": auth})
        log_event("source_added", new_url)
        st.success(f"Source added: {alias}")


def _render_demo_buttons():
    section_header("Quick-Add Demo Sources")
    cols = st.columns(len(DEMO_APIS))
    for i, (label, url) in enumerate(DEMO_APIS.items()):
        with cols[i]:
            if st.button(f"＋ {label}", key=f"demo_{i}"):
                if not any(s["url"] == url for s in st.session_state.sources):
                    save_source(url, label, {})
                    st.session_state.sources.append({"url": url, "alias": label, "auth": {}})
                    log_event("demo_source_added", label)
                    st.rerun()
                else:
                    st.info(f"'{label}' already added.")


def _render_source_table():
    if not st.session_state.sources:
        st.info("No sources added yet. Use the form above or click a demo source.")
        return

    section_header("Sources Queue")

    table = pd.DataFrame(
        [{"Alias": s["alias"], "URL": s["url"]} for s in st.session_state.sources]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    remove_choice = st.selectbox(
        "Remove a source",
        ["— select to remove —"] + [s["alias"] for s in st.session_state.sources],
    )
    if remove_choice != "— select to remove —" and st.button("✕ Remove Selected"):
        st.session_state.sources = [
            s for s in st.session_state.sources if s["alias"] != remove_choice
        ]
        # Also clear its results/report if present
        url_to_remove = next(
            (s["url"] for s in st.session_state.sources if s["alias"] == remove_choice), None
        )
        if url_to_remove:
            st.session_state.fetch_results.pop(url_to_remove, None)
            st.session_state.reports.pop(url_to_remove, None)
            st.session_state.modified_dfs.pop(url_to_remove, None)
            st.session_state.applied.pop(url_to_remove, None)
        st.rerun()


def _render_failed_sources():
    """Show failure cards for any source that errored on the last fetch."""
    failed = {
        url: res
        for url, res in st.session_state.fetch_results.items()
        if res.get("error")
    }
    if not failed:
        return

    section_header("Failed Sources (last run)")
    for url, res in failed.items():
        alias = next((s["alias"] for s in st.session_state.sources if s["url"] == url), url[:40])
        failed_fetch_card(alias, res["error"], res.get("hint", "Check the URL and try again."))


def _render_fetch_button():
    if not st.session_state.sources:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.button("⬡ Fetch & Analyse All Sources", type="primary"):
        return

    n = len(st.session_state.sources)
    progress = st.progress(0, text="Initialising…")

    # ── Step 1: fetch every source ─────────────────────────────────────────────
    for i, src in enumerate(st.session_state.sources):
        progress.progress(i / n, text=f"Fetching {src['alias']}…")
        raw, err, hint = fetch_api(src["url"], src.get("auth") or None)

        if err:
            # Store error so the failure card renders
            st.session_state.fetch_results[src["url"]] = {
                "error": err, "hint": hint, "df": None, "raw": None, "fetch_id": None,
            }
            save_fetch_error(src["alias"], src["url"], err, hint)
            log_event("fetch_error", f"{src['url']}: {err}")
            continue

        df = to_dataframe(raw)
        src_id = load_source_id(src["url"])
        fetch_id = save_fetch(src_id, json.dumps(raw), len(df))

        st.session_state.fetch_results[src["url"]] = {
            "df": df, "raw": raw, "error": None, "hint": None, "fetch_id": fetch_id,
        }
        log_event("fetch_ok", f"{src['url']} rows={len(df)}")

    # ── Step 2: score every successful source ──────────────────────────────────
    progress.progress(0.8, text="Computing quality scores…")

    successful_urls = [
        src["url"]
        for src in st.session_state.sources
        if not st.session_state.fetch_results.get(src["url"], {}).get("error")
        and st.session_state.fetch_results.get(src["url"], {}).get("df") is not None
    ]

    for url in successful_urls:
        src = next(s for s in st.session_state.sources if s["url"] == url)
        res = st.session_state.fetch_results[url]
        df  = res["df"]
        raw = res["raw"]

        other_dfs = [
            st.session_state.fetch_results[u]["df"]
            for u in successful_urls
            if u != url
        ]

        c_s, c_i   = score_completeness(df)
        a_s, a_i   = score_accuracy(df)
        v_s, v_i   = score_validity(df)
        co_s, co_i = score_consistency(df, other_dfs)
        t_s, t_i   = score_timeliness(raw, df)

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
            "validity_issues": v_i, "consistency_issues": co_i,
            "timeliness_issues": t_i,
        }
        suggestions = build_suggestions(scores, issues)

        st.session_state.reports[url]      = {"alias": src["alias"], **scores, **issues, "suggestions": suggestions}
        st.session_state.modified_dfs[url] = df.copy()
        st.session_state.applied[url]      = []

        save_report(res["fetch_id"], src["alias"], scores, suggestions)
        log_event("report_saved", f"{url} score={scores['total']}")

    progress.progress(1.0, text="Done!")
    time.sleep(0.3)
    progress.empty()

    ok_count   = len(successful_urls)
    fail_count = n - ok_count

    if ok_count:
        st.success(f"✓ {ok_count} source(s) analysed successfully. Open **◈ Quality Report** to explore.")
    if fail_count:
        st.error(f"✕ {fail_count} source(s) failed — see the red cards above for details.")