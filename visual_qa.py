"""Deterministic contextual help for each dashboard visual and section."""

import re
from difflib import SequenceMatcher

import pandas as pd

from language_utils import closest_suggestions, extracted_keywords, flexible_tokens, normalized_text
from qa_engine import METRICS, _format, _metrics_in, _value


def _v(purpose, focus, action, callout, limits, metrics=(), calculation="See the visual axes, legend, and supporting table."):
    return {
        "purpose": purpose, "focus": focus, "action": action, "callout": callout,
        "limits": limits, "metrics": metrics, "calculation": calculation,
    }


VISUALS = {
    "1": {
        "Executive KPI Cards": _v("Summarizes current system performance, capacity, workforce, experience, and evidence readiness.", "Start with the lowest-performing domain and whether its movement is material versus the comparable period.", "Validate the underlying denominator and operating context, assign an accountable owner, and use a time-bounded improvement cycle.", "Scores and targets are illustrative portfolio constructs; stable displayed deltas are not described as directional changes.", "The Executive Health Score is not a validated clinical score or forecast.", ("margin", "bed_utilization", "boarding", "readmission", "rn_vacancy", "agency_share", "experience")),
        "Executive Health Score by Domain": _v("Compares Quality & Safety, Patient Flow, Financial, Workforce, Access, and Patient Experience on a 0–100 modeled portfolio scale. A higher bar means the selected synthetic results are closer to the dashboard's illustrative target thresholds; a lower bar means a larger modeled performance gap to validate.", "The shortest bar is the largest modeled performance gap and deserves validation first.", "Review the component metrics behind the weakest domain before selecting an intervention.", "Quality, flow, finance, workforce, access, and experience use transparent illustrative weights and thresholds.", "Bars compare a modeled composite, not certified external benchmarks.", ("readmission", "mortality", "harm", "boarding", "bed_utilization", "discharge_delay", "margin", "denial_rate", "rn_vacancy", "overtime_share", "agency_share", "lwbs", "specialty_wait", "experience"), calculation="Weighted higher/lower-is-better component scores on a 0–100 illustrative scale."),
        "Margin and Flow Pressure by Month": _v("Shows monthly operating contribution beside an indexed ED-boarding pressure series.", "Look for months where contribution weakens while boarding pressure rises; treat this as a co-movement signal.", "Validate throughput timestamps, discharge constraints, staffing, volume, and payer mix before acting.", "Boarding is multiplied only to share a readable axis with dollars; it is not a dollar value.", "The dual-scale view does not establish that boarding caused margin movement.", ("margin", "boarding")),
        "Executive Priority Queue": _v("Ranks hospital-domain priorities by modeled severity and then modeled exposure.", "Priority #1 is the first validation target; review its owner, severity components, and exposure assumptions.", "Assign the listed executive owner, validate inputs, and move an approved response into a PDSA cycle.", "The orange #1 treatment identifies the highest current modeled portfolio priority.", "The queue is not a clinical risk score or validated forecast.", ("readmission", "mortality", "harm", "boarding", "bed_utilization", "discharge_delay", "margin", "denial_rate", "rn_vacancy", "overtime_share", "agency_share", "lwbs", "specialty_wait", "experience"), calculation="Severity descending; modeled exposure descending as tie-breaker."),
    },
    "2": {
        "Capacity KPI Cards": _v("Summarizes licensed, staffed, occupied, and available bed capacity plus ED and discharge pressure.", "Focus on high utilization paired with boarding, pending admissions, or discharge delay.", "Validate bed-ready and discharge timestamps, staffing constraints, and unit-level demand before changing targets.", "Available staffed beds are staffed beds minus census, averaged across the selected period.", "System averages can hide unit and shift variation.", ("licensed_beds", "staffed_beds", "census", "bed_utilization", "available_beds", "boarding", "ed_provider", "pending_admissions", "expected_discharges", "discharge_delay")),
        "Occupancy and Boarding by Hospital": _v("Compares staffed-bed occupancy across hospitals while color encodes boarding hours.", "Hospitals that combine high occupancy with darker/high boarding values warrant throughput review.", "Examine discharge reliability, staffed capacity, pending admissions, and demand by day and unit.", "The visual identifies concurrent pressure; it does not prove one measure causes the other.", "Hospital averages hide within-hospital variation.", ("bed_utilization", "boarding")),
        "Discharge Delay and ED Boarding": _v("Plots discharge-order-to-exit delay against ED boarding, sized by ED arrivals.", "Upper-right, large-volume points indicate the most consequential joint flow pressure.", "Validate timestamps and test discharge coordination, transport, pharmacy, and post-acute placement constraints.", "Bubble size represents demand, so small and large points should not be interpreted equally.", "Association is descriptive and non-causal.", ("boarding", "discharge_delay")),
        "Patient-Flow Operating Matrix": _v("Provides hospital-level demand, capacity, discharge, and delay values behind the flow visuals.", "Use it to confirm which hospital and metric drive the aggregate signal.", "Drill into daily and unit-level operations before assigning accountability.", "This table is the auditable supporting layer for the page.", "It contains synthetic hospital averages, not encounter-level timestamp validation.", ("boarding", "available_beds", "bed_utilization", "pending_admissions", "expected_discharges", "discharge_delay", "ed_provider")),
        "System Patient-Flow Funnel": _v("Illustrates how arrivals move through modeled admission and placement stages.", "The largest drop or queue indicates where modeled flow loss is concentrated.", "Validate real encounter timestamps before using the funnel to set operational targets.", "The placement split is a scenario derived from average boarding pressure.", "It is not an observed patient-level transition funnel.", ("boarding",)),
    },
    "3": {"Deterioration-to-Harm Reliability Matrix": _v("Compares deterioration and harm rates by hospital and service line; bubble size is encounter volume.", "Prioritize large bubbles in the upper-right after confirming event definitions.", "Review rescue protocols, escalation reliability, staffing, and documentation with clinical governance.", "The chart is a surveillance-prioritization tool only.", "It cannot guide bedside care or prove causality.", ("deterioration", "harm"))},
    "4": {"Harm Signal by Service Line": _v("Ranks service lines by synthetic harm rate while color reflects total cost.", "Consider harm rate together with encounter volume; a high rate from a small denominator can be unstable.", "Verify event definitions and denominators, then select an accountable quality-improvement pathway.", "Modeled financial exposure is illustrative and is not booked loss.", "Synthetic harm signals are not certified patient-safety measures.", ("harm",))},
    "5": {"Readmission Risk by Service Line and Discharge Barrier": _v("Shows readmission rate and cohort size for service-line/barrier groups.", "Large, high-rate groups are the strongest transition-reliability screening signals.", "Validate the cohort, then test confirmed follow-up, transition nursing, transportation, medication, or caregiver support.", "Observed group differences are not automatically equity disparities or causal effects.", "The chart is synthetic and not an individual risk model.", ("readmission",))},
    "6": {"Staffing Intensity Versus Composite Outcome Pressure": _v("Plots hours per patient day against a composite outcome-pressure index by hospital.", "Look for persistent clusters or outliers, but do not interpret the fitted line as a staffing effect.", "Validate acuity, skill mix, vacancies, agency use, unit assignments, and workflow before redesigning staffing.", "The trendline is descriptive only; staffing should never be reduced from this chart alone.", "The outcome index is illustrative and the relationship is confounded.", ("hppd", "rn_vacancy", "overtime_share", "agency_share", "mortality", "falls", "hai"))},
    "7": {"Access Leakage Signals by Hospital": _v("Compares hospital LWBS and specialty-wait signals.", "Focus on the hospital with the strongest combined wait, LWBS, and boarding pressure after checking demand volume.", "Test ED fast track, demand-capacity matching, centralized scheduling, referral navigation, and cancellation recovery.", "Recoverable value is an illustrative gross-revenue scenario.", "The measures use different units and should not be compared by raw bar height alone.", ("lwbs", "specialty_wait", "boarding"))},
    "8": {"Procedural Volume and Utilization by Day": _v("Compares OR case volume and utilization by hospital and day of week.", "Find recurring low-utilization/high-demand mismatches and confirm whether they reflect block allocation or constraints.", "Review first-case starts, turnover, cancellations, block release, surgeon availability, and staffing before adding rooms.", "Unused-capacity value is illustrative and not fully recoverable.", "The data do not include surgeon availability or block ownership.", ("or_cases", "or_utilization"))},
    "9": {"Outcomes by Social Vulnerability Quartile": _v("Compares readmission and follow-up across synthetic SVI quartiles.", "Look for consistent gaps while checking cohort size and whether results persist by service line and hospital.", "Validate access barriers and test navigation, transportation, and language support without using SVI to restrict care.", "Group-level differences are screening signals, not proof of inequity or individual risk.", "No patient-level geocoding is included.", ("readmission", "followup"))},
    "10": {"Contribution by Service Line and Payer": _v("Shows encounter contribution by service line and payer.", "Start with negative or weak-contribution combinations that also have meaningful volume.", "Validate contracts and adjudication, then address authorization, documentation, coding, and denial workflow.", "Contribution is revenue minus cost in the synthetic encounter cohort.", "Contract terms and final claims outcomes are not included.", ("contribution", "margin", "denial_rate"))},
    "11": {
        "Intervention Value Frontier": _v("Compares modeled annual cost and annual value; bubble size is capacity days and color is confidence.", "Look for higher-value, lower-cost options with useful capacity release and stronger confidence, while considering strategic fit.", "Fund in stages, define milestones, and re-estimate benefits after implementation evidence is available.", "ROI is one input—not the sole decision rule.", "All benefits, costs, confidence, and capacity release are modeled and not guaranteed.", calculation="Net value = annual value - annual cost; ROI = net value / annual cost."),
        "Selected Portfolio Table": _v("Lists interventions that fit under the selected budget after priority sorting.", "Review cumulative spend, confidence, feasibility, and whether the portfolio is overly concentrated in one domain.", "Use milestone-based releases and stop/go governance rather than committing all funding at once.", "Selection changes with the budget slider and modeled priority score.", "This is a scenario, not an approved capital plan.", calculation="Priority score combines confidence-adjusted ROI and modeled capacity days; cumulative cost must remain within budget."),
    },
    "12": {
        "Decision Integrity Components": _v("Shows the strengths and weaknesses of source authority, completeness, definitions, timeliness, causal confidence, and external validity.", "The lowest component is the largest evidence-readiness gap.", "Close the weakest evidence and governance gaps before production decision support.", "The composite is an illustrative readiness score, not model accuracy.", "Component scores require local governance validation."),
        "Source and Evidence Registry": _v("Documents source, evidence type, use, and limitations for dashboard inputs.", "Confirm that each decision-relevant metric has a clear definition, owner, lineage, and validation status.", "Resolve missing lineage or limitations before promoting a conclusion.", "Public sources provide definitions and context; they are not direct GulfStar rankings.", "The registry does not certify local production readiness."),
    },
    "13": {
        "Privacy Risk by Event Type and Severity": _v("Shows affected synthetic records by privacy-event type and severity.", "Focus first on high-severity, high-exposure categories while separating exposure from legal breach determination.", "Review minimum necessary access, monitoring, incident response, vendor controls, and legal/privacy obligations.", "Records affected is not the count of legally reportable breaches.", "All events are synthetic and legal determination requires review."),
        "CIPP-Informed Governance Gates": _v("Lists privacy-by-design questions and accountable owners.", "Confirm each gate has an owner, evidence, and disposition before deployment.", "Document purpose limitation, minimum necessary, rights, vendor governance, and responsible-analytics controls.", "The gates turn privacy principles into operational review steps.", "They do not replace legal or privacy-officer judgment."),
    },
    "14": {
        "Statistical Process Control Chart": _v("Plots the selected monthly quality measure against a center line and three-sigma analytic limits.", "Investigate points beyond limits and non-random patterns, but first confirm denominator and definition stability.", "Use a PDSA cycle to test a process change and monitor whether the signal sustains.", "A point beyond a limit is an investigation signal, not proof of failure.", "The simple limits do not adjust for seasonality, case mix, or changing denominators.", ("readmission", "mortality", "boarding", "falls", "hai")),
        "Pareto: Discharge Barriers": _v("Ranks discharge barriers by frequency to show where a small number of categories may drive most recorded barriers.", "Start with the largest categories while checking severity and whether categories are consistently coded.", "Select one high-frequency barrier for a small test, then measure outcome and unintended effects.", "Frequency alone does not determine clinical or operational importance.", "Synthetic categories do not establish root cause."),
        "PDSA Learning System": _v("Defines the Plan-Do-Study-Act evidence cycle used to test and refine improvements.", "Focus on a specific aim, prediction, small-scale test, learning, and documented next decision.", "Adopt, adapt, or abandon based on measured results rather than preference.", "PDSA is a learning framework, not evidence that an intervention works.", "Production changes require governance and sustainment monitoring."),
    },
}

VISUAL_SUGGESTIONS = (
    "What is this visual telling me?",
    "What happened on this visual?",
    "What is positive or good on this visual?",
    "What is negative or concerning on this visual?",
    "What should I focus on, and why does it matter?",
    "What can we do to improve this result?",
    "What should we do next?",
    "What are the callouts or warnings?",
    "How is this visual calculated or encoded?",
    "How did you get this number?",
    "What are this visual's limitations?",
    "Can I trust this visual?",
)


NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

MONTH_ALIASES = {
    1: ("january", "jan"), 2: ("february", "feb"), 3: ("march", "mar"),
    4: ("april", "apr"), 5: ("may",), 6: ("june", "jun"),
    7: ("july", "jul"), 8: ("august", "aug"), 9: ("september", "sep", "sept"),
    10: ("october", "oct"), 11: ("november", "nov"), 12: ("december", "dec"),
}
MONTH_LOOKUP = {alias: number for number, aliases in MONTH_ALIASES.items() for alias in aliases}


def requested_month_numbers(question):
    """Return every explicitly named calendar month, expanding inclusive ranges."""
    q = normalized_text(question)
    found = set()
    aliases = "|".join(sorted(MONTH_LOOKUP, key=len, reverse=True))
    for start_name, end_name in re.findall(rf"\b({aliases})\b\s*(?:through|thru|to|-)\s*\b({aliases})\b", q):
        start, end = MONTH_LOOKUP[start_name], MONTH_LOOKUP[end_name]
        current = start
        while True:
            found.add(current)
            if current == end:
                break
            current = 1 if current == 12 else current + 1
    for month_name in re.findall(rf"\b({aliases})\b", q):
        found.add(MONTH_LOOKUP[month_name])
    return sorted(found)


def requested_month_phrase(question):
    months = requested_month_numbers(question)
    return ", ".join(pd.Timestamp(2000, month, 1).strftime("%B") for month in months)


