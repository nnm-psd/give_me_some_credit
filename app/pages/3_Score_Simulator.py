import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import streamlit as st

from app.components.loaders import (
    FEATURE_COLS,
    artifacts_available,
    data_profile_available,
    load_binner,
    load_data_profile,
    load_scorecard,
)

st.set_page_config(page_title="Score Simulator", layout="wide")
st.title("Score Simulator")
st.caption(
    "Enter values for a hypothetical applicant and see exactly how the scorecard "
    "builds up the score, feature by feature."
)

if not artifacts_available():
    st.error("No trained artifacts found. Run `python -m src.pipeline.train` first.")
    st.stop()

binner = load_binner()
scorecard = load_scorecard()
selected_features = scorecard.feature_names_

# Defaults come from the real training data's median (via data_profile.json's
# describe() stats — see src/data/profile.py), not hardcoded guesses, and not
# a dependency on the raw CSV being present — see docs/plans/0002-streamlit-app.md §6.
if data_profile_available():
    profile = load_data_profile()
    defaults = {f: float(profile["features"][f]["describe"]["50%"]) for f in FEATURE_COLS}
else:
    defaults = {f: 0.0 for f in FEATURE_COLS}

INTEGER_FEATURES = {
    "age",
    "NumberOfTime30-59DaysPastDueNotWorse",
    "NumberOfOpenCreditLinesAndLoans",
    "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines",
    "NumberOfTime60-89DaysPastDueNotWorse",
}
NULLABLE_FEATURES = {"MonthlyIncome", "NumberOfDependents"}

st.subheader("Applicant inputs")
inputs: dict[str, float] = {}
cols = st.columns(2)
for i, feature in enumerate(FEATURE_COLS):
    with cols[i % 2]:
        is_nullable = feature in NULLABLE_FEATURES
        unknown = st.checkbox(f"{feature} — unknown / missing", value=False) if is_nullable else False
        if unknown:
            inputs[feature] = np.nan
            continue
        step = 1.0 if feature in INTEGER_FEATURES else 0.01
        inputs[feature] = st.number_input(
            feature, value=round(defaults.get(feature, 0.0), 2), step=step, format="%.2f"
        )

if st.button("Score this applicant", type="primary"):
    row = pd.DataFrame([inputs])[FEATURE_COLS]
    woe_row_df = binner.transform(row[selected_features])
    woe_row = woe_row_df.iloc[0]

    breakdown = scorecard.points_breakdown(woe_row).sort_values(ascending=False)
    total_score = float(breakdown.sum())
    pd_pred = float(scorecard.predict_pd(woe_row_df)[0])

    st.divider()
    col1, col2 = st.columns(2)
    col1.metric("Scorecard points", f"{total_score:.0f}")
    col2.metric("Predicted probability of default", f"{pd_pred:.2%}")

    st.subheader("Points breakdown by feature")
    bin_labels = binner.bin_labels(row[selected_features]).iloc[0]
    breakdown_df = pd.DataFrame(
        {
            "Feature": breakdown.index,
            "Value": [inputs[f] for f in breakdown.index],
            "Bin": [bin_labels[f] for f in breakdown.index],
            "WoE": [woe_row[f] for f in breakdown.index],
            "Points": breakdown.values,
        }
    )
    st.dataframe(
        breakdown_df.style.format({"WoE": "{:.3f}", "Points": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(breakdown_df.set_index("Feature")["Points"])
