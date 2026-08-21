from pathlib import Path

import pandas as pd

from qa_engine import METRICS
from visual_qa import DOCUMENTED_CONTENT, DOCUMENTED_IMPROVEMENTS, VISUALS, answer_visual_question, resolve_visual, visual_options


ROOT = Path(__file__).resolve().parent
daily = pd.read_csv(ROOT / "data/daily_operations.csv.gz", parse_dates=["date"])
encounters = pd.read_csv(ROOT / "data/synthetic_encounters.csv.gz", parse_dates=["admit_date", "discharge_date"])


def test_every_analysis_sheet_has_visual_context():
    assert set(VISUALS) == {str(number) for number in range(1, 15)}
    for number in range(1, 15):
        assert visual_options(f"{number} — Sheet")


def test_every_visual_answers_core_contextual_questions():
    questions = [
        "What is this visual telling me?",
        "What happened on this visual?",
        "What should I be most interested in and why?",
        "What can I do to improve the output?",
        "What are the callouts on this visual?",
        "How is this calculated?",
        "What are the limitations?",
    ]
    for page_number, visuals in VISUALS.items():
        for visual in visuals:
            for question in questions:
                result = answer_visual_question(page_number, visual, question, daily, encounters)
                assert not result["answer"].startswith("I can explain"), (page_number, visual, question)
                assert result["calculation"]
                assert "does not establish cause" in result["limitation"]


def test_deterioration_matrix_explain_output_covers_every_available_hospital():
    result = answer_visual_question(
        "3 — Deterioration", "Deterioration-to-Harm Reliability Matrix",
        "explain the output", daily, encounters,
    )
    assert result.get("display")
    assert "farther right means" in result["answer"]
    assert "farther up means" in result["answer"]
    assert "larger bubbles mean more encounters" in result["answer"]
    for hospital in sorted(encounters.hospital.unique()):
        assert f"{hospital}: Deterioration" in result["answer"]
        assert f"{hospital.replace('GulfStar ', '')}:" in result["answer"]
    assert "highest combined displayed pressure" in result["answer"]
    assert result["display"]["action_heading"] == "What Leadership Should Validate"
    assert "Current filtered signals:" not in result["answer"]


def test_unsupported_visual_question_refuses_to_guess():
    visual = visual_options("1 — CEO")[0]
    result = answer_visual_question("1 — CEO", visual, "Predict next year's exact result", daily, encounters)
    assert result["evidence"] == "Validation Required"
    assert "No supported visual-question intent" in result["calculation"]
    assert len(result["suggestions"]) == 3
    assert result["keywords"]


def test_combined_visual_question_answers_each_requested_part():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "What is this visual telling me, what should I focus on, and what can I do to improve it?",
        daily, encounters,
    )
    assert "What it shows:" in result["answer"]
    assert "What to focus on:" in result["answer"]
    assert "Possible improvement response:" in result["answer"]


def test_human_variance_typos_and_paraphrases_are_understood():
    visual = "Executive KPI Cards"
    expectations = {
        "wht is this vizual tryin to tel me": "What it shows:",
        "anything gud or positve in these outputs": "Positive movement:",
        "where are we doing well": "Positive movement:",
        "what is bad or negatve here": "Negative movement:",
        "what is not working": "Negative movement:",
        "any red flags or worrying results": "Negative movement:",
        "how can we make this better": "Possible improvement response:",
        "what could be improvde": "Possible improvement response:",
        "what should we do next": "Possible improvement response:",
        "why should i care about this": "What to focus on:",
        "what stands out": "What to focus on:",
        "how did you get this number": "How it is calculated or encoded:",
        "can i trust this chart": "Limitation:",
    }
    for question, expected in expectations.items():
        result = answer_visual_question("1 — CEO", visual, question, daily, encounters)
        assert expected in result["answer"], (question, result["answer"])


def test_visual_suggestions_use_extracted_keywords_and_close_intent():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "forecast the exact future chart outcome", daily, encounters,
    )
    assert len(result["suggestions"]) == 3
    assert "visual" in result["keywords"]
    assert any("visual" in suggestion.lower() for suggestion in result["suggestions"])


def test_explicit_visual_name_overrides_stale_dropdown_selection():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what does executive health score by domain mean", daily, encounters,
    )
    assert result["resolved_visual"] == "Executive Health Score by Domain"
    assert "used that visual instead" in result["selection_note"]
    assert "Financial 90; Workforce 90; Patient Flow 86; Quality & Safety 80; Access 77; Patient Experience 63" in result["answer"]
    assert "Patient Experience is lowest at 63" in result["answer"]
    assert "each domain is the unweighted mean of its components" in result["calculation"]
    assert result["evidence"] == "Synthetic Result / Modeled Estimate"


