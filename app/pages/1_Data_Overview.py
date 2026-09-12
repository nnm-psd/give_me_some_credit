import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.charts import histogram_from_bins, target_rate_bar
from app.components.loaders import FEATURE_COLS, data_profile_available, load_data_profile

st.set_page_config(page_title="Data Overview", layout="wide")
st.title("Data Overview")
st.caption(
    "Built from `models/give-me-some-credit/data_profile.json` — a small, aggregate-only "
    "summary (histogram bin counts, describe() stats, missing rates) computed once by "
    "`src/pipeline/train.py`. This works without the raw Kaggle CSV present (e.g. hosted "
    "deployment) — see `src/data/profile.py` for why aggregates are safe to ship when the "
    "raw file itself is not."
)

if not data_profile_available():
    st.error(
        "No data profile found at `models/give-me-some-credit/data_profile.json`. "
        "Run `python -m src.pipeline.train` first."
    )
    st.stop()

profile = load_data_profile()

st.subheader("Target")
col1, col2 = st.columns([1, 2])
with col1:
    default_rate = profile["target"]["default_rate"]
    st.metric("Default rate", f"{default_rate:.2%}")
    st.metric("Rows", f"{profile['n_rows']:,}")
with col2:
    st.plotly_chart(target_rate_bar(default_rate), use_container_width=True)

st.divider()

st.subheader("Missing values")
missing_rows = [
    {"feature": f, "count": profile["features"][f]["missing_count"], "share missing": profile["features"][f]["missing_share"]}
    for f in FEATURE_COLS
    if profile["features"][f]["missing_count"] > 0
]
if not missing_rows:
    st.write("No missing values.")
else:
    missing_df = pd.DataFrame(missing_rows).set_index("feature")
    st.dataframe(missing_df.style.format({"share missing": "{:.1%}"}), use_container_width=True)
    st.caption(
        "Missing values are not imputed here — the Binning Explorer page shows how "
        "each is given its own WOE bin instead. See notebooks/01_eda.ipynb."
    )

st.divider()

st.subheader("Feature distributions")
selected = st.selectbox("Feature", FEATURE_COLS)
feature_profile = profile["features"][selected]
hist = feature_profile["histogram"]
st.plotly_chart(
    histogram_from_bins(hist["counts"], hist["bin_edges"], f"Distribution — {selected}", selected),
    use_container_width=True,
)
describe_df = pd.DataFrame([feature_profile["describe"]])
st.dataframe(describe_df, use_container_width=True)