def requested_count(question, default=1):
    """Extract a requested top/bottom result count without mistaking dates for counts."""
    q = normalized_text(question)
    ranking = r"(?:top|bottom|best|worst|highest|lowest|strongest|weakest)"
    entity_numeric = re.search(r"\b(\d{1,2})\s+(?:months?|hospitals?|domains?|metrics?|measures?|service\s+lines?|payers?|barriers?|days?\b(?!\s+(?:readmission|mortality)))", q)
    if entity_numeric:
        return max(1, int(entity_numeric.group(1)))
    numeric = re.search(rf"\b{ranking}\s+(\d{{1,2}})\b(?!\s+day\b)|\b(\d{{1,2}})\s+{ranking}\b", q)
    if numeric:
        return max(1, int(next(group for group in numeric.groups() if group)))
    words = "|".join(NUMBER_WORDS)
    word_match = re.search(rf"\b{ranking}\s+({words})\b|\b({words})\s+{ranking}\b", q)
    if word_match:
        return NUMBER_WORDS[next(group for group in word_match.groups() if group)]
    entity_word = re.search(rf"\b({words})\s+(?:months?|hospitals?|domains?|metrics?|measures?|service\s+lines?|payers?|barriers?|days?\b(?!\s+(?:readmission|mortality)))", q)
    if entity_word:
        return NUMBER_WORDS[entity_word.group(1)]
    return default


def visual_options(page):
    return list(VISUALS.get(str(page).split(" ", 1)[0], {}).keys())


def resolve_visual(page, selected_visual, question):
    """Honor a clearly named visual even when the dropdown still points elsewhere."""
    options = visual_options(page)
    q_text = normalized_text(question)
    q_tokens = set(extracted_keywords(question))
    best_visual, best_score = selected_visual, 0.0
    for option in options:
        option_text = normalized_text(option)
        option_tokens = set(extracted_keywords(option))
        if option_text and option_text in q_text:
            score = 1.0
        else:
            union = q_tokens | option_tokens
            overlap = len(q_tokens & option_tokens) / len(union) if union else 0.0
            phrase = SequenceMatcher(None, q_text, option_text).ratio()
            score = 0.78 * overlap + 0.22 * phrase
        if score > best_score:
            best_visual, best_score = option, score
    # Require a strong explicit match so generic language such as "this visual"
    # continues to use the user's dropdown selection.
    return (best_visual, best_score) if best_score >= 0.42 else (selected_visual, best_score)


def _current_signal(spec, daily, encounters):
    values = []
    for key in spec.get("metrics", ()):
        metric = next((item for item in METRICS if item.key == key), None)
        if metric:
            value = _value(metric, daily, encounters)
            if not pd.isna(value):
                values.append(f"{metric.label}: {_format(value, metric.unit)}")
    return "; ".join(values)


def _visual_movements(spec, daily, encounters, wanted):
    if daily.empty or not spec.get("metrics"):
        return ""
    end = daily.date.max()
    current_start = end - pd.Timedelta(days=29)
    prior_end = current_start - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=29)
    current_daily = daily[daily.date.between(current_start, end)]
    prior_daily = daily[daily.date.between(prior_start, prior_end)]
    if current_daily.empty or prior_daily.empty:
        return ""
    current_encounters = encounters[encounters.admit_date.between(current_start, end)]
    prior_encounters = encounters[encounters.admit_date.between(prior_start, prior_end)]
    rows = []
    for key in spec["metrics"]:
        metric = next((item for item in METRICS if item.key == key), None)
        if metric is None or metric.better not in {"high", "low"}:
            continue
        current = _value(metric, current_daily, current_encounters)
        prior = _value(metric, prior_daily, prior_encounters)
        if pd.isna(current) or pd.isna(prior):
            continue
        delta = current - prior
        display_delta = 100 * delta if metric.unit == "percent" else delta
        if f"{abs(display_delta):.1f}" == "0.0":
            direction = "stable"
        else:
            improved = (delta > 0) if metric.better == "high" else (delta < 0)
            direction = "positive" if improved else "negative"
        if direction == wanted:
            rows.append(f"{metric.label}: {_format(prior, metric.unit)} → {_format(current, metric.unit)}")
    return "; ".join(rows)


def _lower_score(value, target, bad):
    if pd.isna(value): return 50.0
    if value <= target: return 100.0
    if value >= bad: return 0.0
    return 100.0 * (bad - value) / (bad - target)


def _higher_score(value, target, bad):
    if pd.isna(value): return 50.0
    if value >= target: return 100.0
    if value <= bad: return 0.0
    return 100.0 * (value - bad) / (target - bad)


def _executive_domain_snapshot(daily, encounters):
    if daily.empty:
        return None, None, None
    revenue = daily.revenue.sum()
    staff_hours = max(daily.staff_hours.sum(), 1)
    metrics = {
        "margin": (revenue - daily.cost.sum()) / max(revenue, 1),
        "denial_rate": daily.denials.sum() / max(revenue, 1),
        "boarding": daily.boarding_hours.mean(),
        "occupancy": daily.census.sum() / max(daily.staffed_beds.sum(), 1),
        "discharge_delay": daily.discharge_order_to_exit_hours.mean(),
        "readmission": daily.readmission_rate.mean(),
        "mortality": daily.mortality_rate.mean(),
        "harm": encounters.harm.mean() if not encounters.empty else float("nan"),
        "vacancy": daily.rn_vacancy_rate.mean(),
        "overtime_share": daily.overtime_hours.sum() / staff_hours,
        "agency_share": daily.agency_hours.sum() / staff_hours,
        "lwbs": daily.lwbs_rate.mean(),
        "wait": daily.specialty_wait_days.mean(),
        "experience": daily.patient_experience.mean(),
    }
    components = {
        "Quality & Safety": [
            ("30-Day Readmission", metrics["readmission"], "percent", _lower_score(metrics["readmission"], .12, .18)),
            ("Mortality", metrics["mortality"], "percent", _lower_score(metrics["mortality"], .020, .035)),
            ("Harm", metrics["harm"], "percent", _lower_score(metrics["harm"], .020, .060)),
        ],
        "Patient Flow": [
            ("ED Boarding", metrics["boarding"], "hours", _lower_score(metrics["boarding"], 4.0, 10.0)),
            ("Staffed-Bed Utilization", metrics["occupancy"], "percent", _lower_score(metrics["occupancy"], .85, .98)),
            ("Discharge Delay", metrics["discharge_delay"], "hours", _lower_score(metrics["discharge_delay"], 2.0, 5.0)),
        ],
        "Financial": [
            ("Operating Margin", metrics["margin"], "percent", _higher_score(metrics["margin"], .05, -.02)),
            ("Denial Rate", metrics["denial_rate"], "percent", _lower_score(metrics["denial_rate"], .040, .075)),
        ],
        "Workforce": [
            ("RN Vacancy", metrics["vacancy"], "percent", _lower_score(metrics["vacancy"], .08, .18)),
            ("Overtime Share", metrics["overtime_share"], "percent", _lower_score(metrics["overtime_share"], .07, .16)),
            ("Agency Share", metrics["agency_share"], "percent", _lower_score(metrics["agency_share"], .04, .10)),
        ],
        "Access": [
            ("Left Without Being Seen", metrics["lwbs"], "percent", _lower_score(metrics["lwbs"], .02, .07)),
            ("Specialty Wait", metrics["wait"], "days", _lower_score(metrics["wait"], 10.0, 24.0)),
        ],
        "Patient Experience": [
            ("Patient Experience", metrics["experience"], "percent", _higher_score(metrics["experience"], .82, .68)),
        ],
    }
    scores = {domain: sum(item[3] for item in items) / len(items) for domain, items in components.items()}
    return metrics, components, scores


def _executive_domain_interpretation(daily, encounters):
    metrics, components, scores = _executive_domain_snapshot(daily, encounters)
    if scores is None:
        return None
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    score_text = "; ".join(f"{name} {score:.0f}" for name, score in ranked)
    high_score = ranked[0][1]
    leaders = [name for name, score in ranked if round(score) == round(high_score)]
    weakest_name, weakest_score = ranked[-1]
    gap = high_score - weakest_score
    leader_text = " and ".join(leaders)
    details = (
        f"Financial reflects operating margin {_format(metrics['margin'], 'percent')} and denial rate {_format(metrics['denial_rate'], 'percent')}. "
        f"Workforce reflects RN vacancy {_format(metrics['vacancy'], 'percent')}, overtime share {_format(metrics['overtime_share'], 'percent')}, and agency share {_format(metrics['agency_share'], 'percent')}. "
        f"Patient Flow reflects boarding {_format(metrics['boarding'], 'hours')}, staffed-bed utilization {_format(metrics['occupancy'], 'percent')}, and discharge delay {_format(metrics['discharge_delay'], 'hours')}. "
        f"Patient Experience is based on the synthetic experience composite of {_format(metrics['experience'], 'percent')}."
    )
    answer = (
        f"What you are looking at: six horizontal bars ranked from the strongest to weakest modeled domain score for the current filters. "
        f"The displayed scores are {score_text}. {leader_text} lead at {high_score:.0f}, while {weakest_name} is lowest at {weakest_score:.0f}—a {gap:.0f}-point modeled gap. "
        f"What it means: performance is most aligned with the dashboard's illustrative thresholds in {leader_text}, while {weakest_name} is the clearest area for leadership to validate and investigate first. "
        f"A score of {weakest_score:.0f} does not mean {100-weakest_score:.0f}% failure; it is a normalized distance from illustrative thresholds. {details}"
    )
    calculation = (
        "Each underlying metric is clipped to 0–100 between an illustrative favorable target and unfavorable threshold; "
        "each domain is the unweighted mean of its components. Quality & Safety uses readmission, mortality, and harm; "
        "Patient Flow uses boarding, staffed-bed utilization, and discharge delay; Financial uses margin and denial rate; "
        "Workforce uses RN vacancy, overtime, and agency share; Access uses LWBS and specialty wait; Patient Experience uses the synthetic experience composite."
    )
    return {"answer": answer, "calculation": calculation, "evidence": "Synthetic Result / Modeled Estimate"}


def _named_domain_interpretation(visual, question, daily, encounters):
    """Explain the named displayed domain before metric aliases such as access."""
    if visual != "Executive Health Score by Domain":
        return None
    q = normalized_text(question)
    if not ({"why", "high", "low", "highest", "lowest"} & flexible_tokens(question)):
        return None
    aliases = {
        "Quality & Safety": ("quality and safety", "quality safety"),
        "Patient Flow": ("patient flow", "flow"),
        "Financial": ("financial", "finance"),
        "Workforce": ("workforce",),
        "Access": ("access",),
        "Patient Experience": ("patient experience",),
    }
    matched_domains = []
    for name, names in aliases.items():
        positions = [q.find(alias) for alias in names if alias in q]
        if positions:
            matched_domains.append((min(positions), name))
    named_domains = [name for _, name in sorted(matched_domains)]
    if not named_domains:
        return None
    _, components, scores = _executive_domain_snapshot(daily, encounters)
    if scores is None:
        return None
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    displayed_scores = {name: round(value) for name, value in scores.items()}
    details = []
    for domain in named_domains:
        score = scores[domain]
        displayed_score = displayed_scores[domain]
        higher_names = [name for name, value in ranked if displayed_scores[name] > displayed_score]
        tied_names = [name for name, value in ranked if name != domain and displayed_scores[name] == displayed_score]
        lower_names = [name for name, value in ranked if displayed_scores[name] < displayed_score]
        rank = 1 + len(higher_names)
        component_rows = [
            f"{domain} - {label}: {_format(value, unit)}; modeled component score {component_score:.0f}/100."
            for label, value, unit, component_score in components[domain]
        ]
        if rank == 1 and tied_names:
            position = f"tied for highest at displayed precision with {', '.join(tied_names)}"
        elif rank == 1:
            position = "highest"
        elif not lower_names and tied_names:
            position = f"tied for lowest at displayed precision with {', '.join(tied_names)}"
        elif not lower_names:
            position = "lowest"
        else:
            position = f"ranked {rank} of {len(ranked)}"
        component_average = sum(item[3] for item in components[domain]) / len(components[domain])
        higher_domains = [f"{name} ({displayed_scores[name]})" for name in higher_names]
        tied_domains = [f"{name} ({displayed_scores[name]})" for name in tied_names]
        lower_domains = [f"{name} ({displayed_scores[name]})" for name in lower_names]
        domain_why = (
            f"{domain} has this displayed position because its component scores average to {component_average:.1f}, which rounds to {score:.0f}/100. "
            + (f"Domains scoring higher at displayed precision are {', '.join(higher_domains)}. " if higher_domains else "No selected domain scores higher at displayed precision. ")
            + (f"The same displayed score is shared by {', '.join(tied_domains)}. " if tied_domains else "")
            + (f"Domains scoring lower are {', '.join(lower_domains)}." if lower_domains else "No selected domain scores lower.")
        )
        domain_answer = (
            f"The displayed {domain} domain score is {score:.0f}/100 and is {position}. It is the unweighted average of "
            f"{len(component_rows)} normalized component score{'s' if len(component_rows) != 1 else ''}."
        )
        calculation = f"{domain} = unweighted mean of " + " + ".join(item[0] for item in components[domain]) + "."
        details.append({"domain": domain, "score": score, "answer": domain_answer, "components": component_rows, "why": domain_why, "calculation": calculation})

    answer = " ".join(item["answer"] for item in details)
    component_rows = [row for item in details for row in item["components"]]
    why = " ".join(item["why"] for item in details)
    if len(details) > 1:
        high = max(details, key=lambda item: item["score"])
        low = min(details, key=lambda item: item["score"])
        why += f" Among the named domains, {high['domain']} is {high['score'] - low['score']:.0f} points higher than {low['domain']}."
    domain_label = " and ".join(item["domain"] for item in details)
    tokens = flexible_tokens(question)
    title_direction = "High" if tokens & {"high", "highest", "top"} else "Low" if tokens & {"low", "lowest", "bottom"} else "Different"
    actions = [
        "Validate the component definitions, denominators, and selected-period completeness.",
        f"Review the underlying {domain_label} measures by hospital, service line, month, and operating context.",
        "Investigate the least favorable component within each named domain while monitoring the other components as guardrails.",
    ]
    limitation = "This is a modeled portfolio domain score using illustrative thresholds. It is not a validated benchmark, causal model, or patient-care measure."
    return {
        "answer": answer + " " + " ".join(component_rows),
        "calculation": " ".join(item["calculation"] for item in details),
        "evidence": "Synthetic Result / Modeled Estimate", "limitation": limitation,
        "display": {
            "title": (f"{details[0]['domain']} Domain - Why It Has This Score" if len(details) == 1 else f"{' vs. '.join(item['domain'] for item in details)} - Why These Scores Are {title_direction}"),
            "answer": answer, "what_matters": component_rows, "why": why, "actions": actions,
            "action_heading": "What Leadership Should Validate", "limitation": limitation,
        },
    }


