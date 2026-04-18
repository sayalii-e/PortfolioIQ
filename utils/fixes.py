"""
utils/fixes.py
==============
Each function takes a DataFrame and returns:
  (modified_df, human_readable_result_message)

The action key in a suggestion maps 1-to-1 to a function here.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def apply_fix(df: pd.DataFrame, action: str) -> tuple[pd.DataFrame, str]:
    """
    Dispatcher.  Routes an action key to the correct fix function.
    Falls back gracefully if the key is unknown.
    """
    dispatch = {
        "fill_nulls":         _fill_nulls,
        "cap_outliers":       _cap_outliers,
        "validate_domain":    _validate_domain,
        "fix_consistency":    _fix_consistency,
        "increase_frequency": _increase_frequency,
    }
    fn = dispatch.get(action)
    if fn is None:
        return df, f"⚠ Unknown action '{action}' – no fix applied."
    return fn(df.copy())


# ── Individual fix functions ───────────────────────────────────────────────────

def _fill_nulls(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Fill numeric nulls with column median; string nulls with 'N/A'."""
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    obj_cols = df.select_dtypes(include=["object"]).columns
    df[obj_cols] = df[obj_cols].fillna("N/A")

    return df, "Filled numeric nulls with column medians; string nulls with 'N/A'."


def _cap_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Clip numeric columns to ±3 standard deviations."""
    num_cols = df.select_dtypes(include=[np.number]).columns
    capped = 0
    for col in num_cols:
        mean, std = df[col].mean(), df[col].std()
        before = df[col].copy()
        df[col] = df[col].clip(lower=mean - 3 * std, upper=mean + 3 * std)
        capped += (df[col] != before).sum()

    return df, f"Capped {capped} outlier value(s) to ±3σ across {len(num_cols)} numeric column(s)."


def _validate_domain(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Coerce date columns to ISO format; replace invalid dates with NaT."""
    fixed_cols = []
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            coerced = pd.to_datetime(df[col], errors="coerce")
            df[col] = coerced.astype(str).replace("NaT", "")
            fixed_cols.append(col)

    msg = (
        f"Coerced {len(fixed_cols)} date column(s) to ISO format: {', '.join(fixed_cols)}."
        if fixed_cols
        else "No date columns found to coerce."
    )
    return df, msg


def _fix_consistency(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Set Low = High wherever Low > High (OHLC invariant)."""
    high_cols = [c for c in df.columns if "high" in c.lower()]
    low_cols  = [c for c in df.columns if "low"  in c.lower()]
    total_fixed = 0

    for h_col in high_cols:
        for l_col in low_cols:
            try:
                h = pd.to_numeric(df[h_col], errors="coerce")
                l = pd.to_numeric(df[l_col], errors="coerce")
                mask = l > h
                total_fixed += mask.sum()
                df.loc[mask, l_col] = df.loc[mask, h_col]
            except Exception:
                pass

    msg = (
        f"Fixed {total_fixed} Low > High violation(s)."
        if total_fixed
        else "No Low > High violations found."
    )
    return df, msg


def _increase_frequency(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Manual action – no automatic fix available."""
    return df, (
        "⚠ Manual action required: upgrade your API subscription or switch to a "
        "higher-frequency / streaming endpoint to improve timeliness."
    )
