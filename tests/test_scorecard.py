import numpy as np
import pandas as pd
import pytest

from src.models.scorecard import Scorecard, ScorecardConfig


def _woe_and_target(n=1000, seed=0):
    """Synthetic WOE-like features: higher value => safer => lower default rate."""
    rng = np.random.default_rng(seed)
    woe_a = rng.normal(0, 1, n)
    woe_b = rng.normal(0, 1, n)
    logit_good = 0.5 + 1.2 * woe_a + 0.8 * woe_b
    p_good = 1 / (1 + np.exp(-logit_good))
    y_good = (rng.random(n) < p_good).astype(int)
    y_default = 1 - y_good
    X = pd.DataFrame({"feat_a": woe_a, "feat_b": woe_b})
    return X, pd.Series(y_default)


def test_fit_produces_positive_coefficients_on_well_behaved_data():
    X, y = _woe_and_target()

    sc = Scorecard().fit(X, y)

    assert (sc.coefficients() > 0).all()


def test_fit_raises_on_sign_flip():
    X, y = _woe_and_target()
    # flip feat_a's WOE sign relative to the target -> coefficient should go negative
    X_broken = X.copy()
    X_broken["feat_a"] = -X_broken["feat_a"]

    with pytest.raises(ValueError, match="Coefficient sign check failed"):
        Scorecard().fit(X_broken, y)


def test_points_matrix_sums_to_score():
    X, y = _woe_and_target()
    sc = Scorecard(ScorecardConfig(pdo=20, base_score=600, base_odds=50)).fit(X, y)

    points = sc.points_matrix(X)
    score = sc.score(X)

    pd.testing.assert_series_equal(points.sum(axis=1), score, check_names=False)


def test_points_breakdown_matches_points_matrix_row():
    X, y = _woe_and_target()
    sc = Scorecard().fit(X, y)

    matrix = sc.points_matrix(X)
    breakdown = sc.points_breakdown(X.iloc[0])

    pd.testing.assert_series_equal(breakdown, matrix.iloc[0], check_names=False)


def test_higher_woe_scores_higher_and_predicts_lower_pd():
    X, y = _woe_and_target()
    sc = Scorecard().fit(X, y)

    safe_row = pd.Series({"feat_a": 3.0, "feat_b": 3.0})
    risky_row = pd.Series({"feat_a": -3.0, "feat_b": -3.0})
    safe_df = safe_row.to_frame().T
    risky_df = risky_row.to_frame().T

    assert sc.score(safe_df).iloc[0] > sc.score(risky_df).iloc[0]
    assert sc.predict_pd(safe_df)[0] < sc.predict_pd(risky_df)[0]


def test_methods_raise_before_fit():
    sc = Scorecard()
    X, _ = _woe_and_target()

    with pytest.raises(RuntimeError, match="not fitted"):
        sc.coefficients()

    with pytest.raises(RuntimeError, match="not fitted"):
        sc.score(X)
