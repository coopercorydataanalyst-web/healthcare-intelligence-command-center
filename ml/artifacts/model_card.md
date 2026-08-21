# GulfStar Census Forecast Model Card

## Intended use
Forecast the next 30 days of synthetic hospital census for staffing and capacity scenario planning.

## Model
Ridge regression with hospital and weekday indicators, trend, annual Fourier terms, census lags (1, 7, 14, 28 days), and trailing 7/28-day means.

## Validation
Six rolling-origin folds with a 30-day recursive horizon. Random train/test splitting is not used. Ridge MAE: 6.23 beds; seasonal-naive MAE: 8.48; improvement: 26.6%.

## Pre-registered selection rule
Adopt gradient boosting only if it reduces rolling-origin MAE by at least 5% versus Ridge. It did not, so Ridge remains selected.

## Uncertainty
A 90% conformal interval is calibrated separately for days 1–7, 8–21, and 22–30. Bucket and sequential coverage are reported in the artifacts.

## Explainability
Standardized Ridge coefficients are committed as an association artifact. They are associations within overlapping simulated measurement windows, not causal effects.

## Drift and maintenance
Monitor PSI on lagged census features. PSI at or above 0.20 triggers review and prospective error validation before retraining.

## Limitations
Synthetic portfolio data only. Error is nearly horizon-invariant because census was simulated around a slowly varying mean; this would not be expected to hold prospectively. The model does not include acuity, scheduled procedures, closures, weather, outbreaks, or real staffing constraints. It is not patient-care decision support and requires external validation before operational use.
