import pandas as pd

from src.data.clean import clean, split


def _frame(n=20):
    return pd.DataFrame(
        {
            "SeriousDlqin2yrs": [0, 1] * (n // 2),
            "age": [30 + i for i in range(n)],
        }
    )


def test_clean_drops_age_zero_rows():
    df = _frame()
    df.loc[0, "age"] = 0

    cleaned = clean(df)

    assert (cleaned["age"] > 0).all()
    assert len(cleaned) == len(df) - 1


def test_clean_does_not_mutate_input():
    df = _frame()
    df.loc[0, "age"] = 0
    original_len = len(df)

    clean(df)

    assert len(df) == original_len


def test_split_is_stratified_and_reproducible():
    df = _frame(n=200)
    df["SeriousDlqin2yrs"] = ([0] * 180) + ([1] * 20)

    train_a, test_a = split(df, test_size=0.3, seed=42)
    train_b, test_b = split(df, test_size=0.3, seed=42)

    assert len(test_a) == 60
    assert train_a.index.equals(train_b.index)
    # stratification keeps the ~10% default rate in both splits
    assert abs(train_a["SeriousDlqin2yrs"].mean() - 0.10) < 0.02
    assert abs(test_a["SeriousDlqin2yrs"].mean() - 0.10) < 0.02
