# GulfStar Census Forecast Model Card

## Intended use
Forecast the next 30 days of synthetic hospital census for staffing and capacity scenario planning.

## Model
Ridge regression with hospital and weekday indicators, trend, annual Fourier terms, census lags (1, 7, 14, 28 days), and trailing 7/28-day means.

## Validation
Six rolling-origin folds with a 30-day recursive horizon. Random train/test splitting is not used. Ridge MAE: 6.23 beds; seasonal-naive MAE: 8.48; improvement: 26.6%.

## Uncertainty
A 90% split-conformal interval is calibrated on the latest held-out 30 days.

## Limitations
Synthetic portfolio data only. The model does not include acuity, scheduled procedures, closures, weather, outbreaks, or real staffing constraints. It is not patient-care decision support and requires external validation before operational use.
