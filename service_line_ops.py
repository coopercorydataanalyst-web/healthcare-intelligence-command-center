"""Deterministic service-line allocation for synthetic hospital-day operations.

The source daily table is hospital-day grain. This layer allocates its totals to
service lines, preserves exact hospital-day totals when all lines are selected,
and rolls selected lines back to hospital-day grain for the dashboard.
"""

import numpy as np
import pandas as pd


SERVICE_WEIGHTS = {
    "Heart Failure": .18,
    "Sepsis": .16,
    "COPD": .17,
    "Diabetes": .19,
    "Joint Replacement": .18,
    "Maternal Care": .12,
}

FACTORS = {
    "Heart Failure": dict(demand=1.10, acuity=1.16, flow=1.12, workforce=1.08, experience=.97, procedural=.45, revenue=1.08, cost=1.12, denial=1.03),
    "Sepsis": dict(demand=.88, acuity=1.34, flow=1.20, workforce=1.16, experience=.94, procedural=.25, revenue=1.20, cost=1.29, denial=1.00),
    "COPD": dict(demand=1.08, acuity=1.12, flow=1.15, workforce=1.08, experience=.96, procedural=.20, revenue=.92, cost=.98, denial=1.08),
    "Diabetes": dict(demand=1.12, acuity=.94, flow=1.02, workforce=.98, experience=.99, procedural=.30, revenue=.86, cost=.88, denial=1.12),
    "Joint Replacement": dict(demand=.92, acuity=.78, flow=.78, workforce=.90, experience=1.07, procedural=2.85, revenue=1.28, cost=1.10, denial=.94),
    "Maternal Care": dict(demand=.98, acuity=.70, flow=.82, workforce=.94, experience=1.08, procedural=.55, revenue=1.05, cost=.91, denial=.88),
}

CAPACITY = ("licensed_beds", "staffed_beds")
DEMAND = ("admissions", "ed_arrivals", "discharges", "expected_discharges", "pending_admissions")
ACUITY = ("census", "falls", "hai", "privacy_events")
WORK = ("staff_hours",)
VARIABLE_LABOR = ("overtime_hours", "agency_hours")
PROCEDURAL = ("or_cases",)
FINANCE_FACTORS = {"revenue": "revenue", "cost": "cost", "denials": "denial"}
RATE_FACTORS = {
    "boarding_hours": "flow", "ed_to_provider_minutes": "flow",
    "discharge_order_to_exit_hours": "flow", "lwbs_rate": "flow",
    "readmission_rate": "acuity", "mortality_rate": "acuity",
    "rn_vacancy_rate": "workforce", "patient_experience": "experience",
    "or_utilization": "procedural", "specialty_wait_days": "flow",
}


def _shares(factor=None):
    raw = {
        service: weight * (FACTORS[service][factor] if factor else 1.0)
        for service, weight in SERVICE_WEIGHTS.items()
    }
    total = sum(raw.values())
    return {service: value / total for service, value in raw.items()}


def _work_pressure_shares(power):
    raw = {
        service: weight * FACTORS[service]["workforce"] ** power
        for service, weight in SERVICE_WEIGHTS.items()
    }
    total = sum(raw.values())
    return {service: value / total for service, value in raw.items()}


def allocate_service_lines(daily):
    """Expand hospital-day operations to deterministic service-line components."""
    frames = []
    base_rate_means = {
        factor: sum(SERVICE_WEIGHTS[s] * FACTORS[s][factor] for s in SERVICE_WEIGHTS)
        for factor in set(RATE_FACTORS.values())
    }
    shares = {
        "base": _shares(), "demand": _shares("demand"), "acuity": _shares("acuity"),
        "workforce": _shares("workforce"), "procedural": _shares("procedural"),
        "overtime": _work_pressure_shares(1.55), "agency": _work_pressure_shares(2.15),
        "revenue": _shares("revenue"), "cost": _shares("cost"), "denial": _shares("denial"),
    }
    for service, weight in SERVICE_WEIGHTS.items():
        part = daily.copy()
        part["service_line"] = service
        part["service_weight"] = weight
        for col in CAPACITY:
            part[col] = daily[col] * shares["base"][service]
        for col in DEMAND:
            part[col] = daily[col] * shares["demand"][service]
        for col in ACUITY:
            part[col] = daily[col] * shares["acuity"][service]
        for col in WORK:
            part[col] = daily[col] * shares["workforce"][service]
        part["overtime_hours"] = daily["overtime_hours"] * shares["overtime"][service]
        part["agency_hours"] = daily["agency_hours"] * shares["agency"][service]
        for col in PROCEDURAL:
            part[col] = daily[col] * shares["procedural"][service]
        for col, factor in FINANCE_FACTORS.items():
            part[col] = daily[col] * shares[factor][service]
        for col, factor in RATE_FACTORS.items():
            part[col] = daily[col] * FACTORS[service][factor] / base_rate_means[factor]
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def rollup_selected_service_lines(allocated, services):
    """Return selected service-line operations at the app's hospital-day grain."""
    selected = allocated[allocated.service_line.isin(services)].copy()
    if selected.empty:
        return selected.drop(columns=["service_line", "service_weight"], errors="ignore")
    keys = ["date", "hospital"]
    additive = list(CAPACITY + DEMAND + ACUITY + WORK + VARIABLE_LABOR + PROCEDURAL) + list(FINANCE_FACTORS)
    rows = []
    for key, group in selected.groupby(keys, sort=False):
        row = {"date": key[0], "hospital": key[1]}
        for col in additive:
            row[col] = group[col].sum()
        weights = group.service_weight.to_numpy()
        for col in RATE_FACTORS:
            row[col] = np.average(group[col], weights=weights)
        rows.append(row)
    return pd.DataFrame(rows)


def service_filter_is_complete(services):
    return set(services) == set(SERVICE_WEIGHTS)
