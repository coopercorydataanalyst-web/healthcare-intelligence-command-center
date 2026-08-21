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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from ml.census_forecast import hospital_day_census, recursive_forecast, supervised_rows
except ModuleNotFoundError:  # Direct execution from the ml directory.
    from census_forecast import hospital_day_census, recursive_forecast, supervised_rows


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


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


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv(ROOT / "data" / "daily_operations.csv.gz", parse_dates=["date"])
    census = hospital_day_census(daily)
    backtest = rolling_backtest(census)
    summary = backtest.groupby("model").absolute_error.mean().sort_values()

    # Split-conformal calibration on the most recent 30 observed days.
    calibration_start = census.date.max() - pd.Timedelta(days=29)
    fit = census[census.date < calibration_start]
    calibration = census[census.date >= calibration_start]
    x_fit, y_fit = supervised_rows(fit)
    calibration_model = pipeline(Ridge(alpha=10.0)).fit(x_fit, y_fit)
    calibration_prediction = recursive_forecast(calibration_model, fit, sorted(calibration.date.unique()))
    calibration_joined = calibration.merge(calibration_prediction, on=["date", "hospital"])
    calibration_errors = (calibration_joined.census - calibration_joined.predicted_census).abs()
    conformal_radius = float(np.quantile(calibration_errors, 0.90, method="higher"))

    x_all, y_all = supervised_rows(census)
    final_model = pipeline(Ridge(alpha=10.0)).fit(x_all, y_all)
    future_dates = pd.date_range(census.date.max() + pd.Timedelta(days=1), periods=30, freq="D")
    future = recursive_forecast(final_model, census, future_dates)
    future["lower_90"] = (future.predicted_census - conformal_radius).clip(lower=0)
    future["upper_90"] = future.predicted_census + conformal_radius

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
        "conformal_radius_90": conformal_radius,
        "calibration_empirical_coverage": float((calibration_errors <= conformal_radius).mean()),
        "model_selected": "Ridge",
    }
    joblib.dump(final_model, ARTIFACTS / "census_ridge.joblib")
    backtest.to_csv(ARTIFACTS / "backtest_predictions.csv.gz", index=False, compression="gzip")
    future.to_csv(ARTIFACTS / "forecast_30d.csv", index=False)
    (ARTIFACTS / "backtest_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (ARTIFACTS / "model_card.md").write_text(
        "# GulfStar Census Forecast Model Card\n\n"
        "## Intended use\nForecast the next 30 days of synthetic hospital census for staffing and capacity scenario planning.\n\n"
        "## Model\nRidge regression with hospital and weekday indicators, trend, annual Fourier terms, census lags (1, 7, 14, 28 days), and trailing 7/28-day means.\n\n"
        "## Validation\nSix rolling-origin folds with a 30-day recursive horizon. Random train/test splitting is not used. "
        f"Ridge MAE: {ridge_mae:.2f} beds; seasonal-naive MAE: {seasonal_mae:.2f}; improvement: {metrics['ridge_improvement_vs_seasonal_pct']:.1f}%.\n\n"
        "## Uncertainty\nA 90% split-conformal interval is calibrated on the latest held-out 30 days.\n\n"
        "## Limitations\nSynthetic portfolio data only. The model does not include acuity, scheduled procedures, closures, weather, outbreaks, or real staffing constraints. It is not patient-care decision support and requires external validation before operational use.\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
