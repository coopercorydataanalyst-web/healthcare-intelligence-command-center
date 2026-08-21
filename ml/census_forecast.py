"""Deterministic census-forecast feature engineering and recursive prediction."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


LAGS = (1, 7, 14, 28)


def hospital_day_census(daily: pd.DataFrame) -> pd.DataFrame:
    """Return one validated census observation per hospital and calendar day."""
    required = {"date", "hospital", "census"}
    missing = required - set(daily.columns)
    if missing:
        raise ValueError(f"Missing census columns: {sorted(missing)}")
    frame = daily.loc[:, ["date", "hospital", "census"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["census"] = pd.to_numeric(frame["census"], errors="raise")
    if frame.duplicated(["date", "hospital"]).any():
        raise ValueError("Census training data must have one row per hospital-day.")
    return frame.sort_values(["date", "hospital"]).reset_index(drop=True)


def _date_features(date: pd.Timestamp) -> dict[str, float]:
    day_of_year = date.dayofyear
    return {
        "day_of_week": int(date.dayofweek),
        "trend_day": int((date - pd.Timestamp("2025-01-01")).days),
        "annual_sin": np.sin(2 * np.pi * day_of_year / 365.25),
        "annual_cos": np.cos(2 * np.pi * day_of_year / 365.25),
    }


def supervised_rows(census: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Create leakage-safe rows whose features use only earlier census values."""
    rows, targets = [], []
    for hospital, group in census.groupby("hospital", sort=True):
        history = group.set_index("date").census.sort_index()
        for date, target in history.items():
            prior = history.loc[history.index < date]
            if len(prior) < max(LAGS):
                continue
            row = {"hospital": hospital, **_date_features(date)}
            row.update({f"lag_{lag}": float(prior.iloc[-lag]) for lag in LAGS})
            row["rolling_7"] = float(prior.tail(7).mean())
            row["rolling_28"] = float(prior.tail(28).mean())
            rows.append(row)
            targets.append(float(target))
    return pd.DataFrame(rows), pd.Series(targets, name="census")


def recursive_forecast(model, history: pd.DataFrame, forecast_dates) -> pd.DataFrame:
    """Forecast each hospital recursively without using future observed census."""
    history = hospital_day_census(history)
    values = defaultdict(dict)
    hospitals = sorted(history.hospital.unique())
    for row in history.itertuples(index=False):
        values[row.hospital][pd.Timestamp(row.date)] = float(row.census)
    output = []
    for date in pd.DatetimeIndex(forecast_dates).sort_values():
        feature_rows = []
        for hospital in hospitals:
            prior_values = pd.Series(values[hospital], dtype=float).sort_index()
            row = {"hospital": hospital, **_date_features(date)}
            row.update({f"lag_{lag}": float(prior_values.iloc[-lag]) for lag in LAGS})
            row["rolling_7"] = float(prior_values.tail(7).mean())
            row["rolling_28"] = float(prior_values.tail(28).mean())
            feature_rows.append(row)
        predictions = np.asarray(model.predict(pd.DataFrame(feature_rows)), dtype=float)
        for hospital, prediction in zip(hospitals, predictions):
            prediction = max(float(prediction), 0.0)
            values[hospital][date] = prediction
            output.append({"date": date, "hospital": hospital, "predicted_census": prediction})
    return pd.DataFrame(output)


def load_forecast_artifacts(root: Path):
    artifact_dir = Path(root) / "ml" / "artifacts"
    return (
        joblib.load(artifact_dir / "census_ridge.joblib"),
        json.loads((artifact_dir / "backtest_metrics.json").read_text()),
        pd.read_csv(artifact_dir / "forecast_30d.csv", parse_dates=["date"]),
    )