def test_named_access_domain_uses_displayed_domain_not_specialty_wait_component():
    result = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "why is access so low", daily, encounters,
    )
    assert "displayed Access domain score is 77/100" in result["answer"]
    assert "ranked 5 of 6" in result["answer"]
    assert "Left Without Being Seen: 3.4%" in result["answer"]
    assert "Specialty Wait: 12.5 days" in result["answer"]
    assert "unweighted average" in result["answer"]
    assert "mean daily specialty_wait_days; illustrative component score = 82/100" not in result["calculation"]
    assert result["display"]["title"] == "Access Domain - Why It Has This Score"
    assert "component scores average to 76.8, which rounds to 77/100" in result["display"]["why"]
    assert "Patient Experience (63)" in result["display"]["why"]


def test_every_named_executive_domain_has_domain_level_explanation():
    for domain in ("quality and safety", "patient flow", "financial", "workforce", "access", "patient experience"):
        result = answer_visual_question(
            "1 — CEO", "Executive Health Score by Domain",
            f"why is {domain} high or low", daily, encounters,
        )
        assert "domain score is" in result["answer"], (domain, result["answer"])
        assert "component score" in result["answer"], (domain, result["answer"])
        assert result.get("display"), domain


def test_multi_domain_question_answers_every_named_domain_and_compares_them():
    result = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "why is access and patient experience so low", daily, encounters,
    )
    assert "displayed Access domain score is 77/100" in result["answer"]
    assert "displayed Patient Experience domain score is 63/100" in result["answer"]
    assert "Access - Left Without Being Seen: 3.4%" in result["answer"]
    assert "Access - Specialty Wait: 12.5 days" in result["answer"]
    assert "Patient Experience - Patient Experience: 76.8%" in result["answer"]
    assert "Access is 14 points higher than Patient Experience" in result["display"]["why"]
    assert result["display"]["title"] == "Access vs. Patient Experience - Why These Scores Are Low"
    assert "Access = unweighted mean" in result["calculation"]
    assert "Patient Experience = unweighted mean" in result["calculation"]


def test_multi_domain_high_question_has_correct_title_order_and_displayed_ties():
    result = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "why is financial and patient flow so high", daily, encounters,
    )
    assert result["display"]["title"] == "Financial vs. Patient Flow - Why These Scores Are High"
    assert "displayed Financial domain score is 90/100" in result["answer"]
    assert "tied for highest at displayed precision with Workforce" in result["answer"]
    assert "No selected domain scores higher at displayed precision" in result["display"]["why"]
    assert "same displayed score is shared by Workforce (90)" in result["display"]["why"]
    assert "Financial is 4 points higher than Patient Flow" in result["display"]["why"]


def test_generic_this_visual_keeps_dropdown_selection():
    resolved, _ = resolve_visual("1 — CEO", "Executive KPI Cards", "what is this visual telling me")
    assert resolved == "Executive KPI Cards"


def test_named_kpi_inside_visual_gets_granular_data_aware_explanation():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what does Patient Experience: 76.8% mean", daily, encounters,
    )
    assert "Patient Experience of 76.8%" in result["answer"]
    assert "mean synthetic patient-experience composite" in result["answer"]
    assert "5.2 percentage points below the favorable threshold" in result["answer"]
    assert "63/100" in result["answer"]
    assert "Across the selected hospitals" in result["answer"]
    assert "mean synthetic patient_experience composite" in result["calculation"]
    assert result["evidence"] == "Synthetic Result / Modeled Estimate"
    assert "not an official HCAHPS score" in result["limitation"]
    assert "Operating Margin:" not in result["answer"]


def test_other_named_kpi_inside_visual_uses_its_own_definition():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "Can you explain what the RN vacancy number means?", daily, encounters,
    )
    assert "RN Vacancy of" in result["answer"]
    assert "mean synthetic RN vacancy rate" in result["answer"]
    assert "unit-level skill mix" in result["limitation"]


