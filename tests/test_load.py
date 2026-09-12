import pandas as pd
import pytest

from src.data.load import EXPECTED_COLUMNS, load_raw


def _write_csv(tmp_path, df: pd.DataFrame, name: str = "sample.csv"):
    path = tmp_path / name
    df.to_csv(path, index=True)
    return path


def _valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SeriousDlqin2yrs": [0, 1, 0],
            "RevolvingUtilizationOfUnsecuredLines": [0.1, 0.9, 0.5],
            "age": [25, 40, 60],
            "NumberOfTime30-59DaysPastDueNotWorse": [0, 2, 0],
            "DebtRatio": [0.2, 1.5, 0.3],
            "MonthlyIncome": [3000, None, 5000],
            "NumberOfOpenCreditLinesAndLoans": [3, 10, 5],
            "NumberOfTimes90DaysLate": [0, 1, 0],
            "NumberRealEstateLoansOrLines": [1, 0, 2],
            "NumberOfTime60-89DaysPastDueNotWorse": [0, 0, 1],
            "NumberOfDependents": [0, 2, None],
        }
    )


def test_load_raw_returns_expected_columns(tmp_path):
    path = _write_csv(tmp_path, _valid_frame())

    df = load_raw(path)

    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 3


def test_load_raw_rejects_missing_column(tmp_path):
    df = _valid_frame().drop(columns=["age"])
    path = _write_csv(tmp_path, df)

    with pytest.raises(ValueError, match="Missing columns"):
        load_raw(path)


def test_load_raw_rejects_unexpected_column(tmp_path):
    df = _valid_frame()
    df["some_new_column"] = 1
    path = _write_csv(tmp_path, df)

    with pytest.raises(ValueError, match="Unexpected columns"):
        load_raw(path)


def test_load_raw_rejects_non_binary_target(tmp_path):
    df = _valid_frame()
    df["SeriousDlqin2yrs"] = [0, 1, 2]
    path = _write_csv(tmp_path, df)

    with pytest.raises(ValueError, match="must be binary"):
        load_raw(path)
