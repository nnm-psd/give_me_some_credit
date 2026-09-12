# LLM Implementation Guidelines — credit_risk (personal edition)

The coding briefing for any AI assistant writing code in this repo. Read it before the first line.
It is the concrete-implementation companion to [BRAIN.md](./BRAIN.md) (how to *think*) — this file
is how to *build*, for this project. Read BRAIN.md first.

> **The one rule that overrides every other rule below:**
> **Match the existing codebase and conventions of this repo. Convention beats principle.**
> When a "best practice"/textbook instinct conflicts with how this repo already does it, the repo
> wins. Principles serve the code; the code does not serve the principles.

This is a **personal, project-agnostic edition** distilled from a longer, employer-specific guide
(kept alongside as `LLM-GUIDELINES.md` for reference) and adapted for a solo credit-risk / ML
project. It carries the same discipline, generalized: no framework-specific paths, no assumed
platform. As the repo grows its own structure, update the placeholder sections (§3, §10) to point
at the real files.

---

## 0. Think first — read the map

Before touching a file:

1. **Read whatever convention canon already exists** — `README.md`, `docs/`, config files, a data
   dictionary — before writing anything. If none exists yet, the first non-trivial piece of code you
   write *becomes* the convention for what follows — write it like you mean it to be copied.
2. **Trace the data flow end-to-end** before changing anything. For a credit-risk project this is
   almost always: `raw data → cleaning/validation → feature engineering → train/test split →
   model training → evaluation → (optional) serving/inference → monitoring`. A change at one stage
   nearly always has a counterpart at another (a new feature must exist identically at train time
   and at serve time; a new target definition must be re-applied everywhere the old one was used).
3. **Look before building.** Search the repo (and installed libraries — pandas, scikit-learn,
   whatever the project settles on) first. The helper, transform, or metric you're about to write
   may already exist. Don't reimplement what `sklearn.pipeline`, `pandas`, or an existing internal
   utility already does correctly.
4. **Ask only when it changes the work** and you can't resolve it from code, docs, or convention.

### 0.1 Document the *why*, with evidence — cite your sources
Code says *what*; it rarely says *why*. Every non-obvious decision — a feature definition, a
cutoff/threshold, an imputation choice, a "we chose model A over B" — should arrive with its
rationale and, where possible, a citation to an authority.

- **Anchor to an authority, in priority order:** (1) an existing convention already in this repo
  (cite `file:line`); (2) a documented pattern from a credible source (a paper, the scikit-learn/
  pandas docs, a regulator's guidance on credit scoring — e.g. fair-lending / adverse-action
  requirements — a well-known Kaggle solution write-up); (3) a named statistical/engineering
  principle, only when (1) and (2) don't apply.
- **Cite inline.** A one-line comment with a `file:line`/URL beats a paragraph of unsourced
  reasoning.
- **Record the trade-off.** When you pick A over B (e.g. WOE-encoding vs one-hot, logistic
  regression vs gradient boosting for interpretability), say what B was and why A won.
- If you can't find a source for a non-obvious choice, treat that as a signal to look harder or to
  ask — not to assert.

### 0.1.1 Verify before claiming — quote the line, or lower your confidence
Before asserting anything load-bearing about the code or the data — "this column has no nulls",
"the split is stratified", "there's no leakage here", "that's already tested" — you must be able to
point at the specific `file:line` or a command's actual output that motivates the claim. If you
cannot, the claim is *unverified*: say so and do not state it as fact.

- **No completion claim without fresh verification.** "Done"/"fixed"/"works" requires evidence from
  THIS session: a green test run, a re-executed notebook cell, an actually-computed metric — not "it
  should work now" or "I re-read the code and it looks right."
