"""
utils/session.py
================
Centralises all st.session_state keys and their defaults.
Call init_session_state() once at app startup.

Keys:
  sources        – list of {url, alias, auth} dicts the user has added
  fetch_results  – url → {df, raw, error, fetch_id}
  reports        – url → full DQ report dict
  modified_dfs   – url → DataFrame after user-applied fixes
  applied        – url → list of suggestion action keys already applied
"""

import streamlit as st

_DEFAULTS: dict = {
    "sources":       [],   # list[dict]
    "fetch_results": {},   # dict[url, dict]
    "reports":       {},   # dict[url, dict]
    "modified_dfs":  {},   # dict[url, pd.DataFrame]
    "applied":       {},   # dict[url, list[str]]
}


def init_session_state():
    """Set missing session keys to their default values."""
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default