"""
utils/styles.py
===============
Global CSS – light theme.
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');

/* ── Design tokens (light theme) ────────────────────────── */
:root {
    --bg:        #f5f6fa;
    --bg2:       #ffffff;
    --bg3:       #eef0f6;
    --border:    #dde1ed;
    --accent:    #2563eb;
    --accent2:   #7c3aed;
    --warn:      #d97706;
    --danger:    #dc2626;
    --ok:        #059669;
    --text:      #1e2433;
    --muted:     #6b7280;
    --shadow:    0 1px 4px rgba(0,0,0,0.08);
    --mono:      'IBM Plex Mono', monospace;
    --sans:      'Inter', sans-serif;
}

/* ── Base ─────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--sans);
    background-color: var(--bg) !important;
    color: var(--text);
}
::-webkit-scrollbar       { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Hide Streamlit chrome ───────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem; max-width: 1400px; }

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container { padding: 1rem; }

/* ── Top bar ─────────────────────────────────────────────── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 1.2rem;
    border-bottom: 2px solid var(--border);
    margin-bottom: 1.5rem;
}
.logo {
    font-family: var(--mono);
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.02em;
}
.logo span { color: var(--muted); font-weight: 400; }
.badge {
    font-family: var(--mono);
    font-size: 0.6rem;
    padding: 3px 10px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 99px;
    color: var(--accent);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Section headers ─────────────────────────────────────── */
.section-header {
    font-family: var(--mono);
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 1.4rem 0 0.7rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Metric labels ───────────────────────────────────────── */
.metric-label {
    font-family: var(--mono);
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.25rem;
}
.metric-value {
    font-family: var(--mono);
    font-size: 1.9rem;
    font-weight: 600;
    line-height: 1;
    color: var(--text);
}

/* ── Score ring ──────────────────────────────────────────── */
.score-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1.5rem 0;
}
.score-ring {
    width: 148px; height: 148px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-direction: column;
    position: relative;
    margin-bottom: 0.6rem;
}
.score-ring::before {
    content: '';
    position: absolute; inset: -4px;
    border-radius: 50%;
    background: conic-gradient(var(--rc, #059669) var(--pct, 0%), #e5e7eb 0%);
    z-index: -1;
}
.score-ring::after {
    content: '';
    position: absolute; inset: 8px;
    border-radius: 50%;
    background: var(--bg2);
    z-index: -1;
}
.score-num {
    font-family: var(--mono);
    font-size: 2.3rem;
    font-weight: 600;
    line-height: 1;
}
.score-sub {
    font-size: 0.62rem;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* ── Dimension bars ──────────────────────────────────────── */
.dim-bar-wrap { margin: 0.5rem 0; }
.dim-label {
    font-family: var(--mono);
    font-size: 0.65rem;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
}
.dim-bar  { height: 7px; background: var(--bg3); border-radius: 4px; overflow: hidden; }
.dim-fill { height: 100%; border-radius: 4px; }

/* ── Pills ───────────────────────────────────────────────── */
.pill {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.58rem;
    padding: 2px 9px;
    border-radius: 99px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-right: 4px;
}
.pill-ok     { background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }
.pill-warn   { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
.pill-danger { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

/* ── Suggestion box ──────────────────────────────────────── */
.suggestion-box {
    background: #f8f9ff;
    border: 1px solid #c7d2fe;
    border-left: 4px solid var(--sug-color, #2563eb);
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.75rem;
    box-shadow: var(--shadow);
}
.suggestion-title {
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
    font-weight: 600;
}

/* ── Failed fetch card ───────────────────────────────────── */
.failed-card {
    background: #fff5f5;
    border: 1px solid #fecaca;
    border-left: 4px solid #dc2626;
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
}
.failed-title {
    font-family: var(--mono);
    font-size: 0.68rem;
    font-weight: 600;
    color: #991b1b;
    margin-bottom: 0.25rem;
    letter-spacing: 0.05em;
}
.failed-detail { font-size: 0.78rem; color: #7f1d1d; }
.failed-hint   { font-size: 0.72rem; color: var(--muted); margin-top: 0.3rem; }

/* ── Audit log ───────────────────────────────────────────── */
.log-entry {
    font-family: var(--mono);
    font-size: 0.68rem;
    color: var(--muted);
    padding: 5px 0;
    border-bottom: 1px solid var(--border);
}
.log-ts { color: var(--accent); font-weight: 600; }

/* ── Inputs ──────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea textarea {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: var(--mono);
    font-size: 0.82rem;
    border-radius: 6px;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15) !important;
}
.stSelectbox > div > div {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px;
    color: var(--text) !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    background: var(--bg2);
    border: 1.5px solid var(--accent);
    color: var(--accent);
    font-family: var(--mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 5px;
    padding: 0.35rem 0.9rem;
    transition: all 0.15s;
    box-shadow: var(--shadow);
}
.stButton > button:hover { background: var(--accent); color: #fff; }

.stDownloadButton > button {
    background: #eff6ff;
    border: 1.5px solid #bfdbfe;
    color: var(--accent);
    font-family: var(--mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    border-radius: 5px;
    transition: all 0.15s;
}
.stDownloadButton > button:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

/* ── Expander ────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    color: var(--text) !important;
}

/* ── Misc ────────────────────────────────────────────────── */
div[data-testid="stAlert"] { border-radius: 6px; font-size: 0.82rem; }
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px !important; box-shadow: var(--shadow); }
hr { border-color: var(--border); opacity: 1; }
h1,h2,h3,h4 { font-family: var(--mono); color: var(--text); }
</style>
"""


def inject_css():
    """Call once at startup to apply the global stylesheet."""
    st.markdown(CSS, unsafe_allow_html=True)