def _domain_aggregate_interpretation(visual, question, daily, encounters):
    """Answer domain-wide rankings and arithmetic across any named domains."""
    if visual != "Executive Health Score by Domain":
        return None
    tokens = flexible_tokens(question)
    if not (tokens & {"average", "high", "highest", "top", "low", "lowest", "bottom"}):
        return None
    q = normalized_text(question)
    if "gulfstar" in q:
        return None
    aliases = {
        "Quality & Safety": ("quality and safety", "quality safety", "quality & safety"),
        "Patient Flow": ("patient flow",), "Financial": ("financial", "finance"),
        "Workforce": ("workforce",), "Access": ("access",),
        "Patient Experience": ("patient experience",),
    }
    named = []
    for domain, variants in aliases.items():
        positions = [q.find(normalized_text(alias)) for alias in variants if normalized_text(alias) in q]
        if positions:
            named.append((min(positions), domain))
    named = [domain for _, domain in sorted(named)]
    _, components, scores = _executive_domain_snapshot(daily, encounters)
    if not scores:
        return None
    displayed = {domain: round(score) for domain, score in scores.items()}
    wants_average = "average" in tokens
    wants_low = bool(tokens & {"low", "lowest", "bottom"})
    count = requested_count(question)
    limitation = "These are modeled portfolio scores using illustrative thresholds, not validated benchmarks or causal measures."
    if wants_average:
        selected = named or list(scores)
        arithmetic_average = sum(scores[domain] for domain in selected) / len(selected)
        display_average = sum(displayed[domain] for domain in selected) / len(selected)
        detail = [f"{domain}: {displayed[domain]}/100" for domain in selected]
        label = "the named domains" if named else "all six domains"
        answer = f"The average across {label} is {arithmetic_average:.1f}/100 using the underlying modeled scores. The average of the whole-number scores displayed on the chart is {display_average:.1f}/100."
        why = f"The result is the arithmetic mean of {len(selected)} domain scores: " + ", ".join(detail) + "."
        return {
            "answer": answer + " " + "; ".join(detail) + ".",
            "calculation": f"Domain average = ({' + '.join(f'{scores[d]:.1f}' for d in selected)}) / {len(selected)}.",
            "evidence": "Synthetic Result / Modeled Estimate", "limitation": limitation,
            "display": {"title": "Average Domain Score", "filters": _selected_filter_summary(daily, encounters),
                        "answer": answer, "what_matters": detail, "why": why,
                        "actions": ["Use the individual domain scores—not only the average—to identify concentrated performance gaps.", "Validate component definitions and thresholds before operational use."],
                        "action_heading": "What Leadership Should Validate", "limitation": limitation},
        }
    if not named:
        if _metrics_in(question) and "domain" not in tokens:
            return None
        count = min(requested_count(question), len(displayed))
        ordered_domains = sorted(displayed.items(), key=lambda item: item[1], reverse=not wants_low)
        cutoff = ordered_domains[count - 1][1]
        leaders = [(domain, value) for domain, value in ordered_domains if (value <= cutoff if wants_low else value >= cutoff)]
        direction = "lowest" if wants_low else "highest"
        if count == 1 and len(leaders) == 1:
            answer = f"{leaders[0][0]} is {direction} at {leaders[0][1]}/100."
        elif count == 1:
            answer = f"{' and '.join(domain for domain, _ in leaders)} are tied for {direction} at {leaders[0][1]}/100."
        else:
            answer = f"The requested {direction} {count} domains are: " + "; ".join(f"{rank}. {domain}: {value}/100" for rank, (domain, value) in enumerate(leaders, 1)) + "."
        detail = [f"{domain}: {displayed[domain]}/100" for domain in sorted(displayed, key=displayed.get, reverse=True)]
        return {
            "answer": answer + " Displayed domain scores: " + "; ".join(detail) + ".",
            "calculation": f"Rank the six modeled domain scores at the whole-number precision displayed in the chart; preserve ties for the {direction} score.",
            "evidence": "Synthetic Result / Modeled Estimate", "limitation": limitation,
            "display": {"title": f"{direction.title()} Domain Score", "filters": _selected_filter_summary(daily, encounters),
                        "answer": answer, "what_matters": detail,
                        "why": f"The named domain{'s' if len(leaders) > 1 else ''} share the {direction} whole-number score shown in the chart.",
                        "actions": ["Review the component measures behind the ranked domain before selecting an intervention."],
                        "action_heading": "What Leadership Should Validate", "limitation": limitation},
        }
    return None


def _domain_action_interpretation(visual, question, daily, encounters):
    """Explain measured domain drivers and provide validation-first improvement paths."""
    if visual != "Executive Health Score by Domain":
        return None
    tokens = flexible_tokens(question)
    if not (tokens & {"improve", "better", "fix", "action", "cause", "caused", "driver", "get", "reach", "match", "raise", "increase", "decrease"}):
        return None
    q = normalized_text(question)
    aliases = {
        "Quality & Safety": ("quality and safety", "quality safety"), "Patient Flow": ("patient flow",),
        "Financial": ("financial", "finance"), "Workforce": ("workforce",),
        "Access": ("access",), "Patient Experience": ("patient experience",),
    }
    positioned = []
    for domain, variants in aliases.items():
        hits = [q.find(alias) for alias in variants if alias in q]
        if hits:
            positioned.append((min(hits), domain))
    named = [domain for _, domain in sorted(positioned)]
    if not named:
        return None
    _, components, scores = _executive_domain_snapshot(daily, encounters)
    if not scores:
        return None
    component_keys = {
        "30-Day Readmission": "readmission", "Mortality": "mortality", "Harm": "harm",
        "ED Boarding": "boarding", "Staffed-Bed Utilization": "bed_utilization", "Discharge Delay": "discharge_delay",
        "Operating Margin": "margin", "Denial Rate": "denial_rate", "RN Vacancy": "rn_vacancy",
        "Overtime Share": "overtime_share", "Agency Share": "agency_share", "Left Without Being Seen": "lwbs",
        "Specialty Wait": "specialty_wait", "Patient Experience": "experience",
    }
    comparative = any(phrase in q for phrase in ("as high as", "as low as", "lower than", "higher than", "compared with", "compared to"))
    benchmark = max(scores[domain] for domain in named) if comparative and len(named) > 1 else max(scores.values())
    action_domains = [domain for domain in named if not comparative or scores[domain] < benchmark - .5]
    matters, actions, explanations = [], [], []
    for domain in named:
        score = scores[domain]
        gap = benchmark - score
        ordered_components = sorted(components[domain], key=lambda item: item[3])
        weakest = ordered_components[0]
        explanations.append(
            f"{domain} is {score:.0f}/100" + (f", {gap:.0f} points below the strongest named comparison" if gap > .5 else ", at the strongest named comparison level") + "."
        )
        for label, value, unit, component_score in ordered_components:
            matters.append(f"{domain} — {label}: {_format(value, unit)}; modeled component score {component_score:.0f}/100.")
        if domain in action_domains:
            metric_key = component_keys[weakest[0]]
            owner, validation, intervention = IMPROVEMENT_PATHS[metric_key]
            actions.append(f"{domain}: Ask the {owner} to validate {validation}; then {intervention}. Track the other domain components as guardrails.")
    causal = bool(tokens & {"cause", "caused", "driver"})
    answer = " ".join(explanations)
    if causal:
        answer += " The component scores below mathematically explain the displayed result. They identify measured pressure—not a proven operational cause."
    else:
        answer += " Improvement should start with the lowest component score in each named domain, after validating its underlying data and operating context."
    why = "The displayed domain score is the unweighted mean of the component scores listed below. A lower component pulls the domain average down; a higher component pulls it up."
    limitation = "The dashboard identifies measured contributors to the modeled score, not causal effects. Operational cause requires validated timestamps, denominators, context, and governed local investigation."
    return {
        "answer": answer + " " + " ".join(matters + actions),
        "calculation": "For each named domain: normalize each documented component to 0–100, then take the unweighted mean; compare the resulting domain scores and identify the lowest component score.",
        "evidence": "Synthetic Result / Modeled Estimate", "limitation": limitation,
        "display": {"title": f"{' and '.join(named)} — Measured Drivers and Improvement Path",
                    "filters": _selected_filter_summary(daily, encounters), "answer": answer,
                    "what_matters": matters, "why": why, "actions": actions,
                    "action_heading": "What Leadership Can Do Next", "limitation": limitation},
    }


def _dynamic_visual_interpretation(page, visual, daily, encounters):
    page_number = str(page).split(" ", 1)[0]
    if page_number == "1" and visual == "Executive Health Score by Domain":
        return _executive_domain_interpretation(daily, encounters)
    if visual == "Deterioration-to-Harm Reliability Matrix" and not encounters.empty:
        grouped = encounters.groupby("hospital").agg(
            encounters=("encounter_id", "count"),
            deterioration=("deterioration", "mean"),
            harm=("harm", "mean"),
        )
        deterioration_order = grouped.deterioration.sort_values()
        harm_order = grouped.harm.sort_values()
        hospital_rows = []
        for hospital, row in grouped.iterrows():
            deterioration_position = "highest" if hospital == deterioration_order.index[-1] else "lowest" if hospital == deterioration_order.index[0] else "middle"
            harm_position = "highest" if hospital == harm_order.index[-1] else "lowest" if hospital == harm_order.index[0] else "middle"
            hospital_rows.append(
                f"{hospital}: Deterioration {_format(row.deterioration, 'percent')} ({deterioration_position}); "
                f"Harm {_format(row.harm, 'percent')} ({harm_position}); {row.encounters:,.0f} encounters."
            )
        service_rows = []
        if "service_line" in encounters:
            by_service = encounters.groupby(["hospital", "service_line"]).agg(
                encounters=("encounter_id", "count"), deterioration=("deterioration", "mean"), harm=("harm", "mean")
            ).reset_index()
            for hospital, frame in by_service.groupby("hospital"):
                pressure = frame.assign(joint_pressure=frame.deterioration + frame.harm).sort_values(
                    ["joint_pressure", "encounters"], ascending=False
                ).iloc[0]
                service_rows.append(
                    f"{hospital.replace('GulfStar ', '')}: {pressure.service_line} has the highest combined displayed pressure "
                    f"({_format(pressure.deterioration, 'percent')} deterioration; {_format(pressure.harm, 'percent')} harm; "
                    f"{pressure.encounters:,.0f} encounters)."
                )
        answer = (
            "The matrix compares each hospital and service line on two rates: farther right means more selected encounters "
            "were flagged for deterioration, farther up means more were flagged for harm, and larger bubbles mean more encounters. "
            "Hospital-level results are summarized below; the plotted bubbles provide the service-line detail."
        )
        limitation = (
            "The flags and rates are synthetic and not risk-adjusted. Position and bubble size identify where validation should start; "
            "they do not establish cause, clinical performance, or patient-level risk."
        )
        return {
            "answer": answer + " " + " ".join(hospital_rows + service_rows),
            "calculation": "Hospital and hospital-service-line encounter counts with mean Boolean deterioration and harm flags; bubble size = encounter count.",
            "evidence": "Synthetic Result / Analytical Signal", "limitation": limitation,
            "display": {
                "title": "Deterioration-to-Harm Reliability Matrix — Executive Readout",
                "filters": _selected_filter_summary(daily, encounters), "answer": answer,
                "what_matters": hospital_rows + service_rows,
                "actions": [
                    "Start validation with large bubbles that are simultaneously farther right and higher on the matrix.",
                    "Confirm deterioration, harm, encounter-eligibility, service-line, and reporting definitions.",
                    "Review persistent differences by hospital, service line, acuity, and period through clinical governance before selecting an intervention.",
                ],
                "action_heading": "What Leadership Should Validate", "limitation": limitation,
            },
        }
    spec = VISUALS.get(page_number, {}).get(visual, {})
    if "hospital" in (visual + " " + spec.get("purpose", "")).lower() and spec.get("metrics"):
        hospitals = sorted(set(daily.hospital.unique()) | set(encounters.hospital.unique()))
        metric_values = {}
        for key in spec["metrics"]:
            metric = _metric_by_key(key)
            if metric is None:
                continue
            values = []
            for hospital in hospitals:
                value = _value(metric, daily[daily.hospital == hospital], encounters[encounters.hospital == hospital])
                if not pd.isna(value):
                    values.append((hospital, float(value)))
            if values:
                metric_values[metric] = sorted(values, key=lambda item: item[1])
        hospital_rows = []
        for hospital in hospitals:
            parts = []
            for metric, ordered in metric_values.items():
                match = next(((name, value) for name, value in ordered if name == hospital), None)
                if match is None:
                    continue
                rank = ordered.index(match) + 1
                position = "lowest" if rank == 1 else "highest" if rank == len(ordered) else "middle"
                parts.append(f"{metric.label} {_format(match[1], metric.unit)} ({position})")
            if parts:
                hospital_rows.append(f"{hospital}: " + "; ".join(parts) + ".")
        if hospital_rows:
            answer = (
                f"This visual compares the selected hospitals using {', '.join(metric.label for metric in metric_values)}. "
                "Each hospital's current filtered values and relative position are listed below."
            )
            limitation = (
                "The high, middle, and low labels are relative only to the currently selected hospitals. They describe the output "
                "but do not explain cause or establish that a difference is statistically unusual."
            )
            return {
                "answer": answer + " " + " ".join(hospital_rows),
                "calculation": spec["calculation"], "evidence": "Synthetic Result / Analytical Signal", "limitation": limitation,
                "display": {
                    "title": f"{visual} — Executive Readout", "filters": _selected_filter_summary(daily, encounters),
                    "answer": answer, "what_matters": hospital_rows,
                    "actions": [
                        "Review the hospital with the least favorable combination of displayed measures first.",
                        "Confirm definitions, denominators, time periods, volume, and data completeness.",
                        "Validate whether the difference persists in comparable service lines, units, days, and operating shifts before assigning a cause.",
                    ],
                    "action_heading": "What Leadership Should Validate", "limitation": limitation,
                },
            }
    return None


