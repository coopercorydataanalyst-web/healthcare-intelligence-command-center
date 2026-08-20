from pathlib import Path

import numpy as np
import pandas as pd

from service_line_ops import (
    RATE_FACTORS,
    SERVICE_WEIGHTS,
    allocate_service_lines,
    rollup_selected_service_lines,
)


ROOT = Path(__file__).resolve().parent
daily = pd.read_csv(ROOT / "data/daily_operations.csv.gz", parse_dates=["date"])
allocated = allocate_service_lines(daily)


def test_all_service_lines_reconcile_to_original_hospital_day_operations():
    rolled = rollup_selected_service_lines(allocated, list(SERVICE_WEIGHTS)).sort_values(["date", "hospital"]).reset_index(drop=True)
    original = daily.sort_values(["date", "hospital"]).reset_index(drop=True)
    for column in original.columns:
        if column in {"date", "hospital"}:
            assert rolled[column].equals(original[column])
        else:
            assert np.allclose(rolled[column], original[column], rtol=1e-10, atol=1e-10), column


def test_service_line_subset_changes_operations_and_financial_kpis():
    all_lines = rollup_selected_service_lines(allocated, list(SERVICE_WEIGHTS))
    copd = rollup_selected_service_lines(allocated, ["COPD"])
    assert not np.isclose(copd.boarding_hours.mean(), all_lines.boarding_hours.mean())
    assert not np.isclose(copd.patient_experience.mean(), all_lines.patient_experience.mean())
    assert not np.isclose(copd.census.sum() / copd.staffed_beds.sum(), all_lines.census.sum() / all_lines.staffed_beds.sum())
    copd_margin = (copd.revenue.sum() - copd.cost.sum()) / copd.revenue.sum()
    all_margin = (all_lines.revenue.sum() - all_lines.cost.sum()) / all_lines.revenue.sum()
    assert not np.isclose(copd_margin, all_margin)


def test_each_service_line_produces_complete_hospital_day_rows():
    for service in SERVICE_WEIGHTS:
        rolled = rollup_selected_service_lines(allocated, [service])
        assert len(rolled) == len(daily)
        assert not rolled[list(RATE_FACTORS)].isna().any().any()
