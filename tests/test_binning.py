import numpy as np
import pandas as pd
import pytest

from src.features.binning import FeatureBinner


def _synthetic_frame(n: int = 800, seed: int = 0):
    rng = np.random.default_rng(seed)

    age = rng.normal(45, 12, n)
    # clear monotonic signal: default probability falls as age rises
    default_prob = np.clip(0.45 - 0.006 * age, 0.02, 0.9)

    income = rng.normal(3500, 1200, n)
    nan_idx = rng.choice(n, size=int(n * 0.1), replace=False)
    income[nan_idx] = np.nan

    past_due = rng.integers(0, 5, n).astype(float)
    special_idx = rng.choice(n, size=20, replace=False)
    past_due[special_idx] = 98
    # the special-code rows are much higher risk
    default_prob = np.where(past_due == 98, 0.9, default_prob)

    y = (rng.random(n) < default_prob).astype(int)

    X = pd.DataFrame(
        {
            "age": age,
            "MonthlyIncome": income,
            "NumberOfTimes90DaysLate": past_due,
        }
    )
    return X, pd.Series(y)


def test_fit_transform_returns_woe_for_all_features():
    X, y = _synthetic_frame()
    binner = FeatureBinner().fit(X, y)

    woe = binner.transform(X)

    assert list(woe.columns) == list(X.columns)
    assert len(woe) == len(X)
    assert woe.notna().all().all()


def test_missing_values_get_their_own_bin_and_transform_cleanly():
    X, y = _synthetic_frame()
    binner = FeatureBinner().fit(X, y)

    table = binner.binning_table("MonthlyIncome")

    assert "Missing" in table["Bin"].values
    missing_row = table.loc[table["Bin"] == "Missing"]
    assert missing_row["Count"].iloc[0] == X["MonthlyIncome"].isna().sum()


def test_special_codes_get_a_dedicated_bin_not_merged_with_ordinary_counts():
    X, y = _synthetic_frame()
    binner = FeatureBinner(special_codes={"NumberOfTimes90DaysLate": [96, 98]}).fit(X, y)

    table = binner.binning_table("NumberOfTimes90DaysLate")

    assert "Special" in table["Bin"].values
    special_row = table.loc[table["Bin"] == "Special"]
    assert special_row["Count"].iloc[0] == (X["NumberOfTimes90DaysLate"] == 98).sum()

    # the special-code rows are the highest-risk segment -> most negative WoE
    all_bins_except_totals = table.iloc[:-1]
    assert special_row["WoE"].iloc[0] == all_bins_except_totals["WoE"].min()


def test_bin_labels_are_human_readable_strings():
    X, y = _synthetic_frame()
    binner = FeatureBinner().fit(X, y)

    labels = binner.bin_labels(X)

    assert list(labels.columns) == list(X.columns)
    assert labels["age"].apply(lambda s: isinstance(s, str)).all()


def test_iv_summary_sorted_descending():
    X, y = _synthetic_frame()
    binner = FeatureBinner().fit(X, y)

    iv = binner.iv_summary()

    assert list(iv.index) == list(iv.sort_values(ascending=False).index)
    assert (iv >= 0).all()


def test_methods_raise_before_fit():
    binner = FeatureBinner()
    X, _ = _synthetic_frame()

    with pytest.raises(RuntimeError, match="not fitted"):
        binner.transform(X)

    with pytest.raises(RuntimeError, match="not fitted"):
        binner.iv_summary()
