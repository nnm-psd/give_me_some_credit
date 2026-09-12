"""Feature selection on top of WOE-transformed features.

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.5. Two checks,
run in order: an IV threshold (drop what isn't predictive), then a VIF
check on the WOE-transformed survivors (catch redundancy before modeling).
VIF is computed by hand via sklearn's LinearRegression (R^2 of each column
regressed on the rest) rather than pulling in statsmodels for one formula —
see LLM.md §2 ("don't hand-roll what a library already validates well", but
also don't add a new dependency for a single R^2-based ratio sklearn already
gives you).
"""
from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LinearRegression

# Industry rule of thumb (see docs/plans/0001... §4.5): IV < 0.02 not
# predictive, 0.02-0.3 useful, > 0.5 suspicious (investigate before trusting).
DEFAULT_MIN_IV = 0.02
SUSPICIOUS_IV = 0.5


def select_by_iv(iv_summary: pd.Series, min_iv: float = DEFAULT_MIN_IV) -> list[str]:
    """Feature names with IV >= min_iv, preserving iv_summary's (descending) order."""
    return iv_summary[iv_summary >= min_iv].index.tolist()


def flag_suspicious_iv(iv_summary: pd.Series, threshold: float = SUSPICIOUS_IV) -> list[str]:
    """Feature names whose IV is high enough to warrant a leakage/definition check."""
    return iv_summary[iv_summary > threshold].index.tolist()


def compute_vif(woe_df: pd.DataFrame) -> pd.Series:
    """VIF per column of a WOE-transformed feature frame.

    VIF_i = 1 / (1 - R_i^2), where R_i^2 comes from regressing column i on
    every other column. A column uncorrelated with the rest has VIF ~= 1;
    VIF > 5 is the common scorecard-industry flag for problematic redundancy.
    """
    vif = {}
    for col in woe_df.columns:
        others = woe_df.drop(columns=[col])
        if others.shape[1] == 0:
            vif[col] = 1.0
            continue
        r2 = LinearRegression().fit(others, woe_df[col]).score(others, woe_df[col])
        r2 = min(r2, 0.999999)  # guard against a perfect/near-perfect fit -> division blow-up
        vif[col] = 1.0 / (1.0 - r2)
    return pd.Series(vif).sort_values(ascending=False)