def test_every_mapped_metric_on_every_visual_gets_metric_level_answer():
    by_key = {metric.key: metric for metric in METRICS}
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            for key in spec["metrics"]:
                metric = by_key[key]
                question = f"What does {metric.aliases[0]} mean on this visual?"
                result = answer_visual_question(page, visual, question, daily, encounters)
                assert f"{metric.label} of" in result["answer"], (page, visual, key, result["answer"])
                assert result["calculation"]
                assert result["evidence"] != "Validation Required — Visual Documentation"


def test_every_metric_alias_on_every_visual_resolves_to_the_same_visible_measure():
    by_key = {metric.key: metric for metric in METRICS}
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            for key in spec["metrics"]:
                metric = by_key[key]
                for alias in metric.aliases:
                    result = answer_visual_question(page, visual, f"what does {alias} mean here", daily, encounters)
                    assert metric.label in result["answer"], (page, visual, key, alias, result["answer"])
                    assert result["evidence"] != "Validation Required", (page, visual, alias)


def test_documented_modeled_and_governance_content_is_explained_specifically():
    for visual, entries in DOCUMENTED_CONTENT.items():
        page = next(page for page, visuals in VISUALS.items() if visual in visuals)
        for aliases, expected_answer, expected_calculation, expected_evidence in entries:
            for alias in aliases:
                result = answer_visual_question(page, visual, f"What does {alias} mean?", daily, encounters)
                assert result["answer"].startswith(expected_answer), (visual, alias, result["answer"])
                assert result["calculation"] == expected_calculation
                assert result["evidence"] == expected_evidence
                assert "operational validation" in result["limitation"]


def test_every_visual_title_resolves_with_human_punctuation_variants():
    for page, visuals in VISUALS.items():
        options = list(visuals)
        for visual in options:
            selected = next((item for item in options if item != visual), visual)
            variants = {visual, visual.replace("&", "and"), visual.replace("-", " "), visual.replace(":", "")}
            for variant in variants:
                resolved, _ = resolve_visual(page, selected, f"explain {variant}")
                assert resolved == visual, (page, visual, variant, resolved)


def test_every_visual_has_a_complete_semantic_contract():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            for field in ("purpose", "focus", "action", "callout", "limits", "calculation"):
                assert spec[field].strip(), (page, visual, field)
            assert spec["metrics"] or visual in DOCUMENTED_CONTENT, (page, visual)


def test_er_boarding_improvement_is_metric_filter_and_hospital_aware():
    copd_daily = daily.copy()
    copd_encounters = encounters[encounters.service_line == "COPD"].copy()
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "how can I improve the er boarding", copd_daily, copd_encounters,
    )
    assert "Improvement opportunity — ED Boarding" in result["answer"]
    assert "Scope:" not in result["answer"]
    assert "Strongest pressure:" in result["answer"]
    assert "Staffed-Bed Utilization" in result["answer"]
    assert "Discharge-Order-to-Exit Time" in result["answer"]
    assert "Chief Operating Officer" in result["answer"]
    assert "not to infer cause" in result["answer"]
    assert "Validate the underlying denominator" not in result["answer"]


def test_generic_improvement_question_uses_weakest_mapped_metric():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "what should we do to improve this visual", daily, encounters,
    )
    assert "Improvement opportunity —" in result["answer"]
    assert "Current result:" in result["answer"]
    assert "Leadership response:" in result["answer"]


def test_domain_score_patient_experience_improvement_uses_metric_path():
    result = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "how can I improve patient experience", daily, encounters,
    )
    assert "Patient Experience is 63/100" in result["answer"]
    assert "Chief Experience Officer" in result["answer"]
    assert "Patient Experience — Patient Experience: 76.8%; modeled component score 63/100" in result["answer"]
    assert "Review the component metrics behind the weakest domain" not in result["answer"]
    assert result["display"]["filters"].startswith("All Hospitals • All Service Lines")
    assert len(result["display"]["what_matters"]) == 1
    assert len(result["display"]["actions"]) == 1
    assert all(action[0].isupper() for action in result["display"]["actions"])


def test_every_metric_backed_visual_has_filter_aware_generic_improvement():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            if not spec["metrics"]:
                continue
            result = answer_visual_question(page, visual, "how can we improve this visual", daily, encounters)
            assert "Improvement opportunity —" in result["answer"], (page, visual, result["answer"])
            assert "Current result:" in result["answer"] or "underlying" in result["answer"]
            assert "Leadership response:" in result["answer"]


