"""End-to-end training pipeline for the Give Me Some Credit PD scorecard.

Run: python -m src.pipeline.train [--config config/give_me_some_credit.yaml]

Wires together every step built in docs/plans/0001-pd-scorecard-give-me-some-credit.md
§4: load -> clean/split -> bin -> select -> model -> evaluate -> save artifacts.
This is an integration script, not a unit — it's verified by actually running it
against the real data (LLM.md §4), not by a pytest that would need the raw CSV.
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
from pathlib import Path

import yaml

from src.data.clean import clean, split
from src.data.load import FEATURE_COLS, TARGET_COL, load_raw
from src.features.binning import FeatureBinner
from src.features.select import compute_vif, flag_suspicious_iv, select_by_iv
from src.models.evaluate import (
    calibration_table,
    discrimination_metrics,
    hosmer_lemeshow_test,
    interpret_psi,
    population_stability_index,
)
from src.models.scorecard import Scorecard, ScorecardConfig

ARTIFACT_DIR = Path("models/give-me-some-credit")


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config_path: str | Path = "config/give_me_some_credit.yaml") -> dict:
    config = load_config(config_path)

    df = clean(load_raw(config["data"]["raw_path"]))
    train_df, test_df = split(df, test_size=config["data"]["test_size"], seed=config["seed"])

    binner = FeatureBinner(special_codes=config["binning"]["special_codes"])
    binner.fit(train_df[FEATURE_COLS], train_df[TARGET_COL])
    iv_summary = binner.iv_summary()

    selected = select_by_iv(iv_summary, min_iv=config["feature_selection"]["min_iv"])
    suspicious = flag_suspicious_iv(iv_summary, threshold=config["feature_selection"]["suspicious_iv"])

    woe_train = binner.transform(train_df[selected])
    woe_test = binner.transform(test_df[selected])
    vif = compute_vif(woe_train)

    scorecard = Scorecard(ScorecardConfig(**config["scorecard"])).fit(woe_train, train_df[TARGET_COL])

    pd_train = scorecard.predict_pd(woe_train)
    pd_test = scorecard.predict_pd(woe_test)
    score_train = scorecard.score(woe_train)
    score_test = scorecard.score(woe_test)

    n_calib_bins = config["evaluation"]["calibration_bins"]
    psi = population_stability_index(score_train, score_test, buckets=config["evaluation"]["psi_buckets"])
    hl_stat, hl_p = hosmer_lemeshow_test(test_df[TARGET_COL], pd_test, n_bins=n_calib_bins)

    metrics = {
        "n_train": len(train_df),
        "n_test": len(test_df),
        "selected_features": selected,
        "suspicious_high_iv_features": suspicious,
        "iv_summary": {k: float(v) for k, v in iv_summary.to_dict().items()},
        "vif": {k: float(v) for k, v in vif.to_dict().items()},
        "discrimination": {
            "train": discrimination_metrics(train_df[TARGET_COL], pd_train),
            "test": discrimination_metrics(test_df[TARGET_COL], pd_test),
        },
        "hosmer_lemeshow_test": {"statistic": hl_stat, "p_value": hl_p},
        "psi_train_vs_test": {"value": psi, "interpretation": interpret_psi(psi)},
    }

    calib = calibration_table(test_df[TARGET_COL], pd_test, n_bins=n_calib_bins)
    _save_artifacts(config_path, binner, scorecard, metrics, calib)
    return metrics


def _save_artifacts(config_path, binner, scorecard, metrics, calib_table) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ARTIFACT_DIR / "binner.pkl", "wb") as f:
        pickle.dump(binner, f)
    with open(ARTIFACT_DIR / "scorecard.pkl", "wb") as f:
        pickle.dump(scorecard, f)
    with open(ARTIFACT_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    calib_table.to_csv(ARTIFACT_DIR / "calibration_table.csv", index=False)
    shutil.copy(config_path, ARTIFACT_DIR / "config.yaml")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/give_me_some_credit.yaml")
    args = parser.parse_args()

    result = run(args.config)
    print(json.dumps(result, indent=2))