METRIC_DETAIL = {
    "mortality": {"definition": "the mean synthetic daily mortality-event rate", "context": "This is not risk-adjusted, certified, or suitable for patient-level inference."},
    "falls": {"definition": "the total synthetic falls recorded during the selected period", "context": "Counts require validated event definitions, reporting completeness, exposure days, and severity review."},
    "hai": {"definition": "the total synthetic healthcare-associated infection events during the selected period", "context": "This is not a certified NHSN measure and does not apply device-day or procedure-specific denominators."},
    "ed_provider": {"definition": "the mean synthetic minutes from ED arrival to first provider", "context": "Timestamp definitions and fast-track or triage workflows require operational validation."},
    "available_beds": {"definition": "the average selected-day staffed-bed capacity remaining after census", "context": "A positive system average does not prove that the right bed type was available at the needed hospital, unit, or time."},
    "denials": {"definition": "the total synthetic dollars flagged as denied during the selected period", "context": "This is not a final adjudicated or collectible-loss amount and requires finance validation."},
    "or_utilization": {"definition": "the mean synthetic share of available OR time used", "context": "The data do not include block ownership, room availability, surgeon schedules, turnover definitions, or urgency."},
    "experience": {
        "definition": "the mean synthetic patient-experience composite across the selected hospitals and dates",
        "context": "It is a portfolio demonstration measure and is not an official HCAHPS score.",
        "target": .82, "bad": .68, "direction": "high",
        "threshold_text": "The dashboard's illustrative favorable threshold is 82% and its lower scoring reference is 68%.",
    },
    "margin": {
        "definition": "the share of gross operating revenue remaining after synthetic operating cost",
        "context": "It is not audited operating income and excludes real contract and accounting adjustments.",
        "target": .05, "bad": -.02, "direction": "high",
        "threshold_text": "The illustrative favorable threshold is 5% and the unfavorable scoring reference is -2%.",
    },
    "bed_utilization": {
        "definition": "selected-period census divided by staffed-bed capacity",
        "context": "It measures use of staffed—not licensed—capacity and can hide unit, shift, and daily variation.",
        "target": .85, "bad": .98, "direction": "low",
        "threshold_text": "For pressure scoring, 85% is the illustrative favorable threshold and 98% is the high-pressure reference; lower is not automatically operationally optimal.",
    },
    "boarding": {
        "definition": "the mean synthetic ED boarding hours across the selected hospitals and dates",
        "context": "Validate real arrival, admission-decision, bed-ready, and placement timestamps before operational use.",
        "target": 4.0, "bad": 10.0, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 4 hours and the high-pressure reference is 10 hours.",
    },
    "readmission": {
        "definition": "the share of selected synthetic encounters flagged for readmission within 30 days",
        "context": "It is not a certified CMS measure and is not risk-adjusted for production comparison.",
        "target": .12, "bad": .18, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 12% and the unfavorable reference is 18%.",
    },
    "rn_vacancy": {
        "definition": "the mean synthetic RN vacancy rate across selected hospitals and dates",
        "context": "It does not include unit-level skill mix, recruiting pipeline, leave, or position-control validation.",
        "target": .08, "bad": .18, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 8% and the high-pressure reference is 18%.",
    },
    "agency_share": {
        "definition": "total synthetic agency hours divided by total productive staff hours",
        "context": "It does not establish whether agency coverage was avoidable or clinically inappropriate.",
        "target": .04, "bad": .10, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 4% and the high-use reference is 10%.",
    },
    "lwbs": {
        "definition": "the mean synthetic share of ED arrivals leaving without being seen",
        "context": "Validate arrival and disposition definitions before external comparison.",
        "target": .02, "bad": .07, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 2% and the unfavorable reference is 7%.",
    },
    "specialty_wait": {
        "definition": "the mean synthetic specialty wait in days",
        "context": "It does not distinguish urgency, specialty, referral completeness, or patient preference.",
        "target": 10.0, "bad": 24.0, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 10 days and the long-wait reference is 24 days.",
    },
    "denial_rate": {
        "definition": "synthetic denied dollars divided by synthetic gross revenue",
        "context": "It is not a final adjudicated claims denial rate and requires finance validation.",
        "target": .04, "bad": .075, "direction": "low",
        "threshold_text": "The illustrative favorable threshold is 4% and the unfavorable reference is 7.5%.",
    },
    "deterioration": {"definition": "the share of selected synthetic encounters flagged with a deterioration event", "context": "The flag is synthetic, is not a validated early-warning model, and cannot guide bedside care."},
    "harm": {"definition": "the share of selected synthetic encounters flagged with the dashboard's composite harm indicator", "context": "The composite is synthetic, not a certified patient-safety measure, and does not identify cause."},
    "followup": {"definition": "the share of selected synthetic encounters with follow-up recorded as booked", "context": "Booked follow-up does not prove attendance, timely access, appropriateness, or outcome improvement."},
    "los": {"definition": "the mean synthetic encounter length of stay in days", "context": "The result is not case-mix or severity adjusted and should not be used for individual care decisions."},
    "discharge_delay": {"definition": "the mean synthetic hours from discharge order to patient exit", "context": "Validate order, readiness, transport, pharmacy, placement, and physical-exit timestamps before operational use."},
    "pending_admissions": {"definition": "the mean synthetic count of patients awaiting inpatient placement", "context": "This is a daily portfolio average and can hide hour, hospital, unit, and bed-type constraints."},
    "expected_discharges": {"definition": "the mean synthetic number of discharges expected per selected day", "context": "Expected does not mean completed and depends on the dashboard's synthetic planning assumptions."},
    "licensed_beds": {"definition": "the mean licensed-bed count represented in the selected daily records", "context": "Licensed capacity is not the same as staffed, available, clinically appropriate, or immediately usable capacity."},
    "staffed_beds": {"definition": "the mean bed count staffed for operation in the selected daily records", "context": "A staffed bed may still be constrained by unit type, isolation, skill mix, or real-time placement conditions."},
    "census": {"definition": "the mean occupied-bed census in the selected daily records", "context": "A portfolio average can hide peaks, unit-level crowding, transfers, and within-day variation."},
    "overtime_share": {"definition": "total synthetic overtime hours divided by total productive staff hours", "context": "It does not establish whether overtime was avoidable, unsafe, or caused by a specific operating condition."},
    "hppd": {"definition": "total synthetic productive staff hours divided by total census patient-days", "context": "It is an aggregate staffing-intensity measure without acuity, skill-mix, unit, assignment, or worked-hours validation."},
    "or_cases": {"definition": "the total synthetic OR cases recorded during the selected period", "context": "Volume alone does not measure complexity, urgency, room availability, productivity, or appropriate capacity."},
    "contribution": {"definition": "total synthetic encounter revenue minus total synthetic encounter cost", "context": "It is not audited contribution margin and omits real contracts, allocation methods, and final claims adjudication."},
}


IMPROVEMENT_PATHS = {
    "boarding": ("Chief Operating Officer", "arrival, admission-decision, bed-ready, placement, discharge-order, and physical-exit timestamps", "test discharge-readiness coordination, admission-placement escalation, and demand-capacity huddles"),
    "ed_provider": ("Chief Operating Officer", "arrival, triage, provider-contact, fast-track, and staffing timestamps", "test demand-matched coverage, triage streaming, and fast-track reliability"),
    "bed_utilization": ("Chief Operating Officer", "staffed-bed definitions, census, unit type, isolation constraints, and shift-level peaks", "test staffed-capacity alignment, discharge reliability, and inter-unit placement escalation"),
    "available_beds": ("Chief Operating Officer", "whether the available beds match the required hospital, unit, acuity, and time", "test real-time bed-type visibility and placement escalation"),
    "discharge_delay": ("Chief Operating Officer", "discharge order, clinical readiness, pharmacy, transport, placement, and physical-exit timestamps", "test earlier readiness identification and barrier-specific discharge coordination"),
    "pending_admissions": ("Chief Operating Officer", "queue definitions, bed type, placement timing, and demand peaks", "test admission-placement escalation and demand-capacity huddles"),
    "readmission": ("Chief Clinical Officer", "cohort eligibility, discharge disposition, follow-up, barriers, and risk adjustment", "test transition calls, follow-up reliability, medication access, and barrier-specific navigation"),
    "mortality": ("Chief Medical Officer", "event definitions, case mix, severity, expected mortality, and rescue-process data", "conduct governed case review and test escalation or rescue-process reliability"),
    "falls": ("Chief Nursing Officer", "event reporting, patient-days, location, severity, and contributing conditions", "test unit-specific prevention reliability after governed event review"),
    "hai": ("Chief Quality Officer", "infection definitions, device or procedure denominators, attribution windows, and surveillance completeness", "test the relevant prevention bundle and audit process reliability"),
    "harm": ("Chief Quality Officer", "harm definitions, denominator stability, event severity, and reporting completeness", "conduct governed event review and test the most frequent validated process gap"),
    "deterioration": ("Chief Medical Officer", "deterioration definitions, escalation timing, rescue response, acuity, and documentation", "test recognition and escalation reliability through clinical governance"),
    "rn_vacancy": ("Chief Nursing Officer", "approved positions, filled FTEs, leave, recruiting pipeline, unit, shift, and skill mix", "prioritize the highest-pressure units for retention, recruiting, scheduling, and workload redesign"),
    "agency_share": ("Chief Nursing Officer", "productive, agency, overtime, unit, shift, vacancy, and demand hours", "test internal staffing-pool coverage and vacancy-focused workforce actions"),
    "overtime_share": ("Chief Nursing Officer", "productive and overtime hours by unit, shift, vacancy, demand, and scheduling practice", "test schedule redesign, internal coverage, and vacancy-focused actions"),
    "experience": ("Chief Experience Officer", "survey eligibility, response mix, domain composition, service recovery, and unit-level variation", "test communication, responsiveness, discharge information, and service-recovery reliability"),
    "margin": ("Chief Financial Officer", "revenue, cost allocation, payer mix, volume, labor, and claims adjudication", "test the largest validated labor, throughput, denial, or service-line contribution opportunity"),
    "denial_rate": ("Chief Financial Officer", "denial definitions, adjudication status, payer, reason code, authorization, coding, and documentation", "test prevention work queues for the largest validated denial categories"),
    "denials": ("Chief Financial Officer", "denied dollars, final adjudication, payer, reason code, and recoverability", "test prevention and recovery workflows for the largest validated denial categories"),
    "or_utilization": ("Chief Operating Officer", "available room time, block ownership, case duration, first-case starts, turnover, cancellations, and staffing", "test first-case reliability, block release, turnover, and schedule matching before adding capacity"),
    "specialty_wait": ("Chief Operating Officer", "referral completeness, urgency, specialty, template supply, cancellations, and patient preference", "test centralized scheduling, referral navigation, template release, and cancellation recovery"),
    "lwbs": ("Chief Operating Officer", "arrival, triage, departure, provider-contact, demand, and fast-track definitions", "test demand-matched staffing, streaming, fast track, and waiting-room communication"),
    "followup": ("Chief Clinical Officer", "booking status, appointment timing, attendance, specialty, barriers, and discharge cohort", "test confirmed scheduling and barrier-specific navigation before discharge"),
    "hppd": ("Chief Nursing Officer", "worked hours, patient-days, acuity, unit, shift, skill mix, and assignments", "test acuity- and demand-aligned staffing with workforce and clinical guardrails"),
    "contribution": ("Chief Financial Officer", "encounter revenue, cost allocation, payer, service line, volume, and claims status", "test the largest validated contract, denial, documentation, throughput, or cost opportunity"),
}

RELATED_METRICS = {
    "boarding": ("bed_utilization", "discharge_delay", "pending_admissions", "ed_provider"),
    "bed_utilization": ("available_beds", "boarding", "discharge_delay"),
    "margin": ("denial_rate", "agency_share", "overtime_share"),
    "readmission": ("followup", "los"),
    "rn_vacancy": ("agency_share", "overtime_share", "hppd"),
    "agency_share": ("rn_vacancy", "overtime_share"),
    "experience": ("boarding", "lwbs", "rn_vacancy"),
    "or_utilization": ("or_cases",),
    "specialty_wait": ("lwbs", "boarding"),
    "harm": ("deterioration", "mortality", "falls", "hai"),
}

METRIC_DOMAINS = {
    "readmission": "Quality & Safety", "mortality": "Quality & Safety", "harm": "Quality & Safety",
    "boarding": "Patient Flow", "bed_utilization": "Patient Flow", "discharge_delay": "Patient Flow",
    "margin": "Financial", "denial_rate": "Financial",
    "rn_vacancy": "Workforce", "overtime_share": "Workforce", "agency_share": "Workforce",
    "lwbs": "Access", "specialty_wait": "Access", "experience": "Patient Experience",
}


def _metric_by_key(key):
    return next((metric for metric in METRICS if metric.key == key), None)


def _selected_filter_summary(daily, encounters):
    hospitals = sorted(daily.hospital.unique()) if not daily.empty else sorted(encounters.hospital.unique())
    services = sorted(encounters.service_line.unique()) if not encounters.empty and "service_line" in encounters else []
    dates = daily.date if not daily.empty and "date" in daily else encounters.admit_date
    hospital_filter = "All Hospitals" if len(hospitals) == 3 else (", ".join(hospitals) if hospitals else "Selected Hospitals")
    service_filter = "All Service Lines" if len(services) == 6 else (", ".join(services) if services else "Selected Service Lines")
    return f"{hospital_filter} • {service_filter} • {dates.min():%b %-d, %Y}–{dates.max():%b %-d, %Y}"


def _visual_comparison_interpretation(visual, spec, question, daily, encounters):
    """Answer hospital comparisons and relative-outlier questions from current filtered values."""
    tokens = flexible_tokens(question)
    comparison_language = bool(tokens & {"outlier", "outliers", "compare", "versus", "vs", "difference", "different", "high", "low", "highest", "lowest", "average"})
    if not comparison_language or not spec.get("metrics"):
        return None
    hospitals = sorted(set(daily.hospital.unique()) | set(encounters.hospital.unique()))
    q = normalized_text(question)
    named = [
        name for name in hospitals
        if normalized_text(name) in q or normalized_text(name.replace("GulfStar ", "")) in q
    ]
    asks_outliers = bool(tokens & {"outlier", "outliers"})
    if len(named) < 2 and not asks_outliers:
        return None

    explicit_keys = {metric.key for metric in _metrics_in(question)}
    metric_keys = [key for key in spec.get("metrics", ()) if not explicit_keys or key in explicit_keys]
    rows = []
    relative_outliers = []
    for key in metric_keys:
        metric = _metric_by_key(key)
        if metric is None:
            continue
        values = []
        for hospital in hospitals:
            value = _value(metric, daily[daily.hospital == hospital], encounters[encounters.hospital == hospital])
            if not pd.isna(value):
                values.append((hospital, float(value)))
        if len(values) < 2:
            continue
        ordered = sorted(values, key=lambda item: item[1])
        median = float(pd.Series([value for _, value in values]).median())
        span = ordered[-1][1] - ordered[0][1]
        selected = named or hospitals
        positions = []
        for hospital in selected:
            match = next(((name, value) for name, value in ordered if name == hospital), None)
            if match is None:
                continue
            rank = ordered.index(match) + 1
            label = "lowest" if rank == 1 else "highest" if rank == len(ordered) else "middle"
            displayed = (
                f"{match[1]:.2f} hours"
                if visual == "Discharge Delay and ED Boarding" and metric.unit == "hours"
                else _format(match[1], metric.unit)
            )
            positions.append(f"{hospital.replace('GulfStar ', '')}: {displayed} ({label})")
        if positions:
            rows.append(f"{metric.label}: " + "; ".join(positions) + ".")
        if asks_outliers and span > 0:
            deviations = [(name, abs(value - median), value) for name, value in values]
            name, deviation, value = max(deviations, key=lambda item: item[1])
            # With only a few hospitals, label the most separated point as a relative
            # outlier candidate, never as a statistically confirmed anomaly.
            relative_outliers.append(
                f"{metric.label}: {name} is the most separated from the selected-hospital median "
                f"({_format(value, metric.unit)} versus {_format(median, metric.unit)})."
            )
    if not rows:
        return None

    if asks_outliers:
        answer = "Relative outlier review: " + " ".join(relative_outliers or rows)
        title = f"{visual} — Relative Outliers"
    else:
        answer = "Hospital comparison: " + " ".join(rows)
        title = f"{visual} — Hospital Comparison"
    limitation = (
        "These are descriptive relative positions within the currently selected hospitals. With a small peer set, "
        "the dashboard does not label any point a statistically confirmed outlier or infer why it differs."
    )
    return {
        "answer": answer,
        "calculation": "Current filtered hospital values ranked independently for each mapped visual measure; relative outlier candidate = largest absolute distance from the selected-hospital median.",
        "evidence": "Synthetic Result / Analytical Signal",
        "limitation": limitation,
        "display": {
            "title": title, "filters": _selected_filter_summary(daily, encounters),
            "answer": answer, "what_matters": rows,
            "actions": [
                "Confirm the difference persists across comparable months, days, units, and operating shifts.",
                "Validate definitions, denominators, timestamps, case mix, volume, and data completeness.",
                "Review the visual's related capacity, workforce, quality, access, or financial guardrails before selecting an intervention.",
            ],
            "action_heading": "What Leadership Should Validate", "limitation": limitation,
        },
    }


