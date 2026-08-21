# CMS Hospital Readmission-Performance Classifier Model Card

## Intended use
Portfolio benchmarking: estimate whether a hospital's mean reportable HRRP excess readmission ratio is above 1.0 from published structural and HCAHPS attributes.

## Out-of-scope use
No patient-level prediction, payment decision, hospital ranking for contracting, or patient-care use. This is cross-sectional association modeling—not a prospective causal model.

## Data and timing
Official CMS Provider Data Catalog sources retrieved by `etl/fetch_cms.py`. HRRP outcomes cover an earlier measurement window than the current HCAHPS snapshot; therefore the model must not be represented as forecasting future readmissions.

## Evaluation
Five grouped-by-state outer folds, nested grouped isotonic calibration, an otherwise-identical five-fold stratified comparison, Brier score, AUC with bootstrap intervals, reliability table, and subgroup audit. State grouping did not reduce AUC materially; the overlapping intervals indicate that the small difference is consistent with fold-composition noise and that state is a weak clustering boundary for this target.

## Calibration finding
Isotonic calibration did not improve Brier score at displayed precision and slightly reduced AUC. The raw model was already reasonably calibrated, so calibrated probabilities are retained for transparency rather than claimed as a performance improvement.

## Explanations
Committed standardized logistic coefficients are associations from overlapping or differently timed public measurement windows, not causal effects.

## Maintenance
Refresh only after CMS source-version review, rerun grouped validation and calibration, compare subgroup performance, and approve the new manifest and hashes.
