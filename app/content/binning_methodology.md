### Why WOE/IV binning at all?

Feeding a raw continuous variable (like `DebtRatio` or `age`) straight into a logistic regression
assumes its relationship with the log-odds of default is a straight line — often false, and
fragile against outliers. **Weight of Evidence (WOE) binning** splits each feature into ordered
groups and replaces every value with `ln(% good in bin / % bad in bin)` for that group. This does
three things at once:

1. **Turns a possibly non-linear relationship into a monotonic one that logistic regression can use
   directly** — a positive WOE always means "safer than average," a negative WOE "riskier than
   average," by construction.
2. **Absorbs outliers automatically.** An extreme value doesn't distort the fit — it just falls
   into the top or bottom bin along with every other extreme value. This project's own data has a
   concrete example: `DebtRatio` has values up to 329,664 (see `notebooks/01_eda.ipynb`) — binning
   handles that tail without needing to clip or transform it by hand.
3. **Turns "missing" into a legitimate category with its own risk estimate**, instead of forcing an
   imputation guess. If missingness itself correlates with risk (it does here — see the Binning
   Explorer for `MonthlyIncome`), that signal is kept, not thrown away.

### Why a monotonic constraint on the bins?

The bins are constrained so risk moves in one direction as the raw value increases (or decreases) —
never zigzags. Two reasons this is standard, not just tidy:

- **Economic sanity.** "More past-due history" should never come out looking *safer* than "less
  past-due history." A non-monotonic bin ordering is a sign something in the data or the binning
  itself is broken, not a real pattern to trust.
- **Defensibility.** A scorecard is often reviewed by someone other than the person who built it —
  a risk committee, an auditor, in some jurisdictions a regulator. "Risk increases consistently with
  this variable" is a one-sentence justification. "Risk goes up, then down, then up again for
  reasons the model found" is not something anyone can sign off on with confidence.

### Why `optbinning` specifically?

`optbinning` searches for the monotonic split points that best separate good from bad (an
optimization problem), rather than using ad hoc equal-width or equal-frequency cuts and hoping they
happen to be monotonic. It's also a maintained, tested library — this project uses it rather than
hand-rolling a binning algorithm, following the same reasoning as using `scikit-learn` for the model
itself: don't re-derive what a library already validates (see `LLM.md` §2).

### Why WOE + logistic regression instead of a more powerful model?

Interpretability and auditability. Every bin's contribution to the final score is a single,
traceable number (see the Score Simulator page) — you can point at any prediction and explain
exactly which pieces of evidence produced it. This is the actual reason WOE-binned logistic
regression is still the production standard for consumer credit scorecards across the industry,
despite the fact that a gradient-boosted model usually scores a few points higher on raw AUC. The
trade-off is explicit, not accidental: a small amount of discriminative power traded for a model
whose every decision can be explained line by line.

### What you're looking at below

The section below this write-up is **not** hand-typed — it's read directly from the binning object
that `src/pipeline/train.py` actually fit and saved. If you retrain the model, this page updates
automatically; it can't drift out of sync with the real model the way a hardcoded description could.
