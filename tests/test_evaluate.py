import numpy as np
import pandas as pd

from src.models.evaluate import (
    calibration_table,
    discrimination_metrics,
    hosmer_lemeshow_test,
    interpret_psi,
    population_stability_index,
)


def test_discrimination_metrics_perfect_separation():
    y = [0, 0, 0, 1, 1, 1]
    score = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]

    m = discrimination_metrics(y, score)

    assert m["auc"] == 1.0
    assert m["gini"] == 1.0
    assert m["ks"] == 1.0


def test_discrimination_metrics_random_score_near_chance():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 5000)
    score = rng.random(5000)  # uninformative

    m = discrimination_metrics(y, score)

    assert abs(m["auc"] - 0.5) < 0.03
    assert abs(m["gini"]) < 0.06


def test_calibration_table_shape_and_columns():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 1000)
    score = rng.random(1000)

    table = calibration_table(y, score, n_bins=5)

    assert list(table.columns) == ["bin", "n", "predicted_rate", "observed_rate"]
    assert table["n"].sum() == 1000
    assert len(table) <= 5


def test_hosmer_lemeshow_high_pvalue_for_well_calibrated_model():
    rng = np.random.default_rng(0)
    n = 20000
    score = rng.uniform(0.01, 0.99, n)
    y = (rng.random(n) < score).astype(int)  # predicted prob == true prob

    stat, p_value = hosmer_lemeshow_test(y, score, n_bins=10)

    assert p_value > 0.05


def test_hosmer_lemeshow_low_pvalue_for_badly_calibrated_model():
    rng = np.random.default_rng(0)
    n = 20000
    true_p = rng.uniform(0.01, 0.99, n)
    y = (rng.random(n) < true_p).astype(int)
    bad_score = np.clip(true_p + 0.3, 0, 1)  # systematically overpredicts risk

    stat, p_value = hosmer_lemeshow_test(y, bad_score, n_bins=10)

    assert p_value < 0.05


def test_psi_near_zero_for_identical_distributions():
    rng = np.random.default_rng(0)
    expected = pd.Series(rng.normal(600, 40, 5000))
    actual = pd.Series(rng.normal(600, 40, 5000))

    psi = population_stability_index(expected, actual, buckets=10)

    assert psi < 0.05


def test_psi_large_for_shifted_distribution():
    rng = np.random.default_rng(0)
    expected = pd.Series(rng.normal(600, 40, 5000))
    actual = pd.Series(rng.normal(500, 40, 5000))  # shifted by 2.5 std devs

    psi = population_stability_index(expected, actual, buckets=10)

    assert psi > 0.25


def test_interpret_psi_thresholds():
    assert interpret_psi(0.05) == "stable"
    assert interpret_psi(0.15) == "moderate shift — monitor"
    assert interpret_psi(0.3) == "significant shift — investigate"
