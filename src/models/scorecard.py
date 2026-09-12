"""Logistic regression on WOE features, scaled to a points-based scorecard.

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.6. Follows the
standard scorecard points formula (Siddiqi, "Credit Risk Scorecards"):

    factor = PDO / ln(2)
    offset = base_score - factor * ln(base_odds)
    score  = offset + factor * ln(odds_good)
           = offset + factor * (intercept + sum(coef_i * WOE_i))

The model is fit on y_good = 1 - default (not on the default flag directly)
so that a higher score always means lower risk, matching the usual FICO-style
convention, and so every coefficient is expected to be positive: optbinning's
WOE is ln(%good/%bad) per bin (see src/features/binning.py — a safer bin has
higher WOE), so a safer bin should never pull predicted good-odds down. A
negative coefficient means a binning or leakage problem, not a model to ship
— fit() raises rather than silently returning a broken scorecard.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


@dataclass
class ScorecardConfig:
    pdo: float = 20.0
    base_score: float = 600.0
    base_odds: float = 50.0  # odds of good:bad at base_score


class Scorecard:
    def __init__(self, config: ScorecardConfig | None = None):
        self.config = config or ScorecardConfig()
        self.model = LogisticRegression(C=np.inf)  # unregularized — see class docstring
        self.feature_names_: list[str] | None = None

    def fit(self, woe_df: pd.DataFrame, y_default: pd.Series) -> "Scorecard":
        y_good = 1 - y_default
        self.feature_names_ = list(woe_df.columns)
        self.model.fit(woe_df[self.feature_names_], y_good)
        self._check_coefficient_signs()
        return self

    def _check_coefficient_signs(self) -> None:
        coefs = self.coefficients()
        negative = coefs[coefs < 0]
        if len(negative) > 0:
            raise ValueError(
                f"Coefficient sign check failed for {negative.index.tolist()}: a "
                "safer bin (higher WOE) must never lower predicted good-odds. This "
                "points to a binning or leakage problem — not a model to ship."
            )

    def coefficients(self) -> pd.Series:
        self._check_fitted()
        return pd.Series(self.model.coef_[0], index=self.feature_names_)

    @property
    def intercept(self) -> float:
        self._check_fitted()
        return float(self.model.intercept_[0])

    def _factor_offset(self) -> tuple[float, float]:
        factor = self.config.pdo / np.log(2)
        offset = self.config.base_score - factor * np.log(self.config.base_odds)
        return factor, offset

    def points_matrix(self, woe_df: pd.DataFrame) -> pd.DataFrame:
        """Per-feature points contribution for every row — the pieces that sum to `score()`."""
        self._check_fitted()
        factor, offset = self._factor_offset()
        coefs = self.coefficients()
        n = len(self.feature_names_)
        constant_share = (offset + factor * self.intercept) / n
        return factor * woe_df[self.feature_names_].multiply(coefs, axis=1) + constant_share

    def points_breakdown(self, woe_row: pd.Series) -> pd.Series:
        """Points contribution per feature for a single applicant (Plan 0002's Score Simulator)."""
        row_df = woe_row[self.feature_names_].to_frame().T
        return self.points_matrix(row_df).iloc[0]

    def score(self, woe_df: pd.DataFrame) -> pd.Series:
        """Total scorecard score per row — higher score means lower risk."""
        return self.points_matrix(woe_df).sum(axis=1)

    def predict_pd(self, woe_df: pd.DataFrame) -> np.ndarray:
        """Predicted probability of default (1 - predicted probability of good)."""
        self._check_fitted()
        proba_good = self.model.predict_proba(woe_df[self.feature_names_])[:, 1]
        return 1 - proba_good

    def _check_fitted(self) -> None:
        if self.feature_names_ is None:
            raise RuntimeError("Scorecard is not fitted yet — call fit() first.")
