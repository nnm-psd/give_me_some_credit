import numpy as np
import pandas as pd

from src.data.profile import compute_data_profile


def _frame():
    return pd.DataFrame(
        {
            "target": [0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
            "age": [20, 25, 30, 35, 40, 45, 50, 55, 60, np.nan],
            "income": [1000.0, 2000.0, 1500.0, np.nan, 3000.0, 2500.0, 1800.0, 2200.0, 1900.0, 2100.0],
        }
    )


def test_profile_top_level_fields():
    df = _frame()

    profile = compute_data_profile(df, target_col="target", feature_cols=["age", "income"])

    assert profile["n_rows"] == 10
    assert profile["target"]["default_rate"] == 0.3


def test_profile_missing_counts():
    df = _frame()

    profile = compute_data_profile(df, target_col="target", feature_cols=["age", "income"])

    assert profile["features"]["age"]["missing_count"] == 1
    assert profile["features"]["age"]["missing_share"] == 0.1
    assert profile["features"]["income"]["missing_count"] == 1


def test_profile_histogram_counts_sum_to_non_missing_rows():
    df = _frame()

    profile = compute_data_profile(df, target_col="target", feature_cols=["age"], n_bins=5)

    hist = profile["features"]["age"]["histogram"]
    assert len(hist["bin_edges"]) == 6  # n_bins + 1 edges
    assert sum(hist["counts"]) == 9  # 10 rows minus 1 missing age


def test_profile_describe_matches_pandas():
    df = _frame()

    profile = compute_data_profile(df, target_col="target", feature_cols=["income"])

    described = profile["features"]["income"]["describe"]
    assert described["count"] == 9
    assert abs(described["mean"] - df["income"].mean()) < 1e-9
