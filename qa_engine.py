"""Deterministic, read-only natural-language query layer for GulfStar data."""

from dataclasses import dataclass
import re

import numpy as np
import pandas as pd

from language_utils import closest_suggestions, extracted_keywords, flexible_tokens


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
    Metric("deterioration", "Deterioration Rate", ("deterioration", "deterioration rate"), "deterioration encounters / selected encounters", "percent", better="low"),
    Metric("harm", "Harm Rate", ("harm", "harm rate", "composite harm"), "harm encounters / selected encounters", "percent", better="low"),
    Metric("followup", "Follow-Up Booked", ("follow up", "followup", "follow-up booked"), "encounters with follow-up booked / selected encounters", "percent", better="high"),
    Metric("los", "Length of Stay", ("length of stay", "los"), "mean synthetic encounter length of stay", "days", better="low"),
    Metric("discharge_delay", "Discharge-Order-to-Exit Time", ("discharge delay", "discharge order to exit", "order to exit"), "mean daily discharge_order_to_exit_hours", "hours", better="low"),
    Metric("pending_admissions", "Pending Admissions", ("pending admissions", "admission queue"), "mean daily pending_admissions", "count", better="low"),
    Metric("expected_discharges", "Expected Discharges", ("expected discharges",), "mean daily expected_discharges", "count", better="context"),
    Metric("licensed_beds", "Licensed Beds", ("licensed beds", "licensed capacity"), "mean daily licensed_beds", "count", better="context"),
    Metric("staffed_beds", "Staffed Beds", ("staffed beds", "staffed capacity"), "mean daily staffed_beds", "count", better="context"),
    Metric("census", "Average Census", ("average census", "census", "occupied beds"), "mean daily census", "count", better="context"),
    Metric("overtime_share", "Overtime Labor Share", ("overtime share", "overtime labor", "overtime"), "total overtime hours / total productive staff hours", "percent", better="low"),
    Metric("hppd", "Hours per Patient Day", ("hours per patient day", "hppd", "staffing intensity"), "total productive staff hours / total census patient-days", "number", better="context"),
    Metric("or_cases", "OR Case Volume", ("or cases", "case volume", "procedural volume"), "sum of daily OR cases", "count", better="context"),
    Metric("contribution", "Encounter Contribution", ("contribution", "operating contribution"), "sum of synthetic encounter revenue minus cost", "currency", better="high"),
)

MAIN_SUGGESTIONS = (
    "Tell me about this dashboard.",
    "What can I ask?",
    "What has improved in the last 30 days?",
    "What got worse in the last 30 days?",
    "Give me the executive summary.",
    "What should leadership focus on?",
    "Which hospital has the highest readmission rate?",
    "Which hospital has the highest mortality rate?",
    "Which hospital has the most falls?",
    "Which hospital has the most HAI events?",
    "What changed in ED boarding over the last 90 days?",
    "Compare hospitals on ED-to-provider time.",
    "Which hospital has the highest LWBS rate?",
    "Compare hospitals on staffed-bed utilization and available staffed beds.",
    "Which hospital has the highest workforce RN vacancy?",
    "Compare hospitals on workforce agency labor share.",
    "Compare hospitals on patient experience.",
    "Compare hospitals on operating margin and denial rate.",
    "Compare hospitals on OR utilization.",
    "Which hospital has the longest specialty wait?",
    "Which intervention has the highest modeled ROI?",
    "What is the top executive priority?",
    "Which priority has the highest modeled exposure?",
)


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _metrics_in(question):
    q = _norm(question)
    question_tokens = flexible_tokens(question)
    found = []
    for metric in METRICS:
        if any(
            re.search(rf"\b{re.escape(_norm(alias))}\b", q)
            or (len(_norm(alias)) >= 4 and flexible_tokens(alias).issubset(question_tokens))
            for alias in metric.aliases
        ):
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
    if metric.key == "deterioration": return encounters.deterioration.mean() if not encounters.empty else np.nan
    if metric.key == "harm": return encounters.harm.mean() if not encounters.empty else np.nan
    if metric.key == "followup": return encounters.followup_booked.mean() if not encounters.empty else np.nan
    if metric.key == "los": return encounters.los.mean() if not encounters.empty else np.nan
    if metric.key == "discharge_delay": return daily.discharge_order_to_exit_hours.mean()
    if metric.key == "pending_admissions": return daily.pending_admissions.mean()
    if metric.key == "expected_discharges": return daily.expected_discharges.mean()
    if metric.key == "licensed_beds": return daily.licensed_beds.mean()
    if metric.key == "staffed_beds": return daily.staffed_beds.mean()
    if metric.key == "census": return daily.census.mean()
    if metric.key == "overtime_share": return daily.overtime_hours.sum() / max(daily.staff_hours.sum(), 1)
    if metric.key == "hppd": return daily.staff_hours.sum() / max(daily.census.sum(), 1)
    if metric.key == "or_cases": return daily.or_cases.sum()
    if metric.key == "contribution": return (encounters.revenue - encounters.cost).sum() if not encounters.empty else np.nan
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