def _metric_group_ranking_interpretation(visual, spec, question, daily, encounters):
    """Rank valid visual groups for explicitly named metrics and preserve displayed ties."""
    if "what does" in normalized_text(question):
        return None
    tokens = flexible_tokens(question)
    if not (tokens & {"high", "highest", "top", "low", "lowest", "bottom", "average"}):
        return None
    q = normalized_text(question)
    if "average" not in tokens and "which" not in tokens and not any(group in q for group in ("hospital", "service line", "payer", "barrier", "day of week", "weekday")):
        return None
    explicit = [metric for metric in _metrics_in(question) if metric.key in spec.get("metrics", ())]
    if not explicit:
        return None
    q = normalized_text(question)
    hospitals = sorted(set(daily.hospital.unique()) | set(encounters.hospital.unique()))
    service_lines = sorted(encounters.service_line.dropna().unique()) if "service_line" in encounters else []
    payers = sorted(encounters.payer.dropna().unique()) if "payer" in encounters else []
    barriers = sorted(encounters.discharge_barrier.dropna().unique()) if "discharge_barrier" in encounters else []
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    named_hospitals = [name for name in hospitals if normalized_text(name) in q or normalized_text(name.replace("GulfStar ", "")) in q]
    named_services = [name for name in service_lines if normalized_text(name) in q]
    named_payers = [name for name in payers if normalized_text(name) in q]
    named_barriers = [name for name in barriers if normalized_text(name) in q]
    named_days = [name for name in weekdays if normalized_text(name) in q]
    if "service line" in q or named_services:
        group_label, groups, named_groups = "service line", service_lines, named_services
        slicer = lambda group: (daily, encounters[encounters.service_line == group])
    elif "payer" in q or named_payers:
        group_label, groups, named_groups = "payer", payers, named_payers
        slicer = lambda group: (daily, encounters[encounters.payer == group])
    elif "barrier" in q or named_barriers:
        group_label, groups, named_groups = "discharge barrier", barriers, named_barriers
        slicer = lambda group: (daily, encounters[encounters.discharge_barrier == group])
    elif "day of week" in q or "weekday" in q or named_days:
        group_label, groups, named_groups = "day of week", weekdays, named_days
        slicer = lambda group: (
            daily[pd.to_datetime(daily.date).dt.day_name() == group],
            encounters[pd.to_datetime(encounters.admit_date).dt.day_name() == group],
        )
    else:
        group_label, groups, named_groups = "hospital", hospitals, named_hospitals
        slicer = lambda group: (daily[daily.hospital == group], encounters[encounters.hospital == group])
    wants_average = "average" in tokens
    wants_low = bool(tokens & {"low", "lowest", "bottom"})
    count = requested_count(question)
    rows, answers = [], []
    for metric in explicit:
        if group_label in {"service line", "payer", "discharge barrier"} and metric.key not in {"readmission", "deterioration", "harm", "followup", "los", "contribution"}:
            continue
        values = []
        for group in groups:
            group_daily, group_encounters = slicer(group)
            value = _value(metric, group_daily, group_encounters)
            if not pd.isna(value):
                values.append((group, float(value)))
        if not values:
            continue
        selected_values = [(name, value) for name, value in values if not named_groups or name in named_groups]
        if not selected_values:
            selected_values = values
        if wants_average:
            average = sum(value for _, value in selected_values) / len(selected_values)
            scope = "named" if named_groups else "selected"
            answers.append(f"The average {metric.label} across the {scope} {group_label}s is {_format(average, metric.unit)}.")
        else:
            ordered_all = sorted(selected_values, key=lambda item: item[1], reverse=not wants_low)
            requested = ordered_all[:min(count, len(ordered_all))]
            cutoff = _format(requested[-1][1], metric.unit)
            # Preserve every tie at the requested cutoff using displayed precision.
            leaders = [(name, value) for name, value in ordered_all if name in {item[0] for item in requested} or _format(value, metric.unit) == cutoff]
            direction = "lowest" if wants_low else "highest"
            ranked_text = "; ".join(f"{rank}. {name}: {_format(value, metric.unit)}" for rank, (name, value) in enumerate(leaders, 1))
            requested_n = min(count, len(ordered_all))
            tie_note = f" {len(leaders)} results are shown because a tie occurs at the requested cutoff." if len(leaders) > requested_n else ""
            answers.append(f"The requested {direction} {requested_n} {group_label}{'s' if requested_n != 1 else ''} for {metric.label} {'are' if requested_n != 1 else 'is'}: {ranked_text}.{tie_note}")
        ordered = sorted(selected_values, key=lambda item: item[1], reverse=not wants_low)
        rows.append(f"{metric.label}: " + "; ".join(f"{name}: {_format(value, metric.unit)}" for name, value in ordered) + ".")
    if not answers:
        return None
    limitation = "The ranking is descriptive within the currently selected hospitals and does not establish cause, statistical significance, or a patient-care conclusion."
    return {
        "answer": " ".join(answers + rows),
        "calculation": f"Calculate each explicitly named metric separately for every applicable {group_label}; rank in the requested direction or take the arithmetic mean. Ties use displayed precision.",
        "evidence": "Synthetic Result / Analytical Signal", "limitation": limitation,
        "display": {"title": f"{visual} — Requested Ranking", "filters": _selected_filter_summary(daily, encounters),
                    "answer": " ".join(answers), "what_matters": rows,
                    "why": "The answer follows from the separately calculated hospital values shown under What matters; metrics with different units are never averaged together.",
                    "actions": ["Validate definitions, denominators, time coverage, and peer comparability before acting on the rank."],
                    "action_heading": "What Leadership Should Validate", "limitation": limitation},
    }


def _entity_position_interpretation(visual, spec, question, daily, encounters):
    """Explain a named hospital's plotted position without inventing a cause."""
    q = normalized_text(question)
    hospitals = sorted(set(daily.hospital.unique()) | set(encounters.hospital.unique()))
    hospital = next((name for name in hospitals if normalized_text(name) in q), None)
    tokens = flexible_tokens(question)
    if hospital is None or not spec.get("metrics") or not ({"why", "low", "high", "bottom", "top", "outlier", "average"} & tokens):
        return None

    if visual == "Discharge Delay and ED Boarding":
        grouped = daily.groupby("hospital").agg(
            boarding=("boarding_hours", "mean"),
            delay=("discharge_order_to_exit_hours", "mean"),
            arrivals=("ed_arrivals", "sum"),
        )
        if hospital not in grouped.index:
            return None
        row = grouped.loc[hospital]
        boarding_order = grouped.boarding.sort_values()
        delay_order = grouped.delay.sort_values()
        boarding_peers = ", ".join(f"{name.replace('GulfStar ', '')} {value:.2f}" for name, value in boarding_order.items() if name != hospital)
        delay_peers = ", ".join(f"{name.replace('GulfStar ', '')} {value:.2f}" for name, value in delay_order.items() if name != hospital)
        boarding_rank = int(boarding_order.index.get_loc(hospital)) + 1
        delay_rank = int(delay_order.index.get_loc(hospital)) + 1
        count = len(grouped)

        def position(rank):
            if count == 1:
                return "the only selected value"
            if rank == 1:
                return "lowest"
            if rank == count:
                return "highest"
            return "in the middle"

        boarding_position = position(boarding_rank)
        delay_position = position(delay_rank)
        if boarding_position == delay_position:
            position_summary = f"{boarding_position} on both plotted measures"
        else:
            position_summary = f"{boarding_position} on ED Boarding and {delay_position} on Discharge Order-to-Exit"
        answer = (
            f"{hospital} is {position_summary}. Its ED Boarding value is {row.boarding:.2f} hours and its "
            f"Discharge Order-to-Exit value is {row.delay:.2f} hours. Those values explain where the point appears; "
            "the visual does not identify the operational cause."
        )
        what_matters = [
            f"ED Boarding: {row.boarding:.2f} hours versus {boarding_peers} hours.",
            f"Discharge Order-to-Exit: {row.delay:.2f} hours versus {delay_peers} hours.",
            f"Bubble size represents {row.arrivals:,.0f} selected ED arrivals—not performance severity.",
        ]
        actions = [
            "Confirm that the relative position persists by month, day, and operating shift.",
            "Validate admission-decision, bed-ready, placement, discharge-order, and exit timestamps.",
            "Compare demand, staffed capacity, pending admissions, and discharge reliability before attributing the difference.",
        ]
        limitation = f"The chart shows a descriptive difference; it cannot explain why {hospital}'s values differ or establish causality."
        return {
            "answer": answer + " " + " ".join(what_matters) + " " + limitation,
            "calculation": "Hospital means for discharge_order_to_exit_hours and boarding_hours; bubble size = total selected ed_arrivals.",
            "evidence": "Synthetic Result",
            "limitation": limitation,
            "display": {
                "title": f"{hospital} — Visual Position",
                "filters": _selected_filter_summary(daily, encounters),
                "answer": answer,
                "what_matters": what_matters,
                "actions": actions,
                "action_heading": "What Leadership Should Validate",
                "limitation": limitation,
            },
        }

    comparisons = []
    for key in spec.get("metrics", ()):
        metric = _metric_by_key(key)
        if metric is None:
            continue
        values = []
        for name in hospitals:
            value = _value(metric, daily[daily.hospital == name], encounters[encounters.hospital == name])
            if not pd.isna(value):
                values.append((name, value))
        entity_value = next((value for name, value in values if name == hospital), None)
        if entity_value is None:
            continue
        ordered = sorted(values, key=lambda item: item[1])
        rank = next(index for index, item in enumerate(ordered, 1) if item[0] == hospital)
        comparisons.append(f"{metric.label}: {_format(entity_value, metric.unit)}; rank {rank} of {len(ordered)} from low to high.")
    if not comparisons:
        return None
    answer = f"{hospital}'s position reflects the values plotted for the selected visual. It does not, by itself, explain why those values differ."
    limitation = "This is a descriptive comparison. Validate underlying definitions, denominators, timing, and operating context before attributing cause."
    return {
        "answer": answer + " " + " ".join(comparisons),
        "calculation": spec["calculation"], "evidence": "Synthetic Result", "limitation": limitation,
        "display": {
            "title": f"{hospital} — Visual Position", "filters": _selected_filter_summary(daily, encounters),
            "answer": answer, "what_matters": comparisons,
            "actions": ["Validate the underlying data and operating context before assigning a cause."],
            "action_heading": "What Leadership Should Validate", "limitation": limitation,
        },
    }