def test_every_documented_improvement_family_has_specific_action():
    for visual, entries in DOCUMENTED_IMPROVEMENTS.items():
        page = next(page for page, visuals in VISUALS.items() if visual in visuals)
        alias = entries[0][0][0]
        result = answer_visual_question(page, visual, f"how can we improve {alias}", daily, encounters)
        assert entries[0][1] in result["answer"], (visual, alias, result["answer"])
        assert "not a causal or patient-care recommendation" in result["answer"]


def test_named_hospital_low_position_uses_actual_scatter_values():
    result = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding",
        "why is gulfstar north so low?", daily, encounters,
    )
    assert "GulfStar North is lowest on ED Boarding and in the middle on Discharge Order-to-Exit" in result["answer"]
    assert "ED Boarding value is 5.84 hours" in result["answer"]
    assert "Discharge Order-to-Exit: 2.26 hours" in result["answer"]
    assert "Bubble size represents" in result["answer"]
    assert "does not identify the operational cause" in result["answer"]
    assert "Upper-right, large-volume points" not in result["answer"]
    assert result["display"]["action_heading"] == "What Leadership Should Validate"


def test_named_hospital_high_position_uses_actual_scatter_values():
    result = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding",
        "why is gulfstar medical center so high?", daily, encounters,
    )
    assert "GulfStar Medical Center is highest on both plotted measures" in result["answer"]
    assert "ED Boarding value is 5.97 hours" in result["answer"]
    assert "Discharge Order-to-Exit value is 2.30 hours" in result["answer"]
    assert "lowest point" not in result["answer"]
    assert "cannot explain why GulfStar Medical Center's values differ" in result["limitation"]


def test_scatter_positions_are_calculated_for_every_hospital():
    expected = {
        "GulfStar Community": "in the middle on ED Boarding and lowest on Discharge Order-to-Exit",
        "GulfStar Medical Center": "highest on both plotted measures",
        "GulfStar North": "lowest on ED Boarding and in the middle on Discharge Order-to-Exit",
    }
    for hospital, phrase in expected.items():
        result = answer_visual_question(
            "2 — Flow", "Discharge Delay and ED Boarding",
            f"why is {hospital} high or low", daily, encounters,
        )
        assert phrase in result["answer"], (hospital, result["answer"])


def test_relative_outlier_questions_use_current_visual_metrics():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            if not spec["metrics"]:
                continue
            result = answer_visual_question(page, visual, "are there any outliers and why", daily, encounters)
            assert "Relative outlier review:" in result["answer"], (page, visual, result["answer"])
            assert "selected-hospital median" in result["answer"], (page, visual, result["answer"])
            assert "statistically confirmed outlier" in result["limitation"], (page, visual)
            assert result.get("display"), (page, visual)


def test_multi_hospital_comparison_supports_natural_executive_wording():
    result = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding",
        "why is GulfStar Medical Center high but GulfStar North low and Community average", daily, encounters,
    )
    assert "Hospital comparison:" in result["answer"]
    assert "Medical Center: 5.97 hours (highest)" in result["answer"]
    assert "North: 5.84 hours (lowest)" in result["answer"]
    assert "Community: 5.94 hours (middle)" in result["answer"]
    assert "does not label any point a statistically confirmed outlier" in result["limitation"]


def test_hospital_position_questions_are_data_aware_across_metric_visuals():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            if not spec["metrics"]:
                continue
            result = answer_visual_question(page, visual, "why is GulfStar North so low", daily, encounters)
            assert "GulfStar North" in result["answer"], (page, visual, result["answer"])
            assert result.get("display"), (page, visual)
            assert "descriptive" in result["limitation"].lower() or "cannot explain" in result["limitation"].lower()


def test_modeled_delayed_placements_question_uses_actual_funnel_math():
    result = answer_visual_question(
        "2 — Flow", "System Patient-Flow Funnel",
        "why is modeled delayed placements so low", daily, encounters,
    )
    assert "21,020, or 24.0% of admissions" in result["answer"]
    assert "66,575 (76.0% of admissions)" in result["answer"]
    assert "average ED Boarding of 5.9 hours" in result["answer"]
    assert "Discharges (86,512) are a separate" in result["answer"]
    assert "The largest drop or queue" not in result["answer"]
    assert result["evidence"] == "Modeled Estimate"
    assert result["display"]["action_heading"] == "What Leadership Should Validate"


