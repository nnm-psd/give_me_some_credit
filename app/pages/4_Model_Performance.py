import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.charts import STATUS_COLOR, calibration_chart, roc_chart
from app.components.loaders import (
    FEATURE_COLS,
    TARGET_COL,
    artifacts_available,
    load_binner,
    load_calibration_table,
    load_metrics,
    load_raw_data,
    load_scorecard,
    raw_data_available,
)
from src.data.clean import clean, split

st.set_page_config(page_title="Model Performance", layout="wide")
st.title("Model Performance")
st.caption(
    "All figures below are read from `models/give-me-some-credit/metrics.json`, produced by "
    "the last run of `src/pipeline/train.py` — nothing on this page is recomputed live."
)

if not artifacts_available():
    st.error("No trained artifacts found. Run `python -m src.pipeline.train` first.")
    st.stop()

metrics = load_metrics()

st.subheader("Discrimination")
disc = metrics["discrimination"]
col1, col2, col3 = st.columns(3)
col1.metric("AUC (test)", f"{disc['test']['auc']:.3f}", help=f"train: {disc['train']['auc']:.3f}")
col2.metric("Gini (test)", f"{disc['test']['gini']:.3f}", help=f"train: {disc['train']['gini']:.3f}")
col3.metric("KS (test)", f"{disc['test']['ks']:.3f}", help=f"train: {disc['train']['ks']:.3f}")

st.divider()

st.subheader("ROC curve (test set)")
if raw_data_available():
    df = clean(load_raw_data())
    _, test_df = split(df, test_size=0.3, seed=42)  # must mirror config/give_me_some_credit.yaml
    binner = load_binner()
    scorecard = load_scorecard()
    woe_test = binner.transform(test_df[FEATURE_COLS])
    pd_test = scorecard.predict_pd(woe_test)
    st.plotly_chart(roc_chart(test_df[TARGET_COL], pd_test, disc["test"]["auc"]), use_container_width=True)
else:
    st.info("Raw data not available — cannot recompute the ROC curve points (AUC/Gini/KS above are still exact, from the saved metrics).")

st.divider()

st.subheader("Calibration")
calib = load_calibration_table()
st.plotly_chart(calibration_chart(calib), use_container_width=True)
st.dataframe(
    calib.style.format({"predicted_rate": "{:.2%}", "observed_rate": "{:.2%}"}),
    use_container_width=True,
)

hl = metrics["hosmer_lemeshow_test"]
st.caption(
    f"Hosmer-Lemeshow: statistic = {hl['statistic']:.1f}, p-value = {hl['p_value']:.2e}. "
    "See the model card for why a low p-value at this sample size doesn't necessarily mean "
    "practically meaningful miscalibration (docs/model_cards/give-me-some-credit-pd-v1.md)."
)

st.divider()

st.subheader("Population Stability Index — train vs. test")
psi = metrics["psi_train_vs_test"]
color = STATUS_COLOR.get(psi["interpretation"], "#898781")
st.markdown(
    f"**PSI = {psi['value']:.4f}** — "
    f"<span style='color:{color}; font-weight:600'>{psi['interpretation']}</span>",
    unsafe_allow_html=True,
)
st.warning(
    "This dataset has no time/vintage field — this PSI compares two random splits of the same "
    "population, not real drift over time. Near-zero is expected by construction here; it is not "
    "evidence the model would stay stable against genuine future drift (see the model card)."
)
