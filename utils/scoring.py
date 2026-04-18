"""
utils/scoring.py
================
The heart of FinDQE.  Calculates five DQ dimensions and assembles
the weighted total score (0-100).

Dimensions & weights:
  Completeness  25%  – Are all expected fields present?
  Accuracy      25%  – Do values reflect reality (outlier / sign checks)?
  Validity      20%  – Are values within acceptable domains?
  Consistency   15%  – Does data agree with itself / other sources?
  Timeliness    15%  – Is the data fresh enough to be useful?
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime

# Known financial field name fragments used in completeness checks
FINANCIAL_FIELDS = [
    "price", "open", "high", "low", "close", "volume", "change", "changePercent",
    "date", "symbol", "ticker", "currency", "market", "exchange", "bid", "ask",
    "eps", "pe", "revenue", "profit", "loss", "assets", "liabilities", "equity",
    "rate", "yield", "spread", "maturity", "coupon", "notional", "nav", "aum",
]

# Valid ISO 4217 currency codes (abbreviated list)
VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY",
    "INR", "HKD", "SGD", "NZD", "MXN", "BRL", "ZAR", "KRW",
}

# Dimension colour map (used in the UI suggestion cards)
DIM_COLORS = {
    "completeness": "#00e5c8",
    "accuracy":     "#4f7cff",
    "validity":     "#ff9f43",
    "consistency":  "#a78bfa",
    "timeliness":   "#fb7185",
}


# ── 1. Completeness ────────────────────────────────────────────────────────────

def score_completeness(df: pd.DataFrame) -> tuple[float, list[str]]:
    """
    Penalises:
      • Missing / null / empty / 'N/A' cells
      • Complete absence of recognised financial field names
    """
    if df.empty:
        return 0.0, ["No data extracted – completeness cannot be measured."]

    total_cells = df.shape[0] * df.shape[1]
    missing = (
        df.isnull().sum().sum()
        + (df == "").sum().sum()
        + (df == "N/A").sum().sum()
    )
    pct_present = max(0.0, 1.0 - missing / max(total_cells, 1))

    issues: list[str] = []

    # Flag columns with > 30 % nulls
    high_null_cols = df.columns[df.isnull().mean() > 0.3].tolist()
    if high_null_cols:
        issues.append(f"High null rate (>30%) in: {', '.join(high_null_cols[:5])}")

    # Penalise if no financial vocabulary found
    fin_col_count = sum(
        1 for c in df.columns if any(f in c.lower() for f in FINANCIAL_FIELDS)
    )
    if fin_col_count == 0:
        issues.append("No recognised financial fields detected in column names.")
        pct_present *= 0.7

    return round(pct_present * 100, 1), issues


# ── 2. Accuracy ────────────────────────────────────────────────────────────────

def score_accuracy(df: pd.DataFrame) -> tuple[float, list[str]]:
    """
    Penalises:
      • Statistical outliers (|z| > 4)
      • Negative values in price-like columns
    """
    if df.empty:
        return 0.0, ["No data to assess accuracy."]

    score = 100.0
    issues: list[str] = []
    num_cols = df.select_dtypes(include=[np.number]).columns

    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 2:
            continue
        z = np.abs((series - series.mean()) / (series.std() + 1e-9))
        outlier_count = (z > 4).sum()
        if outlier_count:
            pct_out = outlier_count / len(series) * 100
            score -= min(15, pct_out * 2)
            issues.append(f"Outliers in '{col}': {outlier_count} rows exceed 4σ.")

    # Negative prices
    price_keywords = ["price", "close", "open", "high", "low", "bid", "ask", "nav"]
    for col in df.columns:
        if any(k in col.lower() for k in price_keywords):
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if (series < 0).any():
                score -= 10
                issues.append(f"Negative price values in '{col}'.")

    return max(0.0, round(score, 1)), issues


# ── 3. Validity ────────────────────────────────────────────────────────────────

def score_validity(df: pd.DataFrame) -> tuple[float, list[str]]:
    """
    Penalises:
      • Unparseable or future date values
      • Extreme percentage values (< -100 or > 1000)
      • Unknown currency codes
    """
    if df.empty:
        return 0.0, ["No data for validity check."]

    score = 100.0
    issues: list[str] = []

    for col in df.columns:
        cl = col.lower()
        series = df[col].dropna().astype(str)

        # Date fields
        if "date" in cl or "time" in cl:
            parsed = pd.to_datetime(series, errors="coerce", utc=True)
            bad_count = parsed.isna().sum()
            if bad_count:
                score -= min(10, bad_count * 2)
                issues.append(f"Unparseable dates in '{col}': {bad_count} values.")
            # Compare using a timezone-aware "now" so tz-aware and tz-naive
            # timestamps (e.g. CoinGecko UTC dates) never clash.
            now_utc = pd.Timestamp.now(tz="UTC")
            future_count = (parsed > now_utc).sum()
            if future_count:
                score -= 5
                issues.append(f"Future timestamps in '{col}': {future_count} values.")

        # Percentage fields
        if any(k in cl for k in ["percent", "pct", "change", "return"]):
            nums = pd.to_numeric(series, errors="coerce").dropna()
            extreme = ((nums < -100) | (nums > 1_000)).sum()
            if extreme:
                score -= 8
                issues.append(f"Extreme percentage values in '{col}': {extreme} rows.")

        # Currency codes
        if "currency" in cl or col.lower() in ("ccy", "curr"):
            unrecognised = series[~series.str.upper().isin(VALID_CURRENCIES)].count()
            if unrecognised:
                score -= 5
                issues.append(f"Unrecognised currency codes in '{col}': {unrecognised} values.")

    return max(0.0, round(score, 1)), issues


# ── 4. Consistency ─────────────────────────────────────────────────────────────

def score_consistency(
    df: pd.DataFrame,
    other_dfs: list[pd.DataFrame],
) -> tuple[float, list[str]]:
    """
    Penalises:
      • Intra-source: Low > High OHLC violations
      • Cross-source: >50% mean divergence on shared numeric columns
    """
    if df.empty:
        return 50.0, ["Single source – cross-source consistency not applicable."]

    score = 100.0
    issues: list[str] = []

    # Intra-source: High >= Low
    high_cols = [c for c in df.columns if "high" in c.lower()]
    low_cols  = [c for c in df.columns if "low"  in c.lower()]
    for h_col in high_cols:
        for l_col in low_cols:
            try:
                h = pd.to_numeric(df[h_col], errors="coerce")
                l = pd.to_numeric(df[l_col], errors="coerce")
                violations = (l > h).sum()
                if violations:
                    score -= 15
                    issues.append(
                        f"Low > High in {violations} rows ('{l_col}' vs '{h_col}')."
                    )
            except Exception:
                pass

    # Cross-source: compare means on shared columns
    for other in other_dfs:
        if other is df or other.empty:
            continue
        shared = set(df.columns) & set(other.columns)
        for col in list(shared)[:3]:
            try:
                v1 = pd.to_numeric(df[col],    errors="coerce").mean()
                v2 = pd.to_numeric(other[col], errors="coerce").mean()
                if v1 and v2 and abs(v1 - v2) / (abs(v1) + 1e-9) > 0.5:
                    score -= 10
                    issues.append(f"Cross-source divergence >50% on '{col}'.")
            except Exception:
                pass

    if not issues:
        issues.append("No consistency violations found.")

    return max(0.0, round(score, 1)), issues


# ── 5. Timeliness ──────────────────────────────────────────────────────────────

def score_timeliness(
    raw_data: dict | list | None,
    df: pd.DataFrame,
) -> tuple[float, list[str]]:
    """
    Finds the most recent timestamp in column data or top-level JSON keys
    and penalises based on data age.

    Age thresholds:
      < 1 h   →  100
      1–24 h  →  -10
      1–7 d   →  -30
      > 7 d   →  -60
    """
    score = 100.0
    issues: list[str] = []
    date_found: pd.Timestamp | None = None

    # Search DataFrame columns first
    for col in df.columns:
        if any(k in col.lower() for k in ["date", "time", "timestamp", "updated", "created"]):
            try:
                # utc=True unifies tz-aware and tz-naive columns
                dates = pd.to_datetime(df[col], errors="coerce", utc=True).dropna()
                if not dates.empty:
                    date_found = dates.max()
                    break
            except Exception:
                pass

    # Fall back to top-level JSON keys
    if date_found is None and isinstance(raw_data, dict):
        for key in ["date", "updated", "timestamp", "lastUpdated", "refreshed_at", "as_of", "time"]:
            if key in raw_data:
                try:
                    date_found = pd.to_datetime(raw_data[key], utc=True)
                    break
                except Exception:
                    pass

    if date_found is None:
        return 60.0, ["No timestamp field found – timeliness assumed moderate."]

    # Strip tz before subtracting so naive datetime.now() works safely
    age_hours = (
        datetime.now() - date_found.to_pydatetime().replace(tzinfo=None)
    ).total_seconds() / 3_600

    if age_hours < 1:
        issues.append(f"Data is fresh ({age_hours*60:.0f} min old).")
    elif age_hours < 24:
        score -= 10
        issues.append(f"Data is {age_hours:.0f} h old – consider a real-time feed.")
    elif age_hours < 168:
        score -= 30
        issues.append(f"Data is {age_hours/24:.1f} days old.")
    else:
        score -= 60
        issues.append(f"Data is {age_hours/168:.1f} weeks old – stale for financial use.")

    return max(0.0, round(score, 1)), issues


# ── Weighted total ─────────────────────────────────────────────────────────────

WEIGHTS = {
    "completeness": 0.25,
    "accuracy":     0.25,
    "validity":     0.20,
    "consistency":  0.15,
    "timeliness":   0.15,
}


def compute_total(scores: dict[str, float]) -> float:
    return round(sum(scores[k] * w for k, w in WEIGHTS.items()), 1)


# ── Suggestion builder ─────────────────────────────────────────────────────────

def build_suggestions(
    scores: dict[str, float],
    issues:  dict[str, list[str]],
) -> list[dict]:
    """
    Produces a prioritised list of actionable suggestions.
    Each suggestion describes:
      dim     – which DQ dimension it targets
      impact  – estimated score gain
      title   – short human label
      body    – detail / rationale
      action  – key used by the fix engine in utils/fixes.py
    """
    THRESHOLDS = {
        "completeness": (90, "Fill Missing Fields",
                         "fill_nulls",
                         "Add fallback values or enrich from secondary sources."),
        "accuracy":     (85, "Remove / Cap Outliers",
                         "cap_outliers",
                         "Apply z-score capping (±3σ) on numeric columns."),
        "validity":     (85, "Enforce Domain Constraints",
                         "validate_domain",
                         "Add schema validation for dates, enums, and ranges."),
        "consistency":  (80, "Resolve Cross-Field Conflicts",
                         "fix_consistency",
                         "Ensure High ≥ Low ≥ 0 invariants across OHLC columns."),
        "timeliness":   (80, "Increase Refresh Frequency",
                         "increase_frequency",
                         "Switch to a streaming or higher-frequency endpoint."),
    }

    suggestions = []
    for dim, (threshold, title, action, default_body) in THRESHOLDS.items():
        current = scores.get(dim, 100)
        if current < threshold:
            dim_issues = issues.get(f"{dim}_issues", [])
            body = dim_issues[0] if dim_issues else default_body
            suggestions.append({
                "dim":    dim,
                "impact": round(threshold - current, 1),
                "title":  title,
                "body":   body,
                "action": action,
                "color":  DIM_COLORS[dim],
            })

    # Highest impact first
    suggestions.sort(key=lambda s: s["impact"], reverse=True)
    return suggestions