def test_ed_arrivals_high_question_uses_actual_funnel_denominator():
    result = answer_visual_question(
        "2 — Flow", "System Patient-Flow Funnel",
        "why is ed arrivals so high", daily, encounters,
    )
    assert "ED Arrivals is 173,578" in result["answer"]
    assert "Admissions includes only the portion admitted" in result["answer"]
    assert "87,595, or 50.5% of ED Arrivals" in result["answer"]
    assert "85,983 arrivals were not counted as inpatient admissions" in result["answer"]
    assert "The largest drop or queue" not in result["answer"]
    assert result["evidence"] == "Synthetic Result"
    assert result["display"]["title"] == "ED Arrivals"


def test_every_funnel_stage_has_stage_level_interpretation():
    questions = {
        "why are ed arrivals high": "ED Arrivals",
        "why are admissions low": "Admissions",
        "explain bed placement within portfolio target": "Bed Placement Within Portfolio Target",
        "why are modeled delayed placements low": "Modeled Delayed Placements",
        "why are discharges high": "Discharges",
    }
    for question, title in questions.items():
        result = answer_visual_question("2 — Flow", "System Patient-Flow Funnel", question, daily, encounters)
        assert result.get("display"), question
        assert result["display"]["title"] == title, (question, result["answer"])


def test_best_month_requests_clarification_instead_of_guessing():
    result = answer_visual_question(
        "1 — CEO", "Margin and Flow Pressure by Month",
        "what is my best month", daily, encounters,
    )
    assert "Choose the outcome" in result["answer"]
    assert len(result["suggestions"]) == 3
    assert "highest operating contribution" in result["suggestions"][0].lower()
    assert "lowest ed boarding" in result["suggestions"][1].lower()
    assert "best balance" in result["suggestions"][2].lower()
    assert result["evidence"] == "Validation Required — Clarification"


def test_selected_month_interpretations_run_the_requested_calculation():
    contribution = answer_visual_question(
        "1 — CEO", "Margin and Flow Pressure by Month",
        "Which month had the highest operating contribution?", daily, encounters,
    )
    assert "March 2025 had the highest Operating Contribution" in contribution["answer"]
    assert "$8,837,052" in contribution["answer"]
    assert contribution["display"]["title"] == "Highest Operating Contribution Month"

    boarding = answer_visual_question(
        "1 — CEO", "Margin and Flow Pressure by Month",
        "Which month had the lowest ED boarding?", daily, encounters,
    )
    assert "July 2026 had the lowest ED Boarding" in boarding["answer"]
    assert "5.67 hours" in boarding["answer"]
    assert boarding["display"]["title"] == "Lowest ED Boarding Month"

    balanced = answer_visual_question(
        "1 — CEO", "Margin and Flow Pressure by Month",
        "Which month had the best balance of operating contribution and ED boarding?", daily, encounters,
    )
    assert "January 2025 is the best complete month" in balanced["answer"]
    assert "August 2026 (7 days)" in balanced["answer"]
    assert balanced["display"]["title"] == "Best Balanced Month - Margin and Flow"
    assert "equal-weight" in balanced["display"]["why"]


def test_domain_rankings_preserve_ties_and_report_lowest():
    highest = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain", "What is my highest domain?", daily, encounters,
    )
    assert highest["display"]["title"] == "Highest Domain Score"
    assert "Financial and Workforce are tied for highest at 90/100" in highest["answer"]

    lowest = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain", "What is my lowest domain?", daily, encounters,
    )
    assert lowest["display"]["title"] == "Lowest Domain Score"
    assert "Patient Experience is lowest at 63/100" in lowest["answer"]


def test_domain_averages_support_all_or_any_number_of_named_domains():
    all_domains = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain", "What is my average score across all domains?", daily, encounters,
    )
    assert "average across all six domains is 81.0/100" in all_domains["answer"]

    two = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain", "What is the average of Access and Patient Experience?", daily, encounters,
    )
    assert "average across the named domains is 70.0/100" in two["answer"]
    assert "Access: 77/100" in two["answer"] and "Patient Experience: 63/100" in two["answer"]

    three = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "What is the average of Access, Patient Experience, and Patient Flow?", daily, encounters,
    )
    assert "average across the named domains is 75.4/100" in three["answer"]
    assert "average of the whole-number scores displayed on the chart is 75.3/100" in three["answer"]


def test_every_metric_backed_visual_supports_an_explicit_hospital_ranking():
    for page, visuals in VISUALS.items():
        for visual, spec in visuals.items():
            metrics = [next((metric for metric in METRICS if metric.key == key), None) for key in spec.get("metrics", ())]
            metric = next((item for item in metrics if item is not None), None)
            if metric is None:
                continue
            result = answer_visual_question(
                f"{page} — Sheet", visual, f"Which hospital has the highest {metric.label}?", daily, encounters,
            )
            assert not result.get("suggestions"), (page, visual, metric.label, result)
            assert result.get("display"), (page, visual, metric.label, result)
            assert metric.label in result["answer"], (page, visual, metric.label, result["answer"])


