# Plan 0001 — PD Scorecard on "Give Me Some Credit"

Status: **done** — all 9 steps in §6 implemented, 29 unit tests passing, pipeline run end-to-end
against the real data. See [the model card](../model_cards/give-me-some-credit-pd-v1.md) for results.

## 1. Objective

Build a standalone, industry-style **PD (Probability of Default) scorecard** — the classic
WOE/IV binning → logistic regression → points scaling pipeline — end to end on a small, clean,
single-table dataset, so the architecture (not the data engineering) is what gets tested first.
LGD/EAD and the Fannie Mae dataset are deliberately out of scope for this plan; they come later on
a separate dataset (per the earlier conversation).

## 2. Dataset

**Source:** Kaggle competition "Give Me Some Credit" (2011).
**File used:** `cs-training.csv` only — **150,000 rows, 11 columns** (1 target + 10 features), no
join needed. `cs-test.csv` is the original Kaggle submission file and **has no true labels** (it was
scored server-side by Kaggle) — it must NOT be used as our validation set. We will carve our own
train/test (and optionally a validation) split out of `cs-training.csv`.

**Target:** `SeriousDlqin2yrs` (1 = 90+ days past due within 2 years).

**Features (10):** `RevolvingUtilizationOfUnsecuredLines`, `age`,
`NumberOfTime30-59DaysPastDueNotWorse`, `DebtRatio`, `MonthlyIncome`,
`NumberOfOpenCreditLinesAndLoans`, `NumberOfTimes90DaysLate`,
`NumberRealEstateLoansOrLines`, `NumberOfTime60-89DaysPastDueNotWorse`, `NumberOfDependents`.

**Known data quirks to verify on load (unverified until we actually inspect the file — flagging
per LLM.md §0.1.1, not asserting as fact yet):**
- `MonthlyIncome` and `NumberOfDependents` are reported in public write-ups to have missing values.
- The three "past due" count columns are reported to contain sentinel/outlier values (e.g. 96, 98)
  that don't look like genuine counts.
