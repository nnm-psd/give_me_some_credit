"""Cleaning and train/test split for "Give Me Some Credit".

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.3. Cleaning is
deliberately minimal — the EDA in notebooks/01_eda.ipynb found only one
genuine data error (age == 0); missing values and outlier tails are left
for the binning step to absorb (src/features/binning.py), not cleaned here.
"""
from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.load import TARGET_COL


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with a nonsensical age (age <= 0) — see notebooks/01_eda.ipynb."""
    return df.loc[df["age"] > 0].copy()


def split(
    df: pd.DataFrame,
    test_size: float = 0.3,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified train/test split on the target.

    No time field exists in this dataset (see docs/plans/0001... §2), so a
    stratified random split is the closest available substitute for an
    out-of-time split — this is a known limitation, not an oversight.
    """
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=seed,
        stratify=df[TARGET_COL],
    )
    return train_df, test_df
