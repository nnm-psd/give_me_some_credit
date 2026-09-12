"""Validation metrics for the PD scorecard: discrimination, calibration, stability.

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.7. All four run on
both train and test in the pipeline — a large train/test gap on any of them
is a red flag to investigate before anything else (§4.7).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve


def discrimination_metrics(y_true, y_score) -> dict[str, float]:
    """AUC, Gini (2*AUC-1), and the KS statistic (max separation of the ROC curve)."""
    auc = roc_auc_score(y_true, y_score)
    fpr, tpr, _ = roc_curve(y_true, y_score)
    ks = float(np.max(tpr - fpr))
    return {"auc": float(auc), "gini": float(2 * auc - 1), "ks": ks}


def calibration_table(y_true, y_score, n_bins: int = 10) -> pd.DataFrame:
    """Predicted-vs-observed default rate by score band (quantile-binned on y_score)."""
    df = pd.DataFrame({"y": np.asarray(y_true), "score": np.asarray(y_score)})
    df["bin"] = pd.qcut(df["score"], q=n_bins, duplicates="drop")
    table = (
        df.groupby("bin", observed=True)
        .agg(n=("y", "size"), predicted_rate=("score", "mean"), observed_rate=("y", "mean"))
        .reset_index()
    )
    return table


def hosmer_lemeshow_test(y_true, y_score, n_bins: int = 10) -> tuple[float, float]:
    """The Hosmer-Lemeshow goodness-of-fit statistic and its p-value.

    A low p-value (conventionally < 0.05) means predicted and observed rates
    diverge more than chance would explain — the model is poorly calibrated.
    """
    df = pd.DataFrame({"y": np.asarray(y_true), "score": np.asarray(y_score)})
    df["bin"] = pd.qcut(df["score"], q=n_bins, duplicates="drop")
    grouped = df.groupby("bin", observed=True)

    n = grouped["y"].count()
    observed_events = grouped["y"].sum()
    expected_events = grouped["score"].sum()

    stat = (
        (observed_events - expected_events) ** 2 / expected_events
        + (expected_events - observed_events) ** 2 / (n - expected_events)
    ).sum()
    dof = len(n) - 2
    p_value = float(1 - stats.chi2.cdf(stat, dof)) if dof > 0 else float("nan")
    return float(stat), p_value


def population_stability_index(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    """PSI of `actual` relative to `expected` (the reference/baseline distribution).

    Bucket edges come from `expected`'s quantiles (e.g. the train score
    distribution) and are then applied to `actual` (e.g. test) — PSI measures
    how much `actual` has drifted away from that reference, not an arbitrary
    shared binning. With no time field in this dataset, train-vs-test PSI is
    used as the closest available substitute for a real over-time PSI check
    (see docs/plans/0001... §2's stated limitation).
    """
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, buckets + 1)))
    edges[0], edges[-1] = -np.inf, np.inf

    expected_pct = pd.cut(expected, edges).value_counts(normalize=True, sort=False)
    actual_pct = pd.cut(actual, edges).value_counts(normalize=True, sort=False)

    eps = 1e-6  # guards against log(0) / division by zero for an empty bucket
    psi = ((actual_pct - expected_pct) * np.log((actual_pct + eps) / (expected_pct + eps))).sum()
    return float(psi)


def interpret_psi(psi: float) -> str:
    """The conventional PSI thresholds used across the scorecard industry."""
    if psi < 0.1:
        return "stable"
    if psi < 0.25:
        return "moderate shift — monitor"
    return "significant shift — investigate"