def _funnel_stage_interpretation(visual, question, daily, encounters):
    if visual != "System Patient-Flow Funnel" or daily.empty:
        return None
    q = normalized_text(question)
    tokens = flexible_tokens(question)
    if not ({"why", "low", "high", "mean", "explain"} & tokens):
        return None
    admissions = int(daily.admissions.sum())
    arrivals = int(daily.ed_arrivals.sum())
    discharges = int(daily.discharges.sum())
    boarding = daily.boarding_hours.mean()
    delayed_share = float(pd.Series([(boarding - 4) / 8]).clip(0, .55).iloc[0])
    delayed = int(admissions * delayed_share)
    within_target = admissions - delayed
    delayed_pct = delayed / max(admissions, 1)
    admission_pct = admissions / max(arrivals, 1)
    stage = None
    if "delayed placement" in q:
        stage = "delayed"
    elif "within portfolio target" in q or "within target" in q or "target placement" in q:
        stage = "within_target"
    elif "ed arrival" in q or ("arrival" in q and "discharge" not in q):
        stage = "arrivals"
    elif "admission" in q:
        stage = "admissions"
    elif "discharge" in q:
        stage = "discharges"
    if stage is None:
        return None

    stage_content = {
        "arrivals": {
            "title": "ED Arrivals",
            "answer": f"ED Arrivals is {arrivals:,.0f}. It is the largest value because it represents all selected ED visits, while Admissions includes only the portion admitted to inpatient care.",
            "matters": [
                f"Admissions: {admissions:,.0f}, or {100 * admission_pct:.1f}% of ED Arrivals.",
                f"The remaining {arrivals - admissions:,.0f} arrivals were not counted as inpatient admissions; this funnel does not show their individual dispositions.",
                "A large arrival count is demand volume—not automatically poor performance or avoidable utilization.",
            ],
            "actions": [
                "Validate ED-arrival and admission definitions and confirm that repeat, transfer, and observation encounters are handled consistently.",
                "Review arrivals by hospital, day, hour, acuity, and disposition before labeling demand unusually high.",
                "Compare demand with staffed capacity, provider coverage, LWBS, boarding, and admission conversion.",
            ],
        },
        "admissions": {
            "title": "Admissions",
            "answer": f"Admissions is {admissions:,.0f}, representing {100 * admission_pct:.1f}% of ED Arrivals. It is lower than ED Arrivals because not every ED visit becomes an inpatient admission.",
            "matters": [f"ED Arrivals: {arrivals:,.0f}.", f"Admissions: {admissions:,.0f} ({100 * admission_pct:.1f}% of arrivals).", "The funnel does not distinguish discharge, observation, transfer, or other non-admission dispositions."],
            "actions": ["Validate admission and disposition definitions.", "Review conversion by hospital, acuity, service line, and time period.", "Compare admission demand with staffed capacity and placement performance."],
        },
        "within_target": {
            "title": "Bed Placement Within Portfolio Target",
            "answer": f"Modeled Within-Target Placements is {within_target:,.0f}, or {100 * (1 - delayed_pct):.1f}% of admissions. It is the modeled complement of delayed placements—not an observed timestamp result.",
            "matters": [f"Admissions: {admissions:,.0f}.", f"Within-target placements: {within_target:,.0f}.", f"Modeled delayed placements: {delayed:,.0f}."],
            "actions": ["Validate bed-request, bed-ready, and placement timestamps.", "Compare modeled and observed target performance by hospital and shift.", "Replace the modeled split with validated transitions before production use."],
        },
        "delayed": {
            "title": "Modeled Delayed Placements",
            "answer": f"Modeled Delayed Placements is {delayed:,.0f}, or {100 * delayed_pct:.1f}% of admissions. It is lower because it represents only the modeled delayed subset of admissions; it is not total patient-flow volume.",
            "matters": [f"Admissions: {admissions:,.0f}.", f"Modeled within-target placements: {within_target:,.0f} ({100 * (1 - delayed_pct):.1f}% of admissions).", f"Modeled delayed placements: {delayed:,.0f} ({100 * delayed_pct:.1f}% of admissions).", f"The delayed share is derived from average ED Boarding of {boarding:.1f} hours using the dashboard's bounded scenario formula.", f"Discharges ({discharges:,.0f}) are a separate selected-period operating total—not the next subset after delayed placements."],
            "actions": ["Validate admission-decision, bed-ready, placement, and discharge timestamps before treating the split as operational fact.", "Compare the modeled delayed share with observed placement performance by hospital, day, and shift.", "Replace the modeled split with validated patient-level transitions for production use."],
        },
        "discharges": {
            "title": "Discharges",
            "answer": f"Discharges is {discharges:,.0f}. It is a separate selected-period operating total and can be larger than a modeled placement subset because this chart is not a cohort-linked sequential funnel.",
            "matters": [f"Admissions: {admissions:,.0f}.", f"Discharges: {discharges:,.0f}.", "Admissions and discharges occurring in the same reporting window do not necessarily represent the same patients."],
            "actions": ["Validate admission and discharge cohort timing.", "Use patient-level encounter identifiers for a true sequential funnel.", "Review discharge reliability separately from modeled placement status."],
        },
    }[stage]
    answer = stage_content["answer"]
    what_matters = stage_content["matters"]
    actions = stage_content["actions"]
    modeled_stage = stage in {"within_target", "delayed"}
    evidence = "Modeled Estimate" if modeled_stage else "Synthetic Result"
    calculation = (
        "delayed share = clip((mean boarding hours − 4) / 8, 0%, 55%); delayed placements = admissions × delayed share; within-target placements = admissions − delayed placements."
        if modeled_stage else
        f"{stage_content['title']} = sum of the selected synthetic daily operating count."
    )
    limitation = (
        "The placement split is modeled from aggregate boarding pressure; it is not an observed patient-level funnel and does not identify cause."
        if modeled_stage else
        "This is aggregate synthetic volume. The chart is not a cohort-linked patient journey and does not establish why the volume is high or low."
    )
    return {
        "answer": answer + " " + " ".join(what_matters),
        "calculation": calculation, "evidence": evidence, "limitation": limitation,
        "display": {
            "title": stage_content["title"], "filters": _selected_filter_summary(daily, encounters),
            "answer": answer, "what_matters": what_matters, "actions": actions,
            "action_heading": "What Leadership Should Validate", "limitation": limitation,
        },
    }


def _monthly_margin_flow_interpretation(visual, question, daily, encounters):
    """Rank complete months on contribution, boarding, or a disclosed balanced rule."""
    if visual != "Margin and Flow Pressure by Month" or daily.empty:
        return None
    tokens = flexible_tokens(question)
    named_months = requested_month_numbers(question)
    directional = bool(tokens & {"good", "bad", "high", "low", "highest", "lowest", "best", "worst", "top", "bottom"})
    comparison = bool(tokens & {"compare", "versus", "between", "average", "mean"})
    if not named_months and ("month" not in tokens or not directional):
        return None
    if named_months and not (directional or comparison or "month" in tokens):
        return None
    dated = daily.assign(month=pd.to_datetime(daily["date"]).dt.to_period("M").dt.to_timestamp())
    monthly = dated.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), cost=("cost", "sum"),
        boarding=("boarding_hours", "mean"), covered_days=("date", "nunique"),
    ).rename(columns={"month": "date"})
    monthly["contribution"] = monthly.revenue - monthly.cost
    monthly["complete"] = monthly.covered_days == monthly.date.dt.days_in_month
    complete = monthly[monthly.complete].copy()
    if named_months:
        complete = complete[complete.date.dt.month.isin(named_months)].copy()
        complete["calendar_month"] = complete.date.dt.month
        complete = complete.groupby("calendar_month", as_index=False).agg(
            contribution=("contribution", "mean"), boarding=("boarding", "mean"),
            occurrences=("date", "size"),
        )
        complete["date"] = pd.to_datetime({
            "year": [2000] * len(complete),
            "month": complete.calendar_month,
            "day": [1] * len(complete),
        })
        complete["label"] = complete.date.dt.strftime("%B")
    else:
        complete["label"] = complete.date.dt.strftime("%B %Y")
    if complete.empty:
        return None
    complete["contribution_percentile"] = complete.contribution.rank(pct=True, method="average")
    complete["boarding_percentile"] = (-complete.boarding).rank(pct=True, method="average")
    complete["balanced_score"] = (complete.contribution_percentile + complete.boarding_percentile) / 2
    asks_worst = bool(tokens & {"bad", "worst", "low", "lowest"}) and "boarding" not in tokens
    balanced = complete.loc[complete.balanced_score.idxmin() if asks_worst else complete.balanced_score.idxmax()]
    highest_contribution = complete.loc[complete.contribution.idxmax()]
    lowest_boarding = complete.loc[complete.boarding.idxmin()]
    highest_boarding = complete.loc[complete.boarding.idxmax()]
    lowest_contribution = complete.loc[complete.contribution.idxmin()]
    label = "worst" if asks_worst else "best"
    count = min(requested_count(question), len(complete))
    asks_contribution = bool(tokens & {"contribution", "margin", "financial", "finance"})
    asks_boarding = "boarding" in tokens
    asks_balanced = bool(tokens & {"balance", "balanced", "overall", "combined"})
    if named_months and not directional and not any((asks_contribution, asks_boarding, asks_balanced)):
        selected = complete.sort_values("date")
        title = f"Requested Months - Margin and Flow"
        listed = "; ".join(
            f"{row.label}: ${row.contribution:,.0f} average monthly contribution and {row.boarding:.2f} average boarding hours"
            for row in selected.itertuples()
        )
        answer = f"Only the requested month selections are compared: {listed}."
    elif asks_contribution and not asks_balanced:
        selected = complete.sort_values("contribution", ascending=asks_worst).head(count)
        title = f"{'Bottom' if asks_worst else 'Top'} {count} Operating Contribution Month{'s' if count != 1 else ''}"
        listed = "; ".join(f"{rank}. {row.label}: ${row.contribution:,.0f}" for rank, row in enumerate(selected.itertuples(), 1))
        answer = f"The requested {'lowest' if asks_worst else 'highest'} {count} complete month{'s are' if count != 1 else ' is'}: {listed}."
    elif asks_boarding and not asks_balanced:
        selected = complete.sort_values("boarding", ascending=not asks_worst).head(count)
        title = f"{'Highest' if asks_worst else 'Lowest'} {count} ED Boarding Month{'s' if count != 1 else ''}"
        listed = "; ".join(f"{rank}. {row.label}: {row.boarding:.2f} hours" for rank, row in enumerate(selected.itertuples(), 1))
        answer = f"The requested {'highest' if asks_worst else 'lowest'} {count} complete month{'s are' if count != 1 else ' is'}: {listed}."
    else:
        selected = complete.sort_values("balanced_score", ascending=asks_worst).head(count)
        title = f"{label.title()} {count} Balanced Month{'s' if count != 1 else ''} - Margin and Flow"
        listed = "; ".join(
            f"{rank}. {row.label}: ${row.contribution:,.0f} contribution and {row.boarding:.2f} boarding hours"
            for rank, row in enumerate(selected.itertuples(), 1)
        )
        answer = f"Using the equal-weight balanced ranking, the requested {label} {count} complete month{'s are' if count != 1 else ' is'}: {listed}."
    what_matters = [
        f"Highest Operating Contribution: {highest_contribution.label} at ${highest_contribution.contribution:,.0f}.",
        f"Lowest ED Boarding: {lowest_boarding.label} at {lowest_boarding.boarding:.2f} hours.",
        f"Balanced {label.title()} Month: {balanced.label} at ${balanced.contribution:,.0f} and {balanced.boarding:.2f} hours.",
    ]
    partial = monthly[~monthly.complete]
    if named_months:
        partial = partial[partial.date.dt.month.isin(named_months)]
    if not partial.empty:
        partial_names = ", ".join(f"{row.date:%B %Y} ({int(row.covered_days)} days)" for row in partial.itertuples())
        what_matters.append(f"Excluded partial month(s) from ranking: {partial_names}.")
    why = (
        f"The displayed order uses the {label} equal-weight average percentile ranks when monthly Operating Contribution is ranked higher-is-better "
        "and ED Boarding is ranked lower-is-better with equal weight. The separate contribution and boarding leaders are shown because "
        "'best' depends on which outcome leadership prioritizes."
    )
    limitation = "The balanced ranking is an explicit dashboard interpretation rule, not a validated enterprise target or causal conclusion. Partial months are excluded from month-total comparisons."
    return {
        "answer": answer + " " + " ".join(what_matters),
        "calculation": "Monthly Operating Contribution = sum(revenue) - sum(cost). Monthly ED Boarding = mean(boarding_hours). Named calendar months are averaged across their complete occurrences in the selected date range. Balanced score = mean(percentile rank of contribution, percentile rank of negative boarding) across the requested comparison set.",
        "evidence": "Synthetic Result / Analytical Signal", "limitation": limitation,
        "display": {
            "title": title, "filters": _selected_filter_summary(daily, encounters),
            "answer": answer, "what_matters": what_matters, "why": why,
            "actions": [
                "Confirm whether leadership means highest contribution, lowest boarding, or the disclosed balanced view.",
                "Validate monthly revenue, cost, boarding timestamps, and complete-period coverage.",
                "Review hospital and service-line contributors before attributing the selected month's position.",
            ],
            "action_heading": "What Leadership Should Validate", "limitation": limitation,
        },
    }


def _ambiguous_visual_question(visual, spec, question):
    """Return safe choices only when different interpretations change the answer."""
    tokens = flexible_tokens(question)
    if visual == "Margin and Flow Pressure by Month" and ("month" in tokens or requested_month_numbers(question)):
        count = requested_count(question)
        named_month_phrase = requested_month_phrase(question)
        month_phrase = f"{count} months" if count > 1 else "month"
        comparison_scope = f" among {named_month_phrase}" if named_month_phrase else ""
        broad_best = bool(tokens & {"good", "bad", "best", "worst", "high", "low", "highest", "lowest"})
        has_outcome = bool(tokens & {"contribution", "margin", "financial", "finance", "boarding", "balance", "balanced", "overall", "combined"})
        if broad_best and not has_outcome:
            direction = "worst" if bool(tokens & {"bad", "worst", "low", "lowest"}) else "best"
            if direction == "best":
                suggestions = [
                    f"Which {month_phrase} had the highest operating contribution{comparison_scope}?",
                    f"Which {month_phrase} had the lowest ED boarding{comparison_scope}?",
                    f"Which {month_phrase} had the best balance of operating contribution and ED boarding{comparison_scope}?",
                ]
            else:
                suggestions = [
                    f"Which {month_phrase} had the lowest operating contribution{comparison_scope}?",
                    f"Which {month_phrase} had the highest ED boarding{comparison_scope}?",
                    f"Which {month_phrase} had the worst balance of operating contribution and ED boarding{comparison_scope}?",
                ]
            return {
                "answer": "That wording can mean different things on this visual. Choose the outcome that matches your decision so the dashboard does not guess.",
                "evidence": "Validation Required — Clarification",
                "calculation": "No ranking was run until an outcome is selected.",
                "limitation": "Operating Contribution and ED Boarding use different units, so neither should silently define overall performance.",
                "suggestions": suggestions,
                "keywords": extracted_keywords(question),
            }
    if visual not in {"Executive Health Score by Domain", "Margin and Flow Pressure by Month"} and len(spec.get("metrics", ())) > 1:
        directional = bool(tokens & {"high", "highest", "low", "lowest", "top", "bottom", "average"})
        explicit = [metric for metric in _metrics_in(question) if metric.key in spec.get("metrics", ())]
        names_hospital = "gulfstar" in normalized_text(question) or any(name in normalized_text(question) for name in ("community", "medical center", "north"))
        if directional and not explicit and not names_hospital:
            wants_low = bool(tokens & {"bad", "low", "lowest", "bottom"})
            wants_average = "average" in tokens
            count = requested_count(question)
            hospital_phrase = f"{count} hospitals" if count > 1 else "hospital"
            suggestions = []
            for key in spec["metrics"]:
                metric = _metric_by_key(key)
                if metric is None:
                    continue
                if wants_average:
                    suggestions.append(f"What is the average {metric.label} across the selected hospitals?")
                else:
                    direction = "lowest" if wants_low else "highest"
                    suggestions.append(f"Which {hospital_phrase} {'have' if count > 1 else 'has'} the {direction} {metric.label}?")
                if len(suggestions) == 3:
                    break
            if suggestions:
                return {
                    "answer": "This visual contains multiple measures, so that question has more than one valid answer. Choose the measure you mean.",
                    "evidence": "Validation Required — Clarification",
                    "calculation": "No cross-unit ranking or average was run.",
                    "limitation": "Measures with different units or meanings cannot be safely ranked or averaged together.",
                    "suggestions": suggestions, "keywords": extracted_keywords(question),
                }
    return None


def _weakest_visual_metric(spec, daily, encounters):
    candidates = []
    for key in spec.get("metrics", ()):
        metric = _metric_by_key(key)
        detail = METRIC_DETAIL.get(key, {})
        if metric is None or not {"target", "bad", "direction"}.issubset(detail):
            continue
        value = _value(metric, daily, encounters)
        if pd.isna(value):
            continue
        score = _higher_score(value, detail["target"], detail["bad"]) if detail["direction"] == "high" else _lower_score(value, detail["target"], detail["bad"])
        candidates.append((score, metric))
    if candidates:
        return min(candidates, key=lambda item: item[0])[1]
    return _metric_by_key(spec.get("metrics", (None,))[0]) if spec.get("metrics") else None


