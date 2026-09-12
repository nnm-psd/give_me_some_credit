import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.charts import histogram, target_rate_bar
from app.components.loaders import FEATURE_COLS, TARGET_COL, load_raw_data, raw_data_available

st.set_page_config(page_title="Data Overview", layout="wide")
st.title("Data Overview")

if not raw_data_available():
    st.error("Raw data not found at `data/raw/give-me-some-credit/cs-training.csv`.")
    st.stop()

df = load_raw_data()

st.subheader("Target")
col1, col2 = st.columns([1, 2])
with col1:
    default_rate = df[TARGET_COL].mean()
    st.metric("Default rate", f"{default_rate:.2%}")
    st.metric("Rows", f"{len(df):,}")
with col2:
    st.plotly_chart(target_rate_bar(default_rate), use_container_width=True)

st.divider()

st.subheader("Missing values")
missing = df[FEATURE_COLS].isna().sum()
missing = missing[missing > 0]
if missing.empty:
    st.write("No missing values.")
else:
    missing_pct = (missing / len(df)).rename("share missing")
    st.dataframe(
        (missing.rename("count").to_frame().join(missing_pct)).style.format({"share missing": "{:.1%}"}),
        use_container_width=True,
    )
    st.caption(
        "Missing values are not imputed here — the Binning Explorer page shows how "
        "each is given its own WOE bin instead. See notebooks/01_eda.ipynb."
    )

st.divider()

st.subheader("Feature distributions")
selected = st.selectbox("Feature", FEATURE_COLS)
st.plotly_chart(histogram(df[selected], f"Distribution — {selected}"), use_container_width=True)
st.dataframe(df[selected].describe().to_frame().T, use_container_width=True)
