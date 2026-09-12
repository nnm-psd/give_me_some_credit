# Model Card — Give Me Some Credit PD Scorecard v1

Produced by `src/pipeline/train.py` reading `config/give_me_some_credit.yaml`. Regenerate with:
`python -m src.pipeline.train`.

## Data

- Source: Kaggle "Give Me Some Credit" (2011), `cs-training.csv`, 150,000 rows.
- Cleaning: dropped 1 row with `age == 0` (see `notebooks/01_eda.ipynb`).
- Split: stratified random 70/30, seed 42. **No time field exists in this dataset** — this is a
  random split, not an out-of-time split; see the Limitations section below.
- Train: 104,999 rows. Test: 45,000 rows. Overall default rate: 6.68%.

## Features & binning

All 10 raw features were selected (all cleared the IV >= 0.02 threshold; none were dropped for
redundancy — max VIF among the WOE-transformed features was 1.29, well under the common flag of 5).

| Feature | IV | Note |
|---|---|---|
| RevolvingUtilizationOfUnsecuredLines | 1.114 | Flagged as "suspicious" (IV > 0.5) — see below |
| NumberOfTimes90DaysLate | 0.852 | Flagged as "suspicious" — see below |
| NumberOfTime30-59DaysPastDueNotWorse | 0.728 | Flagged as "suspicious" — see below |
| age | 0.248 | |
| MonthlyIncome | 0.085 | 19.8% missing — binned as its own bin |
| NumberOfOpenCreditLinesAndLoans | 0.085 | |
| DebtRatio | 0.084 | Extreme tail entangled with missing income — see notebook |
| NumberRealEstateLoansOrLines | 0.056 | |
| NumberOfTime60-89DaysPastDueNotWorse | 0.037 | |
| NumberOfDependents | 0.036 | 2.6% missing — binned as its own bin |

**On the three "suspicious" (IV > 0.5) features:** past-delinquency history and revolving-line
utilization are, in real-world credit scoring, consistently the two strongest predictor categories
(they correspond to the "payment history" and "amounts owed" categories that make up the majority
of a FICO score) — so IV this high is consistent with known domain behavior, not on its own
evidence of leakage. There is also no structural leakage path here: these columns describe
account behavior *up to* the observation point, and the target is a *future* 2-year delinquency
outcome. This reasoning is recorded here rather than asserted silently, per the IV > 0.5 check in
`docs/plans/0001-...` §4.5 — it should be revisited if this pipeline is ever pointed at a different
dataset where the same argument might not hold.

**Special-value handling:** 269 rows (0.18%) carry a sentinel code (96 or 98) identically across
all three past-due columns, with a 54.6% default rate vs. 6.68% baseline. These are binned as a
dedicated special-value bin (`optbinning`'s `special_codes`), not dropped or treated as literal
counts — see `notebooks/01_eda.ipynb`.

## Model

Logistic regression (unregularized, `sklearn.LogisticRegression(C=np.inf)`) fit on the WOE-transformed
features, predicting `1 - default` (so a higher score always means lower risk). All 10 coefficients
are positive — the sign-consistency check in `src/models/scorecard.py` passed on the real data,
meaning no feature's binning behaves in an economically backwards way.

Scorecard scaling: PDO = 20, base score = 600 at base odds = 50:1 (config in
`config/give_me_some_credit.yaml`).

## Validation results

| Metric | Train | Test |
|---|---|---|
| AUC | 0.851 | 0.850 |
| Gini | 0.702 | 0.700 |
| KS | 0.548 | 0.549 |

Train and test are nearly identical — no overfitting signal. AUC ~0.85 with only these 10 raw
features and no additional engineering is consistent with publicly reported results on this
dataset (top leaderboard solutions with heavy feature engineering reach ~0.86-0.87).

**Calibration:** predicted vs. observed default rate tracks closely across score bands (see
`models/give-me-some-credit/calibration_table.csv`) — e.g. the 5th decile predicts 2.18% vs. an
observed 2.29%; the top decile predicts 33.8% vs. an observed 35.1%.

**Hosmer-Lemeshow test:** statistic = 35.4, p-value = 2.3e-05 (test set, 10 bins) — formally
"significant" miscalibration at the conventional 0.05 threshold. **Caveat, stated honestly rather
than hidden:** the HL test's power scales with sample size, and at N=45,000 even small, practically
unimportant deviations from perfect calibration become statistically significant. Given the
calibration table above shows differences of a few tenths of a percentage point per bin, this is
read as a mild, expected calibration gap rather than a modeling failure — but it is exactly the
kind of "load-bearing claim" that should be re-checked, not just cited, if this model is ever used
to size actual provisions.

**Population Stability Index (train vs. test):** 0.00016 — "stable." **Limitation, not a clean
bill of health:** this dataset has no time/vintage field, so this PSI compares two random splits of
the *same* underlying population, not the model's actual stability over time. A near-zero value
here is expected by construction and should not be read as evidence the model would remain stable
against genuine future drift.

## Known limitations

1. No out-of-time validation possible — see above.
2. No LGD/EAD companion model on this dataset (10 generic behavioral features, no loan-level
   collateral/exposure data) — this is a PD-only exercise by design (see the earlier project
   discussion; Fannie Mae is the planned dataset for full PD+LGD+EAD).
3. No fairness/protected-class review performed — `age` is used as a raw feature here; a
   production scorecard would need a disparate-impact review before using it.

## Artifacts

`models/give-me-some-credit/`: `binner.pkl` (fitted `FeatureBinner`), `scorecard.pkl` (fitted
`Scorecard`), `metrics.json` (full metrics dump), `calibration_table.csv`, `config.yaml` (the exact
config used for this run — reproducibility per LLM.md §5).
