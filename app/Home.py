"""Entry point for the Give Me Some Credit PD scorecard app.

Run from the repo root: `streamlit run app/Home.py`
See docs/plans/0002-streamlit-app.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.components.loaders import artifacts_available, raw_data_available

st.set_page_config(page_title="PD Scorecard — Give Me Some Credit", layout="wide")

st.title("PD Scorecard — Give Me Some Credit")
st.caption(
    "A read-only viewer over the scorecard trained by "
    "`src/pipeline/train.py` (docs/plans/0001-pd-scorecard-give-me-some-credit.md)."
)

st.markdown(
    """
Use the pages in the sidebar:

- **Data Overview** — raw feature distributions, missing rates, target rate.
- **Binning Explorer** — how each feature was turned into WOE, and why that
  method was chosen (methodology + the actual fitted bins, side by side).
- **Score Simulator** — enter values for a hypothetical applicant and see the
  scorecard build up the score and predicted PD, feature by feature.
- **Model Performance** — ROC/KS, calibration, and the train-vs-test PSI, all
  read from the saved evaluation output — nothing here is recomputed live.
"""
)

st.divider()

col1, col2 = st.columns(2)
with col1:
    if raw_data_available():
        st.success("Raw data found.")
    else:
        st.error(
            "Raw data not found at `data/raw/give-me-some-credit/cs-training.csv`. "
            "The Data Overview page needs it."
        )
with col2:
    if artifacts_available():
        st.success("Trained model artifacts found.")
    else:
        st.error(
            "No trained artifacts in `models/give-me-some-credit/`. Run "
            "`python -m src.pipeline.train` first — the Binning Explorer, Score "
            "Simulator, and Model Performance pages need them."
        )