- `age` reportedly has at least one zero value.
- `RevolvingUtilizationOfUnsecuredLines` and `DebtRatio` are ratios that reportedly have extreme
  outliers (values far above 1 / far above what's economically plausible).

  All four points above must be **confirmed against the actual file** during EDA (step 4.2) before
  any cleaning decision is made — we don't clean based on hearsay.

**No time/vintage field** — this dataset cannot support out-of-time (OOT) validation or a real PSI
drift-over-time check. We substitute an IV-stability check and a train-vs-test PSI (population
stability between our two random splits) as the closest available proxy, and note this limitation
in the model card (step 4.8) rather than pretending it's equivalent to OOT.

**License/access:** Kaggle account required to download (`kaggle competitions download -c
GiveMeSomeCredit` via the Kaggle API, or manual download from the competition page).

## 3. Project structure to create

```
data/
  raw/give-me-some-credit/cs-training.csv      # untouched, gitignored
  processed/                                    # generated, reproducible from raw/
src/
  data/load.py            # read + schema/range validation
  features/binning.py     # WOE/IV binning
  features/select.py      # IV-threshold + correlation/VIF filtering
  models/scorecard.py     # logistic regression on WOE features + points scaling
  models/evaluate.py       # AUC, Gini, KS, calibration, PSI
  pipeline/train.py        # wires the above into one runnable script
tests/
  test_binning.py
  test_scorecard.py
  test_evaluate.py
models/
  give-me-some-credit/    # saved artifacts, versioned by filename
docs/
  model_cards/give-me-some-credit-pd-v1.md
config/
  give_me_some_credit.yaml   # IV threshold, PDO/points params, split ratio, seed
```

This instantiates the placeholder layout in [LLM.md](../../LLM.md) §3 for the first time — it
becomes the real convention for later work (per LLM.md §0, "the first non-trivial piece of code you
write becomes the convention"), so §3/§10 there get updated to point here once this lands.

## 4. Step-by-step pipeline

### 4.1 Data ingestion (`src/data/load.py`)
Load `cs-training.csv`, drop the unnamed index column, enforce dtypes, and assert basic schema
(column names/count, target is binary). Fail loudly on a schema mismatch rather than silently
proceeding.

### 4.2 EDA (notebook, exploratory only — not shipped as pipeline code)
Confirm the data quirks listed in §2: null rates per column, distribution/outlier check on each
numeric field, sentinel-value check on the three past-due columns, value_counts on `age`. This step
produces the actual, verified findings that drive step 4.3 — no cleaning decision is made before
this.

### 4.3 Cleaning & split
Based on 4.2's verified findings: decide null handling (WOE binning can treat "missing" as its own
bin, which is actually the industry-standard approach — often preferable to imputation since
missingness itself can carry default signal). Stratified train/test split (default 70/30, seed
fixed and recorded in config) on the target, since there's no time field to split on instead.

### 4.4 WOE/IV binning (`src/features/binning.py`)
For each feature: monotonic binning (equal-frequency or a merge-based monotonic algorithm) against
the target, fit on train only. Compute WOE per bin and Information Value (IV) per feature.
Missing values become their own bin per feature (see 4.3).

### 4.5 Feature selection (`src/features/select.py`)
Keep features by IV threshold (industry rule of thumb: IV < 0.02 not predictive, 0.02–0.3 useful,
> 0.5 suspicious — investigate rather than trust). Check pairwise correlation / VIF among the
survivors to catch redundancy before modeling.

### 4.6 Model (`src/models/scorecard.py`)
Logistic regression on the WOE-transformed features. Check every coefficient sign matches the
expected economic direction (e.g. more past-due history → higher default odds) — a sign flip means
a binning or leakage problem, not a model to ship. Scale to a points-based scorecard (PDO
parameterized in config, default 20 points to double the odds, base score/base odds also in
config).

### 4.7 Validation (`src/models/evaluate.py`)
- Discrimination: AUC, Gini (`2×AUC-1`), KS-statistic.
- Calibration: predicted-vs-observed default rate by score band, Hosmer-Lemeshow test.
- Stability proxy: PSI between train and test score distributions (see §2 limitation note).
All four run on both train and test; a large train/test gap on any metric is a red flag before
anything else.

### 4.8 Model card (`docs/model_cards/give-me-some-credit-pd-v1.md`)
One page: data source + version, features used + their IV, final metrics (train vs test), the
OOT/PSI limitation, the seed, and the config used to produce it — so this run is reproducible and
auditable per LLM.md §5.

### 4.9 Tests
`test_binning.py` (WOE/IV computed correctly on a small synthetic frame with known bins),
`test_scorecard.py` (points formula, coefficient-sign check), `test_evaluate.py` (AUC/KS/PSI against
hand-computable small examples). Per LLM.md §4, these are pure-logic unit tests — no I/O, no real
data file needed to run them.

## 5. Libraries

`pandas`, `numpy`, `scikit-learn` (`LogisticRegression`, train/test split, metrics), `scipy` (KS
test), `matplotlib`/`seaborn` for EDA plots. Binning: evaluate `optbinning` (purpose-built,
maintained, implements monotonic WOE binning directly) vs hand-rolling it — **recommendation:
use `optbinning`** rather than reimplementing monotonic binning by hand, per LLM.md §2 ("prefer the
standard library... don't hand-roll what a library already validates well"); flag this as an ASK
if you'd rather build binning from scratch for learning purposes.

## 6. Order of implementation

1. `src/data/load.py` + its test data fixture → confirm the file loads and schema holds.
2. EDA notebook → verify §2's data-quirk list for real, decide cleaning approach.
3. `src/features/binning.py` + `test_binning.py`.
4. `src/features/select.py`.
5. `src/models/scorecard.py` + `test_scorecard.py`.
6. `src/models/evaluate.py` + `test_evaluate.py`.
7. `src/pipeline/train.py` wiring it all together, run end to end, save artifact to `models/`.
8. `docs/model_cards/give-me-some-credit-pd-v1.md`.

Each numbered item is a natural checkpoint to show you the result before moving to the next.

## 7. Explicitly out of scope for this plan

LGD/EAD modeling, the Fannie Mae dataset, macro overlay/stress testing, IFRS 9 staging, a serving
API, and any monitoring dashboard — these were discussed as the longer-term roadmap but are
separate future plans, not part of this one.
