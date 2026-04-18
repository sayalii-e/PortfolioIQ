"""
utils/database.py
=================
All SQLite interactions live here.

Tables:
  - api_sources       : registered API endpoints
  - fetched_data      : raw JSON snapshots per fetch
  - quality_reports   : DQ scores per fetch
  - applied_changes   : suggestions the user accepted
  - fetch_errors      : failed fetch attempts with reason
  - audit_log         : every meaningful event
"""

import sqlite3
import json

DB_PATH = "findqe.db"


# ── Connection ─────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema bootstrap ───────────────────────────────────────────────────────────

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS api_sources (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        url          TEXT    NOT NULL,
        alias        TEXT,
        auth_header  TEXT,
        added_at     TEXT    DEFAULT (datetime('now')),
        last_fetched TEXT
    );

    CREATE TABLE IF NOT EXISTS fetched_data (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id  INTEGER,
        fetched_at TEXT    DEFAULT (datetime('now')),
        raw_json   TEXT,
        row_count  INTEGER,
        FOREIGN KEY(source_id) REFERENCES api_sources(id)
    );

    CREATE TABLE IF NOT EXISTS quality_reports (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        fetch_id     INTEGER,
        assessed_at  TEXT    DEFAULT (datetime('now')),
        alias        TEXT,
        completeness REAL,
        accuracy     REAL,
        validity     REAL,
        consistency  REAL,
        timeliness   REAL,
        total_score  REAL,
        suggestions  TEXT,
        FOREIGN KEY(fetch_id) REFERENCES fetched_data(id)
    );

    CREATE TABLE IF NOT EXISTS applied_changes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion_key  TEXT,
        suggestion_text TEXT,
        applied_at      TEXT DEFAULT (datetime('now')),
        result          TEXT
    );

    CREATE TABLE IF NOT EXISTS fetch_errors (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        alias      TEXT,
        url        TEXT,
        error_msg  TEXT,
        hint       TEXT,
        failed_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        event  TEXT,
        detail TEXT,
        ts     TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()


# ── Write helpers ──────────────────────────────────────────────────────────────

def log_event(event: str, detail: str = ""):
    conn = get_db()
    conn.execute("INSERT INTO audit_log(event, detail) VALUES (?, ?)", (event, detail))
    conn.commit()
    conn.close()


def save_source(url: str, alias: str, auth: dict) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO api_sources(url, alias, auth_header) VALUES (?, ?, ?)",
        (url, alias, json.dumps(auth)),
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def save_fetch(source_id: int, raw_json: str, row_count: int) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO fetched_data(source_id, raw_json, row_count) VALUES (?, ?, ?)",
        (source_id, raw_json[:50_000], row_count),
    )
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return fid


def save_report(fetch_id: int, alias: str, scores: dict, suggestions: list):
    """Persist a quality report row - alias stored for easy history display."""
    conn = get_db()
    conn.execute(
        """INSERT INTO quality_reports
           (fetch_id, alias, completeness, accuracy, validity,
            consistency, timeliness, total_score, suggestions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            fetch_id,
            alias,
            scores["completeness"],
            scores["accuracy"],
            scores["validity"],
            scores["consistency"],
            scores["timeliness"],
            scores["total"],
            json.dumps(suggestions),
        ),
    )
    conn.commit()
    conn.close()


def save_fetch_error(alias: str, url: str, error_msg: str, hint: str):
    """Record a failed fetch attempt for display in History."""
    conn = get_db()
    conn.execute(
        "INSERT INTO fetch_errors(alias, url, error_msg, hint) VALUES (?, ?, ?, ?)",
        (alias, url, error_msg, hint),
    )
    conn.commit()
    conn.close()


def save_applied_change(suggestion_key: str, suggestion_text: str, result: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO applied_changes(suggestion_key, suggestion_text, result) VALUES (?, ?, ?)",
        (suggestion_key, suggestion_text, result),
    )
    conn.commit()
    conn.close()


# ── Read helpers ───────────────────────────────────────────────────────────────

def load_source_id(url: str) -> int | None:
    conn = get_db()
    row = conn.execute("SELECT id FROM api_sources WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row["id"] if row else None


def load_history():
    """Return all quality_reports rows with alias directly from the table."""
    conn = get_db()
    import pandas as pd
    df = pd.read_sql_query(
        """
        SELECT
            qr.assessed_at   AS "Assessed At",
            qr.alias         AS "Source",
            qr.completeness  AS "Completeness",
            qr.accuracy      AS "Accuracy",
            qr.validity      AS "Validity",
            qr.consistency   AS "Consistency",
            qr.timeliness    AS "Timeliness",
            qr.total_score   AS "Total Score"
        FROM quality_reports qr
        ORDER BY qr.assessed_at DESC
        LIMIT 500
        """,
        conn,
    )
    conn.close()
    return df


def load_applied_changes():
    conn = get_db()
    import pandas as pd
    df = pd.read_sql_query(
        """
        SELECT
            applied_at      AS "Applied At",
            suggestion_key  AS "Fix Type",
            suggestion_text AS "Description",
            result          AS "Result"
        FROM applied_changes
        ORDER BY applied_at DESC
        LIMIT 200
        """,
        conn,
    )
    conn.close()
    return df


def load_fetch_errors():
    conn = get_db()
    import pandas as pd
    df = pd.read_sql_query(
        """
        SELECT
            failed_at  AS "Failed At",
            alias      AS "Source",
            url        AS "URL",
            error_msg  AS "Error",
            hint       AS "Suggested Fix"
        FROM fetch_errors
        ORDER BY failed_at DESC
        LIMIT 200
        """,
        conn,
    )
    conn.close()
    return df


def load_audit_log():
    conn = get_db()
    import pandas as pd
    df = pd.read_sql_query(
        "SELECT ts AS Time, event AS Event, detail AS Detail FROM audit_log ORDER BY ts DESC LIMIT 300",
        conn,
    )
    conn.close()
    return df