- Classify each fix honestly: **verified** (ran it, confirmed) / **best-effort** (applied but
  couldn't fully confirm — say so) / **reverted** (regressed → backed out).

### 0.2 Language: Vietnamese replies, English artifacts
**Reply to the user in Vietnamese** (English technical terms are fine and encouraged —
`feature engineering`, `train/test split`, `leakage`, `AUC`, `WOE`, etc. — don't translate them).
But **everything written into the repo is in English**: code, identifiers, comments, docstrings,
commit messages, and doc/markdown files. The conversation is Vietnamese; the artifacts are English.

### 0.3 Plan first, implement only on explicit approval — for anything non-trivial
**Don't design and build a non-trivial change in the same breath without checking in.** For a small,
obviously-scoped fix, just do it (§0.3.1). For anything that reshapes the pipeline, changes the
target definition, swaps the modeling approach, or touches how data is split/labeled, lay out the
plan first — the approach, the files/stages touched, the trade-offs (§0.1) — and get a go-ahead
before writing code.

#### 0.3.1 Once cleared to implement — AUTO-FIX vs ASK
Classify each concrete edit:

- **AUTO-FIX — apply it, report it in the before/after (§0.4).** A mechanical change a careful
  practitioner would make without discussion: a typo, a missing null-check, an obvious off-by-one,
  reusing an existing helper you overlooked, a missing unit test for a pure function you just
  touched, vectorizing an obviously-slow loop.
- **ASK — surface it, recommend one option, wait.** Anything reasonable practitioners could disagree
  about; changing the target definition, the evaluation metric, or the train/test split strategy;
  introducing a new modeling library/framework; a fix larger than ~20 lines; removing functionality.

**One-way-door rail — ALWAYS ASK, regardless of how "mechanical" it looks:**
- **Anything that touches how data is split or labeled** — train/test/validation boundaries, the
  target definition (e.g. what counts as "default"), time-based cutoffs. Getting this wrong
  silently invalidates every downstream metric.
- **Anything that could introduce leakage** — a feature computed using information not available at
  prediction time, fitting a transform (scaler, encoder, imputer) on data that includes the test
  set.
- **Model/data versioning changes** — overwriting a saved model artifact, changing a data file that
  other saved results depend on, without a version bump.
- **Credentials / secrets** — API keys, database connection strings, anything that shouldn't be
  committed.
- **Destructive operations** — deleting raw data, overwriting a checkpoint, dropping columns from a
  source file in place.

A change in this list is never "just mechanical" — it is a checkpoint even inside an approved plan.

### 0.4 Explain every change — before vs after
After each implementation batch, give a concise before/after summary before moving on:
- **Before:** the prior state — what the code/pipeline did (or didn't).
- **After:** the new state — what changed, referencing `file:line`.
- **Why:** the rationale, citing the authority per §0.1 when non-obvious.

Keep it terse; scale it to the size of the change. Skip it after pure exploration.

### 0.5 Keep the docs in sync — check after every implementation, notify, ask before applying
After every implementation, check whether `README.md` or any doc under `docs/` now says something
false, incomplete, or outdated. If so, **tell the user** — name the file, quote the stale line,
propose the exact edit — and **wait for approval before editing docs**. If nothing needs updating,
say so in one line.

### 0.6 If there's a UI, dashboard, or API surface — say where to see the change
If the project grows a Streamlit/dashboard/API layer and a change touches it, include a short note:
the route/page, the control, and any prerequisite state needed to see it. Skip this entirely for
pure data/model/backend changes — say so in one line.

### 0.7 Data & model changes — the credit-risk-specific danger zone
This is the highest-risk category in an ML project — more so than in typical CRUD code, because a
subtle mistake doesn't crash, it silently produces a wrong (and plausible-looking) number.

**Before any change that touches data prep, features, splitting, or the model itself, check:**
1. **Leakage.** Is any feature computed using information that would not be available at the actual
   prediction time in production (a value derived from the outcome, a future date, a post-hoc
   status)? Is any transform (scaler, imputer, target/WOE encoder, PCA) fit on the *full* dataset
   instead of fit-on-train-only and applied-to-test?
2. **Split integrity.** Is the same row ever in both train and test (duplicate rows, resampling
   before splitting)? For time-based data, is the split time-ordered (train strictly before test),
   not a random shuffle that lets the model see the future?
3. **Target definition drift.** If the target ("default", "bad", "delinquent", …) is redefined, has
   every place that depends on the old definition (saved labels, cached features, prior model
   artifacts) been identified and either regenerated or explicitly left alone with a note why?
4. **Reproducibility.** Is the random seed fixed and recorded for anything stochastic (split,
   model init, SMOTE/resampling, cross-validation folds)? Can the current result be regenerated from
   a documented command/notebook run?
5. **Versioning.** Is a saved model/data artifact being overwritten in place? If it's referenced by
   a report, a saved metric, or another notebook, bump a version/filename rather than silently
   replacing it.
6. **Class imbalance handling.** If resampling (SMOTE, undersampling, class weights) is used, is it
   applied only to the training fold, never to validation/test?
7. **Fairness/compliance surface (know it, don't skip it).** Credit-risk models are subject to
   fair-lending scrutiny in most jurisdictions (e.g. ECOA/Reg B, adverse-action notice requirements
   in the US). Don't silently include a protected-class proxy feature (zip code as an obvious proxy
   for race, for example) without flagging it to the user — this is a "surface it, don't decide it
   alone" situation.

**State the concern, the affected stage, and the proposed direction. Wait for the user's direction
before proceeding** on anything in this list — it's the ML-project equivalent of a schema change.

### 0.8 Merge-request / PR content — from the actual diff, into a file
When asked for PR/MR content, read the actual diff first (`git log`, `git diff --stat
<base>...<branch>`) — never write it from memory. Group by feature, not by commit. Sections:
Summary / What's included / Files / Notes / How to test. Accuracy over completeness: describe only
what the diff contains, and say whether tests pass on the branch.

---

## 1. Convention-first — the prime rule

Extend the codebase *invisibly* — new code should be indistinguishable from what's there. Before
writing anything new, find the nearest existing example (a similar notebook, a similar transform, a
similar test) and copy its shape.

**Authorities, in order:**
1. **This repo itself** — the closest existing module/notebook/script to what you're building.
2. **The wider Python data-science ecosystem** — `pandas`, `scikit-learn`, `numpy` idioms are the
   default convention when this repo hasn't established its own. Don't invent a bespoke pattern
   (e.g. a hand-rolled train/test splitter) when the standard library one does the job.
3. **External prior art (papers, competition write-ups, vendor docs) — for technique, not shape.**
   Mine a Kaggle credit-scoring write-up or a scikit-learn example for *what* to do (which encoding,
   which metric), not for *how the code should be organized* — organize it to match this repo.

### 1.1 One mechanism per concern — don't build a second way to do the same thing
If this repo already has a config file, a features module, or a metrics module, extend it — don't
start a second, parallel config system or a duplicate feature-computation path "for this one model."
When in doubt, grep for how a comparable thing (a feature, a metric, a config value) is currently
defined and do that.

### 1.2 Don't fork — extend
If an existing helper/transform is *almost* right, extend or parameterize it rather than copy-pasting
it with one line changed. Two near-identical feature functions that drift apart over time are a
maintenance trap.

### 1.3 Build local first, don't build infrastructure speculatively
Don't reach for a full MLOps stack (experiment tracker, orchestrator, feature store, model registry
service) before the project actually needs it. A `models/` directory with versioned filenames and a
`results.csv`/`experiments.md` log is enough until real pain justifies more.

### 1.4 External references — mine for knowledge, not for shape
Papers, competition solutions, and vendor blog posts carry real prior art on feature ideas,
validation strategies, and known pitfalls in credit scoring (e.g. reject inference, population
stability index for monitoring, WOE/IV for feature selection). Treat them as **orientation, not
authority** for how *this* repo's code should look — cite them when they justify a choice (§0.1),
but write the code in this repo's own idiom.

---

## 2. Use what already exists before building

- **Prefer the standard library of the ecosystem** (`pandas`, `numpy`, `scikit-learn`,
  `statsmodels`, `matplotlib`/`seaborn` or whatever plotting library the repo settles on) over
  hand-rolled equivalents.
- **Don't hand-roll what a library already validates well** — a cross-validation splitter, a metric
  (AUC, KS-statistic, Gini), a calibration check — use the library's implementation and cite it,
  rather than re-deriving the formula by hand where a subtle bug can hide.
- **Config belongs in one place.** Once the repo has a config file/module, new tunables go there —
  not scattered as magic numbers across notebooks and scripts.

---

## 3. Project layout (real, as of Plan 0001)

This is the actual layout, established by
[docs/plans/0001-pd-scorecard-give-me-some-credit.md](docs/plans/0001-pd-scorecard-give-me-some-credit.md)
— match it rather than inventing a parallel structure for the next dataset/model:

```
data/
  raw/<dataset-slug>/          untouched source files (gitignored — never committed)
  processed/                   generated, reproducible from raw/ (gitignored)
notebooks/                     EDA only (e.g. 01_eda.ipynb) — findings feed decisions in src/,
                                never the reverse; a notebook is not a pipeline step
src/
  data/       load.py (schema-validated read), clean.py (documented, evidence-driven cleaning)
  features/   binning.py (WOE/IV via optbinning), select.py (IV threshold + VIF)
  models/     scorecard.py (logistic regression + points scaling), evaluate.py (AUC/KS/
              calibration/PSI)
  pipeline/   train.py — the one script that wires load -> clean -> bin -> select -> model ->
              evaluate -> save-artifacts; run as `python -m src.pipeline.train`
tests/        one test file per src/ module, pure-logic + synthetic fixtures only — never
              depends on a real file under data/raw/
config/       one YAML per dataset/model (e.g. give_me_some_credit.yaml) — seed, split ratio,
              special codes, IV threshold, scorecard PDO/base score/base odds
models/<dataset-slug>/   pipeline output: binner.pkl, scorecard.pkl, metrics.json,
                calibration_table.csv, roc_curve.csv, data_profile.json (an aggregate-only
                summary — histogram bin counts, describe() stats, missing rates, never raw
                rows — see src/data/profile.py), a copy of the config that produced them.
                Gitignored (regenerated by train.py) by default EXCEPT for
                give-me-some-credit/, which is deliberately committed (see .gitignore's
                comment) because the app is hosted without a training step or the raw data
                present — evaluate this same trade-off per dataset, don't assume it by default
docs/
  plans/        numbered plan docs (this project's own decision history — see §10)
  model_cards/  one per trained model — data/features/metrics/limitations, written from the
                real run's output, never from memory (see the give-me-some-credit-pd-v1 card)
app/            the Streamlit interaction layer (Plan 0002) — reads models/ artifacts, never
                recomputes the pipeline itself
requirements.txt (pipeline deps), requirements-app.txt (adds streamlit/plotly on top),
pyproject.toml (pytest config), .venv/ (gitignored)
```

A new dataset/model follows the same `src/{data,features,models,pipeline}` + `tests/` + `config/`
+ `models/<slug>/` + `docs/model_cards/` shape — extend this layout, don't start a second one.

---

## 4. Data & tests

- **Raw data is immutable.** Never edit a file under `data/raw/` in place; every transformation
  produces a new file under `data/processed/` (or is fully reproducible by re-running a script).
- **Validate data on load.** Check shapes, dtypes, null rates, and value ranges against what's
  expected — fail loudly on a schema surprise rather than silently propagating garbage.
- **Fit-then-transform discipline.** Any stateful transform (scaler, imputer, encoder) is fit on the
  training fold only, then applied (`.transform`, not `.fit_transform`) to validation/test/serving
  data. This is the single most common source of leakage — treat it as a hard rule, not a
  guideline.
- **Tests are for pure logic.** A feature transform, a metric calculation, a data-validation
  function — anything with no I/O — ships with a unit test. Notebooks and full-pipeline runs are
  exercised manually / via a smoke-test script, not unit-tested cell-by-cell.
- **Seeds are fixed and recorded** for every stochastic step (split, model init, resampling, CV
  folds) so a result can be regenerated.

---

## 5. Reproducibility & versioning doctrine

- **Every trained model artifact is versioned** — by filename (`model_v3_2026-09-12.pkl`), a small
  metadata file next to it (features used, training data version, metrics, seed), or a registry —
  never silently overwritten.
- **Every reported metric is traceable** to the exact code + data version that produced it. If you
  can't point to the commit/run that generated a number, don't present it as current.
- **Config drives runs, not hardcoded notebook cells.** Hyperparameters, feature lists, and paths
  belong in a config (file, dict, or dataclass) that's saved alongside the run's output, not typed
  inline and forgotten.

---

## 6. Data privacy & secrets

- **No PII or raw credentials committed to the repo.** Credit data often includes sensitive fields
  (income, SSN-like IDs, address). Keep real data out of version control (`.gitignore` on
  `data/raw/` and any file containing real records); use synthetic/sample data in anything committed.
- **Secrets** (API keys, DB connection strings) go in an untracked `.env` or local config, never
  hardcoded or committed.
- **Watch for protected-class proxies** in features (see §0.7.7) and flag them rather than silently
  including or silently dropping them — that's a decision for the user, not a default.

---

## 7. Performance — follow the pattern, don't pre-optimize

- **Vectorize.** Use `pandas`/`numpy` vectorized operations instead of `.iterrows()`/`.apply()` with
  a Python-level loop over rows, once the data is more than trivially small.
- **Avoid recomputing expensive features** on every run — cache intermediate processed data under
  `data/processed/` when a step is slow and deterministic.
- **Profile before optimizing.** Don't restructure working code for speed without evidence it's the
  bottleneck.

---

## 8. Maintainability — applied with restraint

### 8.1 Do NOT over-engineer (explicit)
Following a principle too literally is itself a defect here. Avoid:

- **A model-abstraction framework** ("pluggable" model backends) before there are actually two
  models that need swapping.
- **An orchestration/workflow engine** (Airflow, Prefect, …) before the pipeline has outgrown a
  script or a Makefile.
- **A feature store / model registry service** before a `models/` folder + a metadata file has
  actually become insufficient.
- **Speculative abstractions** — no helper/base class for a single use case. Abstract on the third
  concrete repetition, not the first.
- **Gold-plating** — unrequested config options, metrics, or plots that widen scope.
- **Restructuring working code** to satisfy a principle when it already matches the surrounding
  style. Touch only what the task requires.

The test: *does this make the change smaller and more like the existing code, or larger and more
clever?* Prefer smaller and more like.

---

## 9. Pre-implementation checklist

```
[ ] Framed the actual ask and, for anything non-trivial, checked in on the plan before coding (§0.3)
[ ] Read whatever convention already exists (README, docs, nearest similar module) before writing
[ ] Traced the full chain this change touches (data → features → split → train → eval → [serve])
[ ] Found the nearest existing example and mirrored its shape, rather than inventing a new one
[ ] Checked: does this belong in the existing config/features/model structure, or does it truly
    need a new mechanism (§1.1)?
[ ] No leakage: any fit-on-train transform is not fit on test/validation; no feature uses
    information unavailable at prediction time (§0.7)
[ ] Split integrity: no row duplicated across train/test; time-based data split in time order
[ ] Target definition unchanged, or every downstream dependent identified and handled (§0.7)
[ ] Seeds fixed and recorded for anything stochastic; result is regenerable
[ ] Any saved model/data artifact versioned, not silently overwritten
[ ] Each edit classified AUTO-FIX vs ASK; anything touching data splitting/labeling, leakage risk,
    model/data versioning, secrets, or destructive ops went to ASK regardless (§0.3.1)
[ ] No PII/secrets committed; no protected-class proxy silently included or dropped without flagging
[ ] Vectorized where it matters; no N+1-style per-row Python loop on non-trivial data
[ ] Pure-logic change (a transform, a metric) ships with a unit test; tests pass
[ ] Smallest correct change — no speculative MLOps infrastructure, no refactor of untouched code
[ ] Non-obvious decision documented with its why + a citation (§0.1)
[ ] Load-bearing claims about the code/data quote a file:line or an actual command output, or are
    marked unverified (§0.1.1)
[ ] Provided a before-vs-after summary of what changed and why (§0.4)
[ ] Re-checked README/docs for drift, notified the user, and asked before editing them (§0.5)
```

---

## 10. Where conventions live

| Source | Use for |
|---|---|
| [docs/plans/](docs/plans/) | Numbered plan docs — this project's own decision history. Read the nearest one before extending its area (e.g. 0001 for the data/binning/scorecard pipeline shape, 0002 for the app) |
| [docs/model_cards/](docs/model_cards/) | Per-model data/features/metrics/limitations, generated from real runs — the source of truth for "what does the current model actually do," not a re-derivation from memory |
| `notebooks/01_eda.ipynb` | The verified data-quirk findings (missing values, sentinel codes, outlier entanglement) that justify the cleaning/binning decisions in `src/data/clean.py` and `config/*.yaml` |
| The nearest similar module in `src/` | The working example of the pattern to copy for a new dataset/model (§3) |
| `optbinning` / `scikit-learn` / `pandas` docs | Default conventions for binning, modeling, and data handling — don't hand-roll what these already validate (§2) |
| Credit-scoring prior art (papers, competition write-ups) | Feature ideas, validation strategy, known pitfalls — orientation, cite when used (§0.1), never blind-copy the code shape |

When a pattern exists in two or more places in this repo, it's the convention — match it, don't
invent a different "better" way.
