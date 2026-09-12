"""Load and schema-validate the raw "Give Me Some Credit" training data.

See docs/plans/0001-pd-scorecard-give-me-some-credit.md §4.1.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TARGET_COL = "SeriousDlqin2yrs"

FEATURE_COLS = [
    "RevolvingUtilizationOfUnsecuredLines",
    "age",
    "NumberOfTime30-59DaysPastDueNotWorse",
    "DebtRatio",
    "MonthlyIncome",
    "NumberOfOpenCreditLinesAndLoans",
    "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines",
    "NumberOfTime60-89DaysPastDueNotWorse",
    "NumberOfDependents",
]

EXPECTED_COLUMNS = [TARGET_COL, *FEATURE_COLS]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Load cs-training.csv, drop the unnamed index column, and validate its schema.

    Raises ValueError if the file doesn't match the expected "Give Me Some Credit"
    schema (missing/extra columns, or a non-binary target) — fail loudly rather than
    silently proceeding on a wrong or corrupted file.
    """
    df = pd.read_csv(path, index_col=0)
    _validate_schema(df)
    return df


def _validate_schema(df: pd.DataFrame) -> None:
    actual = set(df.columns)
    expected = set(EXPECTED_COLUMNS)

    missing = expected - actual
    unexpected = actual - expected
    if missing or unexpected:
        raise ValueError(
            "Schema mismatch in raw data. "
            f"Missing columns: {sorted(missing) or 'none'}. "
            f"Unexpected columns: {sorted(unexpected) or 'none'}."
        )

    target_values = set(df[TARGET_COL].dropna().unique())
    if not target_values <= {0, 1}:
        raise ValueError(
            f"Target column '{TARGET_COL}' must be binary (0/1), "
            f"found values: {sorted(target_values)}"
        )
