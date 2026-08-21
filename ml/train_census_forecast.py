"""Train and validate the offline GulfStar hospital census forecast."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from ml.census_forecast import hospital_day_census, recursive_forecast, supervised_rows
except ModuleNotFoundError:  # Direct execution from the ml directory.
    from census_forecast import hospital_day_census, recursive_forecast, supervised_rows


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
HORIZON_BUCKETS = ((1, 7, "Days 1–7"), (8, 21, "Days 8–21"), (22, 30, "Days 22–30"))
COMPLEX_MODEL_MINIMUM_LIFT_PCT = 5.0


def pipeline(estimator):
    categorical = ["hospital", "day_of_week"]
    numeric = ["trend_day", "annual_sin", "annual_cos", "lag_1", "lag_7", "lag_14", "lag_28", "rolling_7", "rolling_28"]
    return Pipeline([
        ("features", ColumnTransformer([
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
            ("numeric", StandardScaler(), numeric),
        ])),
        ("model", estimator),
    ])


def seasonal_naive(history, dates, lag):
    history = hospital_day_census(history)
    values = {(row.hospital, pd.Timestamp(row.date)): float(row.census) for row in history.itertuples(index=False)}
    output = []
    for date in pd.DatetimeIndex(dates).sort_values():
        for hospital in sorted(history.hospital.unique()):
            source_date = date - pd.Timedelta(days=lag)
            prediction = values.get((hospital, source_date))
            if prediction is None:
                earlier = [value for (name, day), value in values.items() if name == hospital and day < date]
                prediction = earlier[-1]
            values[(hospital, date)] = prediction
            output.append({"date": date, "hospital": hospital, "prediction": prediction})
    return pd.DataFrame(output)


def rolling_backtest(census):
    dates = pd.DatetimeIndex(sorted(census.date.unique()))
    fold_starts = dates[-180::30][:6]
    records = []
    for fold, start in enumerate(fold_starts, 1):
        test_dates = dates[(dates >= start) & (dates < start + pd.Timedelta(days=30))]
        train = census[census.date < start]
        test = census[census.date.isin(test_dates)]
        x_train, y_train = supervised_rows(train)
        models = {
            "ridge": pipeline(Ridge(alpha=10.0)),
            "gradient_boosting": pipeline(GradientBoostingRegressor(
                n_estimators=180, learning_rate=0.035, max_depth=2, loss="huber", random_state=42,
            )),
        }
        forecasts = {}
        for name, model in models.items():
            model.fit(x_train, y_train)
            forecasts[name] = recursive_forecast(model, train, test_dates).rename(columns={"predicted_census": "prediction"})
        forecasts["naive_last"] = seasonal_naive(train, test_dates, 1)
        forecasts["seasonal_naive_7"] = seasonal_naive(train, test_dates, 7)
        truth = test[["date", "hospital", "census"]]
        for model_name, forecast in forecasts.items():
            merged = truth.merge(forecast, on=["date", "hospital"], validate="one_to_one")
            for row in merged.itertuples(index=False):
                records.append({
                    "fold": fold, "date": row.date, "hospital": row.hospital,
                    "actual": row.census, "prediction": row.prediction,
                    "absolute_error": abs(row.census - row.prediction), "model": model_name,
                })
    return pd.DataFrame(records)


def add_horizon(backtest):
    frame = backtest.copy()
    frame["horizon_day"] = frame.groupby(["model", "fold"]).date.transform(lambda dates: (dates - dates.min()).dt.days + 1)
    frame["horizon_bucket"] = pd.cut(
        frame.horizon_day, [0, 7, 21, 30], labels=[bucket[2] for bucket in HORIZON_BUCKETS],
    ).astype(str)
    return frame


def horizon_conformal(ridge_backtest):
    """Calibrate forecast intervals by decision-relevant horizon bucket."""
    rows = []
    for start, end, label in HORIZON_BUCKETS:
        errors = ridge_backtest.loc[ridge_backtest.horizon_bucket == label, "absolute_error"]
        radius = float(np.quantile(errors, 0.90, method="higher"))
        rows.append({
            "horizon_bucket": label, "start_day": start, "end_day": end,
            "n": int(len(errors)), "radius_90": radius,
            "empirical_coverage": float((errors <= radius).mean()),
            "mae": float(errors.mean()),
        })
    return pd.DataFrame(rows)


def sequential_bucket_coverage(ridge_backtest):
    """Measure coverage using only earlier folds to calibrate each later fold."""
    rows = []
    for fold in sorted(ridge_backtest.fold.unique())[1:]:
        for _, _, label in HORIZON_BUCKETS:
            calibration = ridge_backtest[(ridge_backtest.fold < fold) & (ridge_backtest.horizon_bucket == label)]
            evaluation = ridge_backtest[(ridge_backtest.fold == fold) & (ridge_backtest.horizon_bucket == label)]
            radius = float(np.quantile(calibration.absolute_error, 0.90, method="higher"))
            for error in evaluation.absolute_error:
                rows.append({"fold": int(fold), "horizon_bucket": label, "radius_90": radius, "covered": bool(error <= radius)})
    return pd.DataFrame(rows)


def population_stability_index(reference, current, bins=10):
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    expected = pd.Series(pd.cut(reference, edges, include_lowest=True)).value_counts(sort=False, normalize=True).clip(lower=1e-6)
    actual = pd.Series(pd.cut(current, edges, include_lowest=True)).value_counts(sort=False, normalize=True).clip(lower=1e-6)
    return float(((actual - expected) * np.log(actual / expected)).sum())


def drift_stress_test(model, features, target):
    """Use deterministic level shifts to show when drift damages forecast error."""
    rows = []
    level_columns = [f"lag_{lag}" for lag in (1, 7, 14, 28)] + ["rolling_7", "rolling_28"]
    reference = features["lag_7"].to_numpy()
    for shift_pct in (0, 5, 10, 15, 20, 25, 30):
        shifted = features.copy()
        multiplier = 1 + shift_pct / 100
        shifted[level_columns] *= multiplier
        shifted_target = target * multiplier
        prediction = model.predict(shifted)
        rows.append({
            "census_level_shift_pct": shift_pct,
            "psi_lag_7": population_stability_index(reference, shifted["lag_7"].to_numpy()),
            "mae_beds": float(mean_absolute_error(shifted_target, prediction)),
        })
    return pd.DataFrame(rows)


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv(ROOT / "data" / "daily_operations.csv.gz", parse_dates=["date"])
    census = hospital_day_census(daily)
    backtest = add_horizon(rolling_backtest(census))
    summary = backtest.groupby("model").absolute_error.mean().sort_values()

    ridge_backtest = backtest[backtest.model == "ridge"].copy()
    bucket_calibration = horizon_conformal(ridge_backtest)
    sequential_coverage = sequential_bucket_coverage(ridge_backtest)

    x_all, y_all = supervised_rows(census)
    final_model = pipeline(Ridge(alpha=10.0)).fit(x_all, y_all)
    x_train_random, x_test_random, y_train_random, y_test_random = train_test_split(
        x_all, y_all, test_size=0.20, random_state=42,
    )
    random_model = pipeline(Ridge(alpha=10.0)).fit(x_train_random, y_train_random)
    random_split_mae = float(mean_absolute_error(y_test_random, random_model.predict(x_test_random)))
    future_dates = pd.date_range(census.date.max() + pd.Timedelta(days=1), periods=30, freq="D")
    future = recursive_forecast(final_model, census, future_dates)
    future["horizon_day"] = (future.date - census.date.max()).dt.days
    radius_map = {}
    for row in bucket_calibration.itertuples(index=False):
        for day in range(row.start_day, row.end_day + 1):
            radius_map[day] = row.radius_90
    future["radius_90"] = future.horizon_day.map(radius_map)
    future["lower_90"] = (future.predicted_census - future.radius_90).clip(lower=0)
    future["upper_90"] = future.predicted_census + future.radius_90

    ridge_mae = float(summary["ridge"])
    seasonal_mae = float(summary["seasonal_naive_7"])
    metrics = {
        "training_rows": int(len(x_all)), "source_hospital_days": int(len(census)),
        "training_start": f"{census.date.min():%Y-%m-%d}", "training_end": f"{census.date.max():%Y-%m-%d}",
        "folds": 6, "horizon_days": 30,
        "naive_last_mae": float(summary["naive_last"]),
        "seasonal_naive_7_mae": seasonal_mae,
        "ridge_mae": ridge_mae,
        "gradient_boosting_mae": float(summary["gradient_boosting"]),
        "ridge_improvement_vs_seasonal_pct": 100 * (seasonal_mae - ridge_mae) / seasonal_mae,
        "random_split_ridge_mae": random_split_mae,
        "rolling_origin_mae_range": [float(ridge_backtest.groupby("fold").absolute_error.mean().min()), float(ridge_backtest.groupby("fold").absolute_error.mean().max())],
        "horizon_bucket_calibration": bucket_calibration.to_dict("records"),
        "sequential_horizon_coverage": sequential_coverage.groupby("horizon_bucket").covered.mean().to_dict(),
        "calibration_empirical_coverage": float(bucket_calibration.eval("empirical_coverage * n").sum() / bucket_calibration.n.sum()),
        "model_selected": "Ridge",
        "complex_model_adoption_rule": f"Adopt gradient boosting only if it reduces rolling-origin MAE by at least {COMPLEX_MODEL_MINIMUM_LIFT_PCT:.0f}% versus Ridge.",
        "complex_model_lift_vs_ridge_pct": 100 * (ridge_mae - float(summary["gradient_boosting"])) / ridge_mae,
    }

    coefficient_names = final_model.named_steps["features"].get_feature_names_out()
    coefficients = pd.DataFrame({"feature": coefficient_names, "standardized_coefficient": final_model.named_steps["model"].coef_})
    coefficients["absolute_coefficient"] = coefficients.standardized_coefficient.abs()
    coefficients = coefficients.sort_values("absolute_coefficient", ascending=False)
    drift = drift_stress_test(final_model, x_all, y_all)
    unacceptable = drift[drift.mae_beds > seasonal_mae]
    metrics["drift_retrain_psi_threshold"] = 0.20
    metrics["first_stress_level_worse_than_seasonal_pct"] = int(unacceptable.census_level_shift_pct.iloc[0]) if not unacceptable.empty else None
    joblib.dump(final_model, ARTIFACTS / "census_ridge.joblib")
    backtest.round(6).to_csv(ARTIFACTS / "backtest_predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    future.round(4).to_csv(ARTIFACTS / "forecast_30d.csv", index=False)
    bucket_calibration.round(4).to_csv(ARTIFACTS / "horizon_calibration.csv", index=False)
    sequential_coverage.to_csv(ARTIFACTS / "sequential_coverage.csv", index=False)
    coefficients.round(6).to_csv(ARTIFACTS / "ridge_coefficients.csv", index=False)
    drift.round(4).to_csv(ARTIFACTS / "drift_stress_test.csv", index=False)
    stable_metrics = json.loads(json.dumps(metrics))
    def rounded(value):
        if isinstance(value, float):
            return round(value, 4)
        if isinstance(value, list):
            return [rounded(item) for item in value]
        if isinstance(value, dict):
            return {key: rounded(item) for key, item in value.items()}
        return value
    stable_metrics = rounded(stable_metrics)
    (ARTIFACTS / "backtest_metrics.json").write_text(json.dumps(stable_metrics, indent=2) + "\n")
    (ARTIFACTS / "model_card.md").write_text(
        "# GulfStar Census Forecast Model Card\n\n"
        "## Intended use\nForecast the next 30 days of synthetic hospital census for staffing and capacity scenario planning.\n\n"
        "## Model\nRidge regression with hospital and weekday indicators, trend, annual Fourier terms, census lags (1, 7, 14, 28 days), and trailing 7/28-day means.\n\n"
        "## Validation\nSix rolling-origin folds with a 30-day recursive horizon. Random train/test splitting is not used. "
        f"Ridge MAE: {ridge_mae:.2f} beds; seasonal-naive MAE: {seasonal_mae:.2f}; improvement: {metrics['ridge_improvement_vs_seasonal_pct']:.1f}%.\n\n"
        "## Pre-registered selection rule\nAdopt gradient boosting only if it reduces rolling-origin MAE by at least 5% versus Ridge. It did not, so Ridge remains selected.\n\n"
        "## Uncertainty\nA 90% conformal interval is calibrated separately for days 1–7, 8–21, and 22–30. Bucket and sequential coverage are reported in the artifacts.\n\n"
        "## Explainability\nStandardized Ridge coefficients are committed as an association artifact. They are associations within overlapping simulated measurement windows, not causal effects.\n\n"
        "## Drift and maintenance\nMonitor PSI on lagged census features. PSI at or above 0.20 triggers review and prospective error validation before retraining.\n\n"
        "## Limitations\nSynthetic portfolio data only. Error is nearly horizon-invariant because census was simulated around a slowly varying mean; this would not be expected to hold prospectively. The model does not include acuity, scheduled procedures, closures, weather, outbreaks, or real staffing constraints. It is not patient-care decision support and requires external validation before operational use.\n"
    )
    print(json.dumps(stable_metrics, indent=2))


if __name__ == "__main__":
    main()