def _response(answer, calculation, evidence="Synthetic Result", limitation=None, data=None, suggestions=None, keywords=None):
    return {
        "answer": answer,
        "calculation": calculation,
        "evidence": evidence,
        "limitation": limitation or "Descriptive synthetic data only; this result does not establish cause or support patient-care decisions.",
        "data": data,
        "suggestions": suggestions or [],
        "keywords": keywords or [],
    }


def _summary_intent(question):
    q = _norm(question)
    tokens = flexible_tokens(question)
    # Executive questions are intentionally tolerant of conversational grammar
    # and common tense variants (for example, "has happen positively").
    positive_patterns = (
        r"\bwhat\s+(?:has\s+|have\s+|is\s+|was\s+)?happen(?:ed|s|ing)?\s+positively\b",
        r"\bwhat\s+(?:has\s+|have\s+)?improv(?:e|ed|es|ing)\b",
        r"\bwhat\s+(?:has\s+|have\s+)?got(?:ten)?\s+better\b",
        r"\bwhere\s+(?:are|have)\s+we\s+improv(?:e|ed|ing)\b",
    )
    negative_patterns = (
        r"\bwhat\s+(?:has\s+|have\s+)?got(?:ten)?\s+worse\b",
        r"\bwhat\s+(?:has\s+|have\s+)?worsen(?:ed|s|ing)?\b",
        r"\bwhat\s+(?:has\s+|have\s+)?declin(?:e|ed|es|ing)\b",
        r"\bwhere\s+(?:is|are|have)\s+(?:performance|we)\s+declin(?:e|ed|ing)\b",
    )
    positive = (
        "what improved", "what got better", "happened positively", "changed positively",
        "good news", "our wins", "what are the wins", "where are we improving",
        "leadership celebrate", "should we celebrate",
    )
    negative = (
        "what got worse", "what worsened", "what declined", "performance declining",
        "where are we declining", "leadership know about", "what are the concerns",
        "concerns should", "bad news",
    )
    executive = (
        "executive summary", "summarize performance", "summary of performance",
        "what should the ceo know", "what should leadership know", "what should i know",
    )
    trend = (
        "what changed this month", "what has changed this month", "trend summary",
        "summarize trends", "how are we trending", "what changed recently",
    )
    asks_for_action = bool(tokens & {"how", "can", "could", "should", "do", "action", "fix", "recommend"}) and "improve" in tokens
    positive_language = bool(tokens & {"good", "positive", "better", "improve", "improved", "win", "strength", "celebrate", "well"})
    negative_language = bool(tokens & {"bad", "negative", "worse", "decline", "concern", "risk", "problem", "weakness", "issue", "downside", "redflag", "flag"}) or {"not", "working"}.issubset(tokens)
    if not asks_for_action and (any(re.search(pattern, q) for pattern in positive_patterns) or any(phrase in q for phrase in positive) or positive_language): return "positive_change"
    if any(re.search(pattern, q) for pattern in negative_patterns) or any(phrase in q for phrase in negative) or negative_language: return "negative_change"
    if any(phrase in q for phrase in executive): return "executive_summary"
    if any(phrase in q for phrase in trend): return "trend_summary"
    return None


