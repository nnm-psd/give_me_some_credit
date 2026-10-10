# PD Credit Scorecard — Give Me Some Credit

[![tests](https://github.com/nnm-psd/give_me_some_credit/actions/workflows/tests.yml/badge.svg)](https://github.com/nnm-psd/give_me_some_credit/actions/workflows/tests.yml)

A probability-of-default (PD) scorecard built the way banks build them: WOE binning, IV-based feature
selection, a logistic regression scaled to points, and a validation report. It's trained on Kaggle's
[Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) data (150,000 borrowers) and comes with an
interactive app.

**Live app:** https://givemesomecredit-nnmpsd.streamlit.app/ (may take ~30 s to wake up)

## Results

| Metric | Train | Test |
|---|---|---|
| AUC | 0.851 | 0.850 |
| Gini | 0.702 | 0.700 |
| KS | 0.548 | 0.549 |

Train and test are almost identical, so there's no sign of overfitting. An AUC of about 0.85 from the 10 raw
features, with no extra feature engineering, is in line with public results on this dataset. Full details
are in the [model card](docs/model_cards/give-me-some-credit-pd-v1.md).

## Method

1. **Cleaning:** drops one invalid row (`age == 0`). Sentinel codes 96/98 in the past-due columns (0.18% of
   rows, 54.6% default rate) get their own bin instead of being read as real counts.
2. **Binning:** optimal binning with `optbinning`; missing values (monthly income, dependents) get their own
   bin.
3. **Feature selection:** keeps features with IV ≥ 0.02 and checks VIF on the WOE features (max 1.29).
   IV above 0.5 is flagged and justified in the model card rather than ignored.
4. **Model:** logistic regression on WOE features. All coefficients must have the same sign, so no feature
   behaves in an economically backwards way.
5. **Scaling:** PDO = 20, 600 points at odds of 50:1, so a higher score always means lower risk.
6. **Validation:** ROC/KS, calibration by score band, Hosmer–Lemeshow, and train-vs-test PSI.

## The app

- **Data Overview:** feature distributions, missing rates and the default rate.
- **Binning Explorer:** the fitted bins and WOE for each feature, next to the methodology.
- **Score Simulator:** enter an applicant and see the score and PD build up feature by feature.
- **Model Performance:** ROC curve, KS, calibration and PSI.

The app reads only small committed artifacts in `models/give-me-some-credit/` (bin tables, coefficients,
metrics and an aggregate data profile). The raw Kaggle file is never committed or needed to run it.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/Home.py      # the app, from committed artifacts
pytest                         # 34 offline tests, no data needed
python -m src.pipeline.train   # retrain: needs Kaggle's cs-training.csv in data/raw/give-me-some-credit/
```

## Layout

| Path | Role |
|---|---|
| `src/data/` | Loading, cleaning and the aggregate data profile |
| `src/features/` | WOE binning and IV / VIF feature selection |
| `src/models/` | Scorecard (logistic regression + points scaling) and evaluation metrics |
| `src/pipeline/train.py` | End-to-end training run, driven by `config/give_me_some_credit.yaml` |
| `app/` | Streamlit app |
| `docs/` | Model card and design plans |
| `notebooks/01_eda.ipynb` | Exploratory analysis |

## Limitations

- **No out-of-time validation.** The dataset has no date field, so the test set is a random 30% split. The
  near-zero PSI compares two samples of the same population and says nothing about drift over time.
- **Hosmer–Lemeshow rejects perfect calibration** (p = 2.3e-05). With 45,000 test rows even tiny deviations
  are significant; per-band gaps are a few tenths of a percentage point.
- **PD only.** There's no exposure or collateral data, so no LGD or EAD model.
- **No fairness review.** `age` is used as a raw feature; a production scorecard would need a disparate-impact
  review first.
