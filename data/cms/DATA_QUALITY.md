# CMS Hospital Feature Table — Data Quality Assessment

## Dataset and grain

The committed feature table contains 2,620 unique six-character CMS facility IDs at one row per hospital. Inclusion requires at least two reportable HRRP condition ratios. The target is whether the hospital's mean reportable excess readmission ratio exceeds 1.0; prevalence is 50.9%.

## Checks performed

- Exact row-count and facility-ID uniqueness
- Six-character identifier preservation, including leading zeroes
- Pagination reconciliation against every CMS API count
- Source and feature-table SHA-256 verification
- Required-column and model feature-contract validation
- Target leakage exclusion
- Missingness and subgroup coverage review
- State isolation across grouped validation folds
- Probability bounds, calibration, and baseline comparison

## Findings

- No duplicate facility IDs or missing ownership values were found.
- Each HCAHPS star feature is unavailable for 4.05% of included hospitals; training uses median imputation inside each fold.
- The birthing-friendly field is unavailable for 25.0% of hospitals; categorical imputation occurs inside each fold.
- The model's worst audited reporting-breadth slice is hospitals with two reportable HRRP conditions (235 hospitals; Brier 0.2556).
- The highest ownership-slice Brier score is 0.2499 for Government–Local hospitals (122 hospitals).
- The 106 hospitals without a summary HCAHPS star have Brier 0.2486.

## Material analytical limitation

The published HRRP outcome window ends before the current HCAHPS measurement window. This prevents prospective or causal interpretation. The model is safe only as a cross-sectional public-data benchmarking demonstration. It must not be described as forecasting future hospital readmission performance.

## Unavailable audits

The selected official feature contract does not contain defensible bed-size, SVI, or safety-net designations. These subgroups are reported as unavailable rather than inferred from ZIP code, ownership, or hospital type.

## Automated controls

`test_cms_model.py` enforces source hashes, feature-table grain, identifier formatting, target balance, leakage exclusions, grouped-state isolation, calibration outputs, subgroup coverage, and the serving feature contract.