def _dashboard_overview_intent(question):
    q = _norm(question)
    patterns = (
        r"\btell me (?:more )?about (?:this|the) dashboard\b",
        r"\bwhat is (?:this|the) dashboard\b",
        r"\bwhat does (?:this|the) dashboard do\b",
        r"\bexplain (?:this|the) dashboard\b",
        r"\b(?:give me|show me) (?:an? )?(?:dashboard )?overview\b",
        r"\bhelp me understand (?:this|the) dashboard\b",
        r"\bwhat can (?:i|we) ask\b",
        r"\bhow (?:does|do) (?:this|the) dashboard work\b",
    )
    return any(re.search(pattern, q) for pattern in patterns)


def _dashboard_overview(daily, encounters):
    hospital_count = daily.hospital.nunique() if not daily.empty else 0
    service_count = encounters.service_line.nunique() if not encounters.empty else 0
    if not daily.empty:
        scope = f"The active filters currently cover {hospital_count} hospital(s) from {daily.date.min():%b %d, %Y} through {daily.date.max():%b %d, %Y}"
        if service_count:
            scope += f" and {service_count} selected encounter service line(s)"
        scope += "."
    else:
        scope = "The current filters contain no operational rows."
    answer = (
        "GulfStar Intelligence is a 16-sheet executive healthcare analytics dashboard for a fictional three-hospital system. "
        "It connects clinical quality, patient flow and staffed capacity, workforce, access, patient experience, margin and denials, "
        "OR utilization, equity, privacy, quality improvement, modeled intervention ROI, and validated census forecasting. Its Ask GulfStar page uses a deterministic "
        "local query layer—not a generative LLM—so it answers only supported questions with predefined calculations and refuses to guess. "
        + scope
    )
    coverage = pd.DataFrame([
        ["Executive command", "Health-system scorecard, changes, priorities, ownership, and modeled exposure"],
        ["Operations", "Patient flow, capacity, ED access, workforce, OR utilization, and patient experience"],
        ["Clinical quality", "Readmission, mortality, falls, HAI, deterioration, harm, and improvement reliability"],
        ["Finance and portfolio", "Operating margin, denials, access leakage, and modeled intervention ROI"],
        ["Governance", "Methods, source lineage, privacy, ethics, evidence confidence, and validation gates"],
        ["Natural-language Q&A", "Safe comparisons, rankings, trends, executive summaries, priorities, ROI, and overview/help"],
    ], columns=["Dashboard Area", "What It Covers"])
    return _response(
        answer,
        "Dashboard configuration summary; no performance metric aggregation was run for this overview question.",
        "Validation Required — Dashboard Documentation",
        "All hospitals, people, and operational results are fictional and synthetic. Public sources provide definitions and context only. The dashboard is not patient-care, legal, privacy, or financial decision support.",
        coverage,
    )


def _summary_horizon(question, daily):
    match = re.search(r"(?:last|past)\s+(\d+)\s+days?", _norm(question))
    requested = max(int(match.group(1)), 1) if match else 30
    if daily.empty:
        return requested, daily, daily, pd.DataFrame(), pd.DataFrame()
    active_end = daily.date.max()
    current_start = active_end - pd.Timedelta(days=requested - 1)
    prior_end = current_start - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=requested - 1)
    return (
        requested,
        daily[daily.date.between(current_start, active_end)],
        daily[daily.date.between(prior_start, prior_end)],
        (current_start, active_end),
        (prior_start, prior_end),
    )


def _trend_delta_display(delta, unit):
    if unit == "percent": return f"{100 * delta:+.1f} percentage points"
    if unit == "currency": return f"{delta:+,.0f} dollars"
    if unit == "count": return f"{delta:+,.0f} events"
    return f"{delta:+.1f} {unit}"


def _movement_is_visible(delta, unit):
    display_delta = 100 * delta if unit == "percent" else delta
    return f"{abs(display_delta):.1f}" != "0.0"


