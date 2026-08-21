import json
from pathlib import Path

import joblib
import pandas as pd

from ml.census_forecast import hospital_day_census, load_forecast_artifacts, supervised_rows


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "ml" / "artifacts"


def test_census_training_grain_and_features_are_leakage_safe():
    daily = pd.read_csv(ROOT / "data" / "daily_operations.csv.gz", parse_dates=["date"])
    census = hospital_day_census(daily)
    assert len(census) == 1_752
    assert not census.duplicated(["date", "hospital"]).any()
    assert census.date.min() == pd.Timestamp("2025-01-01")
    assert census.date.max() == pd.Timestamp("2026-08-07")
    features, target = supervised_rows(census)
    assert len(features) == len(target) == 1_668
    assert {"lag_1", "lag_7", "lag_14", "lag_28", "rolling_7", "rolling_28"}.issubset(features)


def test_committed_forecast_beats_baselines_and_reports_time_aware_validation():
    metrics = json.loads((ARTIFACTS / "backtest_metrics.json").read_text())
    assert metrics["model_selected"] == "Ridge"
    assert metrics["folds"] == 6
    assert metrics["horizon_days"] == 30
    assert metrics["ridge_mae"] < metrics["seasonal_naive_7_mae"]
    assert metrics["ridge_mae"] < metrics["naive_last_mae"]
    assert metrics["ridge_mae"] < metrics["gradient_boosting_mae"]
    assert metrics["ridge_improvement_vs_seasonal_pct"] > 20
    assert 0.85 <= metrics["calibration_empirical_coverage"] <= 1.0


def test_committed_forecast_has_complete_hospital_day_grain_and_valid_intervals():
    forecast = pd.read_csv(ARTIFACTS / "forecast_30d.csv", parse_dates=["date"])
    assert len(forecast) == 90
    assert forecast.hospital.nunique() == 3
    assert forecast.date.nunique() == 30
    assert not forecast.duplicated(["date", "hospital"]).any()
    assert forecast.date.min() == pd.Timestamp("2026-08-08")
    assert forecast.date.max() == pd.Timestamp("2026-09-06")
    assert (forecast.lower_90 <= forecast.predicted_census).all()
    assert (forecast.predicted_census <= forecast.upper_90).all()
    assert (forecast.lower_90 >= 0).all()


def test_dashboard_artifact_loader_returns_runnable_model_and_documentation():
    model, metrics, forecast = load_forecast_artifacts(ROOT)
    assert model is not None
    assert metrics["model_selected"] == "Ridge"
    assert len(forecast) == 90
    assert joblib.load(ARTIFACTS / "census_ridge.joblib") is not None
    model_card = (ARTIFACTS / "model_card.md").read_text()
    assert "rolling-origin" in model_card.lower()
    assert "not patient-care decision support" in model_card.lower()
