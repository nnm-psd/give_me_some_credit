# Plan 0002 — Streamlit App: Model Interaction, Data Distributions & Binning Explainability

Status: **done** — all 4 pages built and verified with `streamlit.testing.v1.AppTest` (every page,
every feature selection, the Score Simulator's button click with normal/missing/outlier inputs —
zero exceptions) plus a live `streamlit run` smoke check. Depends on
[Plan 0001](./0001-pd-scorecard-give-me-some-credit.md), which was completed first.

## 1. Objective

A local Streamlit web app that lets you: explore the raw data's distributions, see exactly how each
feature was binned into WOE and *why* that method was chosen, interactively score a hypothetical
applicant and watch the scorecard build up the answer, and inspect the model's validation metrics —
all in one place, without needing a notebook open.

## 2. Why Streamlit (confirming the pick, not re-opening it)

Pure Python, no separate frontend stack to build; native `st.cache_data`/`st.cache_resource` fits
"load an artifact once, let the user poke at it many times"; built-in multipage app support
(`pages/` directory); first-class with pandas/matplotlib/plotly. It's the de facto convention in the
Python ML ecosystem for exactly this kind of internal model-exploration app (the alternative,
Dash/Gradio, is less common for this specific shape — a multi-tab data+model dashboard). No reason
to look further per LLM.md §1 (convention before invention).

## 3. Relationship to Plan 0001 — read-only consumer, never retrains

The app **loads saved artifacts, it never recomputes the pipeline from the raw CSV on page load.**
Training happens once, in 0001's `src/pipeline/train.py`; the app reads:
- the fitted binning object(s) (per feature, from `optbinning`) — pickled,
- the fitted logistic regression + scorecard scaling — pickled,
- the saved evaluation metrics (ROC points, KS, calibration bins, PSI) — a small JSON/parquet,
all under `models/give-me-some-credit/` as 0001 already lays out.

**Why this matters enough to write down (LLM.md §0.1):** if the app recomputed anything itself, "the
model you're looking at in the browser" could silently drift from "the model that was actually
validated and saved." Read-only-from-artifact keeps those identical by construction — the same
reasoning as the release-projection discipline in LLM.md's source material, applied to a UI instead
of an API.

## 4. Structure

```
app/
  Home.py                      # entry point: project overview, links to the four pages
  pages/
    1_Data_Overview.py         # raw-feature distributions, missing rates, target rate
    2_Binning_Explorer.py      # per-feature bins + WOE/IV, PLUS the methodology write-up
    3_Score_Simulator.py       # interactive form -> live score/PD breakdown
    4_Model_Performance.py     # ROC, KS, calibration, PSI (from 0001's saved metrics)
  components/
    loaders.py                 # cached loaders for the raw data + saved artifacts
    charts.py                  # shared plotting helpers (WOE bar, ROC, calibration curve)
  content/
    binning_methodology.md     # the static "how and why" write-up — see §5
requirements-app.txt           # streamlit, plotly (or matplotlib), reuses src/ for shared logic
```

`app/` imports from `src/` (e.g. `src/models/evaluate.py`'s metric functions) rather than
duplicating logic — one implementation of "how PSI is computed," used by both the training pipeline
and the app.

## 5. The Binning Explorer page — the specific requirement

This page has **two distinct parts, deliberately kept separate:**

**(a) Static "why" — `app/content/binning_methodology.md`, written once, rendered as-is.**
Covers the reasoning that doesn't change from run to run:
- *Why WOE/IV binning at all:* it turns a possibly non-linear, outlier-prone raw feature into a
  value that has a monotonic relationship with log-odds of default — which is exactly what a
  logistic regression coefficient can use directly and linearly. It also turns "missing" into a
  legitimate bin with its own WOE, instead of forcing an imputation guess.
- *Why a monotonic constraint on the bins:* economic sanity ("more past-due history should never
  look safer") and defensibility — a scorecard whose risk ordering can flip direction inside one
  feature is much harder to justify to a reviewer or a regulator than one that can't.
- *Why `optbinning` specifically:* it searches for an optimal monotonic binning rather than using
  ad hoc equal-width/equal-frequency cuts, and is a maintained library rather than a hand-rolled
  algorithm (per LLM.md §2 — use the library, don't reimplement what it already validates).
- *Why WOE/logistic over a black-box model here:* interpretability and auditability — every bin's
  contribution to the final score is a traceable number, which is the actual reason this technique
  is still the production standard for consumer credit scorecards despite gradient boosting usually
  scoring higher on raw AUC.

**(b) Dynamic "how it turned out this run" — pulled live from the saved binning artifact.**
`st.selectbox` to pick a feature, then render (from the actual fitted `optbinning` object, never
retyped by hand): the bin edges, event rate per bin, WOE per bin as a bar chart, and the feature's
IV. This can never drift out of sync with the real model, because it isn't independently authored —
it's read straight from the artifact 0001 produced.

**This split is itself the non-obvious design decision worth recording** (LLM.md §0.1): the *why*
is prose that a person reviews once; the *what happened* is data that must always match the real
model. Conflating them (e.g. hardcoding "Feature X got 5 bins" into prose) is exactly the kind of
stale-doc drift LLM.md §0.5 warns about — here applied to the app instead of a markdown file.

## 6. Score Simulator page

One input per feature (`st.slider`/`st.number_input`, bounded to ranges observed in Plan 0001's
EDA), a "Score" button, and on submit: which bin each input value fell into, that bin's WOE, its
points contribution, the running total, and the resulting predicted PD. This is the concrete
"tương tác trực quan với model" requirement — you can see, feature by feature, why the model landed
on a given score.

## 7. Model Performance page

Reads 0001's saved evaluation output — ROC curve, KS chart, calibration plot, train-vs-test PSI —
rather than recomputing. If a metric isn't in the saved artifact yet, that's a gap in 0001's
`evaluate.py` output to fix there, not something to patch by recomputing inside the app.

## 8. Data Overview page

Histograms/boxplots per raw feature, target default-rate bar, missing-value summary, correlation
heatmap. This page only needs the raw CSV — it can be built and shown before 0001's model artifacts
exist, unlike the other three pages.

## 9. Explicitly out of scope for this plan

No authentication, no database/persistence, no deployment/hosting (local `streamlit run` only for
now), no "retrain from the UI" button. These are separate decisions if you want them later.

## 10. Order of implementation

1. `components/loaders.py` (cached loaders — data first, artifact-loading stubbed until 0001 exists)
2. `pages/1_Data_Overview.py` — buildable and testable right away against the raw CSV
3. `content/binning_methodology.md` (review this prose with you before wiring it into the page)
4. `pages/2_Binning_Explorer.py` — needs 0001's binning artifacts
5. `pages/3_Score_Simulator.py` — needs 0001's model + binning artifacts
6. `pages/4_Model_Performance.py` — needs 0001's saved metrics
7. `Home.py` wiring it together

## 11. Sequencing recommendation

Pages 2–4 have nothing real to show until Plan 0001 has actually run and produced artifacts.
**Recommendation: finish Plan 0001 first** (through its step 4.9 tests passing and the model card
written), then build this app against real artifacts — rather than building the app's shell now
against fake/placeholder data and rewiring it later. The one exception, if you'd rather see visible
progress sooner, is step 2 above (`1_Data_Overview.py`), which only needs the raw CSV and could be
built in parallel with 0001's later steps.