def _executive_trends(question, intent, daily, encounters, priority):
    days, current_daily, prior_daily, current_dates, prior_dates = _summary_horizon(question, daily)
    if current_daily.empty or prior_daily.empty:
        return _response(
            f"A {days}-day executive trend summary is not available under the current date filter because two complete comparison windows are required.",
            f"Attempted latest {days} filtered days versus the preceding {days} filtered days.",
            "Validation Required",
            "Expand the reporting range to at least two complete windows or ask for a current-period metric.",
        )
    cur_start, cur_end = current_dates
    old_start, old_end = prior_dates
    current_enc = encounters[encounters.admit_date.between(cur_start, cur_end)]
    prior_enc = encounters[encounters.admit_date.between(old_start, old_end)]
    rows = []
    for metric in METRICS:
        current = _value(metric, current_daily, current_enc)
        prior = _value(metric, prior_daily, prior_enc)
        if pd.isna(current) or pd.isna(prior):
            continue
        delta = current - prior
        if not _movement_is_visible(delta, metric.unit):
            direction = "Stable"
        elif metric.better == "high":
            direction = "Improved" if delta > 0 else "Worsened"
        elif metric.better == "low":
            direction = "Improved" if delta < 0 else "Worsened"
        else:
            direction = "Changed"
        # Rank unlike units by proportional movement, never by raw dollars,
        # counts, hours, or percentage points against one another.
        magnitude = abs(delta) / max(abs(prior), 1e-9)
        rows.append({
            "Metric": metric.label,
            "Current": _format(current, metric.unit),
            "Prior": _format(prior, metric.unit),
            "Change": _trend_delta_display(delta, metric.unit),
            "Direction": direction,
            "_magnitude": magnitude,
            "Calculation": metric.calculation,
        })
    movements = pd.DataFrame(rows)
    if movements.empty:
        return _response("No comparable executive metrics are available for the requested windows.", f"Latest {days} filtered days versus the preceding {days} filtered days.", "Validation Required")
    improved = movements[movements.Direction == "Improved"].sort_values("_magnitude", ascending=False)
    worsened = movements[movements.Direction == "Worsened"].sort_values("_magnitude", ascending=False)
    stable = movements[movements.Direction == "Stable"]

    def describe(frame, limit=3):
        return "; ".join(
            f"{row.Metric} ({row.Prior} → {row.Current}; {row.Change})"
            for row in frame.head(limit).itertuples()
        )

    if intent == "positive_change":
        answer = f"Positive changes in the latest {days} days: {describe(improved)}." if not improved.empty else f"No supported metric improved beyond displayed reporting precision in the latest {days} days."
        shown = improved
    elif intent == "negative_change":
        answer = f"Negative changes in the latest {days} days: {describe(worsened)}." if not worsened.empty else f"No supported metric worsened beyond displayed reporting precision in the latest {days} days."
        shown = worsened
    else:
        parts = []
        if not improved.empty: parts.append("Leading improvements: " + describe(improved, 2))
        if not worsened.empty: parts.append("Leading concerns: " + describe(worsened, 2))
        if stable.shape[0]: parts.append(f"{len(stable)} supported metrics were stable at displayed precision")
        if intent == "executive_summary" and not priority.empty:
            top = priority.iloc[0]
            parts.append(f"#1 modeled portfolio priority: {top.domain} at {top.hospital} (severity {top.severity_score:.1f}/100)")
        answer = f"Executive trend summary for the latest {days} days. " + ". ".join(parts) + "."
        shown = pd.concat([improved.head(3), worsened.head(3), stable.head(3)])
    shown = shown.drop(columns=["_magnitude"], errors="ignore")
    evidence = "Synthetic Result / Modeled Estimate" if intent == "executive_summary" and not priority.empty else "Synthetic Result"
    return _response(
        answer,
        f"Each metric compares the latest {days} days ({cur_start:%b %d}–{cur_end:%b %d, %Y}) with the preceding {days} days ({old_start:%b %d}–{old_end:%b %d, %Y}); direction uses the documented higher/lower-is-better rule, stable values use displayed precision, and movements across unlike units are ranked by proportional change.",
        evidence,
        "These are descriptive synthetic movements and an illustrative portfolio signal. They do not establish why performance changed; operational validation is required before attribution or action.",
        shown,
    )


