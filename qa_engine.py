"""Deterministic, read-only natural-language query layer for GulfStar data."""

from dataclasses import dataclass
import re

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    aliases: tuple[str, ...]
    calculation: str
    unit: str
    evidence: str = "Synthetic Result"
    better: str = "context"


METRICS = (
    Metric("readmission", "30-Day Readmission Rate", ("readmission", "readmit"), "readmission_30d encounters / selected encounters", "percent", better="low"),
    Metric("mortality", "Mortality Rate", ("mortality", "death rate"), "mean daily mortality_rate", "percent", better="low"),
    Metric("falls", "Falls", ("falls", "fall count"), "sum of daily falls", "count", better="low"),
    Metric("hai", "Healthcare-Associated Infections", ("hai", "infection", "healthcare associated infection"), "sum of daily HAI events", "count", better="low"),
    Metric("boarding", "ED Boarding", ("boarding", "ed boarding"), "mean daily boarding_hours", "hours", better="low"),
    Metric("ed_provider", "ED-to-Provider Time", ("ed to provider", "provider time", "door to provider"), "mean daily ed_to_provider_minutes", "minutes", better="low"),
    Metric("lwbs", "Left Without Being Seen", ("lwbs", "left without being seen"), "mean daily lwbs_rate", "percent", better="low"),
    Metric("bed_utilization", "Staffed-Bed Utilization", ("staffed bed utilization", "bed utilization", "occupancy"), "total census / total staffed beds", "percent", better="low"),
    Metric("available_beds", "Available Staffed Beds", ("available staffed beds", "available beds", "bed availability"), "mean daily staffed beds minus census", "count", better="high"),
    Metric("rn_vacancy", "RN Vacancy", ("rn vacancy", "nurse vacancy", "vacancy"), "mean daily rn_vacancy_rate", "percent", better="low"),
    Metric("agency_share", "Agency Labor Share", ("agency labor share", "agency share", "agency labor"), "total agency hours / total staff hours", "percent", better="low"),
    Metric("experience", "Patient Experience", ("patient experience", "experience score", "hcahps"), "mean synthetic patient_experience composite", "percent", better="high"),
    Metric("margin", "Operating Margin", ("operating margin", "margin"), "(total revenue - total cost) / total revenue", "percent", better="high"),
    Metric("denials", "Denial Exposure", ("denials", "denial exposure", "denied revenue"), "sum of daily denied dollars", "currency", better="low"),
    Metric("denial_rate", "Denial Rate", ("denial rate",), "total denied dollars / total revenue", "percent", better="low"),
    Metric("or_utilization", "OR Utilization", ("or utilization", "operating room utilization", "procedural utilization"), "mean daily or_utilization", "percent", better="high"),
    Metric("specialty_wait", "Access / Specialty Wait", ("specialty wait", "access wait", "wait days", "access"), "mean daily specialty_wait_days", "days", better="low"),
)


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _metrics_in(question):
    q = _norm(question)
    found = []
    for metric in METRICS:
        if any(_norm(alias) in q for alias in metric.aliases):
            found.append(metric)
    # Prefer the more specific denial-rate interpretation.
    if any(m.key == "denial_rate" for m in found):
        found = [m for m in found if m.key != "denials"]
    return found


def _value(metric, daily, encounters):
    if daily.empty:
        return np.nan
    if metric.key == "readmission":
        return encounters.readmission_30d.mean() if not encounters.empty else np.nan
    if metric.key == "mortality": return daily.mortality_rate.mean()
    if metric.key == "falls": return daily.falls.sum()
    if metric.key == "hai": return daily.hai.sum()
    if metric.key == "boarding": return daily.boarding_hours.mean()
    if metric.key == "ed_provider": return daily.ed_to_provider_minutes.mean()
    if metric.key == "lwbs": return daily.lwbs_rate.mean()
    if metric.key == "bed_utilization": return daily.census.sum() / max(daily.staffed_beds.sum(), 1)
    if metric.key == "available_beds":
        by_day = daily.groupby("date").agg(staffed=("staffed_beds", "sum"), census=("census", "sum"))
        return (by_day.staffed - by_day.census).mean()
    if metric.key == "rn_vacancy": return daily.rn_vacancy_rate.mean()
    if metric.key == "agency_share": return daily.agency_hours.sum() / max(daily.staff_hours.sum(), 1)
    if metric.key == "experience": return daily.patient_experience.mean()
    if metric.key == "margin": return (daily.revenue.sum() - daily.cost.sum()) / max(daily.revenue.sum(), 1)
    if metric.key == "denials": return daily.denials.sum()
    if metric.key == "denial_rate": return daily.denials.sum() / max(daily.revenue.sum(), 1)
    if metric.key == "or_utilization": return daily.or_utilization.mean()
    if metric.key == "specialty_wait": return daily.specialty_wait_days.mean()
    return np.nan


