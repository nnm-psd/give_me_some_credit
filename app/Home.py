"""Entry point for the Give Me Some Credit PD scorecard app.

Run from the repo root: `streamlit run app/Home.py`
See docs/plans/0002-streamlit-app.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.components.loaders import artifacts_available, data_profile_available, raw_data_available

st.set_page_config(page_title="PD Scorecard — Give Me Some Credit", layout="wide")

st.title("PD Scorecard — Give Me Some Credit")
st.caption(
    "A read-only viewer over the scorecard trained by "
    "`src/pipeline/train.py` (docs/plans/0001-pd-scorecard-give-me-some-credit.md)."
)

st.markdown(
    """
Use the pages in the sidebar:

- **Data Overview** — feature distributions, missing rates, target rate — from a
  small aggregate summary, not the raw file (see the note below).
- **Binning Explorer** — how each feature was turned into WOE, and why that
  method was chosen (methodology + the actual fitted bins, side by side).
- **Score Simulator** — enter values for a hypothetical applicant and see the
  scorecard build up the score and predicted PD, feature by feature.
- **Model Performance** — ROC/KS, calibration, and the train-vs-test PSI, all
  read from the saved evaluation output — nothing here is recomputed live.

Every page reads artifacts committed under `models/give-me-some-credit/` — bin
tables, model coefficients, evaluation metrics, and an aggregate-only data
profile (histogram bin counts, describe() stats, never individual rows). The
raw Kaggle CSV itself is never committed or required by the app; it's only
used locally, by `src/pipeline/train.py`, to produce those artifacts.
"""
)

st.divider()

col1, col2 = st.columns(2)
with col1:
    if artifacts_available() and data_profile_available():
        st.success("Trained model artifacts + data profile found — every page will render.")
    else:
        st.error(
            "No trained artifacts in `models/give-me-some-credit/`. Run "
            "`python -m src.pipeline.train` first."
        )
with col2:
    if raw_data_available():
        st.info("Raw data also found locally (not required — used only to regenerate artifacts).")
    else:
        st.caption("Raw data not present — not needed to run this app.")