def answer_question(question, daily, encounters, prior_daily, prior_encounters, interventions, priority, all_hospitals=None):
    """Answer only recognized, predefined aggregations over already-filtered frames."""
    q = _norm(question)
    if not q:
        return _response("Enter a question about a supported dashboard metric.", "No calculation run.", "Validation Required")

    if _dashboard_overview_intent(question):
        return _dashboard_overview(daily, encounters)

    hospitals = list(daily.hospital.dropna().unique())
    known_hospitals = list(all_hospitals) if all_hospitals is not None else hospitals
    requested_hospital = _hospital_from_question(question, known_hospitals)
    if requested_hospital and requested_hospital not in hospitals:
        return _response(f"{requested_hospital} is excluded by the current Hospital filter.", "No calculation run.", "Validation Required", "Add that hospital to the global filter or ask about one of the currently selected hospitals.")
    named_hospital = requested_hospital

    metrics = _metrics_in(question)
    executive_intent = _summary_intent(question)
    if executive_intent and not metrics:
        return _executive_trends(question, executive_intent, daily, encounters, priority)

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

    priority_intent = bool(re.search(r"\b(?:top|highest)(?: executive)? priority\b", q))
    if (priority_intent or "modeled exposure" in q or "financial exposure" in q or ("why" in q and "priority" in q)):
        if priority.empty:
            return _response("No priority score is available for the current filters.", "No calculation run.", "Modeled Estimate")
        row = priority.iloc[0]
        exposure_only = "modeled exposure" in q or "financial exposure" in q
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
        shown = priority.sort_values("modeled_exposure", ascending=ascending).head(5) if exposure_only else priority.head(5)
        return _response(answer, calculation, "Modeled Estimate", "This is an illustrative portfolio ranking, not a clinical risk score, causal finding, or validated forecast.", shown)

    if not metrics:
        keywords = extracted_keywords(question)
        suggestions = closest_suggestions(question, MAIN_SUGGESTIONS)
        keyword_text = ", ".join(keywords) if keywords else "no clear supported keywords"
        return _response(
            f"I’m not certain which supported question you intended. I extracted: {keyword_text}. Select the closest safe match below rather than having the dashboard guess.",
            "No calculation run because no supported metric or intent was identified.",
            "Validation Required",
            "Suggestions are similarity-ranked from an allowlist. Review the wording before running one; the dashboard will not infer an unsupported metric or causal claim.",
            suggestions=suggestions,
            keywords=keywords,
        )

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
    high = any(word in words for word in ("highest", "most", "maximum", "max", "longest"))
    low = any(word in words for word in ("lowest", "least", "minimum", "min", "shortest"))
    if "best" in words:
        high, low = metric.better == "high", metric.better == "low"
    elif "worst" in words:
        high, low = metric.better == "low", metric.better == "high"
    if high or low:
        ascending = low
        ranked = comparison.sort_values(metric.label, ascending=ascending)
        row = ranked.iloc[0]
        direction = "lowest" if low else "highest"
        winning_display = _format(row[metric.label], metric.unit)
        tied = ranked[ranked[metric.label].map(lambda value: _format(value, metric.unit)) == winning_display]
        if len(tied) > 1:
            hospital_names = ", ".join(tied.Hospital.tolist()[:-1]) + f", and {tied.Hospital.iloc[-1]}" if len(tied) > 2 else " and ".join(tied.Hospital)
            answer = f"{hospital_names} are tied for the {direction} {metric.label} at {winning_display} under the current filters."
        else:
            answer = f"{row.Hospital} has the {direction} {metric.label} at {winning_display} under the current filters."
        return _response(answer, f"Hospital-level {metric.calculation}; ranked {'ascending' if low else 'descending'}.", data=_display_comparison(ranked, metrics))

    if named_hospital and len(metrics) == 1:
        row = comparison.iloc[0]
        answer = f"{named_hospital}'s current-period {metric.label} is {_format(row[metric.label], metric.unit)}."
    else:
        labels = ", ".join(m.label for m in metrics)
        answer = f"Here is the current filtered hospital comparison for {labels}."
    calculations = "; ".join(f"{m.label}: {m.calculation}" for m in metrics)
    return _response(answer, calculations, data=_display_comparison(comparison, metrics))