def _format(value, unit, signed=False):
    if pd.isna(value): return "not available"
    sign = "+" if signed and value > 0 else ""
    if unit == "percent": return f"{sign}{100 * value:.1f}%"
    if unit == "currency": return f"{sign}${value:,.0f}"
    if unit == "count": return f"{sign}{value:,.0f}"
    return f"{sign}{value:,.1f} {unit}"


def _hospital_from_question(question, hospitals):
    q = _norm(question)
    for hospital in sorted(hospitals, key=len, reverse=True):
        if _norm(hospital) in q:
            return hospital
    return None


def _display_comparison(frame, metrics):
    shown = frame.copy()
    for metric in metrics:
        if metric.label in shown:
            shown[metric.label] = shown[metric.label].map(lambda value: _format(value, metric.unit))
    return shown


def _response(answer, calculation, evidence="Synthetic Result", limitation=None, data=None):
    return {
        "answer": answer,
        "calculation": calculation,
        "evidence": evidence,
        "limitation": limitation or "Descriptive synthetic data only; this result does not establish cause or support patient-care decisions.",
        "data": data,
    }


def answer_question(question, daily, encounters, prior_daily, prior_encounters, interventions, priority, all_hospitals=None):
    """Answer only recognized, predefined aggregations over already-filtered frames."""
    q = _norm(question)
    if not q:
        return _response("Enter a question about a supported dashboard metric.", "No calculation run.", "Validation Required")

    hospitals = list(daily.hospital.dropna().unique())
    known_hospitals = list(all_hospitals) if all_hospitals is not None else hospitals
    requested_hospital = _hospital_from_question(question, known_hospitals)
    if requested_hospital and requested_hospital not in hospitals:
        return _response(f"{requested_hospital} is excluded by the current Hospital filter.", "No calculation run.", "Validation Required", "Add that hospital to the global filter or ask about one of the currently selected hospitals.")
    named_hospital = requested_hospital

    if any(term in q for term in ("intervention", "roi", "return on investment")):
        work = interventions.copy()
        work["net_value"] = work.annual_value - work.annual_cost
        work["roi"] = work.net_value / work.annual_cost.replace(0, np.nan)
        if work.empty:
            return _response("No intervention records are available.", "No calculation run.", "Modeled Estimate")
        ascending = any(word in q.split() for word in ("lowest", "least", "worst"))
        ranked = work.sort_values("roi", ascending=ascending)
        top = ranked.iloc[0]
        direction = "lowest" if ascending else "highest"
        answer = f"{top.intervention} has the {direction} modeled ROI at {top.roi:.2f}x, with modeled annual value {_format(top.annual_value, 'currency')} and annual cost {_format(top.annual_cost, 'currency')}."
        shown = ranked[["intervention", "domain", "annual_cost", "annual_value", "net_value", "roi", "capacity_days", "confidence"]].copy()
        return _response(answer, "ROI = (modeled annual value - annual cost) / annual cost; interventions are not changed by hospital, service-line, or date filters.", "Modeled Estimate", "Scenario inputs are illustrative and benefits are not guaranteed; validate costs, attribution, feasibility, and realized outcomes.", shown)

    if ("top priority" in q or "highest priority" in q or "modeled exposure" in q or "financial exposure" in q or ("why" in q and "priority" in q)):
        if priority.empty:
            return _response("No priority score is available for the current filters.", "No calculation run.", "Modeled Estimate")
        row = priority.iloc[0]
        exposure_only = ("modeled exposure" in q or "financial exposure" in q) and "priority" not in q
        if exposure_only:
            ascending = any(word in q.split() for word in ("lowest", "least"))
            row = priority.sort_values("modeled_exposure", ascending=ascending).iloc[0]
        if named_hospital:
            subset = priority[priority.hospital == named_hospital]
            if subset.empty:
                return _response(f"{named_hospital} is not available under the current filters.", "No calculation run.", "Validation Required")
            row = subset.iloc[0]
        if exposure_only:
            prefix = f"The {'lowest' if ascending else 'highest'} modeled-exposure item"
        else:
            prefix = f"{row.hospital}'s leading priority" if named_hospital else "The #1 filtered priority"
        if exposure_only:
            rationale = "It was selected by sorting the modeled exposure field only—not because the dashboard proved a cause."
            calculation = "Modeled priority exposure sorted by value; exposure formulas are the dashboard's illustrative domain scenarios."
        else:
            rationale = "It ranks first because its predefined severity score is highest, with modeled exposure used as the tie-breaker—not because the dashboard proved a cause."
            calculation = "Priority order = severity score descending, then modeled exposure descending. Domain scores use the dashboard's documented synthetic metric thresholds."
        answer = f"{prefix} at {row.hospital} is {row.domain} (severity {row.severity_score:.1f}/100; modeled exposure {_format(row.modeled_exposure, 'currency')}; owner {row.accountable_owner}). {rationale}"
        return _response(answer, calculation, "Modeled Estimate", "This is an illustrative portfolio ranking, not a clinical risk score, causal finding, or validated forecast.", priority.head(5))

    metrics = _metrics_in(question)
    if not metrics:
        return _response("I can answer hospital comparisons, highest/lowest values, current-period values, prior-period changes, intervention ROI, and the executive priority ranking for supported metrics.", "No calculation run because no supported metric or intent was identified.", "Validation Required", "Try: “Which hospital has the highest RN vacancy?”, “What changed in ED boarding over the last 90 days?”, or “Compare hospitals on operating margin and patient experience.”")

    # Last-N-day change stays inside the active date filter; otherwise use the dashboard's comparable prior frame.
    change_intent = any(term in q for term in ("change", "changed", "prior", "previous", "trend", "versus", "vs"))
    days_match = re.search(r"(?:last|past)\s+(\d+)\s+days?", q)
    if change_intent:
        metric = metrics[0]
        cur_daily, old_daily = daily, prior_daily
        cur_enc, old_enc = encounters, prior_encounters
        period_label = "selected period versus the immediately preceding equal-length period"
        if days_match and not daily.empty:
            requested = max(int(days_match.group(1)), 1)
            active_end = daily.date.max()
            cur_start = active_end - pd.Timedelta(days=requested - 1)
            old_end = cur_start - pd.Timedelta(days=1)
            old_start = old_end - pd.Timedelta(days=requested - 1)
            cur_daily = daily[daily.date.between(cur_start, active_end)]
            old_daily = daily[daily.date.between(old_start, old_end)]
            cur_enc = encounters[encounters.admit_date.between(cur_start, active_end)]
            old_enc = encounters[encounters.admit_date.between(old_start, old_end)]
            period_label = f"latest {requested} days versus the preceding {requested} days within the active filter"
        if named_hospital:
            cur_daily = cur_daily[cur_daily.hospital == named_hospital]
            old_daily = old_daily[old_daily.hospital == named_hospital]
            cur_enc = cur_enc[cur_enc.hospital == named_hospital]
            old_enc = old_enc[old_enc.hospital == named_hospital]
        cur = _value(metric, cur_daily, cur_enc)
        old = _value(metric, old_daily, old_enc)
        if pd.isna(cur) or pd.isna(old):
            return _response(f"A comparable prior value for {metric.label} is not available under the current filters.", f"Attempted {period_label} using {metric.calculation}.", "Validation Required", "Choose a shorter date range with enough preceding filtered data, or ask for the current-period value.")
        delta = cur - old
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "was unchanged"
        subject = named_hospital or "The selected hospitals"
        answer = f"{subject}: {metric.label} {direction} from {_format(old, metric.unit)} to {_format(cur, metric.unit)} (change {_format(delta, metric.unit, signed=True)})."
        return _response(answer, f"{period_label}; {metric.calculation}.")

    # Build a hospital comparison for one or more supported metrics.
    rows = []
    for hospital, hospital_daily in daily.groupby("hospital"):
        hospital_enc = encounters[encounters.hospital == hospital]
        row = {"Hospital": hospital}
        for metric in metrics:
            row[metric.label] = _value(metric, hospital_daily, hospital_enc)
        rows.append(row)
    comparison = pd.DataFrame(rows)
    if comparison.empty:
        return _response("No rows are available under the current filters.", "No calculation run.", "Validation Required")

    if named_hospital:
        comparison = comparison[comparison.Hospital == named_hospital]
        if comparison.empty:
            return _response(f"{named_hospital} is not available under the current filters.", "No calculation run.", "Validation Required")

    metric = metrics[0]
    words = set(q.split())
    high = any(word in words for word in ("highest", "most", "maximum", "max"))
    low = any(word in words for word in ("lowest", "least", "minimum", "min"))
    if "best" in words:
        high, low = metric.better == "high", metric.better == "low"
    elif "worst" in words:
        high, low = metric.better == "low", metric.better == "high"
    if high or low:
        ascending = low
        ranked = comparison.sort_values(metric.label, ascending=ascending)
        row = ranked.iloc[0]
        direction = "lowest" if low else "highest"
        answer = f"{row.Hospital} has the {direction} {metric.label} at {_format(row[metric.label], metric.unit)} under the current filters."
        return _response(answer, f"Hospital-level {metric.calculation}; ranked {'ascending' if low else 'descending'}.", data=_display_comparison(ranked, metrics))

    if named_hospital and len(metrics) == 1:
        row = comparison.iloc[0]
        answer = f"{named_hospital}'s current-period {metric.label} is {_format(row[metric.label], metric.unit)}."
    else:
        labels = ", ".join(m.label for m in metrics)
        answer = f"Here is the current filtered hospital comparison for {labels}."
    calculations = "; ".join(f"{m.label}: {m.calculation}" for m in metrics)
    return _response(answer, calculations, data=_display_comparison(comparison, metrics))