def _kpi_card_performance_interpretation(visual, question, daily, encounters):
    """Rank unlike KPI cards safely on their disclosed normalized threshold scores."""
    if visual != "Executive KPI Cards" or daily.empty:
        return None
    tokens = flexible_tokens(question)
    q = normalized_text(question)
    explicitly_asks_about_kpis = bool(re.search(r"\bkpis?\b|\bkey performance indicators?\b", q))
    ranking_language = bool(tokens & {
        "best", "strong", "strongest", "highest", "top", "lowest", "low", "weak",
        "weakest", "worst", "bottom", "critical", "concern", "improve", "improvement",
    }) or bool(re.search(r"\b(best|strongest|highest|top|lowest|weakest|worst|bottom|critical|improv\w*)\b", q))
    if not explicitly_asks_about_kpis or not ranking_language:
        return None
    named_metrics = [
        metric for metric in _metrics_in(question)
        if metric.key in VISUALS["1"]["Executive KPI Cards"]["metrics"]
    ]
    if named_metrics and bool(re.search(r"\b(improve|improvement|better|fix)\b", q)):
        # Preserve the existing metric-specific improvement response, which is
        # more detailed than a portfolio ranking for explicitly named measures.
        return None
    rows = []
    for key in VISUALS["1"]["Executive KPI Cards"]["metrics"]:
        metric = _metric_by_key(key)
        detail = METRIC_DETAIL.get(key, {})
        if metric is None or not {"target", "bad", "direction"}.issubset(detail):
            continue
        value = _value(metric, daily, encounters)
        if pd.isna(value):
            continue
        score = (
            _higher_score(value, detail["target"], detail["bad"])
            if detail["direction"] == "high"
            else _lower_score(value, detail["target"], detail["bad"])
        )
        rows.append((metric, value, score))
    if not rows:
        return None

    wants_improvement = bool(re.search(r"\b(improve|improvement|better|fix|action)\b", q))
    wants_critical = bool(re.search(r"\b(critical|urgent|red flag|danger)\b", q))
    wants_low = wants_critical or bool(re.search(r"\b(lowest|low|weak|weakest|worst|bottom|concern)\b", q))
    count = min(requested_count(question, default=3), len(rows))
    ordered = sorted(rows, key=lambda row: row[2], reverse=not wants_low)
    selected = [row for row in ordered if row[0] in named_metrics] if named_metrics else ordered[:count]
    if wants_critical:
        critical = [row for row in rows if row[2] < 50]
        if critical:
            selected = sorted(critical, key=lambda row: row[2])
        else:
            selected = sorted(rows, key=lambda row: row[2])[:count]

    def status(score):
        if score < 50:
            return "Critical"
        if score < 80:
            return "Needs attention"
        return "Favorable"

    matters = [
        f"{rank}. {metric.label}: {_format(value, metric.unit)}; modeled performance score {score:.0f}/100; {status(score)}."
        for rank, (metric, value, score) in enumerate(selected, 1)
    ]
    if wants_critical and not any(score < 50 for _, _, score in rows):
        answer = "No operating KPI meets the dashboard's modeled critical threshold below 50/100. The least favorable KPIs are shown for attention."
        title = "Critical KPI Review"
    elif wants_improvement:
        answer = "The improvement priorities are the named KPIs, or otherwise the three least favorable current KPI results, ranked on a common 0–100 threshold scale."
        title = "KPI Improvement Priorities"
    elif wants_low:
        answer = f"The least favorable {len(selected)} operating KPI{'s' if len(selected) != 1 else ''} are ranked below using each metric's documented direction and thresholds."
        title = "Lowest-Performing KPIs"
    else:
        answer = f"The strongest {len(selected)} operating KPI{'s' if len(selected) != 1 else ''} are ranked below using each metric's documented direction and thresholds."
        title = "Best-Performing KPIs"

    actions = []
    if wants_improvement or wants_low or wants_critical:
        for metric, _, _ in selected:
            owner, validation, intervention = IMPROVEMENT_PATHS.get(
                metric.key,
                ("accountable operational executive", metric.calculation, "run a time-bounded improvement cycle"),
            )
            actions.append(
                f"{metric.label}: assign the {owner}; validate {validation}; then {intervention}."
            )
    else:
        actions = [
            "Confirm that the favorable position persists by hospital, service line, and comparable period.",
            "Use the modeled score for portfolio screening—not as a certified external benchmark.",
        ]
    limitation = (
        "Raw KPI values use different units and cannot be ranked directly. This answer uses transparent illustrative threshold scores; "
        "it does not establish cause, statistical significance, or patient-care guidance. Decision Integrity and the Executive Health Score "
        "are separate governance/composite cards and are not mixed into the operating-KPI ranking."
    )
    return {
        "answer": answer + " " + " ".join(matters),
        "calculation": "For each operating KPI, map the current result to 0–100 between its documented favorable and unfavorable thresholds, honor higher- or lower-is-better direction, then rank the normalized scores.",
        "evidence": "Synthetic Result / Modeled Estimate", "limitation": limitation,
        "display": {
            "title": title, "filters": _selected_filter_summary(daily, encounters),
            "answer": answer, "what_matters": matters, "actions": actions,
            "action_heading": "What Leadership Should Do" if actions else "What Leadership Should Know",
            "why": "The ranking compares each KPI with its own disclosed favorable and unfavorable thresholds, avoiding invalid comparisons of percentages, hours, rates, counts, and composite scores.",
            "limitation": limitation,
        },
    }


def _metric_improvement(metric, daily, encounters, visual=None):
    value = _value(metric, daily, encounters)
    if pd.isna(value):
        return None
    owner, validation, intervention = IMPROVEMENT_PATHS.get(
        metric.key,
        ("accountable operational executive", metric.calculation, "run a time-bounded validation and improvement cycle"),
    )
    hospitals = sorted(daily.hospital.unique()) if not daily.empty else sorted(encounters.hospital.unique())
    filter_summary = _selected_filter_summary(daily, encounters)
    hospital_values = []
    for hospital in hospitals:
        hd = daily[daily.hospital == hospital]
        he = encounters[encounters.hospital == hospital]
        hospital_value = _value(metric, hd, he)
        if not pd.isna(hospital_value):
            hospital_values.append((hospital, hospital_value))
    concentration = None
    if hospital_values:
        worst = min(hospital_values, key=lambda item: item[1]) if metric.better == "high" else max(hospital_values, key=lambda item: item[1])
        concentration = f"Strongest pressure: {worst[0]} at {_format(worst[1], metric.unit)}."
    detail = METRIC_DETAIL.get(metric.key, {})
    threshold = None
    displayed_context = f"Current result: {_format(value, metric.unit)}."
    if "target" in detail:
        gap = value - detail["target"]
        gap_text = f"{100 * abs(gap):.1f} percentage points" if metric.unit == "percent" else _format(abs(gap), metric.unit)
        relation = "above" if gap > 0 else "below" if gap < 0 else "at"
        threshold = f"{gap_text} {relation} the dashboard's illustrative favorable threshold."
        if visual == "Executive Health Score by Domain":
            component_score = _higher_score(value, detail["target"], detail["bad"]) if detail["direction"] == "high" else _lower_score(value, detail["target"], detail["bad"])
            domain = METRIC_DOMAINS.get(metric.key, metric.label)
            if metric.key == "experience":
                displayed_context = (
                    f"The displayed Patient Experience domain score is {component_score:.0f}/100. "
                    f"It is derived from the underlying synthetic Patient Experience KPI of {_format(value, metric.unit)}; "
                    "76.8% and 63/100 are different scales, not conflicting results."
                )
            else:
                displayed_context = (
                    f"The underlying {metric.label} result is {_format(value, metric.unit)} and maps to a modeled component score of {component_score:.0f}/100. "
                    f"That component contributes to the displayed {domain} domain score together with the other documented domain components."
                )
    related = []
    for key in RELATED_METRICS.get(metric.key, ()):
        related_metric = _metric_by_key(key)
        related_value = _value(related_metric, daily, encounters)
        if not pd.isna(related_value):
            related.append(f"{related_metric.label} {_format(related_value, related_metric.unit)}")
    what_matters = [item for item in (threshold, concentration) if item]
    if related:
        what_matters.append("Related signals: " + ", ".join(related) + ".")
    actions = [
        f"Assign the {owner} as accountable executive.",
        f"Validate {validation}.",
        intervention[:1].upper() + intervention[1:] + ".",
        f"Monitor {metric.label} and related guardrails through a time-bounded PDSA cycle.",
    ]
    limitation = "Use this to prioritize investigation—not to infer cause or make a patient-care decision."
    text = (
        f"Improvement opportunity — {metric.label}: {displayed_context} "
        + " ".join(what_matters)
        + " Leadership response: " + " ".join(f"{i}) {action}" for i, action in enumerate(actions, 1))
        + " " + limitation
    )
    return {
        "text": text,
        "display": {
            "title": metric.label,
            "filters": filter_summary,
            "answer": displayed_context,
            "what_matters": what_matters,
            "actions": actions,
            "limitation": limitation,
        },
    }


DOCUMENTED_CONTENT = {
    "Executive Priority Queue": (
        (("severity", "priority score"), "Severity is the dashboard's modeled size of the validated performance gap; it orders the queue before exposure is used as a tie-breaker.", "Modeled domain-gap logic; severity descending, then modeled exposure descending.", "Modeled Estimate"),
        (("exposure", "financial exposure"), "Exposure is an illustrative estimate of value associated with the priority—not booked loss, guaranteed savings, or a forecast.", "Documented modeled exposure assumptions for the priority domain.", "Modeled Estimate"),
        (("owner", "accountable owner"), "The owner identifies the executive role expected to validate the signal and coordinate follow-up; it does not assign fault.", "Predefined domain-to-owner governance mapping.", "Validation Required — Governance"),
    ),
    "System Patient-Flow Funnel": (
        (("stage", "placement", "funnel"), "Each stage is a modeled portfolio count from ED arrivals through admission demand and placement. The largest narrowing is a scenario signal for where flow loss may be concentrated.", "Placement stages are derived from selected aggregate demand and average boarding pressure; they are not patient-level transitions.", "Modeled Estimate"),
    ),
    "Staffing Intensity Versus Composite Outcome Pressure": (
        (("outcome pressure", "pressure index", "trendline"), "Outcome pressure is an illustrative composite used to compare hospital-level outcome signals. The fitted line shows association only and must not be read as a staffing effect.", "Normalized synthetic outcome components plotted against aggregate hours per patient day; ordinary least-squares line is descriptive.", "Modeled Estimate"),
    ),
    "Intervention Value Frontier": (
        (("annual value", "value"), "Annual value is the intervention table's modeled yearly benefit estimate. A higher position means greater assumed value, not a guaranteed return.", "Modeled annual_value from the intervention scenario table.", "Modeled Estimate"),
        (("annual cost", "cost"), "Annual cost is the modeled yearly resource requirement shown on the horizontal axis; it is not an approved budget.", "Modeled annual_cost from the intervention scenario table.", "Modeled Estimate"),
        (("capacity days", "capacity"), "Bubble size represents modeled capacity days released. Larger bubbles indicate more assumed capacity benefit, not observed bed availability.", "Modeled capacity_days from the intervention scenario table.", "Modeled Estimate"),
        (("confidence",), "Color represents the scenario's predefined confidence factor. It communicates assumption strength; it is not a statistical confidence interval.", "Predefined intervention confidence factor.", "Modeled Estimate"),
        (("roi", "return"), "ROI compares modeled net value with modeled annual cost and should be considered with confidence, feasibility, capacity impact, and strategic fit.", "ROI = (modeled annual value − modeled annual cost) / modeled annual cost.", "Modeled Estimate"),
    ),
    "Selected Portfolio Table": (
        (("budget", "spend", "selected"), "The table shows the interventions retained by the current budget scenario after modeled priority sorting. Inclusion is a scenario result, not funding approval.", "Modeled interventions are sorted by priority; cumulative annual cost must remain within the selected budget.", "Modeled Estimate"),
    ),
    "Decision Integrity Components": (
        (("source authority", "completeness", "definitions", "timeliness", "causal confidence", "external validity", "component"), "Each bar is an illustrative evidence-readiness component. A shorter bar identifies a larger governance or validation gap; it is not model accuracy.", "Predefined 0–100 readiness components displayed independently; review the named component's evidence before use.", "Validation Required — Governance"),
    ),
    "Source and Evidence Registry": (
        (("source", "evidence type", "registry", "limitation", "lineage"), "Each row documents what a source contributes, its evidence category, intended use, and known limitation. It supports traceability but does not certify production readiness.", "Documented source/evidence metadata; no analytical inference is made from the registry itself.", "Validation Required — Governance"),
    ),
    "Privacy Risk by Event Type and Severity": (
        (("records affected", "severity", "event type", "privacy event"), "Bar length is the number of synthetic records affected, grouped by event type; color shows the synthetic severity category. Exposure is not the same as a legally reportable breach.", "Sum of synthetic records_affected grouped by event_type and severity.", "Synthetic Result / Validation Required"),
    ),
    "CIPP-Informed Governance Gates": (
        (("gate", "privacy", "owner", "purpose limitation", "minimum necessary"), "Each gate is a required governance question with an accountable review role. It is a decision checkpoint, not proof of compliance.", "Documented privacy-by-design control questions and owner mapping.", "Validation Required — Governance"),
    ),
    "Statistical Process Control Chart": (
        (("center line", "ucl", "lcl", "control limit", "sigma", "spc"), "The center line is the selected monthly measure's mean; UCL and LCL are three-sigma analytic limits. A point beyond a limit is an investigation signal, not proof of failure or cause.", "Monthly aggregation; center = mean; limits = mean ± 3 sample standard deviations, with the lower limit clipped at zero where applicable.", "Synthetic Result / Analytical Signal"),
    ),
    "Pareto: Discharge Barriers": (
        (("barrier", "pareto", "count", "frequency"), "Bars rank synthetic discharge barriers by encounter frequency. The tallest category is the most frequently recorded—not automatically the most severe or causal.", "Count selected encounters by discharge_barrier and sort descending.", "Synthetic Result"),
    ),
    "PDSA Learning System": (
        (("plan", "do", "study", "act", "pdsa"), "Plan defines the aim and prediction; Do runs a small test; Study compares results with the prediction; Act decides whether to adopt, adapt, or abandon. The framework organizes learning but does not prove effectiveness.", "Documented Plan–Do–Study–Act learning cycle; evidence must come from the measured test.", "Validation Required — Improvement Method"),
    ),
}


