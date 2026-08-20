"""Deterministic contextual help for each dashboard visual and section."""

import re
from difflib import SequenceMatcher

import pandas as pd

from language_utils import closest_suggestions, extracted_keywords, flexible_tokens, normalized_text
from qa_engine import METRICS, _format, _value


def _v(purpose, focus, action, callout, limits, metrics=(), calculation="See the visual axes, legend, and supporting table."):
    return {
        "purpose": purpose, "focus": focus, "action": action, "callout": callout,
        "limits": limits, "metrics": metrics, "calculation": calculation,
    }


VISUALS = {
    "1": {
        "Executive KPI Cards": _v("Summarizes current system performance, capacity, workforce, experience, and evidence readiness.", "Start with the lowest-performing domain and whether its movement is material versus the comparable period.", "Validate the underlying denominator and operating context, assign an accountable owner, and use a time-bounded improvement cycle.", "Scores and targets are illustrative portfolio constructs; stable displayed deltas are not described as directional changes.", "The Executive Health Score is not a validated clinical score or forecast.", ("margin", "bed_utilization", "boarding", "readmission", "rn_vacancy", "experience")),
        "Executive Health Score by Domain": _v("Compares Quality & Safety, Patient Flow, Financial, Workforce, Access, and Patient Experience on a 0–100 modeled portfolio scale. A higher bar means the selected synthetic results are closer to the dashboard's illustrative target thresholds; a lower bar means a larger modeled performance gap to validate.", "The shortest bar is the largest modeled performance gap and deserves validation first.", "Review the component metrics behind the weakest domain before selecting an intervention.", "Quality, flow, finance, workforce, access, and experience use transparent illustrative weights and thresholds.", "Bars compare a modeled composite, not certified external benchmarks.", calculation="Weighted higher/lower-is-better component scores on a 0–100 illustrative scale."),
        "Margin and Flow Pressure by Month": _v("Shows monthly operating contribution beside an indexed ED-boarding pressure series.", "Look for months where contribution weakens while boarding pressure rises; treat this as a co-movement signal.", "Validate throughput timestamps, discharge constraints, staffing, volume, and payer mix before acting.", "Boarding is multiplied only to share a readable axis with dollars; it is not a dollar value.", "The dual-scale view does not establish that boarding caused margin movement.", ("margin", "boarding")),
        "Executive Priority Queue": _v("Ranks hospital-domain priorities by modeled severity and then modeled exposure.", "Priority #1 is the first validation target; review its owner, severity components, and exposure assumptions.", "Assign the listed executive owner, validate inputs, and move an approved response into a PDSA cycle.", "The orange #1 treatment identifies the highest current modeled portfolio priority.", "The queue is not a clinical risk score or validated forecast.", calculation="Severity descending; modeled exposure descending as tie-breaker."),
    },
    "2": {
        "Capacity KPI Cards": _v("Summarizes licensed, staffed, occupied, and available bed capacity plus ED and discharge pressure.", "Focus on high utilization paired with boarding, pending admissions, or discharge delay.", "Validate bed-ready and discharge timestamps, staffing constraints, and unit-level demand before changing targets.", "Available staffed beds are staffed beds minus census, averaged across the selected period.", "System averages can hide unit and shift variation.", ("bed_utilization", "available_beds", "boarding", "ed_provider")),
        "Occupancy and Boarding by Hospital": _v("Compares staffed-bed occupancy across hospitals while color encodes boarding hours.", "Hospitals that combine high occupancy with darker/high boarding values warrant throughput review.", "Examine discharge reliability, staffed capacity, pending admissions, and demand by day and unit.", "The visual identifies concurrent pressure; it does not prove one measure causes the other.", "Hospital averages hide within-hospital variation.", ("bed_utilization", "boarding")),
        "Discharge Delay and ED Boarding": _v("Plots discharge-order-to-exit delay against ED boarding, sized by ED arrivals.", "Upper-right, large-volume points indicate the most consequential joint flow pressure.", "Validate timestamps and test discharge coordination, transport, pharmacy, and post-acute placement constraints.", "Bubble size represents demand, so small and large points should not be interpreted equally.", "Association is descriptive and non-causal.", ("boarding",)),
        "Patient-Flow Operating Matrix": _v("Provides hospital-level demand, capacity, discharge, and delay values behind the flow visuals.", "Use it to confirm which hospital and metric drive the aggregate signal.", "Drill into daily and unit-level operations before assigning accountability.", "This table is the auditable supporting layer for the page.", "It contains synthetic hospital averages, not encounter-level timestamp validation.", ("boarding", "available_beds", "bed_utilization")),
        "System Patient-Flow Funnel": _v("Illustrates how arrivals move through modeled admission and placement stages.", "The largest drop or queue indicates where modeled flow loss is concentrated.", "Validate real encounter timestamps before using the funnel to set operational targets.", "The placement split is a scenario derived from average boarding pressure.", "It is not an observed patient-level transition funnel.", ("boarding",)),
    },
    "3": {"Deterioration-to-Harm Reliability Matrix": _v("Compares deterioration and harm rates by hospital and service line; bubble size is encounter volume.", "Prioritize large bubbles in the upper-right after confirming event definitions.", "Review rescue protocols, escalation reliability, staffing, and documentation with clinical governance.", "The chart is a surveillance-prioritization tool only.", "It cannot guide bedside care or prove causality.")},
    "4": {"Harm Signal by Service Line": _v("Ranks service lines by synthetic harm rate while color reflects total cost.", "Consider harm rate together with encounter volume; a high rate from a small denominator can be unstable.", "Verify event definitions and denominators, then select an accountable quality-improvement pathway.", "Modeled financial exposure is illustrative and is not booked loss.", "Synthetic harm signals are not certified patient-safety measures.")},
    "5": {"Readmission Risk by Service Line and Discharge Barrier": _v("Shows readmission rate and cohort size for service-line/barrier groups.", "Large, high-rate groups are the strongest transition-reliability screening signals.", "Validate the cohort, then test confirmed follow-up, transition nursing, transportation, medication, or caregiver support.", "Observed group differences are not automatically equity disparities or causal effects.", "The chart is synthetic and not an individual risk model.", ("readmission",))},
    "6": {"Staffing Intensity Versus Composite Outcome Pressure": _v("Plots hours per patient day against a composite outcome-pressure index by hospital.", "Look for persistent clusters or outliers, but do not interpret the fitted line as a staffing effect.", "Validate acuity, skill mix, vacancies, agency use, unit assignments, and workflow before redesigning staffing.", "The trendline is descriptive only; staffing should never be reduced from this chart alone.", "The outcome index is illustrative and the relationship is confounded.", ("rn_vacancy", "agency_share"))},
    "7": {"Access Leakage Signals by Hospital": _v("Compares hospital LWBS and specialty-wait signals.", "Focus on the hospital with the strongest combined wait, LWBS, and boarding pressure after checking demand volume.", "Test ED fast track, demand-capacity matching, centralized scheduling, referral navigation, and cancellation recovery.", "Recoverable value is an illustrative gross-revenue scenario.", "The measures use different units and should not be compared by raw bar height alone.", ("lwbs", "specialty_wait", "boarding"))},
    "8": {"Procedural Volume and Utilization by Day": _v("Compares OR case volume and utilization by hospital and day of week.", "Find recurring low-utilization/high-demand mismatches and confirm whether they reflect block allocation or constraints.", "Review first-case starts, turnover, cancellations, block release, surgeon availability, and staffing before adding rooms.", "Unused-capacity value is illustrative and not fully recoverable.", "The data do not include surgeon availability or block ownership.", ("or_utilization",))},
    "9": {"Outcomes by Social Vulnerability Quartile": _v("Compares readmission and follow-up across synthetic SVI quartiles.", "Look for consistent gaps while checking cohort size and whether results persist by service line and hospital.", "Validate access barriers and test navigation, transportation, and language support without using SVI to restrict care.", "Group-level differences are screening signals, not proof of inequity or individual risk.", "No patient-level geocoding is included.", ("readmission",))},
    "10": {"Contribution by Service Line and Payer": _v("Shows encounter contribution by service line and payer.", "Start with negative or weak-contribution combinations that also have meaningful volume.", "Validate contracts and adjudication, then address authorization, documentation, coding, and denial workflow.", "Contribution is revenue minus cost in the synthetic encounter cohort.", "Contract terms and final claims outcomes are not included.", ("margin", "denial_rate"))},
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
        "Statistical Process Control Chart": _v("Plots the selected monthly quality measure against a center line and three-sigma analytic limits.", "Investigate points beyond limits and non-random patterns, but first confirm denominator and definition stability.", "Use a PDSA cycle to test a process change and monitor whether the signal sustains.", "A point beyond a limit is an investigation signal, not proof of failure.", "The simple limits do not adjust for seasonality, case mix, or changing denominators."),
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


def _executive_domain_interpretation(daily, encounters):
    if daily.empty:
        return None
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
    scores = {
        "Quality & Safety": sum([
            _lower_score(metrics["readmission"], .12, .18),
            _lower_score(metrics["mortality"], .020, .035),
            _lower_score(metrics["harm"], .020, .060),
        ]) / 3,
        "Patient Flow": sum([
            _lower_score(metrics["boarding"], 4.0, 10.0),
            _lower_score(metrics["occupancy"], .85, .98),
            _lower_score(metrics["discharge_delay"], 2.0, 5.0),
        ]) / 3,
        "Financial": sum([
            _higher_score(metrics["margin"], .05, -.02),
            _lower_score(metrics["denial_rate"], .040, .075),
        ]) / 2,
        "Workforce": sum([
            _lower_score(metrics["vacancy"], .08, .18),
            _lower_score(metrics["overtime_share"], .07, .16),
            _lower_score(metrics["agency_share"], .04, .10),
        ]) / 3,
        "Access": sum([
            _lower_score(metrics["lwbs"], .02, .07),
            _lower_score(metrics["wait"], 10.0, 24.0),
        ]) / 2,
        "Patient Experience": _higher_score(metrics["experience"], .82, .68),
    }
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


def _dynamic_visual_interpretation(page, visual, daily, encounters):
    page_number = str(page).split(" ", 1)[0]
    if page_number == "1" and visual == "Executive Health Score by Domain":
        return _executive_domain_interpretation(daily, encounters)
    return None


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
    signal = _current_signal(spec, daily, encounters)
    dynamic = _dynamic_visual_interpretation(page, visual, daily, encounters)
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
    # A broad what/how/why question about a selected visual should receive a
    # useful contextual explanation even without a memorized phrase.
    if not any((wants_callout, wants_calculation, wants_limits, wants_action, wants_positive, wants_negative, wants_focus, wants_meaning)) and tokens & {"what", "how", "why"}:
        wants_meaning = True
    sections = []
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
        sections.append("Possible improvement response: " + spec["action"])
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
        "limitation": spec["limits"] + " The answer is descriptive and does not establish cause or support patient-care decisions.",
        "suggestions": [], "keywords": extracted_keywords(question),
        "resolved_visual": visual, "selection_note": selection_note,
    }
