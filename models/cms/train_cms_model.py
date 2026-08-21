"""Train a grouped, calibrated real-data CMS hospital classifier offline."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = Path(__file__).resolve().parent
TARGET = "elevated_readmission_performance"


def feature_columns(frame):
    numeric = sorted([column for column in frame if column.startswith("hcahps_")]) + ["reported_hrrp_conditions"]
    categorical = ["hospital_ownership", "emergency_services", "meets_criteria_for_birthing_friendly_designation"]
    return numeric, categorical


def model_pipeline(numeric, categorical):
    preprocess = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ])
    return Pipeline([("features", preprocess), ("model", LogisticRegression(max_iter=2_000, class_weight="balanced", C=0.5, random_state=42))])


def grouped_calibrated_predictions(frame, features, target, groups, pipeline):
    rows = []
    outer = GroupKFold(n_splits=5)
    for fold, (train_index, test_index) in enumerate(outer.split(features, target, groups), 1):
        x_train, y_train, g_train = features.iloc[train_index], target.iloc[train_index], groups.iloc[train_index]
        x_test, y_test = features.iloc[test_index], target.iloc[test_index]
        inner_probability = np.zeros(len(train_index))
        inner = GroupKFold(n_splits=4)
        for inner_train, inner_test in inner.split(x_train, y_train, g_train):
            candidate = clone(pipeline).fit(x_train.iloc[inner_train], y_train.iloc[inner_train])
            inner_probability[inner_test] = candidate.predict_proba(x_train.iloc[inner_test])[:, 1]
        calibrator = IsotonicRegression(out_of_bounds="clip").fit(inner_probability, y_train)
        fitted = clone(pipeline).fit(x_train, y_train)
        raw_probability = fitted.predict_proba(x_test)[:, 1]
        calibrated_probability = calibrator.transform(raw_probability)
        for position, raw, calibrated in zip(test_index, raw_probability, calibrated_probability):
            rows.append({
                "row": int(position), "fold": fold, "raw_probability": raw,
                "calibrated_probability": calibrated, "actual": int(frame.iloc[position][TARGET]),
            })
    return pd.DataFrame(rows).sort_values("row").reset_index(drop=True)


def reliability_table(predictions, probability_column):
    frame = predictions.copy()
    frame["bin"] = pd.qcut(frame[probability_column], q=10, duplicates="drop")
    result = frame.groupby("bin", observed=True).agg(
        hospitals=("actual", "size"), mean_predicted=(probability_column, "mean"), observed_rate=("actual", "mean"),
    ).reset_index(drop=True)
    result["probability_type"] = "Calibrated" if probability_column.startswith("calibrated") else "Uncalibrated"
    return result


def bootstrap_auc_interval(actual, probability, iterations=500):
    rng = np.random.default_rng(42)
    scores = []
    indices = np.arange(len(actual))
    for _ in range(iterations):
        sample = rng.choice(indices, size=len(indices), replace=True)
        if np.unique(actual[sample]).size == 2:
            scores.append(roc_auc_score(actual[sample], probability[sample]))
    return [float(np.quantile(scores, 0.025)), float(np.quantile(scores, 0.975))]


def main():
    frame = pd.read_csv(ROOT / "data" / "cms" / "cms_hospital_features.csv.gz", dtype={"facility_id": str})
    numeric, categorical = feature_columns(frame)
    x, y, groups = frame[numeric + categorical], frame[TARGET], frame.state
    base = model_pipeline(numeric, categorical)
    predictions = grouped_calibrated_predictions(frame, x, y, groups, base)
    joined = frame.reset_index(drop=True).join(predictions.set_index("row"), how="left")

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.20, stratify=y, random_state=42)
    random_model = clone(base).fit(x_train, y_train)
    random_probability = random_model.predict_proba(x_test)[:, 1]

    raw, calibrated, actual = predictions.raw_probability.to_numpy(), predictions.calibrated_probability.to_numpy(), predictions.actual.to_numpy()
    prevalence = float(y.mean())
    metrics = {
        "rows": int(len(frame)), "states": int(frame.state.nunique()), "positive_rate": prevalence,
        "target": "Mean reportable CMS HRRP excess readmission ratio greater than 1.0",
        "grouped_split": "5-fold GroupKFold by state; no state appears in both train and test within a fold",
        "grouped_raw_auc": float(roc_auc_score(actual, raw)),
        "grouped_calibrated_auc": float(roc_auc_score(actual, calibrated)),
        "grouped_raw_brier": float(brier_score_loss(actual, raw)),
        "grouped_calibrated_brier": float(brier_score_loss(actual, calibrated)),
        "grouped_calibrated_log_loss": float(log_loss(actual, calibrated, labels=[0, 1])),
        "grouped_auc_95_interval": bootstrap_auc_interval(actual, calibrated),
        "random_split_auc": float(roc_auc_score(y_test, random_probability)),
        "random_split_brier": float(brier_score_loss(y_test, random_probability)),
        "prevalence_baseline_brier": float(brier_score_loss(actual, np.repeat(prevalence, len(actual)))),
    }

    final_model = clone(base).fit(x, y)
    full_raw = final_model.predict_proba(x)[:, 1]
    calibration_folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof = np.zeros(len(y))
    for train_index, test_index in calibration_folds.split(x, y):
        oof[test_index] = clone(base).fit(x.iloc[train_index], y.iloc[train_index]).predict_proba(x.iloc[test_index])[:, 1]
    final_calibrator = IsotonicRegression(out_of_bounds="clip").fit(oof, y)

    feature_names = final_model.named_steps["features"].get_feature_names_out()
    coefficients = pd.DataFrame({"feature": feature_names, "coefficient": final_model.named_steps["model"].coef_[0]})
    coefficients["absolute_coefficient"] = coefficients.coefficient.abs()
    coefficients = coefficients.sort_values("absolute_coefficient", ascending=False)

    joined["prediction"] = (joined.calibrated_probability >= 0.5).astype(int)
    joined["correct"] = (joined.prediction == joined[TARGET]).astype(int)
    joined["hcahps_summary_quartile"] = pd.NA
    star_available = joined.hcahps_h_star_rating.notna()
    joined.loc[star_available, "hcahps_summary_quartile"] = pd.qcut(
        joined.loc[star_available, "hcahps_h_star_rating"].rank(method="first"),
        4, labels=["Q1", "Q2", "Q3", "Q4"],
    ).astype(str)
    subgroup_rows = []
    for dimension in ("hospital_ownership", "emergency_services", "hcahps_summary_quartile", "reported_hrrp_conditions"):
        for value, group in joined.groupby(dimension, dropna=False, observed=True):
            if len(group) < 25:
                continue
            subgroup_rows.append({
                "dimension": dimension, "subgroup": str(value), "hospitals": int(len(group)),
                "observed_rate": float(group[TARGET].mean()), "mean_probability": float(group.calibrated_probability.mean()),
                "brier_score": float(brier_score_loss(group[TARGET], group.calibrated_probability)),
                "accuracy_at_0_5": float(group.correct.mean()),
            })
    subgroup = pd.DataFrame(subgroup_rows)
    reliability = pd.concat([reliability_table(predictions, "raw_probability"), reliability_table(predictions, "calibrated_probability")], ignore_index=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final_model, "calibrator": final_calibrator}, MODEL_DIR / "model.joblib")
    predictions.round(6).to_csv(MODEL_DIR / "grouped_predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    reliability.round(6).to_csv(MODEL_DIR / "calibration.csv", index=False)
    subgroup.round(6).to_csv(MODEL_DIR / "subgroup_audit.csv", index=False)
    coefficients.round(6).to_parquet(MODEL_DIR / "association_explanations.parquet", index=False)
    stable_metrics = json.loads(json.dumps(metrics))
    def rounded(value):
        if isinstance(value, float): return round(value, 4)
        if isinstance(value, list): return [rounded(item) for item in value]
        return value
    stable_metrics = {key: rounded(value) for key, value in stable_metrics.items()}
    (MODEL_DIR / "metrics.json").write_text(json.dumps(stable_metrics, indent=2) + "\n")
    manifest = {
        "target": TARGET, "numeric_features": numeric, "categorical_features": categorical,
        "required_columns": numeric + categorical, "facility_id_dtype": "zero-padded six-character string",
        "feature_table": "data/cms/cms_hospital_features.csv.gz",
    }
    (MODEL_DIR / "feature_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (MODEL_DIR / "model_card.md").write_text(
        "# CMS Hospital Readmission-Performance Classifier Model Card\n\n"
        "## Intended use\nPortfolio benchmarking: estimate whether a hospital's mean reportable HRRP excess readmission ratio is above 1.0 from published structural and HCAHPS attributes.\n\n"
        "## Out-of-scope use\nNo patient-level prediction, payment decision, hospital ranking for contracting, or patient-care use. This is cross-sectional association modeling—not a prospective causal model.\n\n"
        "## Data and timing\nOfficial CMS Provider Data Catalog sources retrieved by `etl/fetch_cms.py`. HRRP outcomes cover an earlier measurement window than the current HCAHPS snapshot; therefore the model must not be represented as forecasting future readmissions.\n\n"
        "## Evaluation\nFive grouped-by-state outer folds, nested grouped isotonic calibration, random-split comparison, Brier score, AUC with bootstrap interval, reliability table, and subgroup audit.\n\n"
        "## Explanations\nCommitted standardized logistic coefficients are associations from overlapping or differently timed public measurement windows, not causal effects.\n\n"
        "## Maintenance\nRefresh only after CMS source-version review, rerun grouped validation and calibration, compare subgroup performance, and approve the new manifest and hashes.\n"
    )
    print(json.dumps(stable_metrics, indent=2))


if __name__ == "__main__":
    main()