def test_metric_rankings_support_visual_group_dimensions_and_named_subsets():
    service = answer_visual_question(
        "5 — Readmission", "Readmission Risk by Service Line and Discharge Barrier",
        "Which service line has the highest readmission rate?", daily, encounters,
    )
    assert "among the service lines" in service["answer"]
    assert "30-Day Readmission Rate" in service["answer"]

    named_hospitals = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding",
        "What is the average ED boarding for GulfStar Community and GulfStar North?", daily, encounters,
    )
    assert "average ED Boarding across the named hospitals" in named_hospitals["answer"]
    assert "GulfStar Community" in named_hospitals["answer"] and "GulfStar North" in named_hospitals["answer"]
    assert "GulfStar Medical Center" not in named_hospitals["answer"]


def test_multi_measure_visual_clarifies_an_unnamed_ranking_dimension():
    result = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding", "Which is highest?", daily, encounters,
    )
    assert result["evidence"] == "Validation Required — Clarification"
    assert "multiple measures" in result["answer"]
    assert len(result["suggestions"]) >= 2
    assert any("ED Boarding" in suggestion for suggestion in result["suggestions"])
    assert any("Discharge" in suggestion for suggestion in result["suggestions"])


def test_multi_domain_driver_improvement_comparison_and_target_gap_questions():
    improve = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "How can I improve Access and Patient Experience?", daily, encounters,
    )
    assert "Access is 77/100" in improve["answer"]
    assert "Patient Experience is 63/100" in improve["answer"]
    assert "Chief Operating Officer" in improve["answer"]
    assert "Chief Experience Officer" in improve["answer"]

    cause = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "What caused Access and Patient Experience to be so low?", daily, encounters,
    )
    assert "mathematically explain the displayed result" in cause["answer"]
    assert "not a proven operational cause" in cause["answer"]

    comparison = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "Why is Access lower than Financial?", daily, encounters,
    )
    assert "Access domain score is 77/100" in comparison["answer"]
    assert "Financial domain score is 90/100" in comparison["answer"]

    target = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "How can I get Access as high as Financial?", daily, encounters,
    )
    assert "Access is 77/100, 13 points below" in target["answer"]
    assert any(action.startswith("Access:") for action in target["display"]["actions"])
    assert not any(action.startswith("Financial:") for action in target["display"]["actions"])


def test_multi_metric_improvement_uses_each_named_measure_separately():
    result = answer_visual_question(
        "2 — Flow", "Discharge Delay and ED Boarding",
        "How can I improve ED boarding and discharge delay?", daily, encounters,
    )
    assert "Improvement opportunity — ED Boarding" in result["answer"]
    assert "Improvement opportunity — Discharge-Order-to-Exit Time" in result["answer"]
    assert "units, thresholds, and operating pathways are not blended" in result["display"]["why"]


def test_named_domain_requests_are_not_limited_to_three_items():
    four = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "What is the average of Quality and Safety, Patient Flow, Access, and Patient Experience?", daily, encounters,
    )
    for domain in ("Quality & Safety", "Patient Flow", "Access", "Patient Experience"):
        assert f"{domain}:" in four["answer"]
    assert "average across the named domains" in four["answer"]

    six = answer_visual_question(
        "1 — CEO", "Executive Health Score by Domain",
        "How can I improve Quality and Safety, Patient Flow, Financial, Workforce, Access, and Patient Experience?", daily, encounters,
    )
    for domain in ("Quality & Safety", "Patient Flow", "Financial", "Workforce", "Access", "Patient Experience"):
        assert f"{domain} is" in six["answer"]
        assert any(action.startswith(f"{domain}:") for action in six["display"]["actions"])


def test_multi_measure_improvement_is_not_limited_to_three_items():
    result = answer_visual_question(
        "1 — CEO", "Executive KPI Cards",
        "How can I improve Operating Margin, ED Boarding, RN Vacancy, and Patient Experience?", daily, encounters,
    )
    for metric in ("Operating Margin", "ED Boarding", "RN Vacancy", "Patient Experience"):
        assert f"Improvement opportunity — {metric}" in result["answer"]
        assert metric in result["display"]["title"]
