"""A small, redistributable summary of the raw data — not the raw records.

The Kaggle "Give Me Some Credit" data itself is never committed (see .gitignore
and the model card's Data section) — Kaggle's competition rules don't grant
redistribution rights over the raw file. This module produces the opposite of
that: per-feature histogram bin counts, describe() stats, and missing rates —
aggregate numbers that reveal nothing about any individual row, in the same
spirit as committing the fitted binning object's WOE table (aggregates) but
not the training data itself. Saved by src/pipeline/train.py, read by the
Streamlit app's Data Overview page so it works without the raw CSV present
(e.g. on a hosted deployment) — see docs/plans/0002-streamlit-app.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_data_profile(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    n_bins: int = 40,
) -> dict:
    profile = {
        "n_rows": int(len(df)),
        "target": {
            "default_rate": float(df[target_col].mean()),
        },
        "features": {},
    }
    for col in feature_cols:
        series = df[col]
        missing_count = int(series.isna().sum())
        values = series.dropna().to_numpy(dtype=float)
        counts, edges = np.histogram(values, bins=n_bins)

        profile["features"][col] = {
            "missing_count": missing_count,
            "missing_share": missing_count / len(df),
            "describe": {k: float(v) for k, v in series.describe().items()},
            "histogram": {
                "counts": counts.tolist(),
                "bin_edges": edges.tolist(),
            },
        }
    return profile
