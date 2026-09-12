import numpy as np
import pandas as pd

from src.features.select import compute_vif, flag_suspicious_iv, select_by_iv


def test_select_by_iv_filters_and_preserves_order():
    iv = pd.Series({"a": 0.9, "b": 0.3, "c": 0.01, "d": 0.05}).sort_values(ascending=False)

    selected = select_by_iv(iv, min_iv=0.02)

    assert selected == ["a", "b", "d"]


def test_flag_suspicious_iv():
    iv = pd.Series({"a": 0.9, "b": 0.3, "c": 0.51})

    flagged = flag_suspicious_iv(iv, threshold=0.5)

    assert set(flagged) == {"a", "c"}


def test_compute_vif_high_for_near_duplicate_columns():
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, 500)
    df = pd.DataFrame(
        {
            "independent": rng.normal(0, 1, 500),
            "x1": base,
            "x2": base + rng.normal(0, 0.01, 500),  # near-duplicate of x1
        }
    )

    vif = compute_vif(df)

    assert vif["x1"] > 5
    assert vif["x2"] > 5
    assert vif["independent"] < 2
