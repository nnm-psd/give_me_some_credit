"""Cached loaders for raw data and Plan 0001's saved artifacts.

See docs/plans/0002-streamlit-app.md §3 — the app is a read-only consumer:
it loads what src/pipeline/train.py already produced, it never recomputes
the pipeline itself. `st.cache_resource` is used for the fitted objects
(they carry live sklearn/optbinning state), `st.cache_data` for plain
DataFrames/dicts, per Streamlit's own caching convention.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import pandas as pd
import streamlit as st

from src.data.load import FEATURE_COLS, TARGET_COL, load_raw

# Resolved relative to this file, not the process's CWD, so the app behaves
# the same whether `streamlit run` is invoked from the repo root or elsewhere.
_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = _ROOT / "models" / "give-me-some-credit"
RAW_DATA_PATH = _ROOT / "data" / "raw" / "give-me-some-credit" / "cs-training.csv"


def artifacts_available() -> bool:
    return (ARTIFACT_DIR / "scorecard.pkl").exists() and (ARTIFACT_DIR / "binner.pkl").exists()


def raw_data_available() -> bool:
    return RAW_DATA_PATH.exists()


@st.cache_data(show_spinner="Loading raw data...")
def load_raw_data() -> pd.DataFrame:
    return load_raw(RAW_DATA_PATH)


@st.cache_resource(show_spinner="Loading fitted binner...")
def load_binner():
    with open(ARTIFACT_DIR / "binner.pkl", "rb") as f:
        return pickle.load(f)


@st.cache_resource(show_spinner="Loading fitted scorecard...")
def load_scorecard():
    with open(ARTIFACT_DIR / "scorecard.pkl", "rb") as f:
        return pickle.load(f)


@st.cache_data(show_spinner=False)
def load_metrics() -> dict:
    with open(ARTIFACT_DIR / "metrics.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_calibration_table() -> pd.DataFrame:
    return pd.read_csv(ARTIFACT_DIR / "calibration_table.csv")


__all__ = [
    "FEATURE_COLS",
    "TARGET_COL",
    "artifacts_available",
    "raw_data_available",
    "load_raw_data",
    "load_binner",
    "load_scorecard",
    "load_metrics",
    "load_calibration_table",
]
