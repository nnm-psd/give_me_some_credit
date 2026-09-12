import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.charts import woe_bar_chart
from app.components.loaders import artifacts_available, load_binner, load_metrics

st.set_page_config(page_title="Binning Explorer", layout="wide")
st.title("Binning Explorer")

if not artifacts_available():
    st.error("No trained artifacts found. Run `python -m src.pipeline.train` first.")
    st.stop()

_CONTENT_PATH = Path(__file__).resolve().parents[1] / "content" / "binning_methodology.md"
st.markdown(_CONTENT_PATH.read_text(encoding="utf-8"))

st.divider()

binner = load_binner()
metrics = load_metrics()
iv_summary = metrics["iv_summary"]

feature = st.selectbox(
    "Feature",
    sorted(iv_summary, key=iv_summary.get, reverse=True),
    format_func=lambda f: f"{f}  (IV = {iv_summary[f]:.3f})",
)

if feature in metrics.get("suspicious_high_iv_features", []):
    st.warning(
        f"IV = {iv_summary[feature]:.3f} is above the 0.5 'investigate before trusting' threshold "
        "(docs/plans/0001-... §4.5). See the model card for why this is judged consistent with "
        "known credit-scoring domain behavior rather than leakage: "
        "docs/model_cards/give-me-some-credit-pd-v1.md."
    )

col1, col2 = st.columns([2, 1])
with col1:
    st.plotly_chart(woe_bar_chart(binner.binning_table(feature), feature), use_container_width=True)
with col2:
    st.metric("Information Value (IV)", f"{iv_summary[feature]:.4f}")
    st.caption(
        "IV < 0.02: not predictive · 0.02–0.3: useful · "
        "0.3–0.5: strong · > 0.5: investigate before trusting."
    )

st.subheader("Bin table (from the actual fitted binning object)")
# reset_index: optbinning's index mixes ints with the string label "Totals",
# which pyarrow (Streamlit's dataframe serializer) can't represent as-is.
table = binner.binning_table(feature).reset_index(drop=True).copy()
# The "Totals" summary row is blank in several columns, which makes their
# dtype `object` — coerce to numeric so formatting doesn't choke on it.
for col in ["Count (%)", "Event rate", "WoE", "IV"]:
    table[col] = pd.to_numeric(table[col], errors="coerce")
st.dataframe(
    table.style.format(
        {"Count (%)": "{:.2%}", "Event rate": "{:.2%}", "WoE": "{:.4f}", "IV": "{:.4f}"},
        na_rep="",
    ),
    use_container_width=True,
)
