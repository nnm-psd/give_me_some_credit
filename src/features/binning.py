"""WOE/IV binning wrapper around optbinning.OptimalBinning.

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.4. Fitted objects
from this module are also what Plan 0002's Streamlit app reads directly for
its Binning Explorer page — the app never re-derives these numbers itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import pandas as pd
from optbinning import OptimalBinning


@dataclass
class FeatureBinner:
    """Fits one monotonic `OptimalBinning` per feature and applies the WOE transform.

    special_codes: optional {feature_name: [values]} for columns where certain
    raw values are known sentinel/error codes that must get their own bin
    rather than participate in the ordinary monotonic ordering (e.g. the
    96/98 codes in the past-due columns — see notebooks/01_eda.ipynb).
    """

    special_codes: Mapping[str, Sequence[float]] = field(default_factory=dict)
    _binners: dict[str, OptimalBinning] = field(default_factory=dict, init=False, repr=False)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FeatureBinner":
        for col in X.columns:
            codes = list(self.special_codes.get(col, [])) or None
            binning = OptimalBinning(
                name=col,
                dtype="numerical",
                solver="cp",
                monotonic_trend="auto",
                special_codes=codes,
            )
            binning.fit(X[col].to_numpy(), y.to_numpy())
            binning.binning_table.build()  # cache the table so .iv is available immediately
            self._binners[col] = binning
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame of WOE values, one column per fitted feature present in X."""
        self._check_fitted()
        cols = [c for c in X.columns if c in self._binners]
        woe = {c: self._binners[c].transform(X[c].to_numpy(), metric="woe") for c in cols}
        return pd.DataFrame(woe, index=X.index)

    def bin_labels(self, X: pd.DataFrame) -> pd.DataFrame:
        """Human-readable bin label per row per feature (e.g. "[25.89, 32.29)" or "Missing")."""
        self._check_fitted()
        cols = [c for c in X.columns if c in self._binners]
        labels = {c: self._binners[c].transform(X[c].to_numpy(), metric="bins") for c in cols}
        return pd.DataFrame(labels, index=X.index)

    def binning_table(self, feature: str) -> pd.DataFrame:
        """The per-bin table (edges, counts, event rate, WoE, IV) for one feature."""
        self._check_fitted()
        return self._binners[feature].binning_table.build()

    def iv(self, feature: str) -> float:
        self._check_fitted()
        return float(self._binners[feature].binning_table.iv)

    def iv_summary(self) -> pd.Series:
        """Total Information Value per fitted feature, sorted descending."""
        self._check_fitted()
        return pd.Series({c: self.iv(c) for c in self._binners}).sort_values(ascending=False)

    def _check_fitted(self) -> None:
        if not self._binners:
            raise RuntimeError("FeatureBinner is not fitted yet — call fit() first.")