DOCUMENTED_IMPROVEMENTS = {
    "Executive Priority Queue": (
        (("severity", "priority score"), "Validate the component metrics driving severity, confirm the accountable owner, and rerank only after corrected inputs are approved."),
        (("exposure", "financial exposure"), "Validate volume, unit value, avoidable share, and timing assumptions; report a range and keep booked loss separate from modeled exposure."),
        (("owner", "accountable owner"), "Confirm one accountable executive, named operational partners, a due date, and the evidence required for the next decision."),
    ),
    "System Patient-Flow Funnel": (
        (("stage", "placement", "funnel"), "Validate patient-level stage timestamps, identify the largest confirmed queue, assign an operational owner, and test one stage-specific flow change with balancing measures."),
    ),
    "Staffing Intensity Versus Composite Outcome Pressure": (
        (("outcome pressure", "pressure index", "trendline"), "Validate acuity, skill mix, unit, shift, and outcome definitions; investigate persistent outliers without treating the trendline as a staffing effect."),
    ),
    "Intervention Value Frontier": (
        (("annual value", "value", "annual cost", "cost", "capacity days", "capacity", "confidence", "roi", "return"), "Revalidate cost, benefit, capacity, timing, and confidence assumptions; compare ranges, fund in stages, and use milestone-based stop/go decisions."),
    ),
    "Selected Portfolio Table": (
        (("budget", "spend", "selected", "portfolio"), "Check concentration, feasibility, confidence, cumulative spend, and strategic coverage; stage funding and define stop/go milestones for every selected intervention."),
    ),
    "Decision Integrity Components": (
        (("source authority", "completeness", "definitions", "timeliness", "causal confidence", "external validity", "component"), "Start with the lowest readiness component, assign its governance owner, document the missing evidence, and block production use until the approval criterion is met."),
    ),
    "Source and Evidence Registry": (
        (("source", "evidence type", "registry", "limitation", "lineage"), "Add or repair the metric owner, definition, lineage, refresh date, validation status, and known limitation before using the source for an operational decision."),
    ),
    "Privacy Risk by Event Type and Severity": (
        (("records affected", "severity", "event type", "privacy event"), "Validate event classification and affected-record counts, prioritize confirmed high-severity exposure, and assign privacy/legal review before determining notification or remediation."),
    ),
    "CIPP-Informed Governance Gates": (
        (("gate", "privacy", "owner", "purpose limitation", "minimum necessary"), "Assign every open gate, document evidence and disposition, remediate the highest-risk gap, and require privacy/legal approval before deployment."),
    ),
    "Statistical Process Control Chart": (
        (("center line", "ucl", "lcl", "control limit", "sigma", "spc"), "Confirm stable definitions and denominators, investigate special-cause signals, test one process change, and monitor for sustained shift rather than reacting to routine variation."),
    ),
    "Pareto: Discharge Barriers": (
        (("barrier", "pareto", "count", "frequency"), "Validate category coding, select the highest-frequency actionable barrier, test a small barrier-specific response, and track both frequency and severity."),
    ),
    "PDSA Learning System": (
        (("plan", "do", "study", "act", "pdsa"), "Define a specific aim and prediction, run the smallest safe test, compare results with the prediction, and explicitly adopt, adapt, or abandon based on evidence."),
    ),
}


def _documented_improvement(visual, question):
    q = normalized_text(question)
    for aliases, action in DOCUMENTED_IMPROVEMENTS.get(visual, ()):
        if any(normalized_text(alias) in q for alias in aliases):
            return action + " This is a governance or operating response, not a causal or patient-care recommendation."
    return None


def _documented_content_interpretation(visual, question):
    q = normalized_text(question)
    for aliases, answer, calculation, evidence in DOCUMENTED_CONTENT.get(visual, ()):
        if any(normalized_text(alias) in q for alias in aliases):
            return {
                "answer": answer,
                "calculation": calculation,
                "evidence": evidence,
                "limitation": "This explanation is restricted to the visual's documented deterministic logic and requires local operational validation.",
            }
    return None


def _metric_detail_interpretation(metric, daily, encounters):
    value = _value(metric, daily, encounters)
    if pd.isna(value):
        return None
    detail = METRIC_DETAIL.get(metric.key, {})
    definition = detail.get("definition", metric.calculation)
    context = detail.get("context", "This is a descriptive synthetic dashboard metric requiring local validation.")
    hospital_values = []
    for hospital, hospital_daily in daily.groupby("hospital"):
        hospital_encounters = encounters[encounters.hospital == hospital]
        hospital_value = _value(metric, hospital_daily, hospital_encounters)
        if not pd.isna(hospital_value):
            hospital_values.append((hospital, hospital_value))
    variation = ""
    if hospital_values:
        ordered = sorted(hospital_values, key=lambda item: item[1], reverse=True)
        high_hospital, high_value = ordered[0]
        low_hospital, low_value = ordered[-1]
        variation = (
            f" Across the selected hospitals, {high_hospital} is highest at {_format(high_value, metric.unit)} "
            f"and {low_hospital} is lowest at {_format(low_value, metric.unit)}."
            if high_hospital != low_hospital else ""
        )
    threshold_interpretation = ""
    modeled_score = None
    if {"target", "bad", "direction"}.issubset(detail):
        if detail["direction"] == "high":
            modeled_score = _higher_score(value, detail["target"], detail["bad"])
            gap = value - detail["target"]
        else:
            modeled_score = _lower_score(value, detail["target"], detail["bad"])
            gap = value - detail["target"]
        gap_display = (
            f"{100 * abs(gap):.1f} percentage points"
            if metric.unit == "percent" else _format(abs(gap), metric.unit)
        )
        relation = "above" if gap > 0 else "below" if gap < 0 else "at"
        threshold_interpretation = (
            f" {detail['threshold_text']} The current value is {gap_display} {relation} the favorable threshold "
            f"and maps to an illustrative component score of {modeled_score:.0f}/100."
        )
    answer = (
        f"{metric.label} of {_format(value, metric.unit)} means {definition} is {_format(value, metric.unit)} for the current filters."
        f"{threshold_interpretation}{variation} What leadership should take from it: this value is a screening signal for comparison and follow-up, not a causal explanation."
    )
    return {
        "answer": answer,
        "calculation": metric.calculation + (f"; illustrative component score = {modeled_score:.0f}/100 after linear threshold mapping and clipping." if modeled_score is not None else "."),
        "evidence": "Synthetic Result / Modeled Estimate" if modeled_score is not None else "Synthetic Result",
        "limitation": context,
    }


def answer_visual_question(page, visual, question, daily, encounters):
    sheet = VISUALS.get(str(page).split(" ", 1)[0], {})
    selected_visual = visual
    visual, match_score = resolve_visual(page, selected_visual, question)
    selection_note = (
        f"Your question explicitly matched “{visual}”, so I used that visual instead of the dropdown selection “{selected_visual}”."
        if visual != selected_visual else ""
    )
    spec = sheet.get(visual)
    if spec is None:
        return {"answer": "Select a listed visual or section first.", "evidence": "Validation Required", "calculation": "No visual context selected.", "limitation": "The assistant will not guess which visual you mean.", "resolved_visual": visual, "selection_note": selection_note}
    q = re.sub(r"[^a-z0-9]+", " ", str(question).lower()).strip()
    if not q:
        return {"answer": "Enter a question about the selected visual.", "evidence": "Validation Required", "calculation": "No calculation run.", "limitation": "Try asking what the visual means, what to focus on, what its callouts mean, or what may improve the result.", "resolved_visual": visual, "selection_note": selection_note}
    kpi_performance = _kpi_card_performance_interpretation(visual, question, daily, encounters)
    ambiguity = None if kpi_performance else _ambiguous_visual_question(visual, spec, question)
    if ambiguity:
        ambiguity.update({"resolved_visual": visual, "selection_note": selection_note})
        return ambiguity
    signal = _current_signal(spec, daily, encounters)
    domain_aggregate = _domain_aggregate_interpretation(visual, question, daily, encounters)
    domain_action = _domain_action_interpretation(visual, question, daily, encounters)
    named_domain = _named_domain_interpretation(visual, question, daily, encounters)
    metric_ranking = _metric_group_ranking_interpretation(visual, spec, question, daily, encounters)
    visual_comparison = _visual_comparison_interpretation(visual, spec, question, daily, encounters)
    entity_position = _entity_position_interpretation(visual, spec, question, daily, encounters)
    funnel_stage = _funnel_stage_interpretation(visual, question, daily, encounters)
    monthly_margin_flow = _monthly_margin_flow_interpretation(visual, question, daily, encounters)
    documented_content = _documented_content_interpretation(visual, question)
    explicit_metrics = [metric for metric in _metrics_in(question) if metric.key in spec.get("metrics", ())]
    dynamic = (
        kpi_performance or monthly_margin_flow or domain_aggregate or domain_action or named_domain or metric_ranking or funnel_stage or visual_comparison or entity_position or documented_content or _metric_detail_interpretation(explicit_metrics[0], daily, encounters)
        if explicit_metrics else
        kpi_performance or monthly_margin_flow or domain_aggregate or domain_action or named_domain or metric_ranking or funnel_stage or visual_comparison or entity_position or documented_content or _dynamic_visual_interpretation(page, visual, daily, encounters)
    )
    tokens = flexible_tokens(question)
    wants_callout = bool(tokens & {"callout", "warning", "caution", "note", "annotation", "highlight"})
    wants_calculation = bool(tokens & {"calculate", "metric", "axis", "legend", "measure", "method", "formula", "derive"}) or "get this number" in q or "come up with" in q
    wants_limits = bool(tokens & {"limit", "trust", "reliable", "confidence", "bias", "missing", "caveat"})
    improvement_word = bool(tokens & {"improve", "better", "fix", "action", "recommend", "respond", "change"})
    forward_language = bool(tokens & {"how", "can", "could", "should", "do", "action", "next", "recommend", "fix"})
    wants_positive = bool(tokens & {"good", "positive", "better", "improve", "win", "strength", "celebrate", "improved", "well"}) and not forward_language
    wants_negative = bool(tokens & {"bad", "negative", "worse", "decline", "concern", "risk", "problem", "weakness", "issue", "downside", "redflag", "flag"}) or {"not", "working"}.issubset(tokens)
    asks_next_step = "next" in tokens and bool(tokens & {"what", "should", "do", "how"})
    wants_action = forward_language and (improvement_word or wants_negative or asks_next_step)
    wants_focus = bool(tokens & {"focus", "important", "interest", "attention", "priority", "matter", "why", "care", "outlier"}) or {"stand", "out"}.issubset(tokens)
    wants_meaning = bool(tokens & {"tell", "mean", "explain", "summarize", "show", "happen", "understand", "interpret", "read"})
    if kpi_performance or domain_aggregate or domain_action or named_domain or metric_ranking or visual_comparison or entity_position or funnel_stage or monthly_margin_flow:
        wants_meaning = True
        wants_focus = False
    if monthly_margin_flow:
        # A month ranking is distinct from a recent movement summary.
        wants_positive = False
        wants_negative = False
    if kpi_performance:
        wants_positive = False
        wants_negative = False
        wants_action = False
    if domain_action:
        wants_action = False
    # A broad what/how/why question about a selected visual should receive a
    # useful contextual explanation even without a memorized phrase.
    if not any((wants_callout, wants_calculation, wants_limits, wants_action, wants_positive, wants_negative, wants_focus, wants_meaning)) and tokens & {"what", "how", "why"}:
        wants_meaning = True
    sections = []
    answer_display = dynamic.get("display") if dynamic else None
    if wants_meaning:
        if dynamic:
            sections.append(dynamic["answer"])
        else:
            sections.append("What it shows: " + spec["purpose"] + (f" Current filtered signals: {signal}." if signal else ""))
    if wants_focus:
        sections.append("What to focus on: " + spec["focus"] + " This matters because it identifies the strongest validation or improvement priority represented by this visual.")
    if wants_positive:
        positive = _visual_movements(spec, daily, encounters, "positive")
        sections.append("Positive movement: " + (positive if positive else "No safely mapped positive movement is available for this visual under the current filtered 30-day comparison. Use the visual's documented focus and validate its underlying groups before calling an output positive."))
    if wants_negative:
        negative = _visual_movements(spec, daily, encounters, "negative")
        sections.append("Negative movement: " + (negative if negative else "No safely mapped negative movement is available for this visual under the current filtered 30-day comparison. This does not prove that every underlying subgroup improved."))
    if wants_action:
        documented_action = _documented_improvement(visual, question)
        action_metrics = explicit_metrics or ([ _weakest_visual_metric(spec, daily, encounters) ] if not documented_action else [])
        tailored_actions = [result for metric in action_metrics if metric for result in [_metric_improvement(metric, daily, encounters, visual)] if result]
        if len(tailored_actions) > 1:
            answer_display = {
                "title": " and ".join(result["display"]["title"] for result in tailored_actions) + " — Improvement Path",
                "filters": _selected_filter_summary(daily, encounters),
                "answer": "Each named measure has its own current result, validation need, accountable executive, and improvement pathway.",
                "what_matters": [result["display"]["answer"] for result in tailored_actions] + [item for result in tailored_actions for item in result["display"].get("what_matters", [])],
                "actions": [f"{result['display']['title']}: {action}" for result in tailored_actions for action in result["display"].get("actions", [])],
                "why": "The response treats every named measure separately so unlike units, thresholds, and operating pathways are not blended into one unsupported conclusion.",
                "action_heading": "What Leadership Can Do Next",
                "limitation": "These are validation-first operating options, not proven causal remedies or patient-care recommendations.",
            }
            sections.append("Possible improvement response: " + " ".join(result["text"] for result in tailored_actions))
        else:
            tailored_action = tailored_actions[0] if tailored_actions else None
            if tailored_action:
                answer_display = tailored_action["display"]
            sections.append("Possible improvement response: " + (tailored_action["text"] if tailored_action else documented_action or spec["action"]))
    if wants_callout:
        sections.append("Callout: " + spec["callout"])
    if wants_calculation:
        sections.append("How it is calculated or encoded: " + spec["calculation"])
    if wants_limits:
        sections.append("Limitation: " + spec["limits"])
    if not sections:
        keywords = extracted_keywords(question)
        suggestions = closest_suggestions(question, VISUAL_SUGGESTIONS)
        keyword_text = ", ".join(keywords) if keywords else "no clear supported keywords"
        answer = f"I’m not certain which visual question you intended. I extracted: {keyword_text}. Select the closest safe match below rather than having the dashboard guess."
        return {
            "answer": answer, "evidence": "Validation Required",
            "calculation": "No supported visual-question intent was identified.",
            "limitation": "Suggestions are similarity-ranked from a safe allowlist; review the wording before running one.",
            "suggestions": suggestions, "keywords": keywords,
            "resolved_visual": visual, "selection_note": selection_note,
        }
    answer = " ".join(sections)
    return {
        "answer": answer,
        "evidence": dynamic["evidence"] if dynamic else ("Synthetic Result" if signal else "Validation Required — Visual Documentation"),
        "calculation": dynamic["calculation"] if dynamic else spec["calculation"],
        "limitation": ((dynamic.get("limitation") or spec["limits"]) if dynamic else spec["limits"]) + " The answer is descriptive and does not establish cause or support patient-care decisions.",
        "suggestions": [], "keywords": extracted_keywords(question),
        "resolved_visual": visual, "selection_note": selection_note,
        "display": answer_display,
    }
